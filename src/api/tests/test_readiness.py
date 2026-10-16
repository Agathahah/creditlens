"""Probe and scoring contracts using synthetic injected models only."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.state import ModelRegistry
from src.ml.predict import CreditPredictor


class SyntheticModel:
    """Deterministic software fixture, not a fitted credit model."""

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray[Any, Any]:
        """Return fixed probabilities for contract testing.

        Args:
            frame: Input rows.

        Returns:
            Two-class probabilities for every row.
        """
        return np.tile([0.9, 0.1], (len(frame), 1))


def test_empty_registry_is_alive_but_unready() -> None:
    """A responsive process must not imply an available scoring bundle."""
    client = TestClient(create_app(ModelRegistry()))
    assert client.get("/live").status_code == 200
    assert client.get("/health").status_code == 200
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "model_loaded": False,
        "bundle_verified": False,
    }


def test_loaded_legacy_model_is_unready_and_cannot_score() -> None:
    """Loading arbitrary weights is insufficient to allow inference."""
    registry = ModelRegistry(
        predictor=CreditPredictor(model=SyntheticModel()), expected_features=["annual_inc"]
    )
    client = TestClient(create_app(registry))
    assert client.get("/health").json()["model_loaded"] is True
    assert client.get("/ready").status_code == 503
    assert client.post("/predict", json={"features": {"annual_inc": 60000}}).status_code == 503
    assert client.post("/explain", json={"features": {"annual_inc": 60000}}).status_code == 503


def test_verified_synthetic_fixture_is_ready_for_prediction_only() -> None:
    """A verified injected fixture can score while optional explanation is absent."""
    registry = ModelRegistry(
        predictor=CreditPredictor(model=SyntheticModel()),
        expected_features=["annual_inc"],
        bundle_verified=True,
    )
    client = TestClient(create_app(registry))
    assert client.get("/ready").status_code == 200
    response = client.post("/predict", json={"features": {"annual_inc": 60000}})
    assert response.status_code == 200
    assert response.json()["risk_score"] == 0.1
    assert client.post("/explain", json={"features": {"annual_inc": 60000}}).status_code == 503


def test_verified_marker_without_schema_or_model_is_insufficient() -> None:
    """Incomplete bundle contracts fail even when a verification flag is present."""
    for registry in (
        ModelRegistry(bundle_verified=True, expected_features=["annual_inc"]),
        ModelRegistry(predictor=CreditPredictor(model=SyntheticModel()), bundle_verified=True),
    ):
        client = TestClient(create_app(registry))
        assert client.get("/ready").status_code == 503
