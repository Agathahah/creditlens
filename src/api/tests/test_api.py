"""Unit tests for the CreditLens FastAPI endpoints."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from xgboost import XGBClassifier

from src.api.main import create_app, load_registry
from src.api.state import ModelRegistry
from src.explainability.counterfactual import CounterfactualGenerator
from src.explainability.shap_explainer import ShapExplainer
from src.ml.predict import CreditPredictor

FEATURES = ["loan_amnt", "int_rate", "dti_eff", "annual_inc"]


def _make_training_frame(n: int = 300) -> pd.DataFrame:
    """Build a synthetic training frame with a learnable default signal."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "loan_amnt": rng.uniform(1_000, 40_000, n),
            "int_rate": rng.uniform(5, 30, n),
            "dti_eff": rng.uniform(5, 45, n),
            "annual_inc": rng.uniform(20_000, 150_000, n),
        }
    )
    logits = 0.2 * df["int_rate"] + 0.15 * df["dti_eff"] - 8
    df["is_default"] = (logits + rng.normal(scale=1.0, size=n) > 0).astype(int)
    return df


@pytest.fixture(scope="module")
def registry() -> ModelRegistry:
    """ModelRegistry with a small trained XGBoost model and explainers."""
    train_df = _make_training_frame()
    model = XGBClassifier(n_estimators=20, max_depth=3, random_state=42)
    model.fit(train_df[FEATURES], train_df["is_default"])
    return ModelRegistry(
        predictor=CreditPredictor(model=model, approval_threshold=0.20),
        explainer=ShapExplainer(model),
        counterfactual_generator=CounterfactualGenerator(
            model=model,
            training_data=train_df,
            continuous_features=FEATURES,
            outcome_name="is_default",
        ),
        expected_features=FEATURES,
    )


@pytest.fixture(scope="module")
def client(registry: ModelRegistry) -> TestClient:
    """TestClient bound to an app with the fixture registry injected."""
    return TestClient(create_app(registry=registry))


@pytest.fixture
def low_risk_payload() -> dict[str, object]:
    """Applicant payload the model should score as low risk."""
    return {
        "applicant_id": "app-low-001",
        "features": {
            "loan_amnt": 5_000.0,
            "int_rate": 6.0,
            "dti_eff": 8.0,
            "annual_inc": 120_000.0,
        },
    }


@pytest.fixture
def high_risk_payload() -> dict[str, object]:
    """Applicant payload the model should score as high risk."""
    return {
        "applicant_id": "app-high-001",
        "features": {
            "loan_amnt": 35_000.0,
            "int_rate": 29.0,
            "dti_eff": 44.0,
            "annual_inc": 25_000.0,
        },
    }


def test_health(client: TestClient) -> None:
    """Health endpoint must report ok with artifacts loaded."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["explainer_loaded"] is True


def test_predict_low_risk(client: TestClient, low_risk_payload: dict[str, object]) -> None:
    """Low-risk applicant must be approved with a low score, within 100ms."""
    response = client.post("/predict", json=low_risk_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["score_id"] == "app-low-001"
    assert body["risk_score"] < 0.20
    assert body["approved"] is True
    assert body["risk_tier"] in {"low", "medium"}
    assert body["latency_ms"] < 100.0


def test_predict_high_risk(client: TestClient, high_risk_payload: dict[str, object]) -> None:
    """High-risk applicant must be rejected with a high score."""
    response = client.post("/predict", json=high_risk_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["risk_score"] > 0.25
    assert body["approved"] is False
    assert body["risk_tier"] == "high"


def test_predict_missing_features(client: TestClient) -> None:
    """Missing model features must yield a 422 naming the gap."""
    response = client.post("/predict", json={"features": {"loan_amnt": 5_000.0, "int_rate": 6.0}})
    assert response.status_code == 422
    assert "dti_eff" in response.text


def test_predict_generates_score_id(
    client: TestClient, low_risk_payload: dict[str, object]
) -> None:
    """A score_id must be generated when no applicant_id is supplied."""
    payload = {"features": low_risk_payload["features"]}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["score_id"].startswith("score-")


def test_explain_returns_shap_and_counterfactuals(
    client: TestClient, high_risk_payload: dict[str, object]
) -> None:
    """Explain must return base value, top SHAP features, and counterfactuals."""
    response = client.post("/explain?top_n=3&total_cfs=2", json=high_risk_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["score_id"] == "app-high-001"
    assert isinstance(body["base_value"], float)
    assert len(body["top_features"]) == 3
    for item in body["top_features"]:
        assert item["direction"] in {"increases_risk", "decreases_risk"}
    # High-risk applicant should have at least one actionable change
    assert len(body["counterfactuals"]) >= 1
    assert {"parameter", "current_value", "target_value"} <= set(body["counterfactuals"][0])


def test_endpoints_return_503_without_model(low_risk_payload: dict[str, object]) -> None:
    """Predict and explain must fail with 503 when no model is loaded."""
    bare_client = TestClient(create_app(registry=ModelRegistry()))
    assert bare_client.post("/predict", json=low_risk_payload).status_code == 503
    assert bare_client.post("/explain", json=low_risk_payload).status_code == 503
    health_body = bare_client.get("/health").json()
    assert health_body["model_loaded"] is False


def test_load_registry_missing_artifact(tmp_path: object) -> None:
    """load_registry must return an empty registry for a missing artifact."""
    registry = load_registry(model_path=str(tmp_path) + "/nope.joblib")
    assert registry.model_loaded is False
    assert registry.expected_features == []


def test_load_registry_from_artifact(tmp_path: object) -> None:
    """load_registry must restore predictor, explainer, and feature order."""
    from src.ml.train import save_model_artifact

    train_df = _make_training_frame(100)
    model = XGBClassifier(n_estimators=5, max_depth=2, random_state=42)
    model.fit(train_df[FEATURES], train_df["is_default"])
    path = f"{tmp_path}/model.joblib"
    save_model_artifact(model, path)

    registry = load_registry(model_path=path)
    assert registry.model_loaded is True
    assert registry.expected_features == FEATURES
    assert registry.explainer is not None
