"""Fail-closed reconciliation of service responses against actual private audit records."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from scripts.smoke_research_capacity import CAPACITY_PROBE, reconcile_requests
from src.research.freddie_monitoring import AuditStore


def observed(journal: Path, status: int, probability: float | None) -> dict[str, Any]:
    """Record a toy event and return a matching, credential-free observed response."""
    identity = str(uuid4())
    AuditStore(journal).record(
        identity,
        datetime.now(UTC),
        "POST",
        "/score",
        status,
        1.0,
        "synthetic-model",
        "a" * 64,
        probability,
    )
    return {
        "request_id": identity,
        "status": status,
        "body": {} if probability is None else {"probability": probability, "request_id": identity},
    }


def test_score_and_rejections_must_all_be_committed(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    journal = tmp_path / "audit.sqlite"
    rows = [
        observed(journal, 200, 0.125),
        observed(journal, 429, None),
        observed(journal, 401, None),
    ]
    assert reconcile_requests(journal, rows, "synthetic-model", "a" * 64) == {
        "observed_responses": 3,
        "persisted_scores": 1,
    }


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "status", "probability", "reject_score", "body_id", "model"]
)
def test_mismatched_or_duplicate_service_evidence_is_rejected(tmp_path: Path, change: str) -> None:
    tmp_path.chmod(0o700)
    journal = tmp_path / "audit.sqlite"
    row = observed(journal, 200, 0.125)
    rows = [row]
    if change == "missing":
        row["request_id"] = str(uuid4())
    elif change == "duplicate":
        rows.append(dict(row))
    elif change == "status":
        row["status"] = 429
    elif change == "probability":
        row["body"]["probability"] = 0.5
    elif change == "body_id":
        row["body"]["request_id"] = str(uuid4())
    elif change == "model":
        with pytest.raises(ValueError):
            reconcile_requests(journal, rows, "other-model", "a" * 64)
        return
    else:
        rows = [observed(journal, 429, None)]
        rows[0]["body"]["probability"] = 0.125
    with pytest.raises(ValueError):
        reconcile_requests(journal, rows, "synthetic-model", "a" * 64)


def test_capacity_probe_compiles() -> None:
    compile(CAPACITY_PROBE, "capacity_probe", "exec")
