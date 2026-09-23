"""Verify migration, rollback and resume against a private PostgreSQL fixture."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import psycopg2
import sqlalchemy as sa

from alembic import migration as alembic_migration
from alembic import operations as alembic_operations

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.lending_club import SOURCE_TO_RAW, load_csv  # noqa: E402

PG = Path("/opt/homebrew/opt/postgresql@16/bin")


def main() -> int:
    """Run real database boundary checks and stop the isolated server.

    Returns:
        Zero only when every check and cluster shutdown succeeds.
    """
    work = Path(tempfile.mkdtemp(prefix="creditlens-ingestion-test-", dir="/private/tmp"))
    socket = work / "socket"
    socket.mkdir(mode=0o700)
    report: dict[str, object] = {"workspace": str(work), "checks": [], "status": "running"}
    checks: list[str] = []
    connection = None
    engine = None

    def run(name: str, args: list[str]) -> None:
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
        (work / f"{name}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect {work}")

    try:
        run(
            "init",
            [
                str(PG / "initdb"),
                "-D",
                str(work / "pgdata"),
                "-U",
                "creditlens_m0",
                "--auth=trust",
                "--locale=C",
                "--encoding=UTF8",
            ],
        )
        run(
            "start",
            [
                str(PG / "pg_ctl"),
                "-D",
                str(work / "pgdata"),
                "-l",
                str(work / "pg.log"),
                "-o",
                f"-k {socket} -p 55439 -c listen_addresses='' -c shared_buffers=32MB",
                "-w",
                "start",
            ],
        )
        run(
            "createdb",
            [
                str(PG / "createdb"),
                "-h",
                str(socket),
                "-p",
                "55439",
                "-U",
                "creditlens_m0",
                "creditlens_m0",
            ],
        )
        connection = psycopg2.connect(
            host=str(socket), port=55439, user="creditlens_m0", dbname="creditlens_m0"
        )
        with connection.cursor() as cursor:
            cursor.execute("SHOW data_directory")
            assert Path(cursor.fetchone()[0]).resolve() == (work / "pgdata").resolve()
            cursor.execute("CREATE SCHEMA raw")
            ddl = (ROOT / "scripts/init_db.sql").read_text()
            ddl = ddl[ddl.index("CREATE TABLE IF NOT EXISTS raw.lc_loans") :]
            assert "loan_status TEXT" in ddl
            cursor.execute(ddl.replace("loan_status TEXT", "loan_status VARCHAR(50)"))
            cursor.execute("CREATE SCHEMA staging")
            staging = (ROOT / "models/staging/lc_loans_clean.sql").read_text()
            staging = staging[staging.index("WITH source AS") :].replace(
                "{{ source('raw', 'lc_loans') }}", "raw.lc_loans"
            )
            cursor.execute("CREATE VIEW staging.lc_loans_clean AS " + staging)
            cursor.execute("SELECT pg_get_viewdef('staging.lc_loans_clean'::regclass, true)")
            original_definition = cursor.fetchone()[0]
        connection.commit()
        normal = dict.fromkeys(SOURCE_TO_RAW)
        normal.update(id=1, loan_amnt=1000, issue_d="Jan-2015", loan_status="Fully Paid")
        long_status = "Does not meet the credit policy. Status:Charged Off"
        long_row = {**normal, "id": 2, "loan_status": long_status}
        footer = dict.fromkeys(SOURCE_TO_RAW)
        csv = work / "fixture.csv"
        pd.DataFrame([normal, long_row, footer]).to_csv(csv, index=False)
        try:
            load_csv(csv, connection, chunksize=3)
        except RuntimeError as exc:
            assert "22001" in str(exc)
        else:
            raise AssertionError("Legacy varchar(50) unexpectedly accepted long status")
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM raw.lc_loans")
            assert cursor.fetchone()[0] == 0
        connection.commit()
        checks.append("legacy_status_fails_and_entire_batch_rolls_back")
        spec = importlib.util.spec_from_file_location(
            "m0_status_migration", ROOT / "migrations/versions/4b7d2a91c608_expand_loan_status.py"
        )
        assert spec and spec.loader
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine(
            sa.URL.create(
                "postgresql+psycopg2",
                username="creditlens_m0",
                database="creditlens_m0",
                query={"host": str(socket), "port": "55439"},
            )
        )
        with engine.begin() as sql_connection:
            sql_connection.exec_driver_sql(
                "CREATE VIEW staging.downstream_fixture AS SELECT * FROM staging.lc_loans_clean"
            )
        try:
            with engine.begin() as sql_connection:
                with alembic_operations.Operations.context(
                    alembic_migration.MigrationContext.configure(sql_connection)
                ):
                    migration.upgrade()
        except sa.exc.DBAPIError as exc:
            assert exc.orig.pgcode == "2BP01"
        else:
            raise AssertionError("Unexpected downstream view was not protected")
        with engine.begin() as sql_connection:
            sql_connection.exec_driver_sql("DROP VIEW staging.downstream_fixture")
            assert (
                sql_connection.exec_driver_sql(
                    "SELECT pg_get_viewdef('staging.lc_loans_clean'::regclass, true)"
                ).scalar_one()
                == original_definition
            )
        checks.append("unknown_downstream_view_blocks_migration_without_cascade")
        with engine.begin() as sql_connection:
            with alembic_operations.Operations.context(
                alembic_migration.MigrationContext.configure(sql_connection)
            ):
                migration.upgrade()
        with engine.connect() as sql_connection:
            updated_definition = sql_connection.exec_driver_sql(
                "SELECT pg_get_viewdef('staging.lc_loans_clean'::regclass, true)"
            ).scalar_one()
            (work / "view-before.sql").write_text(original_definition)
            (work / "view-after.sql").write_text(updated_definition)
            # PostgreSQL redistributes equivalent casts from varchar arrays to text elements.
            casts = r"::(?:character varying|text)(?:\[\])?"
            assert re.sub(casts, "", updated_definition) == re.sub(casts, "", original_definition)
        checks.append("migration_upgrades_legacy_column_and_preserves_actual_dbt_view")
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO raw.lc_loans
                (loan_id, loan_amnt, issue_date, loan_status, loaded_at)
                VALUES (1, 500, '2015-01-01', 'Current', '2020-01-01')""")
        connection.commit()
        first = load_csv(csv, connection, insert_missing=True, chunksize=2)
        assert first.written_rows == 1 and first.skipped_existing == 1
        assert first.excluded_required_fields == 1
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT loan_id, loan_amnt, loan_status, loaded_at "
                "FROM raw.lc_loans ORDER BY loan_id"
            )
            before = cursor.fetchall()
        connection.commit()
        assert before[0][2] == "Current" and before[0][1] == 500
        assert before[1][2] == long_status
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT loan_status, is_default FROM staging.lc_loans_clean WHERE loan_id=2"
            )
            assert cursor.fetchone() == (long_status, None)
        connection.commit()
        checks.append("resume_preserves_existing_values_and_full_long_status")
        second = load_csv(csv, connection, insert_missing=True, chunksize=2)
        assert second.written_rows == 0 and second.skipped_existing == 2
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT loan_id, loan_amnt, loan_status, loaded_at "
                "FROM raw.lc_loans ORDER BY loan_id"
            )
            assert cursor.fetchall() == before
        connection.commit()
        checks.append("repeated_resume_is_noop_including_loaded_at")
        update = load_csv(csv, connection, chunksize=2)
        assert update.written_rows == 1 and update.unchanged_or_conflicted == 1
        repeated = load_csv(csv, connection, chunksize=2)
        assert repeated.written_rows == 0 and repeated.unchanged_or_conflicted == 2
        checks.append("default_upsert_updates_changed_outcomes_only")
        try:
            with engine.begin() as sql_connection:
                with alembic_operations.Operations.context(
                    alembic_migration.MigrationContext.configure(sql_connection)
                ):
                    migration.downgrade()
        except RuntimeError as exc:
            assert "exceed 50" in str(exc)
        else:
            raise AssertionError("Unsafe downgrade was not rejected")
        checks.append("downgrade_refuses_long_values")
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM raw.lc_loans WHERE loan_id = 2")
        connection.commit()
        with engine.begin() as sql_connection:
            with alembic_operations.Operations.context(
                alembic_migration.MigrationContext.configure(sql_connection)
            ):
                migration.downgrade()
        with connection.cursor() as cursor:
            cursor.execute("""SELECT character_maximum_length FROM information_schema.columns
                WHERE table_schema='raw' AND table_name='lc_loans' AND column_name='loan_status'""")
            assert cursor.fetchone()[0] == 50
        connection.commit()
        checks.append("safe_downgrade_restores_old_bound")
        report.update(status="passed", first=asdict(first), second=asdict(second))
    except (
        OSError,
        ValueError,
        RuntimeError,
        AssertionError,
        psycopg2.Error,
        sa.exc.SQLAlchemyError,
        subprocess.SubprocessError,
    ) as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        if connection is not None:
            connection.close()
        if engine is not None:
            engine.dispose()
        if (work / "pgdata/postmaster.pid").exists():
            try:
                run(
                    "stop",
                    [str(PG / "pg_ctl"), "-D", str(work / "pgdata"), "-m", "fast", "-w", "stop"],
                )
                report["cluster_stopped"] = True
            except (OSError, RuntimeError, subprocess.SubprocessError):
                report.update(status="failed", cluster_stopped=False)
        report["checks"] = checks
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
