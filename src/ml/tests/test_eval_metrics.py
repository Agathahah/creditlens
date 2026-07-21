"""Unit tests for extended evaluation metrics and diagnostic plots."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.ml.eval_metrics import (
    best_threshold,
    calibration_metrics,
    confusion_at_threshold,
    extended_metrics,
    save_evaluation_artifacts,
)


def _separable_predictions() -> tuple[np.ndarray, np.ndarray]:
    """Build a well-separated label/probability pair."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_prob = np.array([0.05, 0.1, 0.2, 0.3, 0.7, 0.8, 0.9, 0.95])
    return y_true, y_prob


def test_best_threshold_separates_classes() -> None:
    """The optimal threshold must fall between the class score clusters."""
    y_true, y_prob = _separable_predictions()
    thr = best_threshold(y_true, y_prob)
    assert 0.3 < thr <= 0.7


def test_confusion_at_threshold_perfect_split() -> None:
    """At a separating threshold, off-diagonal counts must be zero."""
    y_true, y_prob = _separable_predictions()
    cm = confusion_at_threshold(y_true, y_prob, 0.5)
    assert cm == {"tn": 4, "fp": 0, "fn": 0, "tp": 4}


def test_calibration_metrics_bounds() -> None:
    """Brier score and ECE must be within their valid ranges."""
    y_true, y_prob = _separable_predictions()
    cal = calibration_metrics(y_true, y_prob)
    assert 0.0 <= cal["brier_score"] <= 1.0
    assert 0.0 <= cal["ece"] <= 1.0


def test_extended_metrics_has_all_keys() -> None:
    """extended_metrics must include credit, threshold, confusion, calibration."""
    y_true, y_prob = _separable_predictions()
    metrics = extended_metrics(y_true, y_prob)
    for key in (
        "pr_auc",
        "roc_auc",
        "ks_statistic",
        "best_threshold",
        "confusion_matrix",
        "brier_score",
        "ece",
    ):
        assert key in metrics
    assert set(metrics["confusion_matrix"]) == {"tn", "fp", "fn", "tp"}


def test_save_evaluation_artifacts_writes_all_plots(tmp_path: Path) -> None:
    """All four diagnostic plots must be written to disk."""
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, 200)
    y_prob = rng.uniform(size=200)
    cm = confusion_at_threshold(y_true, y_prob, 0.5)

    paths = save_evaluation_artifacts(y_true, y_prob, cm, str(tmp_path))

    names = {Path(p).name for p in paths}
    assert names == {
        "roc_curve.png",
        "pr_curve.png",
        "confusion_matrix.png",
        "calibration_curve.png",
    }
    assert all(Path(p).exists() and Path(p).stat().st_size > 0 for p in paths)
