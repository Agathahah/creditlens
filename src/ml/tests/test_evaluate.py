"""Unit tests for the model evaluation CLI and PR-AUC gate."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ml import evaluate


def test_evaluate_predictions_returns_metrics() -> None:
    """evaluate_predictions must return the credit metric keys in range."""
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    metrics = evaluate.evaluate_predictions(y_true, y_prob)
    assert set(metrics) == {"pr_auc", "roc_auc", "recall_at_p80", "ks_statistic"}
    assert 0.0 <= metrics["pr_auc"] <= 1.0


def test_passes_threshold_boundary() -> None:
    """The gate must pass at/above the threshold and fail below it."""
    assert evaluate.passes_threshold({"pr_auc": 0.25}, 0.25) is True
    assert evaluate.passes_threshold({"pr_auc": 0.30}, 0.25) is True
    assert evaluate.passes_threshold({"pr_auc": 0.20}, 0.25) is False
    assert evaluate.passes_threshold({}, 0.25) is False


def test_write_metrics_creates_json(tmp_path: Path) -> None:
    """_write_metrics must serialize metrics to metrics.json."""
    out = tmp_path / "results"
    evaluate._write_metrics({"pr_auc": 0.42}, str(out))
    written = json.loads((out / "metrics.json").read_text())
    assert written["pr_auc"] == 0.42


def test_main_returns_zero_when_above_threshold() -> None:
    """main must exit 0 when PR-AUC clears the gate."""
    with patch.object(evaluate, "run_evaluation", return_value={"pr_auc": 0.5, "roc_auc": 0.7}):
        code = evaluate.main(["--threshold-check", "--pr-auc-min", "0.25"])
    assert code == 0


def test_main_returns_one_when_below_threshold() -> None:
    """main must exit 1 when PR-AUC is below the gate."""
    with patch.object(evaluate, "run_evaluation", return_value={"pr_auc": 0.1, "roc_auc": 0.5}):
        code = evaluate.main(["--threshold-check", "--pr-auc-min", "0.25"])
    assert code == 1


def test_main_skips_gate_without_flag() -> None:
    """Without --threshold-check, a low PR-AUC still exits 0."""
    with patch.object(evaluate, "run_evaluation", return_value={"pr_auc": 0.0, "roc_auc": 0.5}):
        code = evaluate.main([])
    assert code == 0
