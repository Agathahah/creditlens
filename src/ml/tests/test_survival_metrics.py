"""Unit tests for survival evaluation metrics (C-index, Brier, IBS)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ml.survival_metrics import (
    brier_score_at,
    concordance_index,
    integrated_brier_score,
)


def test_concordance_index_perfect_and_random() -> None:
    """Perfectly ordered scores give C=1; anti-ordered give C=0."""
    durations = np.array([5.0, 10.0, 15.0, 20.0])
    events = np.array([1, 1, 1, 1])
    assert concordance_index(durations, durations, events) == pytest.approx(1.0)
    assert concordance_index(durations, -durations, events) == pytest.approx(0.0)


def test_concordance_index_handles_censoring() -> None:
    """Censored pairs must not break the C-index computation."""
    durations = np.array([5.0, 10.0, 15.0, 20.0])
    events = np.array([1, 0, 1, 0])
    cindex = concordance_index(durations, np.array([6.0, 9.0, 16.0, 22.0]), events)
    assert 0.0 <= cindex <= 1.0


def test_brier_score_perfect_predictions_near_zero() -> None:
    """Confident correct predictions yield a near-zero Brier score."""
    durations = np.array([5.0, 30.0, 6.0, 32.0])
    events = np.array([1, 0, 1, 0])
    # S(t=12): defaulted-by-12 individuals ~0, survivors ~1
    survival_probs = np.array([0.01, 0.99, 0.01, 0.99])
    assert brier_score_at(durations, events, survival_probs, t=12.0) < 0.05


def test_brier_score_wrong_predictions_high() -> None:
    """Confident wrong predictions yield a high Brier score."""
    durations = np.array([5.0, 30.0, 6.0, 32.0])
    events = np.array([1, 0, 1, 0])
    survival_probs = np.array([0.99, 0.01, 0.99, 0.01])
    assert brier_score_at(durations, events, survival_probs, t=12.0) > 0.5


def test_integrated_brier_score_over_grid() -> None:
    """IBS must integrate per-horizon scores into a bounded scalar."""
    durations = np.array([5.0, 30.0, 6.0, 32.0, 18.0])
    events = np.array([1, 0, 1, 0, 1])
    times = np.array([6.0, 12.0, 24.0])
    curve = pd.DataFrame(
        np.tile(np.array([[0.9], [0.8], [0.6]]), (1, 5)),
        index=[6.0, 12.0, 24.0],
    )
    ibs = integrated_brier_score(durations, events, curve, times)
    assert 0.0 <= ibs <= 1.0


def test_integrated_brier_score_requires_grid() -> None:
    """A single-horizon grid must be rejected."""
    curve = pd.DataFrame({0: [0.9]}, index=[12.0])
    with pytest.raises(ValueError, match="at least two"):
        integrated_brier_score(np.array([5.0]), np.array([1]), curve, [12.0])


def test_cox_model_beats_random_on_cindex() -> None:
    """End-to-end: a fitted Cox model's medians must out-rank random scores."""
    from src.ml.survival import DURATION_COL, EVENT_COL, SurvivalAnalysis
    from src.ml.tests.test_survival import FEATURES, _survival_frame

    df = _survival_frame(n=500, seed=7)
    model = SurvivalAnalysis("cox").fit(df, FEATURES)
    medians = model.predict_median_survival_time(df[FEATURES])
    finite = np.where(np.isfinite(medians), medians, 1e6)
    cindex = concordance_index(df[DURATION_COL], finite, df[EVENT_COL])
    assert cindex > 0.6
