"""Unit tests for the DiCE counterfactual explanation module."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from src.common.models import CounterfactualResult
from src.explainability.counterfactual import (
    CounterfactualGenerator,
    _format_value,
    _values_differ,
)

FEATURES = ["dti_eff", "int_rate", "annual_inc", "loan_amnt"]


@pytest.fixture
def training_frame() -> pd.DataFrame:
    """Synthetic training frame where high dti/int_rate drives default."""
    rng = np.random.default_rng(7)
    n = 400
    df = pd.DataFrame(
        {
            "dti_eff": rng.uniform(5, 45, n),
            "int_rate": rng.uniform(5, 30, n),
            "annual_inc": rng.uniform(20_000, 150_000, n),
            "loan_amnt": rng.uniform(1_000, 40_000, n),
        }
    )
    logits = 0.15 * df["dti_eff"] + 0.2 * df["int_rate"] - 8
    df["is_default"] = (logits + rng.normal(scale=1.0, size=n) > 0).astype(int)
    return df


@pytest.fixture
def generator(training_frame: pd.DataFrame) -> CounterfactualGenerator:
    """Fitted logistic model wrapped in a CounterfactualGenerator."""
    model = LogisticRegression(max_iter=1000)
    model.fit(training_frame[FEATURES], training_frame["is_default"])
    return CounterfactualGenerator(
        model=model,
        training_data=training_frame,
        continuous_features=FEATURES,
        outcome_name="is_default",
        method="random",
    )


@pytest.fixture
def high_risk_applicant(training_frame: pd.DataFrame) -> pd.DataFrame:
    """A single applicant the model predicts as default."""
    return pd.DataFrame(
        [{"dti_eff": 44.0, "int_rate": 29.0, "annual_inc": 25_000.0, "loan_amnt": 35_000.0}]
    )


def test_generate_returns_counterfactuals(
    generator: CounterfactualGenerator, high_risk_applicant: pd.DataFrame
) -> None:
    """generate must return a non-empty DataFrame for a rejectable applicant."""
    cf_df = generator.generate(high_risk_applicant, total_cfs=2)
    assert cf_df is not None
    assert len(cf_df) >= 1
    assert set(FEATURES).issubset(cf_df.columns)


def test_explain_produces_change_recommendations(
    generator: CounterfactualGenerator, high_risk_applicant: pd.DataFrame
) -> None:
    """explain must describe at least one feature change toward approval."""
    results = generator.explain(high_risk_applicant, total_cfs=2)
    assert len(results) >= 1
    for item in results:
        assert isinstance(item, CounterfactualResult)
        assert item.parameter in FEATURES
        assert item.current_value != item.target_value


def test_explain_respects_features_to_vary(
    generator: CounterfactualGenerator, high_risk_applicant: pd.DataFrame
) -> None:
    """Restricting varied features must confine recommendations to them."""
    results = generator.explain(
        high_risk_applicant, total_cfs=2, features_to_vary=["dti_eff", "int_rate"]
    )
    for item in results:
        assert item.parameter in {"dti_eff", "int_rate"}


def test_values_differ_numeric_tolerance() -> None:
    """Numeric comparison must tolerate float noise but flag real changes."""
    assert not _values_differ(35.0, 35.0 + 1e-9)
    assert _values_differ(35.0, 25.0)
    assert _values_differ("RENT", "OWN")
    assert not _values_differ("RENT", "RENT")


def test_format_value() -> None:
    """Values must be formatted for human-readable explanations."""
    assert _format_value(25.0) == "25"
    assert _format_value(35.456) == "35.46"
    assert _format_value("MORTGAGE") == "MORTGAGE"
