"""Verify mart recovery and the label contract in a private PostgreSQL cluster.

Run from the repository: .venv/bin/python scripts/verify_m0_dbt.py
Defaults to PostgreSQL 16; --pg-bin selects another installed PostgreSQL version.
Requires the project's dbt installation.
Never connects to the development database or loads the project's credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
PG_BIN = Path("/opt/homebrew/opt/postgresql@16/bin")
NEW_TESTS = ["nonempty_required_models", "reconcile_loan_counts"]
LABEL_CASES: list[tuple[str | None, int | None]] = [
    ("Fully Paid", 0),
    ("Charged Off", 1),
    ("Default", 1),
    ("Current", None),
    ("Late (31-120 days)", None),
    ("In Grace Period", None),
    ("Late (16-30 days)", None),
    ("Does not meet the credit policy. Status:Fully Paid", None),
    ("Does not meet the credit policy. Status:Charged Off", None),
    (None, None),
    ("Unrecognized status", None),
]


def main() -> int:
    """Run isolated failure/recovery checks and stop the test server.

    Returns:
        Zero when every expected outcome and cluster shutdown succeeds.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=PG_BIN)
    pg_bin = parser.parse_args().pg_bin.resolve()
    dbt = Path(sys.executable).parent / "dbt"
    for binary in [pg_bin / "initdb", pg_bin / "pg_ctl", pg_bin / "createdb", dbt]:
        if not binary.is_file():
            raise FileNotFoundError(f"Required installed binary missing: {binary}")
    work = Path(tempfile.mkdtemp(prefix="creditlens-m0-", dir="/private/tmp"))
    socket = work / "socket"
    socket.mkdir(mode=0o700)
    project = work / "project"
    project.mkdir()
    for directory in ["models", "macros", "tests/dbt"]:
        shutil.copytree(ROOT / directory, project / directory)
    shutil.copy2(ROOT / "dbt_project.yml", project / "dbt_project.yml")
    (project / "profiles.yml").write_text(
        "creditlens:\n  target: m0\n  outputs:\n    m0:\n"
        f"      type: postgres\n      host: {socket}\n"
        '      user: creditlens_m0\n      password: ""\n'
        "      port: 55439\n      dbname: creditlens_m0\n"
        "      schema: public\n      threads: 1\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PG", "POSTGRES", "DBT_"))
    }
    # initdb --locale configures the database, not the environment of pg_ctl/postgres.
    # macOS PostgreSQL startup must not inherit an unset/invalid terminal locale.
    env.update(
        LC_ALL="C",
        LANG="C",
        DBT_SEND_ANONYMOUS_USAGE_STATS="false",
        DBT_USE_COLORS="false",
    )
    report: dict[str, Any] = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "workspace": str(work),
        "database": "creditlens_m0",
        "transport": "private Unix socket; TCP disabled",
        "subprocess_locale": {"LC_ALL": env["LC_ALL"], "LANG": env["LANG"]},
        "postgres_bin": str(pg_bin),
        "source_sha256": {
            name: sha256((ROOT / name).read_bytes()).hexdigest()
            for name in [
                "models/staging/lc_loans_clean.sql",
                "models/mart/loan_features.sql",
                "models/mart/final_features.sql",
                "tests/dbt/loan_label_contract.sql",
                "scripts/verify_m0_dbt.py",
            ]
        },
        "steps": [],
    }
    started = False
    connection = None

    def run(name: str, command: list[str], expected: int = 0) -> None:
        result = subprocess.run(
            command,
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        (work / f"{name}.log").write_text(result.stdout + result.stderr)
        report["steps"].append({"step": name, "exit_code": result.returncode})
        print(f"{name}: exit={result.returncode} expected={expected}", flush=True)
        if result.returncode != expected:
            logs = str(work / (name + ".log"))
            if name == "start":
                logs += f" and {work / 'postgres.log'}"
            raise RuntimeError(f"{name} failed; inspect {logs}")

    def dbt_step(name: str, args: list[str], failures: dict[str, int] | None = None) -> None:
        run(name, [str(dbt), *args, "--profiles-dir", str(project)], 1 if failures else 0)
        results = json.loads((project / "target/run_results.json").read_text())
        summary = [
            {key: item.get(key) for key in ["unique_id", "status", "failures"]}
            for item in results["results"]
        ]
        report["steps"][-1]["results"] = summary
        if not summary:
            raise RuntimeError(f"{name} selected no dbt nodes")
        actual_failures = {
            item["unique_id"].split(".")[2]: item["failures"]
            for item in summary
            if item["status"] == "fail"
        }
        if actual_failures != (failures or {}):
            raise RuntimeError(f"Unexpected failing tests in {name}: {actual_failures}")
        if any(item["status"] not in ("success", "pass", "fail") for item in summary):
            raise RuntimeError(f"Unexpected dbt status in {name}")

    def counts(name: str, expected: list[int]) -> None:
        assert connection is not None
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT (SELECT COUNT(*) FROM staging.lc_loans_clean), "
                "(SELECT COUNT(*) FROM mart.loan_features), "
                "(SELECT COUNT(*) FROM mart.final_features)"
            )
            actual = list(cursor.fetchone())
        report["steps"].append({"step": name, "counts_staging_loan_final": actual})
        if actual != expected:
            raise RuntimeError(f"{name}: expected {expected}, found {actual}")

    try:
        run(
            "initdb",
            [
                str(pg_bin / "initdb"),
                "-D",
                str(work / "pgdata"),
                "-U",
                "creditlens_m0",
                "--auth=trust",
                "--encoding=UTF8",
                "--locale=C",
            ],
        )
        run(
            "start",
            [
                str(pg_bin / "pg_ctl"),
                "-D",
                str(work / "pgdata"),
                "-l",
                str(work / "postgres.log"),
                "-o",
                f"-k {socket} -p 55439 -c listen_addresses='' -c shared_buffers=32MB",
                "-w",
                "start",
            ],
        )
        started = True
        run(
            "createdb",
            [
                str(pg_bin / "createdb"),
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
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SHOW data_directory")
            if Path(cursor.fetchone()[0]).resolve() != (work / "pgdata").resolve():
                raise RuntimeError("Refusing mutation: cluster path mismatch")
            cursor.execute("SHOW server_version")
            report["server_version"] = cursor.fetchone()[0]
            cursor.execute("CREATE SCHEMA raw; CREATE SCHEMA staging; CREATE SCHEMA mart")
            # Reuse raw DDL; omit earlier monitoring/Airflow setup intentionally.
            ddl = (ROOT / "scripts/init_db.sql").read_text()
            raw_ddl = ddl[ddl.index("CREATE TABLE IF NOT EXISTS raw.lc_loans") :]
            cursor.execute(raw_ddl)
        dbt_step("empty_build", ["run"])
        counts("empty_counts", [0, 0, 0])
        dbt_step("legacy_tests_empty", ["test", "--exclude", *NEW_TESTS])
        dbt_step("nonempty_rejects_empty", ["test", "--select", NEW_TESTS[0]], {NEW_TESTS[0]: 3})
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO raw.lc_loans
                    (loan_id, loan_amnt, term, installment, annual_inc,
                     issue_date, loan_status, loaded_at)
                VALUES
                    (1, 1000, '36 months', 35, 24000, '2015-01-01',
                     'Fully Paid', '2020-01-01'),
                    (2, 2000, '36 months', 70, 36000, '2015-01-01',
                     'Charged Off', '2020-01-01');
                INSERT INTO raw.fred_indicators(series_id, observation_date, value)
                VALUES ('UNRATE', '2015-01-01', 5.7);
            """)
        counts("after_ingestion_before_rebuild", [2, 0, 0])
        dbt_step(
            "reconciliation_rejects_stale_mart",
            ["test", "--select", NEW_TESTS[1]],
            {NEW_TESTS[1]: 1},
        )
        dbt_step("populated_build_and_tests", ["build"])
        counts("populated_counts", [2, 2, 2])
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM mart.final_features WHERE id = 2")
        dbt_step(
            "reconciliation_rejects_missing_final",
            ["test", "--select", NEW_TESTS[1]],
            {NEW_TESTS[1]: 1},
        )
        dbt_step("restore_final", ["build", "--select", "final_features"])
        counts("restored_counts", [2, 2, 2])
        expected_labels = [(1, "Fully Paid", 0), (2, "Charged Off", 1)] + [
            (index, status, label) for index, (status, label) in enumerate(LABEL_CASES, 100)
        ]
        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO raw.lc_loans
                    (loan_id, loan_amnt, term, installment, annual_inc,
                     issue_date, loan_status, loaded_at)
                    VALUES (%s, 1000, '36 months', 35, 24000,
                            '2015-01-01', %s, '2020-01-01')""",
                [(index, status) for index, status, _ in expected_labels[2:]],
            )
            cursor.execute("SELECT * FROM raw.lc_loans ORDER BY loan_id")
            raw_before = cursor.fetchall()

        def verify_labels(name: str) -> None:
            """Check exact IDs, preserved statuses and labels through all loan layers."""
            assert connection is not None
            for relation, key in [
                ("staging.lc_loans_clean", "loan_id"),
                ("mart.loan_features", "id"),
                ("mart.final_features", "id"),
            ]:
                with connection.cursor() as cursor:
                    # Relation/key are fixed internal identifiers, never external input.
                    cursor.execute(
                        f"SELECT {key}, loan_status, is_default FROM {relation} ORDER BY {key}"
                    )
                    if cursor.fetchall() != expected_labels:
                        raise RuntimeError(f"Label/ID/status mismatch in {relation}")
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM raw.lc_loans ORDER BY loan_id")
                if cursor.fetchall() != raw_before:
                    raise RuntimeError("Label build changed raw records")
            report["steps"].append(
                {"step": name, "rows_per_layer": len(expected_labels), "raw_unchanged": True}
            )

        dbt_step("label_fixture_build", ["run"])
        dbt_step("label_contract_all_statuses", ["test", "--select", "loan_label_contract"])
        verify_labels("label_ids_statuses_and_nulls_preserved")
        report["label_cases"] = [
            {"status": status, "expected_label": label} for status, label in LABEL_CASES
        ]
        with connection.cursor() as cursor:
            cursor.execute("""UPDATE mart.final_features
                SET is_default = CASE WHEN loan_status = 'Current' THEN 0 ELSE 1 END
                WHERE loan_status IN ('Current', 'Late (31-120 days)')""")
        dbt_step(
            "label_contract_rejects_current_and_late_labels",
            ["test", "--select", "loan_label_contract"],
            {"loan_label_contract": 2},
        )
        dbt_step("restore_label_final", ["build", "--select", "final_features"])
        with connection.cursor() as cursor:
            cursor.execute("UPDATE mart.final_features SET is_default = NULL WHERE id = 1")
        dbt_step(
            "label_contract_rejects_missing_paid_label",
            ["test", "--select", "loan_label_contract"],
            {"loan_label_contract": 1},
        )
        dbt_step("restore_labels_with_null_fixture", ["run"])
        verify_labels("null_status_preserved_without_invented_label")
        dbt_step(
            "source_guard_rejects_null_status",
            ["test"],
            {"source_not_null_raw_lc_loans_loan_status": 1},
        )
        # NULL mapping is safe, but missing source status still fails the existing quality gate.
        # Remove only that deliberately invalid synthetic input before the full healthy build.
        with connection.cursor() as cursor:
            cursor.executemany(
                "DELETE FROM raw.lc_loans WHERE loan_id = %s",
                [(index,) for index, status, _ in expected_labels if status is None],
            )
            cursor.execute("SELECT * FROM raw.lc_loans ORDER BY loan_id")
            raw_before = cursor.fetchall()
        expected_labels = [row for row in expected_labels if row[1] is not None]
        report["steps"].append({"step": "remove_null_source_fixture", "removed_rows": 1})
        dbt_step("restore_label_all_and_tests", ["build"])
        verify_labels("final_label_contract_and_raw_preserved")
        report["status"] = "passed"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, psycopg2.Error) as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(report["error"], flush=True)
    finally:
        if connection is not None:
            connection.close()
        if started or (work / "pgdata/postmaster.pid").exists():
            try:
                run(
                    "stop",
                    [
                        str(pg_bin / "pg_ctl"),
                        "-D",
                        str(work / "pgdata"),
                        "-m",
                        "fast",
                        "-w",
                        "stop",
                    ],
                )
                report["cluster_stopped"] = True
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                report["cluster_stopped"] = False
                report["status"] = "failed"
                report["stop_error"] = str(exc)
        report["finished_at_utc"] = datetime.now(UTC).isoformat()
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f'Report: {work / "report.json"}', flush=True)
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
