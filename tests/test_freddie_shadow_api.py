"""Authenticated private research boundaries; no source files or production claims in fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.research.freddie_shadow_api import create_app, verify_bundle

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "synthetic-test-only-token-not-a-real-credential"


def feature_values() -> dict[str, float | int | None]:
    """Provide a synthetic, semantically current observation with complete clean history."""
    return {
        "upb": 100000.0,
        "loan_age": 36.0,
        "remaining_months": 324.0,
        "interest_rate": 6.0,
        "prior_dq_1": 0,
        "prior_dq_2": 0,
        "credit_score": 700.0,
        "orig_cltv": 80.0,
        "orig_dti": 35.0,
        "orig_ltv": 80.0,
        "worst_dq_6": 0,
        "dq_months_6": 0,
        "complete_status_6": 1,
        "worst_dq_12": 0,
        "dq_months_12": 0,
        "complete_status_12": 1,
        "months_since_known_dq_12": None,
        "upb_change_ratio_3": -0.01,
        "upb_change_ratio_12": -0.03,
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    config = json.loads((ROOT / "config/research/freddie_experiment_v4.json").read_text())

    class FixtureModel:
        def predict_proba(self, frame: pd.DataFrame) -> np.ndarray[Any, Any]:
            assert list(frame.columns) == config["features"]
            assert set(frame.dtypes) == {np.dtype("float32")}
            return np.array([[0.875, 0.125]])

    monkeypatch.setattr(
        "src.research.freddie_shadow_api.verify_bundle",
        lambda _: (
            {"features": config["features"], "model_id": "synthetic-research"},
            FixtureModel(),
        ),
    )
    return TestClient(create_app(Path("/unused-synthetic.json"), TOKEN))


def test_authentication_precedes_body_validation_and_readiness(client: TestClient) -> None:
    """Malformed unauthenticated input must not invoke the model or expose readiness."""
    assert client.get("/ready").status_code == 401
    assert client.post("/score", content="not-json").status_code == 401
    assert client.get("/ready", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_feature_parity_path_remains_explicitly_research_only(client: TestClient) -> None:
    headers = {"Authorization": "Bearer " + TOKEN}
    result = client.post("/score", json={"features": feature_values()}, headers=headers)
    assert result.status_code == 200
    assert result.json()["probability"] == 0.125
    assert result.json()["production_scoring_release"] == "HOLD"
    assert result.json()["public_scoring_authorized"] is False
    assert "approved" not in result.json()
    assert result.headers["cache-control"] == "no-store"
    ready = client.get("/ready", headers=headers).json()
    assert ready["research_ready"] is True and ready["point_in_time_verified"] is False


@pytest.mark.parametrize(
    "mutation", ["missing", "unknown", "negative", "inconsistent", "fractional", "bool", "nan"]
)
def test_invalid_schema_domain_and_missing_history_fail_closed(
    client: TestClient, mutation: str
) -> None:
    values = feature_values()
    if mutation == "missing":
        values.pop("upb")
    elif mutation == "unknown":
        values["wrong_name"] = values.pop("upb")
    elif mutation == "negative":
        values["upb"] = -1
    elif mutation == "inconsistent":
        values["complete_status_12"] = 0
    elif mutation == "fractional":
        values["dq_months_6"] = 0.5
    elif mutation == "bool":
        values["orig_dti"] = True
    else:
        values["upb"] = float("nan")
    result = client.post(
        "/score",
        content=json.dumps({"features": values}),
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
    )
    assert result.status_code == 422


def test_body_limit_uses_actual_received_bytes(client: TestClient) -> None:
    assert (
        client.post(
            "/score", content="x" * 8193, headers={"Authorization": "Bearer " + TOKEN}
        ).status_code
        == 413
    )


def test_rate_budget_is_bounded_even_for_authenticated_client(client: TestClient) -> None:
    headers = {"Authorization": "Bearer " + TOKEN}
    for _ in range(60):
        assert client.get("/ready", headers=headers).status_code == 200
    assert client.get("/ready", headers=headers).status_code == 429


def test_declared_research_pass_does_not_bypass_scope_gate(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(
        json.dumps(
            {
                "scope": "PRODUCTION",
                "public_scoring_authorized": True,
                "production_scoring_release": "READY",
                "protocol_sha256": "untrusted",
            }
        )
    )
    with pytest.raises(ValueError, match="research scope"):
        verify_bundle(path)
