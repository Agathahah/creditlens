"""Unit tests for the MLflow tracking wrappers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.monitoring import tracking


def test_configure_tracking_uses_setting(monkeypatch: object) -> None:
    """configure_tracking must set the URI (from settings) and experiment."""
    with patch.object(tracking, "mlflow") as mlf:
        tracking.configure_tracking(tracking_uri="http://mlflow:5000", experiment="exp")
    mlf.set_tracking_uri.assert_called_once_with("http://mlflow:5000")
    mlf.set_experiment.assert_called_once_with("exp")


def test_log_training_run_logs_params_and_metrics() -> None:
    """log_training_run must log params, metrics, and return the run id."""
    with patch.object(tracking, "mlflow") as mlf:
        run_ctx = MagicMock()
        run_ctx.info.run_id = "run-123"
        mlf.start_run.return_value.__enter__.return_value = run_ctx

        run_id = tracking.log_training_run("xgboost", {"model_type": "xgboost"}, {"pr_auc": 0.4})

    assert run_id == "run-123"
    mlf.log_params.assert_called_once_with({"model_type": "xgboost"})
    mlf.log_metrics.assert_called_once_with({"pr_auc": 0.4})


def test_log_drift_report_logs_summary() -> None:
    """log_drift_report must log drift share/count and the drift flag."""
    report = {"drift_share": 0.5, "n_drifted": 2, "dataset_drift": True}
    with patch.object(tracking, "mlflow") as mlf:
        run_ctx = MagicMock()
        run_ctx.info.run_id = "run-drift"
        mlf.start_run.return_value.__enter__.return_value = run_ctx

        run_id = tracking.log_drift_report(report)

    assert run_id == "run-drift"
    metrics = mlf.log_metrics.call_args.args[0]
    assert metrics == {"drift_share": 0.5, "n_drifted": 2.0}
    mlf.log_param.assert_called_once_with("dataset_drift", True)
