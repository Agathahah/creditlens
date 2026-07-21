"""Unit tests for the train.py CLI wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.ml import train


def _fake_frame(n: int = 40) -> pd.DataFrame:
    """Build a minimal frame accepted by the training pipeline."""
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "loan_amnt": rng.uniform(1_000, 40_000, n),
            "int_rate": rng.uniform(5, 30, n),
            "issue_d": pd.date_range("2015-01-01", periods=n, freq="ME"),
            "is_default": rng.integers(0, 2, n),
        }
    )


def test_default_model_paths_cover_all_models() -> None:
    """Every supported model must have a default artifact path."""
    assert set(train.DEFAULT_MODEL_PATHS) == {
        "xgboost",
        "lightgbm",
        "logistic_regression",
    }


def test_run_training_wires_pipeline(tmp_path: object) -> None:
    """run_training must load, split, train, and persist the model."""
    frame = _fake_frame()
    fake_model = MagicMock()

    with (
        patch("src.features.features.load_feature_data", return_value=frame),
        patch.object(train, "train_model", return_value=(fake_model, {"pr_auc": 0.4})) as tm,
        patch.object(train, "save_model_artifact") as save,
    ):
        model, metrics = train.run_training("xgboost", output_path=f"{tmp_path}/m.joblib")

    assert model is fake_model
    assert metrics["pr_auc"] == 0.4
    tm.assert_called_once()
    save.assert_called_once_with(fake_model, f"{tmp_path}/m.joblib")


def test_main_prints_and_returns_zero(capsys: object) -> None:
    """main must run training and report metrics with a zero exit code."""
    with patch.object(
        train, "run_training", return_value=(MagicMock(), {"pr_auc": 0.4, "roc_auc": 0.7})
    ):
        code = train.main(["--model", "lightgbm"])
    assert code == 0


def test_main_track_logs_to_mlflow() -> None:
    """--track must forward the run to the MLflow tracking helper."""
    metrics = {"pr_auc": 0.4, "roc_auc": 0.7}
    with (
        patch.object(train, "run_training", return_value=(MagicMock(), metrics)),
        patch("src.monitoring.tracking.log_training_run") as log_run,
    ):
        code = train.main(["--model", "xgboost", "--track"])

    assert code == 0
    log_run.assert_called_once_with("xgboost", {"model_type": "xgboost"}, metrics)
