"""Unit tests for the AIF360 fairness audit module."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.fairness.fairness_audit import (
    audit_model,
    binarize_protected_attribute,
    compute_fairness_metrics,
    is_within_di_policy,
)


@pytest.fixture
def fair_frame() -> pd.DataFrame:
    """Frame where predictions are identical across groups (perfectly fair)."""
    protected_raw = ["MORTGAGE"] * 100 + ["RENT"] * 100
    y_true = ([0] * 80 + [1] * 20) * 2
    y_pred = ([0] * 80 + [1] * 20) * 2
    return pd.DataFrame(
        {"home_ownership": protected_raw, "is_default": y_true, "pred_default": y_pred}
    )


@pytest.fixture
def biased_frame() -> pd.DataFrame:
    """Frame where the unprivileged group is rejected far more often."""
    n_priv, n_unpriv = 100, 100
    rng = np.random.default_rng(0)
    protected_raw = ["MORTGAGE"] * n_priv + ["RENT"] * n_unpriv
    y_true = list(rng.choice([0, 1], n_priv, p=[0.85, 0.15])) + list(
        rng.choice([0, 1], n_unpriv, p=[0.85, 0.15])
    )
    # Privileged group almost always approved, unprivileged mostly rejected
    y_pred = [0] * n_priv + [1] * 90 + [0] * 10
    return pd.DataFrame(
        {"home_ownership": protected_raw, "is_default": y_true, "pred_default": y_pred}
    )


def test_binarize_protected_attribute() -> None:
    """Privileged values map to 1, everything else to 0."""
    series = pd.Series(["MORTGAGE", "OWN", "RENT", "OTHER"])
    result = binarize_protected_attribute(series, ["MORTGAGE", "OWN"])
    assert result.tolist() == [1, 1, 0, 0]


def test_fair_predictions_have_di_near_one(fair_frame: pd.DataFrame) -> None:
    """Identical group outcomes must yield DI ~ 1 and zero differences."""
    protected = binarize_protected_attribute(fair_frame["home_ownership"], ["MORTGAGE"])
    metrics = compute_fairness_metrics(
        fair_frame["is_default"], fair_frame["pred_default"], protected
    )
    assert metrics["disparate_impact_ratio"] == pytest.approx(1.0)
    assert metrics["statistical_parity_difference"] == pytest.approx(0.0)
    assert metrics["equal_opportunity_difference"] == pytest.approx(0.0)


def test_biased_predictions_flagged(biased_frame: pd.DataFrame) -> None:
    """Heavily skewed rejections must produce DI far below policy band."""
    protected = binarize_protected_attribute(biased_frame["home_ownership"], ["MORTGAGE"])
    metrics = compute_fairness_metrics(
        biased_frame["is_default"], biased_frame["pred_default"], protected
    )
    assert metrics["disparate_impact_ratio"] < 0.8
    assert metrics["statistical_parity_difference"] < 0.0
    assert not is_within_di_policy(metrics["disparate_impact_ratio"])


def test_is_within_di_policy_band() -> None:
    """Policy band is [0.8, 1.25]; non-finite ratios always fail."""
    assert is_within_di_policy(1.0)
    assert is_within_di_policy(0.8)
    assert is_within_di_policy(1.25)
    assert not is_within_di_policy(0.79)
    assert not is_within_di_policy(1.26)
    assert not is_within_di_policy(float("nan"))
    assert not is_within_di_policy(float("inf"))


def test_audit_model_report_structure(fair_frame: pd.DataFrame) -> None:
    """Audit report must include per-attribute metrics and overall verdict."""
    report = audit_model(
        fair_frame,
        y_true_col="is_default",
        y_pred_col="pred_default",
        protected_attributes={"home_ownership": ["MORTGAGE", "OWN"]},
        model_name="xgboost",
    )
    assert report["model_name"] == "xgboost"
    assert report["policy_band"] == {"lower": 0.8, "upper": 1.25}
    attr_report = report["attributes"]["home_ownership"]
    assert attr_report["di_within_policy"] is True
    assert "disparate_impact_ratio" in attr_report["metrics"]
    assert report["overall_pass"] is True


def test_audit_model_fails_on_bias(biased_frame: pd.DataFrame) -> None:
    """Audit must fail overall when any attribute violates the DI band."""
    report = audit_model(
        biased_frame,
        y_true_col="is_default",
        y_pred_col="pred_default",
        protected_attributes={"home_ownership": ["MORTGAGE"]},
    )
    assert report["overall_pass"] is False
    assert report["attributes"]["home_ownership"]["di_within_policy"] is False
