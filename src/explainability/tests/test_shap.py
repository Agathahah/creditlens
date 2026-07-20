"""Unit tests for the SHAP explainability module."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from src.explainability.shap_explainer import ShapExplainer, build_shap_records

FEATURES = ["loan_amnt", "int_rate", "dti_eff", "annual_inc", "revol_util_clean"]


@pytest.fixture
def dataset() -> tuple[pd.DataFrame, pd.Series]:
    """Synthetic feature matrix with a signal-bearing target."""
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(300, len(FEATURES))), columns=FEATURES)
    # Target depends on int_rate and dti_eff so SHAP has real signal
    logits = 1.5 * X["int_rate"] + 1.0 * X["dti_eff"] + rng.normal(scale=0.5, size=300)
    y = pd.Series((logits > 0.5).astype(int))
    return X, y


@pytest.fixture
def xgb_explainer(dataset: tuple[pd.DataFrame, pd.Series]) -> tuple[ShapExplainer, pd.DataFrame]:
    """Fitted XGBoost model wrapped in a ShapExplainer."""
    X, y = dataset
    model = XGBClassifier(n_estimators=20, max_depth=3, random_state=42)
    model.fit(X, y)
    return ShapExplainer(model), X


def test_shap_values_shape(xgb_explainer: tuple[ShapExplainer, pd.DataFrame]) -> None:
    """SHAP values must be 2D and aligned with the input matrix."""
    explainer, X = xgb_explainer
    values = explainer.shap_values(X.head(20))
    assert values.shape == (20, len(FEATURES))
    assert np.isfinite(values).all()


def test_global_feature_importance_ranking(
    xgb_explainer: tuple[ShapExplainer, pd.DataFrame],
) -> None:
    """Global importance must rank signal features highest and sort descending."""
    explainer, X = xgb_explainer
    importance = explainer.global_feature_importance(X)

    assert set(importance.keys()) == set(FEATURES)
    scores = list(importance.values())
    assert scores == sorted(scores, reverse=True)
    # int_rate and dti_eff carry the target signal
    top_two = list(importance.keys())[:2]
    assert set(top_two) == {"int_rate", "dti_eff"}


def test_explain_single_structure(xgb_explainer: tuple[ShapExplainer, pd.DataFrame]) -> None:
    """Local explanation must be JSON-serializable with expected keys."""
    explainer, X = xgb_explainer
    explanation = explainer.explain_single(X.iloc[[0]], top_n=3)

    assert isinstance(explanation["base_value"], float)
    assert set(explanation["shap_contributions"].keys()) == set(FEATURES)
    assert len(explanation["top_features"]) == 3
    for item in explanation["top_features"]:
        assert item["direction"] in {"increases_risk", "decreases_risk"}


def test_explain_single_rejects_multiple_rows(
    xgb_explainer: tuple[ShapExplainer, pd.DataFrame],
) -> None:
    """explain_single must reject multi-row inputs."""
    explainer, X = xgb_explainer
    with pytest.raises(ValueError, match="exactly one row"):
        explainer.explain_single(X.head(2))


def test_linear_model_requires_background(dataset: tuple[pd.DataFrame, pd.Series]) -> None:
    """Non-tree models require background data; with it, values are produced."""
    X, y = dataset
    model = LogisticRegression(max_iter=500).fit(X, y)

    with pytest.raises(ValueError, match="background_data"):
        ShapExplainer(model)

    explainer = ShapExplainer(model, background_data=X.head(100))
    values = explainer.shap_values(X.head(5))
    assert values.shape == (5, len(FEATURES))


def test_build_shap_records(xgb_explainer: tuple[ShapExplainer, pd.DataFrame]) -> None:
    """DB records must align loan ids with per-feature SHAP maps."""
    explainer, X = xgb_explainer
    values = explainer.shap_values(X.head(2))
    records = build_shap_records(["loan-1", "loan-2"], values, FEATURES, "xgboost")

    assert len(records) == 2
    assert records[0]["loan_id"] == "loan-1"
    assert records[0]["model_name"] == "xgboost"
    assert set(records[0]["shap_values"].keys()) == set(FEATURES)
    assert "created_at" in records[0]


def test_build_shap_records_length_mismatch(
    xgb_explainer: tuple[ShapExplainer, pd.DataFrame],
) -> None:
    """Mismatched loan id count must raise."""
    explainer, X = xgb_explainer
    values = explainer.shap_values(X.head(2))
    with pytest.raises(ValueError, match="must match"):
        build_shap_records(["loan-1"], values, FEATURES, "xgboost")
