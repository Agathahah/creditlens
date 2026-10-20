"""Synthetic contracts for actual inference audit, canonical grain and delayed labels."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.research.freddie_monitoring import AuditStore, SyntheticOutcome
from src.research.freddie_shadow_api import create_app
from tests.test_freddie_shadow_api import TOKEN, feature_values

NOW = datetime(2026, 10, 20, tzinfo=UTC)
AFTER = datetime(2027, 2, 1, tzinfo=UTC)
KEY = b"synthetic-separate-hmac-test-key-32bytes"
SHA = "a" * 64


@pytest.fixture
def store(tmp_path: Path) -> AuditStore:
    tmp_path.chmod(0o700)
    return AuditStore(tmp_path / "journal.sqlite")


def event(store: AuditStore, probability: float = 0.1, sha: str = SHA) -> str:
    """Record and link one successful synthetic model request."""
    request_id = str(uuid4())
    store.record(request_id, NOW, "POST", "/score", 200, 1.0, "synthetic-model", sha, probability)
    store.link(request_id, "toy-loan", "202609", NOW, KEY)
    return request_id


def evidence(request_id: str, statuses: list[int | None]) -> SyntheticOutcome:
    """Describe future toy outcomes; these are never real servicing observations."""
    return SyntheticOutcome.model_validate_json(
        json.dumps(
            {
                "request_id": request_id,
                "loan_key": "toy-loan",
                "as_of_period": "202609",
                "source_kind": "synthetic",
                "report_as_of": AFTER.isoformat(),
                "followup": [
                    {
                        "period": period,
                        "available_at": available,
                        "dq": status,
                        "upb": 100000.0,
                    }
                    for period, available, status in zip(
                        ["202610", "202611", "202612"],
                        ["2026-11-05T00:00:00Z", "2026-12-05T00:00:00Z", "2027-01-05T00:00:00Z"],
                        statuses,
                        strict=False,
                    )
                ],
            }
        )
    )


def quality(store: AuditStore) -> list[dict[str, Any]]:
    """Read canonical synthetic diagnostics at the explicit future simulation cutoff."""
    return list(store.report(AFTER)["synthetic_outcome_diagnostics"])


def test_retry_does_not_inflate_quality_but_traffic_is_preserved(store: AuditStore) -> None:
    original = event(store)
    retry = event(store)
    assert original != retry
    assert store.link(retry, "toy-loan", "202609", NOW, KEY) == original
    assert quality(store)[0]["linked_unique_loan_months"] == 1
    assert quality(store)[0]["pending"] == 1
    assert store.report(AFTER)["traffic"][0]["requests"] == 2
    with pytest.raises(ValueError, match="changed"):
        event(store, 0.9)


@pytest.mark.parametrize("statuses,label", [([0, 0, 0], 0), ([0, 3], 1), ([0, None, 0], None)])
def test_label_maturity_unknowns_and_replay(
    store: AuditStore, statuses: list[int | None], label: int | None
) -> None:
    request_id = event(store)
    payload = evidence(request_id, statuses)
    result = store.ingest(payload, KEY)
    assert result["label"] == label
    assert store.ingest(payload, KEY)["idempotent_replay"] is True
    row = quality(store)[0]
    assert row["resolved"] == (label is not None)
    assert row["censored"] == (label is None)
    assert row["pending"] == 0
    if label is not None:
        assert row["brier_diagnostic"] == pytest.approx((0.1 - label) ** 2)
        with pytest.raises(ValueError, match="cannot be replaced"):
            store.ingest(payload.model_copy(update={"report_as_of": AFTER.replace(day=2)}), KEY)


def test_censored_revision_can_mature_without_replacing_history(store: AuditStore) -> None:
    request_id = event(store)
    payload = evidence(request_id, [0, 0, 0])
    early = payload.model_copy(update={"report_as_of": datetime(2026, 12, 10, tzinfo=UTC)})
    assert store.ingest(early, KEY)["label"] is None
    assert store.ingest(payload, KEY)["label"] == 0
    with store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0] == 2
    earlier = store.report(datetime(2026, 12, 15, tzinfo=UTC))["synthetic_outcome_diagnostics"][0]
    assert earlier["censored"] == 1 and earlier["resolved"] == 0


@pytest.mark.parametrize("mutation", ["gap", "termination", "future"])
def test_missing_future_and_termination_are_never_negative(
    store: AuditStore, mutation: str
) -> None:
    payload = evidence(event(store), [0, 0, 0])
    if mutation == "gap":
        payload.followup.pop(1)
    elif mutation == "termination":
        payload.followup[1].zero_balance_code = "01"
    else:
        payload.report_as_of = datetime(2026, 12, 1, tzinfo=UTC)
    assert store.ingest(payload, KEY)["label"] is None


@pytest.mark.parametrize("mutation", ["duplicate", "outside", "early", "before_score", "key"])
def test_invalid_followup_or_identity_rejected(store: AuditStore, mutation: str) -> None:
    payload = evidence(event(store), [0, 0])
    key = KEY
    if mutation == "duplicate":
        payload.followup[1] = payload.followup[0]
        payload.report_as_of = datetime(2026, 10, 21, tzinfo=UTC)
    elif mutation == "outside":
        payload.followup[0].period = "202701"
    elif mutation == "early":
        payload.followup[0].available_at = NOW
    elif mutation == "before_score":
        payload.report_as_of = NOW.replace(day=19)
    else:
        key = b"different-synthetic-hmac-key-32bytes"
    with pytest.raises(ValueError):
        store.ingest(payload, key)


def test_model_identity_remains_separate_and_journal_has_no_raw_identifier(
    store: AuditStore,
) -> None:
    event(store)
    event(store, sha="b" * 64)
    assert len(quality(store)) == 2
    assert b"toy-loan" not in store.path.read_bytes()
    assert KEY not in store.path.read_bytes()
    assert store.path.stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError, match="Successful persisted"):
        store.link(str(uuid4()), "toy-loan", "202609", NOW, KEY)


def test_private_permissions_and_capacity_fail_closed(tmp_path: Path, monkeypatch: Any) -> None:
    tmp_path.chmod(0o755)
    with pytest.raises(ValueError, match="Owner-only"):
        AuditStore(tmp_path / "unsafe.sqlite")
    tmp_path.chmod(0o700)
    store = AuditStore(tmp_path / "private.sqlite")
    monkeypatch.setattr("src.research.freddie_monitoring.MAX_EVENTS", 0)
    with pytest.raises(ValueError, match="event limit"):
        event(store)


def test_actual_api_audits_rejections_and_does_not_trust_caller_ids(
    store: AuditStore, monkeypatch: Any
) -> None:
    class Model:
        def predict_proba(self, frame: Any) -> Any:
            return np.array([[0.9, 0.1]])

    monkeypatch.setattr(
        "src.research.freddie_shadow_api.verify_bundle",
        lambda _: (
            {"model_id": "toy", "candidate_sha256": SHA, "features": list(feature_values())},
            Model(),
        ),
    )
    app = create_app(Path("unused"), TOKEN, store.path)
    client = TestClient(app)
    auth = {"Authorization": "Bearer " + TOKEN, "X-Request-ID": "untrusted-caller-id"}
    response = client.post("/score", headers=auth, json={"features": feature_values()})
    assert response.status_code == 200
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.json()["request_id"] != "untrusted-caller-id"
    assert client.get("/ready", headers=auth).json()["audit_enabled"] is True
    assert client.get("/unknown?secret=raw-value").status_code == 401
    assert client.post("/score", headers=auth, json={}).status_code == 422
    assert client.post("/score", headers=auth, content="x" * 8193).status_code == 413
    monkeypatch.setattr("src.research.freddie_shadow_api.RATE_PER_MINUTE", 0)
    assert client.get("/ready", headers=auth).status_code == 429
    with store.connection() as connection:
        rows = connection.execute("SELECT * FROM events").fetchall()
    assert {r["status"] for r in rows} == {200, 401, 422, 413, 429}
    raw = store.path.read_bytes()
    assert TOKEN.encode() not in raw and b"raw-value" not in raw and b"credit_score" not in raw

    def failure(*args: Any, **kwargs: Any) -> None:
        raise sqlite3.OperationalError("fixture disk failure")

    monkeypatch.setattr("src.research.freddie_shadow_api.RATE_PER_MINUTE", 60)
    monkeypatch.setattr(AuditStore, "record", failure)
    result = client.post("/score", headers=auth, json={"features": feature_values()})
    assert result.status_code == 503 and "probability" not in result.json()
    assert result.headers["cache-control"] == "no-store"


def test_known_historical_outcome_cannot_be_called_post_inference(store: AuditStore) -> None:
    request_id = str(uuid4())
    store.record(request_id, NOW, "POST", "/score", 200, 1.0, "toy", SHA, 0.1)
    store.link(request_id, "toy-loan", "202509", datetime(2025, 10, 20, tzinfo=UTC), KEY)
    payload = evidence(request_id, [0, 0, 0])
    payload.as_of_period = "202509"
    for record in payload.followup:
        record.period = str(int(record.period) - 100)
        record.available_at = record.available_at.replace(year=record.available_at.year - 1)
    with pytest.raises(ValueError, match="after actual scoring"):
        store.ingest(payload, KEY)


@pytest.mark.parametrize("probability", [None, float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_success_probability_never_committed(store: AuditStore, probability: Any) -> None:
    with pytest.raises(ValueError, match="audit metadata"):
        store.record(str(uuid4()), NOW, "POST", "/score", 200, 1.0, "toy", SHA, probability)


def test_model_failure_is_sanitized_and_audited(store: AuditStore, monkeypatch: Any) -> None:
    class BrokenModel:
        def predict_proba(self, frame: Any) -> Any:
            raise RuntimeError("private model details must not be echoed")

    monkeypatch.setattr(
        "src.research.freddie_shadow_api.verify_bundle",
        lambda _: (
            {"model_id": "toy", "candidate_sha256": SHA, "features": list(feature_values())},
            BrokenModel(),
        ),
    )
    client = TestClient(create_app(Path("unused"), TOKEN, store.path))
    result = client.post(
        "/score", headers={"Authorization": "Bearer " + TOKEN}, json={"features": feature_values()}
    )
    assert result.status_code == 503
    assert "private model details" not in result.text
    with store.connection() as connection:
        row = connection.execute("SELECT status,probability FROM events").fetchone()
    assert row["status"] == 503 and row["probability"] is None
