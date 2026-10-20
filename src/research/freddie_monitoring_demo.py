"""Real local inference with toy delayed outcomes; no training or operational quality claim."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import secrets
import socket
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from src.research.freddie_monitoring import AuditStore, SyntheticOutcome, private_file
from src.research.freddie_monthly_adapter import MonthlySnapshot
from src.research.freddie_monthly_client import score_snapshot

ROOT = Path(__file__).resolve().parents[2]


def _period(index: int) -> str:
    year, month = divmod(index, 12)
    return f"{year:04}{month + 1:02}"


def _available(index: int) -> datetime:
    year, month = divmod(index + 1, 12)
    return datetime(year, month + 1, 5, tzinfo=UTC)


def synthetic_snapshot(loan: int, prediction_time: datetime) -> MonthlySnapshot:
    """Construct a toy active loan with thirteen explicitly available monthly observations.

    Args:
        loan: Small toy scenario number, never a real loan ID.
        prediction_time: Actual local decision time for this simulation.

    Returns:
        Strict monthly input with no future follow-up included in its features.
    """
    current = prediction_time.year * 12 + prediction_time.month - 2
    if _available(current) > prediction_time:
        current -= 1
    key = f"synthetic-monitoring-{loan}"
    data = {
        "loan_key": key,
        "as_of_period": _period(current),
        "prediction_time": prediction_time.isoformat(),
        "origination": {
            "available_at": "2020-01-01T00:00:00Z",
            "credit_score": 700,
            "orig_cltv": 80,
            "orig_dti": 35,
            "orig_ltv": 80,
        },
        "records": [
            {
                "loan_key": key,
                "period": _period(current - lag),
                "available_at": _available(current - lag).isoformat(),
                "upb": float(100000 + loan * 1000 + lag * 1000),
                "dq": 1 if loan == 1 and lag == 2 else 0,
                "loan_age": 36 - lag,
                "remaining_months": 324 + lag,
                "interest_rate": 6.0,
            }
            for lag in range(12, -1, -1)
        ],
    }
    return MonthlySnapshot.model_validate_json(json.dumps(data))


def _probe(port: int, method: str, path: str, token: str, payload: bytes | None = None) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request(method, path, payload, {"Authorization": "Bearer " + token})
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def run_demo(bundle: Path, token_file: Path, output: Path, origin: str) -> dict[str, Any]:
    """Verify real private inference and simulated label linkage in a fresh private directory.

    Args:
        bundle: Existing accepted private research bundle; never rewritten.
        token_file: Owner-only existing bearer token, never printed.
        output: New owner-only directory outside the repository.
        origin: Distinguishes assistant execution from an unverified local command identity.

    Returns:
        Execution receipt; quality figures are explicitly synthetic and not release evidence.

    Raises:
        ValueError: Private boundary or synthetic scenario contract failure.
        RuntimeError: Server startup or request/monitoring verification failure.
    """
    private_file(bundle)
    private_file(token_file)
    resolved = output.resolve()
    if (
        ROOT == resolved
        or ROOT in resolved.parents
        or output.exists()
        or output.is_symlink()
        or not output.parent.is_dir()
        or output.parent.stat().st_mode & 0o077
    ):
        raise ValueError("Fresh output below an owner-only directory outside Git required")
    token = token_file.read_text().strip()
    if len(token) < 32:
        raise ValueError("Private bearer credential required")
    output.mkdir(mode=0o700)
    key = secrets.token_bytes(32)
    key_file = output / "link_key.bin"
    key_file.write_bytes(key)
    key_file.chmod(0o600)
    journal = output / "audit.sqlite"
    with socket.socket() as free_port:
        free_port.bind(("127.0.0.1", 0))
        port = free_port.getsockname()[1]
    process: subprocess.Popen[bytes] | None = None
    log = output / "server.log"
    receipt: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "execution_origin": origin,
        "purpose": "SYNTHETIC_MONITORING_PLUMBING_ONLY",
        "production_scoring_release": "HOLD",
        "operational_quality_verified": False,
        "source_archives_opened": False,
        "training_or_test_rerun": False,
        "status": "INCOMPLETE",
    }
    try:
        with log.open("wb") as stream:
            log.chmod(0o600)
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "src.research.freddie_shadow_api",
                    "--bundle",
                    str(bundle),
                    "--token-file",
                    str(token_file),
                    "--audit-db",
                    str(journal),
                    "--port",
                    str(port),
                ],
                cwd=ROOT,
                stdout=stream,
                stderr=subprocess.STDOUT,
                env={**os.environ, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2"},
            )
            deadline = monotonic() + 40
            while monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Private server exited; inspect its private log")
                try:
                    if _probe(port, "GET", "/ready", token) == 200:
                        break
                except (OSError, http.client.HTTPException):
                    pass
                sleep(0.25)
            else:
                raise RuntimeError("Private server readiness timed out")
            store = AuditStore(journal)
            snapshots = [synthetic_snapshot(i, datetime.now(UTC)) for i in (1, 2, 3)]
            identities = []
            for snapshot in snapshots:
                result = score_snapshot(snapshot, token, port)
                canonical = store.link(
                    result["request_id"],
                    snapshot.loan_key,
                    snapshot.as_of_period,
                    snapshot.prediction_time,
                    key,
                )
                identities.append(canonical)
            retry = score_snapshot(snapshots[0], token, port)
            canonical_retry = store.link(
                retry["request_id"],
                snapshots[0].loan_key,
                snapshots[0].as_of_period,
                snapshots[0].prediction_time,
                key,
            )
            if canonical_retry != identities[0]:
                raise ValueError("Retry changed canonical observation")
            if _probe(port, "GET", "/ready", "deliberately-invalid-synthetic-token") != 401:
                raise ValueError("Authentication negative check failed")
            if _probe(port, "POST", "/score", token, b"{}") != 422:
                raise ValueError("Invalid input negative check failed")
            initial = store.report(datetime.now(UTC))
            if initial["synthetic_outcome_diagnostics"][0]["pending"] != 3:
                raise ValueError("Initial canonical pending count mismatch")
            year, month = int(snapshots[0].as_of_period[:4]), int(snapshots[0].as_of_period[4:])
            base = year * 12 + month - 1
            future_cutoff = _available(base + 3) + timedelta(days=5)
            scenarios: list[list[int | None]] = [[0, 3, 0], [0, 0, 0], [0, None, 0]]
            for request_id, snapshot, statuses in zip(
                identities, snapshots, scenarios, strict=True
            ):
                payload = SyntheticOutcome.model_validate_json(
                    json.dumps(
                        {
                            "request_id": request_id,
                            "loan_key": snapshot.loan_key,
                            "as_of_period": snapshot.as_of_period,
                            "source_kind": "synthetic",
                            "report_as_of": future_cutoff.isoformat(),
                            "followup": [
                                {
                                    "period": _period(base + offset),
                                    "available_at": _available(base + offset).isoformat(),
                                    "dq": dq,
                                    "upb": 100000.0,
                                }
                                for offset, dq in enumerate(statuses, 1)
                            ],
                        }
                    )
                )
                store.ingest(payload, key)
                if store.ingest(payload, key)["idempotent_replay"] is not True:
                    raise ValueError("Outcome replay must be idempotent")
            final = store.report(future_cutoff)
            row = final["synthetic_outcome_diagnostics"][0]
            if (row["resolved"], row["adverse"], row["censored"], row["pending"]) != (2, 1, 1, 0):
                raise ValueError("Synthetic label reconciliation failed")
            receipt.update(
                {
                    "status": "PASS_REAL_INFERENCE_SYNTHETIC_MONITORING",
                    "initial": initial,
                    "future_simulation": final,
                    "canonical_request_ids": identities,
                    "retry_deduplicated": True,
                    "negative_http": [401, 422],
                    "journal_sha256": hashlib.sha256(journal.read_bytes()).hexdigest(),
                }
            )
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            receipt["temporary_owned_server_stopped"] = process.poll() is not None
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        target = output / "receipt.json"
        target.write_text(json.dumps(receipt, indent=2) + "\n")
        target.chmod(0o600)
    return receipt


def main() -> None:
    """Run only explicit toy scenarios against a locally accepted model, never real outcomes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--confirm-synthetic", required=True, action="store_true")
    parser.add_argument("--assistant-check", action="store_true")
    args = parser.parse_args()
    origin = "assistant_check" if args.assistant_check else "local_command_unverified_identity"
    run_demo(args.bundle, args.token_file, args.output, origin)
    print("Berhasil: scoring nyata, jurnal privat, deduplikasi dan simulasi tiga outcome.")
    print("Simulasi label bukan evaluasi produksi. Bukti privat:", args.output / "receipt.json")


if __name__ == "__main__":
    main()
