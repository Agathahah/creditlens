"""Survival model evaluation metrics for CreditLens.

Implements the standard time-to-event metrics: Concordance Index
(discrimination), time-dependent Brier score with IPCW censoring weights
(calibration), and its integral (IBS). The Cox partial log-likelihood is
exposed on ``SurvivalAnalysis.log_likelihood()``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.common.logging import configure_logging

configure_logging()


def concordance_index(
    durations: np.ndarray | pd.Series,
    predicted_scores: np.ndarray | pd.Series,
    events: np.ndarray | pd.Series,
) -> float:
    """Compute the C-index for survival predictions.

    Args:
        durations: Observed durations.
        predicted_scores: Predicted survival scores where **higher means
            longer expected survival** (e.g. predicted median time).
        events: Event indicators (1 = default observed).

    Returns:
        Concordance index in [0, 1]; 0.5 is random.
    """
    from lifelines.utils import concordance_index as _cindex

    return float(_cindex(np.asarray(durations), np.asarray(predicted_scores), np.asarray(events)))


def _censoring_survival(durations: np.ndarray, events: np.ndarray) -> pd.Series:
    """Kaplan-Meier estimate of the censoring distribution G(t).

    Args:
        durations: Observed durations.
        events: Event indicators (1 = event; censoring is the complement).

    Returns:
        Step-function series of G(t) indexed by time.
    """
    from lifelines import KaplanMeierFitter

    km = KaplanMeierFitter()
    km.fit(durations, event_observed=1 - events)
    return km.survival_function_.iloc[:, 0]


def _step_value(series: pd.Series, t: float) -> float:
    """Evaluate a right-continuous step function at time t.

    Args:
        series: Step values indexed by time.
        t: Evaluation time.

    Returns:
        The step-function value at t (1.0 before the first step).
    """
    times = series.index.to_numpy(dtype=float)
    idx = np.searchsorted(times, t, side="right") - 1
    return float(series.iloc[idx]) if idx >= 0 else 1.0


def brier_score_at(
    durations: np.ndarray | pd.Series,
    events: np.ndarray | pd.Series,
    survival_probs: np.ndarray | pd.Series,
    t: float,
) -> float:
    """Time-dependent Brier score at horizon t with IPCW weighting.

    Args:
        durations: Observed durations.
        events: Event indicators (1 = default).
        survival_probs: Predicted S(t | x_i) for each individual at t.
        t: Evaluation horizon.

    Returns:
        The (weighted) Brier score at t.
    """
    dur = np.asarray(durations, dtype=float)
    evt = np.asarray(events, dtype=int)
    s_hat = np.asarray(survival_probs, dtype=float)
    g = _censoring_survival(dur, evt)

    total = 0.0
    for d_i, e_i, s_i in zip(dur, evt, s_hat):
        if d_i <= t and e_i == 1:
            weight = max(_step_value(g, d_i - 1e-9), 1e-6)
            total += (0.0 - s_i) ** 2 / weight
        elif d_i > t:
            weight = max(_step_value(g, t), 1e-6)
            total += (1.0 - s_i) ** 2 / weight
    return float(total / len(dur))


def integrated_brier_score(
    durations: np.ndarray | pd.Series,
    events: np.ndarray | pd.Series,
    survival_curve: pd.DataFrame,
    times: np.ndarray | list[float],
) -> float:
    """Integrated Brier score over a grid of horizons (trapezoid rule).

    Args:
        durations: Observed durations.
        events: Event indicators (1 = default).
        survival_curve: Survival function DataFrame (time index, one column
            per individual) as returned by ``predict_survival_function``.
        times: Increasing evaluation horizons within the observed range.

    Returns:
        The IBS across the horizon grid.
    """
    grid = np.asarray(times, dtype=float)
    if grid.size < 2:
        raise ValueError("times must contain at least two horizons.")
    curve_times = survival_curve.index.to_numpy(dtype=float)
    values = survival_curve.to_numpy()

    scores = []
    for t in grid:
        idx = np.searchsorted(curve_times, t, side="right") - 1
        s_at_t = values[idx, :] if idx >= 0 else np.ones(values.shape[1])
        scores.append(brier_score_at(durations, events, s_at_t, t))
    return float(np.trapezoid(scores, grid) / (grid[-1] - grid[0]))
