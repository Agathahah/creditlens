"""Survival analysis for CreditLens — WHEN does default happen (CLAUDE.md).

Implements time-to-default modeling on top of the mart features:

- **Cox Proportional Hazards** (lifelines) as the interpretable baseline.
- **DeepSurv** (pycox + torch) as the deep-learning variant, behind a lazy
  import so the heavy torch stack stays an optional dependency
  (``pip install creditlens[deepsurv]``).

Durations are derived from the loan lifecycle: months from ``issue_d`` to
``last_pymnt_date`` when available, otherwise the loan term; the event is
default (``is_default``), everything else is right-censored.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.common.logging import configure_logging

configure_logging()

DURATION_COL: str = "duration_months"
EVENT_COL: str = "event"


def derive_survival_data(
    df: pd.DataFrame,
    issue_col: str = "issue_d",
    end_col: str = "last_pymnt_date",
    term_col: str = "term_months",
    event_col: str = "is_default",
) -> pd.DataFrame:
    """Derive (duration, event) columns from loan lifecycle fields.

    Duration is the observed months from issue to the last payment when
    ``end_col`` exists (clipped to [1, term]); otherwise the loan term is
    used as the censoring horizon. The event indicator is default.

    Args:
        df: Frame containing the lifecycle columns.
        issue_col: Loan issue date column.
        end_col: Last observed payment date column (optional in the mart).
        term_col: Loan term in months.
        event_col: Binary default indicator.

    Returns:
        Copy of ``df`` (rows with a known outcome) plus DURATION_COL and
        EVENT_COL.
    """
    out = df.dropna(subset=[event_col]).copy()
    out[EVENT_COL] = out[event_col].astype(int)
    term = pd.to_numeric(out[term_col], errors="coerce").fillna(36.0)

    if end_col in out.columns:
        elapsed = (pd.to_datetime(out[end_col]) - pd.to_datetime(out[issue_col])).dt.days / 30.44
        duration = elapsed.fillna(term)
    else:
        duration = term.astype(float)

    out[DURATION_COL] = np.clip(duration, 1.0, term).astype(float)
    return out


class SurvivalAnalysis:
    """Time-to-default model with Cox PH and DeepSurv backends."""

    def __init__(self, model_type: str = "cox", params: dict[str, Any] | None = None) -> None:
        """Initialize the survival model.

        Args:
            model_type: "cox" (lifelines) or "deepsurv" (pycox + torch).
            params: Backend hyperparameter overrides.
        """
        if model_type not in {"cox", "deepsurv"}:
            raise ValueError(f"Unsupported model_type: {model_type}")
        self.model_type = model_type
        self.params = params or {}
        self.model: Any = None
        self.feature_cols: list[str] = []

    def fit(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        duration_col: str = DURATION_COL,
        event_col: str = EVENT_COL,
    ) -> SurvivalAnalysis:
        """Fit the survival model on a prepared survival frame.

        Args:
            df: Frame containing features, duration, and event columns.
            feature_cols: Numeric feature columns to use.
            duration_col: Duration column name.
            event_col: Event indicator column name.

        Returns:
            Self, fitted.
        """
        self.feature_cols = list(feature_cols)
        train = df[self.feature_cols + [duration_col, event_col]].astype(float)
        if self.model_type == "cox":
            self._fit_cox(train, duration_col, event_col)
        else:
            self._fit_deepsurv(train, duration_col, event_col)
        return self

    def _fit_cox(self, train: pd.DataFrame, duration_col: str, event_col: str) -> None:
        """Fit the lifelines Cox PH baseline.

        Args:
            train: Numeric training frame.
            duration_col: Duration column name.
            event_col: Event indicator column name.
        """
        from lifelines import CoxPHFitter

        penalizer = float(self.params.get("penalizer", 0.1))
        self.model = CoxPHFitter(penalizer=penalizer)
        self.model.fit(train, duration_col=duration_col, event_col=event_col)

    def _fit_deepsurv(self, train: pd.DataFrame, duration_col: str, event_col: str) -> None:
        """Fit the DeepSurv variant (pycox CoxPH over an MLP).

        Args:
            train: Numeric training frame.
            duration_col: Duration column name.
            event_col: Event indicator column name.

        Raises:
            ImportError: When the optional deepsurv extra is not installed.
        """
        try:
            import torch  # noqa: F401
            import torchtuples as tt
            from pycox.models import CoxPH as PycoxCoxPH
        except ImportError as exc:  # pragma: no cover - exercised via tests with fakes
            raise ImportError(
                "DeepSurv requires the optional extra: pip install creditlens[deepsurv]"
            ) from exc

        x = train[self.feature_cols].to_numpy(dtype="float32")
        y = (
            train[duration_col].to_numpy(dtype="float32"),
            train[event_col].to_numpy(dtype="float32"),
        )
        net = tt.practical.MLPVanilla(
            in_features=x.shape[1],
            num_nodes=list(self.params.get("hidden_layers", [32, 32])),
            out_features=1,
            batch_norm=True,
            dropout=float(self.params.get("dropout", 0.1)),
        )
        self.model = PycoxCoxPH(net, tt.optim.Adam(lr=float(self.params.get("lr", 0.01))))
        self.model.fit(
            x,
            y,
            batch_size=int(self.params.get("batch_size", 128)),
            epochs=int(self.params.get("epochs", 20)),
            verbose=False,
        )
        self.model.compute_baseline_hazards()

    def predict_survival_function(self, X: pd.DataFrame) -> pd.DataFrame:
        """Predict per-individual survival curves S(t | x).

        Args:
            X: Feature frame (columns must cover ``feature_cols``).

        Returns:
            DataFrame indexed by time (months) with one column per row of X.
        """
        self._require_fitted()
        features = X[self.feature_cols].astype(float)
        if self.model_type == "cox":
            surv = self.model.predict_survival_function(features)
        else:
            surv = self.model.predict_surv_df(features.to_numpy(dtype="float32"))
        surv.columns = range(len(features))
        return surv

    def predict_median_survival_time(self, X: pd.DataFrame) -> np.ndarray:
        """Predict each individual's median survival time in months.

        Args:
            X: Feature frame.

        Returns:
            Array of median times; inf when the curve never crosses 0.5.
        """
        surv = self.predict_survival_function(X)
        times = surv.index.to_numpy(dtype=float)
        medians = np.full(surv.shape[1], np.inf)
        values = surv.to_numpy()
        for j in range(values.shape[1]):
            below = np.nonzero(values[:, j] <= 0.5)[0]
            if below.size:
                medians[j] = times[below[0]]
        return medians

    def survival_probability_at(self, X: pd.DataFrame, horizons: list[float]) -> pd.DataFrame:
        """Evaluate survival probabilities at fixed horizons.

        Uses step (previous-value) interpolation of the survival curve.

        Args:
            X: Feature frame.
            horizons: Times (months) at which to evaluate S(t).

        Returns:
            DataFrame with one row per individual and one column per horizon.
        """
        surv = self.predict_survival_function(X)
        times = surv.index.to_numpy(dtype=float)
        values = surv.to_numpy()
        result = {}
        for horizon in horizons:
            idx = np.searchsorted(times, horizon, side="right") - 1
            result[horizon] = values[idx, :] if idx >= 0 else np.ones(values.shape[1])
        return pd.DataFrame(result, index=range(values.shape[1]))

    def log_likelihood(self) -> float | None:
        """Return the fitted model's log-likelihood (Cox only).

        Returns:
            The Cox partial log-likelihood, or None for DeepSurv.
        """
        self._require_fitted()
        if self.model_type == "cox":
            return float(self.model.log_likelihood_)
        return None

    def _require_fitted(self) -> None:
        """Raise if the model has not been fitted.

        Raises:
            ValueError: When fit() has not been called.
        """
        if self.model is None:
            raise ValueError("SurvivalAnalysis model is not fitted; call fit() first.")


def load_survival_frame(postgres_url: str | None = None) -> pd.DataFrame:
    """Load mart.final_features and derive the survival columns.

    Args:
        postgres_url: Optional database URL override.

    Returns:
        Survival-ready frame with DURATION_COL and EVENT_COL.
    """
    from src.features.features import load_feature_data

    return derive_survival_data(load_feature_data(postgres_url))
