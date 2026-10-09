"""Restore a scoped archive and rehearse label rollout/rollback on private PostgreSQL.

Never loads project credentials or connects to the active database. Keeps private
logs and the stopped temporary cluster for inspection; does not publish data.
"""

from __future__ import annotations

import argparse
import hashlib
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
PG = Path("/opt/homebrew/opt/postgresql@14/bin")
LAYERS = [
    ("staging.lc_loans_clean", "loan_id"),
    ("mart.loan_features", "id"),
    ("mart.final_features", "id"),
]
EXPECTED_ROWS = 2_260_668


def main() -> int:
    """Verify a supplied archive on a newly created private cluster.

    Returns:
        Zero only after restore, label build, rollback and shutdown succeed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    backup = args.backup.resolve(strict=True)
    with backup.open("rb") as handle:
        checksum = hashlib.file_digest(handle, "sha256").hexdigest()
    if checksum != args.sha256:
        raise ValueError("Backup checksum mismatch; no cluster created")
    if shutil.disk_usage("/private/tmp").free < 8 * 1024**3:
        raise RuntimeError("Need at least 8 GiB free for this scoped rehearsal")
    dbt = Path(sys.executable).parent / "dbt"
    for binary in ["initdb", "pg_ctl", "createdb", "pg_restore"]:
        if not (PG / binary).is_file():
            raise FileNotFoundError(PG / binary)
    if not dbt.is_file():
        raise FileNotFoundError(dbt)
    work = Path(tempfile.mkdtemp(prefix="m0-label-", dir="/private/tmp"))
    socket = work / "socket"
    socket.mkdir(mode=0o700)
    project = work / "project"
    project.mkdir()
    for folder in ["models", "macros", "tests/dbt"]:
        shutil.copytree(ROOT / folder, project / folder)
    shutil.copy2(ROOT / "dbt_project.yml", project / "dbt_project.yml")
    (project / "profiles.yml").write_text(
        "creditlens:\n  target: rehearsal\n  outputs:\n    rehearsal:\n"
        f"      type: postgres\n      host: {socket}\n"
        "      port: 55439\n      user: creditlens_m0\n      password: ''\n"
        "      dbname: creditlens_label_drill\n      schema: public\n      threads: 1\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PG", "POSTGRES", "DBT_"))
    }
    env.update(LC_ALL="C", LANG="C", DBT_SEND_ANONYMOUS_USAGE_STATS="false", DBT_USE_COLORS="false")
    report: dict[str, Any] = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "status": "running",
        "workspace": str(work),
        "backup": {"path": str(backup), "sha256": checksum, "bytes": backup.stat().st_size},
        "transport": "private Unix socket; TCP disabled",
        "ownership_acl_restored": False,
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ["models", "macros", "tests/dbt"]
            for path in (ROOT / folder).rglob("*")
            if path.is_file()
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "steps": [],
    }
    connection = None
    phase = "setup"

    def run(name: str, command: list[str]) -> None:
        nonlocal phase
        phase = name
        result = subprocess.run(
            command, cwd=project, env=env, capture_output=True, text=True, timeout=600
        )
        (work / f"{name}.log").write_text(result.stdout + result.stderr)
        report["steps"].append({"step": name, "exit_code": result.returncode})
        print(f"{name}: exit={result.returncode}", flush=True)
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect private logs")

    def snapshot() -> dict[str, Any]:
        assert connection is not None
        state: dict[str, Any] = {"layers": {}, "input_fingerprints": {}}
        with connection.cursor() as cursor:
            for relation, key in LAYERS:
                cursor.execute(f"""SELECT COUNT(*), COUNT(DISTINCT {key}),
                    COUNT(*) FILTER (WHERE is_default=0),
                    COUNT(*) FILTER (WHERE is_default=1),
                    COUNT(*) FILTER (WHERE is_default IS NULL),
                    COUNT(*) FILTER (WHERE is_default IS DISTINCT FROM CASE
                        WHEN loan_status='Fully Paid' THEN 0
                        WHEN loan_status IN ('Charged Off','Default') THEN 1 ELSE NULL END)
                    FROM {relation}""")
                state["layers"][relation] = dict(
                    zip(
                        ["count", "unique_ids", "zero", "one", "null", "mismatches"],
                        cursor.fetchone(),
                    )
                )
            for relation in ["raw.lc_loans", "mart.macro_features"]:
                # Aggregate fingerprints are supporting evidence, not collision-free equality.
                cursor.execute(
                    f"SELECT COUNT(*), SUM(hashtextextended(to_jsonb(t)::text, 0)::numeric) "
                    f"FROM {relation} t"
                )
                count, fingerprint = cursor.fetchone()
                state["input_fingerprints"][relation] = [count, str(fingerprint)]
            cursor.execute("SELECT pg_get_viewdef('staging.lc_loans_clean'::regclass, true)")
            state["view_definition_sha256"] = hashlib.sha256(
                cursor.fetchone()[0].encode()
            ).hexdigest()
        return state

    def compare_rows(ignore_label: bool) -> dict[str, int]:
        assert connection is not None
        mismatches = {}
        remove = " - 'is_default'" if ignore_label else ""
        with connection.cursor() as cursor:
            for index, (relation, key) in enumerate(LAYERS):
                cursor.execute(
                    f"""SELECT COUNT(*) FROM {relation} a FULL JOIN m0_before.layer_{index} b
                    ON a.{key}=b.{key}
                    WHERE a.{key} IS NULL OR b.{key} IS NULL
                    OR (to_jsonb(a){remove}) IS DISTINCT FROM (to_jsonb(b){remove})"""
                )
                mismatches[relation] = cursor.fetchone()[0]
        if any(mismatches.values()):
            raise RuntimeError("Unexpected row differences against restored baseline")
        return mismatches

    try:
        run(
            "initdb",
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
                str(work / "postgres.log"),
                "-o",
                f"-k {socket} -p 55439 -c listen_addresses='' -c shared_buffers=64MB "
                "-c max_wal_size=512MB",
                "-w",
                "start",
            ],
        )
        base = ["-h", str(socket), "-p", "55439", "-U", "creditlens_m0"]
        run("createdb", [str(PG / "createdb"), *base, "creditlens_label_drill"])
        connection = psycopg2.connect(
            host=str(socket),
            port=55439,
            user="creditlens_m0",
            dbname="creditlens_label_drill",
            options="-c statement_timeout=300000 -c lock_timeout=5000 -c work_mem=16MB",
        )
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SHOW data_directory")
            if Path(cursor.fetchone()[0]).resolve() != (work / "pgdata").resolve():
                raise RuntimeError("Cluster path mismatch; refusing writes")
            cursor.execute("SHOW server_version")
            report["server_version"] = cursor.fetchone()[0]
            cursor.execute(
                "CREATE SCHEMA raw; CREATE SCHEMA staging; CREATE SCHEMA mart; "
                "CREATE SCHEMA m0_before"
            )
        restore = [
            str(PG / "pg_restore"),
            *base,
            "-d",
            "creditlens_label_drill",
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
        ]
        run("restore_archive", [*restore, str(backup)])
        phase = "baseline_snapshot"
        report["before"] = before = snapshot()
        for stats in before["layers"].values():
            if list(stats.values()) != [
                EXPECTED_ROWS,
                EXPECTED_ROWS,
                1076751,
                290066,
                893851,
                21467,
            ]:
                raise RuntimeError("Restored baseline differs from approved preflight")
        if before["input_fingerprints"]["raw.lc_loans"][0] != EXPECTED_ROWS:
            raise RuntimeError("Restored raw row count mismatch")
        with connection.cursor() as cursor:
            for index, (relation, key) in enumerate(LAYERS):
                cursor.execute(f"CREATE TABLE m0_before.layer_{index} AS SELECT * FROM {relation}")
                cursor.execute(f"CREATE UNIQUE INDEX ON m0_before.layer_{index} ({key})")
        report["disk_free_before_build"] = shutil.disk_usage(work).free
        if report["disk_free_before_build"] < 4 * 1024**3:
            raise RuntimeError("Insufficient remaining disk before rehearsal build")
        print("baseline_verified: matched archived counts and labels", flush=True)
        run(
            "build_new_labels",
            [
                str(dbt),
                "build",
                "--profiles-dir",
                str(project),
                "--select",
                "lc_loans_clean",
                "loan_features",
                "final_features",
                "--indirect-selection",
                "cautious",
            ],
        )
        result = json.loads((project / "target/run_results.json").read_text())
        report["dbt_results"] = [
            {key: item.get(key) for key in ["unique_id", "status", "failures"]}
            for item in result["results"]
        ]
        built = {
            item["unique_id"]
            for item in result["results"]
            if item["unique_id"].startswith("model.")
        }
        if built != {"model.creditlens." + relation.split(".")[1] for relation, _ in LAYERS}:
            raise RuntimeError("Unexpected build scope")
        if not result["results"] or any(
            item["status"] not in ("success", "pass") for item in result["results"]
        ):
            raise RuntimeError("Incomplete or failed dbt checks")
        phase = "verify_new_labels"
        report["after"] = after = snapshot()
        for stats in after["layers"].values():
            if list(stats.values()) != [EXPECTED_ROWS, EXPECTED_ROWS, 1076751, 268599, 915318, 0]:
                raise RuntimeError("New labels do not meet expected contract")
        if after["input_fingerprints"] != before["input_fingerprints"]:
            raise RuntimeError("Raw or macro input fingerprints changed")
        report["non_label_row_differences"] = compare_rows(ignore_label=True)
        print("new_labels_verified: counts, IDs and non-label values preserved", flush=True)
        run(
            "rollback_label_relations",
            [
                *restore,
                "--clean",
                "--if-exists",
                "-t",
                "lc_loans_clean",
                "-t",
                "loan_features",
                "-t",
                "final_features",
                str(backup),
            ],
        )
        phase = "verify_rollback"
        report["rollback"] = rollback = snapshot()
        if rollback != before:
            raise RuntimeError("Rollback snapshot differs from restored baseline")
        report["rollback_row_differences"] = compare_rows(ignore_label=False)
        report["status"] = "passed"
        print("rollback_verified: original labels, rows and view restored", flush=True)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, psycopg2.Error) as exc:
        report.update(status="failed", failed_phase=phase, error_type=type(exc).__name__)
        print(f"Failed at {phase}: {type(exc).__name__}; inspect private logs", flush=True)
    finally:
        if connection is not None:
            connection.close()
        if (work / "pgdata/postmaster.pid").exists():
            try:
                run(
                    "stop",
                    [str(PG / "pg_ctl"), "-D", str(work / "pgdata"), "-m", "fast", "-w", "stop"],
                )
            except (OSError, RuntimeError, subprocess.SubprocessError):
                report["status"] = "failed"
        report["cluster_stopped"] = not (work / "pgdata/postmaster.pid").exists()
        report["disk_free_after"] = shutil.disk_usage(work).free
        report["finished_at_utc"] = datetime.now(UTC).isoformat()
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Report: {work / 'report.json'}", flush=True)
    return 0 if report["status"] == "passed" and report["cluster_stopped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
