"""Unit tests for the survival analysis models (Cox PH + DeepSurv)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ml.survival import (
    DURATION_COL,
    EVENT_COL,
    SurvivalAnalysis,
    derive_survival_data,
)

FEATURES = ["int_rate", "dti_eff"]


def _survival_frame(n: int = 400, seed: int = 0) -> pd.DataFrame:
    """Synthetic frame where higher int_rate/dti shortens time to default."""
    rng = np.random.default_rng(seed)
    int_rate = rng.uniform(5, 30, n)
    dti = rng.uniform(5, 45, n)
    hazard = 0.02 * np.exp(0.08 * (int_rate - 15) + 0.03 * (dti - 25))
    event_time = rng.exponential(1.0 / hazard)
    censor_time = np.full(n, 36.0)
    duration = np.minimum(event_time, censor_time)
    event = (event_time <= censor_time).astype(int)
    return pd.DataFrame(
        {
            "int_rate": int_rate,
            "dti_eff": dti,
            DURATION_COL: np.clip(duration, 1.0, 36.0),
            EVENT_COL: event,
        }
    )


def test_derive_survival_data_with_end_date() -> None:
    """Durations must come from issue->last payment, clipped to the term."""
    df = pd.DataFrame(
        {
            "issue_d": pd.to_datetime(["2015-01-01", "2015-01-01", "2015-01-01"]),
            "last_pymnt_date": pd.to_datetime(["2016-01-01", "2020-01-01", None]),
            "term_months": [36, 36, 36],
            "is_default": [1, 0, 0],
        }
    )
    out = derive_survival_data(df)
    assert out[EVENT_COL].tolist() == [1, 0, 0]
    assert out[DURATION_COL].iloc[0] == pytest.approx(12.0, abs=0.5)
    assert out[DURATION_COL].iloc[1] == 36.0  # clipped to term
    assert out[DURATION_COL].iloc[2] == 36.0  # missing end date -> term


def test_derive_survival_data_without_end_date_falls_back_to_term() -> None:
    """Without a last-payment column, the term is the censoring horizon."""
    df = pd.DataFrame({"issue_d": ["2015-01-01"], "term_months": [60], "is_default": [0.0]})
    out = derive_survival_data(df)
    assert out[DURATION_COL].iloc[0] == 60.0
    assert out[EVENT_COL].iloc[0] == 0


def test_derive_survival_data_drops_unknown_outcomes() -> None:
    """Rows with a NULL outcome (ongoing loans) must be dropped."""
    df = pd.DataFrame(
        {
            "issue_d": ["2015-01-01", "2015-01-01"],
            "term_months": [36, 36],
            "is_default": [1.0, None],
        }
    )
    assert len(derive_survival_data(df)) == 1


def test_unsupported_model_type_rejected() -> None:
    """Only cox and deepsurv are valid backends."""
    with pytest.raises(ValueError, match="Unsupported model_type"):
        SurvivalAnalysis(model_type="weibull")


def test_predict_before_fit_raises() -> None:
    """Predicting before fit must raise a clear error."""
    model = SurvivalAnalysis("cox")
    with pytest.raises(ValueError, match="not fitted"):
        model.predict_survival_function(pd.DataFrame({f: [1.0] for f in FEATURES}))


@pytest.fixture(scope="module")
def cox_fitted() -> tuple[SurvivalAnalysis, pd.DataFrame]:
    """Fit the Cox model once for the module."""
    df = _survival_frame()
    model = SurvivalAnalysis("cox").fit(df, FEATURES)
    return model, df


@pytest.fixture(scope="module")
def deepsurv_fitted() -> tuple[SurvivalAnalysis, pd.DataFrame]:
    """Fit a small DeepSurv model once for the module."""
    pytest.importorskip("pycox")
    pytest.importorskip("torch")
    df = _survival_frame(seed=1)
    model = SurvivalAnalysis(
        "deepsurv", params={"epochs": 5, "hidden_layers": [16], "batch_size": 64}
    ).fit(df, FEATURES)
    return model, df


class TestCox:
    """Cox PH baseline behavior on separable synthetic data."""

    def test_survival_function_shape_and_monotonicity(
        self, cox_fitted: tuple[SurvivalAnalysis, pd.DataFrame]
    ) -> None:
        """Curves must have one column per row and be non-increasing in [0, 1]."""
        model, df = cox_fitted
        surv = model.predict_survival_function(df[FEATURES].head(5))
        assert surv.shape[1] == 5
        values = surv.to_numpy()
        assert ((values >= 0) & (values <= 1.0 + 1e-9)).all()
        assert (np.diff(values, axis=0) <= 1e-9).all()

    def test_riskier_applicant_has_shorter_median(
        self, cox_fitted: tuple[SurvivalAnalysis, pd.DataFrame]
    ) -> None:
        """High int_rate/dti must imply an earlier (or equal) median default time."""
        model, _ = cox_fitted
        pair = pd.DataFrame({"int_rate": [6.0, 29.0], "dti_eff": [8.0, 44.0]})
        medians = model.predict_median_survival_time(pair)
        assert medians[1] <= medians[0]

    def test_survival_probability_at_horizons(
        self, cox_fitted: tuple[SurvivalAnalysis, pd.DataFrame]
    ) -> None:
        """Horizon probabilities must be decreasing across 12/24/36 months."""
        model, df = cox_fitted
        probs = model.survival_probability_at(df[FEATURES].head(1), [12.0, 24.0, 36.0])
        row = probs.iloc[0]
        assert row[12.0] >= row[24.0] >= row[36.0]
        assert 0.0 <= row[36.0] <= 1.0

    def test_log_likelihood_available(
        self, cox_fitted: tuple[SurvivalAnalysis, pd.DataFrame]
    ) -> None:
        """The Cox partial log-likelihood must be a finite float."""
        model, _ = cox_fitted
        ll = model.log_likelihood()
        assert ll is not None and np.isfinite(ll)


class TestDeepSurv:
    """DeepSurv variant — runs only when the optional deepsurv extra is installed."""

    def test_survival_function_and_horizons(
        self, deepsurv_fitted: tuple[SurvivalAnalysis, pd.DataFrame]
    ) -> None:
        """DeepSurv curves must be valid probabilities with per-row columns."""
        model, df = deepsurv_fitted
        surv = model.predict_survival_function(df[FEATURES].head(3))
        assert surv.shape[1] == 3
        values = surv.to_numpy()
        assert ((values >= -1e-6) & (values <= 1.0 + 1e-6)).all()
        probs = model.survival_probability_at(df[FEATURES].head(1), [12.0, 36.0])
        assert probs.iloc[0][12.0] >= probs.iloc[0][36.0] - 1e-9

    def test_log_likelihood_none_for_deepsurv(
        self, deepsurv_fitted: tuple[SurvivalAnalysis, pd.DataFrame]
    ) -> None:
        """log_likelihood is a Cox-only diagnostic."""
        model, _ = deepsurv_fitted
        assert model.log_likelihood() is None


def test_deepsurv_without_extra_raises_import_error() -> None:
    """Without pycox/torch, fitting deepsurv must raise a helpful ImportError."""
    import builtins
    from unittest.mock import patch

    real_import = builtins.__import__

    def _no_torch(name: str, *args: object, **kwargs: object) -> object:
        if name in {"torch", "torchtuples", "pycox.models", "pycox"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    df = _survival_frame(n=50)
    with patch.object(builtins, "__import__", side_effect=_no_torch):
        with pytest.raises(ImportError, match="deepsurv"):
            SurvivalAnalysis("deepsurv").fit(df, FEATURES)
