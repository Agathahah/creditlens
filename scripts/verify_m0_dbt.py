"""Reproduce empty marts using real dbt models in a private PostgreSQL cluster.

Run from the repository: .venv/bin/python scripts/verify_m0_dbt.py
Requires existing PostgreSQL 16 binaries and the project's dbt installation.
Never connects to the development database or loads the project's credentials.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
PG_BIN = Path("/opt/homebrew/opt/postgresql@16/bin")
NEW_TESTS = ["nonempty_required_models", "reconcile_loan_counts"]


def main() -> int:
    """Run isolated failure/recovery checks and stop the test server.

    Returns:
        Zero when every expected outcome and cluster shutdown succeeds.
    """
    dbt = Path(sys.executable).parent / "dbt"
    for binary in [PG_BIN / "initdb", PG_BIN / "pg_ctl", PG_BIN / "createdb", dbt]:
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
    env.update(DBT_SEND_ANONYMOUS_USAGE_STATS="false", DBT_USE_COLORS="false")
    report: dict[str, Any] = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "workspace": str(work),
        "database": "creditlens_m0",
        "transport": "private Unix socket; TCP disabled",
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
            raise RuntimeError(f'{name} failed; inspect {work / (name + ".log")}')

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
                str(PG_BIN / "initdb"),
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
                str(PG_BIN / "pg_ctl"),
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
                str(PG_BIN / "createdb"),
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
                        str(PG_BIN / "pg_ctl"),
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
