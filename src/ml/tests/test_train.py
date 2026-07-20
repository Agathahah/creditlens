"""Unit tests for ML model training and inference pipeline."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.common.models import RiskTier
from src.ml.predict import CreditPredictor
from src.ml.train import (
    compute_credit_metrics,
    load_model_artifact,
    save_model_artifact,
    train_model,
)


@pytest.fixture
def synthetic_ml_dataset() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """Fixture generating synthetic train/test matrices for ML tests."""
    np.random.seed(42)
    n_train = 200
    n_test = 50

    features = ["f1", "f2", "f3", "f4", "f5"]

    X_train = pd.DataFrame(np.random.randn(n_train, 5), columns=features)
    y_train = pd.Series(np.random.choice([0, 1], size=n_train, p=[0.8, 0.2]))

    X_test = pd.DataFrame(np.random.randn(n_test, 5), columns=features)
    y_test = pd.Series(np.random.choice([0, 1], size=n_test, p=[0.8, 0.2]))

    return X_train, y_train, X_test, y_test


def test_compute_credit_metrics() -> None:
    """Test computation of credit scoring evaluation metrics."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.15, 0.3, 0.7, 0.85, 0.9, 0.6])

    metrics = compute_credit_metrics(y_true, y_prob)

    assert "pr_auc" in metrics
    assert "roc_auc" in metrics
    assert "recall_at_p80" in metrics
    assert "ks_statistic" in metrics

    assert 0.0 <= metrics["pr_auc"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["ks_statistic"] <= 1.0


def test_train_model_xgboost(
    synthetic_ml_dataset: tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series],
) -> None:
    """Test training XGBoost model."""
    X_train, y_train, X_test, y_test = synthetic_ml_dataset
    model, metrics = train_model(
        X_train, y_train, X_test, y_test, model_type="xgboost", params={"n_estimators": 10}
    )

    assert model is not None
    assert "pr_auc" in metrics
    assert "roc_auc" in metrics


def test_train_model_lightgbm(
    synthetic_ml_dataset: tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series],
) -> None:
    """Test training LightGBM model."""
    X_train, y_train, X_test, y_test = synthetic_ml_dataset
    model, metrics = train_model(
        X_train, y_train, X_test, y_test, model_type="lightgbm", params={"n_estimators": 10}
    )

    assert model is not None
    assert "pr_auc" in metrics


def test_save_and_load_model_artifact(
    synthetic_ml_dataset: tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series],
    tmp_path: Any,
) -> None:
    """Test model serialization and deserialization."""
    X_train, y_train, X_test, y_test = synthetic_ml_dataset
    model, _ = train_model(X_train, y_train, X_test, y_test, model_type="logistic_regression")

    model_path = str(tmp_path / "model.joblib")
    save_model_artifact(model, model_path)
    assert os.path.exists(model_path)

    loaded_model = load_model_artifact(model_path)
    assert loaded_model is not None


def test_credit_predictor(
    synthetic_ml_dataset: tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series],
) -> None:
    """Test CreditPredictor scoring, risk classification, and approval decision."""
    X_train, y_train, X_test, y_test = synthetic_ml_dataset
    model, _ = train_model(X_train, y_train, X_test, y_test, model_type="logistic_regression")

    predictor = CreditPredictor(model=model, approval_threshold=0.20)

    # Test risk tier classification logic
    assert predictor.classify_risk_tier(0.05) == RiskTier.LOW
    assert predictor.classify_risk_tier(0.15) == RiskTier.MEDIUM
    assert predictor.classify_risk_tier(0.40) == RiskTier.HIGH

    # Test single applicant scoring
    single_row = X_test.iloc[[0]]
    result = predictor.score_applicant(single_row, score_id="test-score-123")

    assert result.score_id == "test-score-123"
    assert 0.0 <= result.risk_score <= 1.0
    assert isinstance(result.risk_tier, RiskTier)
    assert isinstance(result.approved, bool)
