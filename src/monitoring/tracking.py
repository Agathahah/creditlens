"""MLflow experiment tracking helpers for CreditLens.

Thin wrappers around MLflow so training runs, evaluation metrics, and drift
reports are logged consistently. The tracking URI defaults to the
``MLFLOW_URL`` setting (the docker-compose MLflow service).
"""

from __future__ import annotations

from typing import Any

import mlflow

from src.common.config import get_settings
from src.common.logging import configure_logging

configure_logging()

DEFAULT_EXPERIMENT: str = "creditlens"


def configure_tracking(
    tracking_uri: str | None = None, experiment: str = DEFAULT_EXPERIMENT
) -> None:
    """Point MLflow at the tracking server and select the experiment.

    Args:
        tracking_uri: MLflow tracking URI. Defaults to the ``MLFLOW_URL`` setting.
        experiment: Experiment name to create or reuse.
    """
    uri = tracking_uri or get_settings().MLFLOW_URL
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment)


def log_training_run(
    model_name: str,
    params: dict[str, Any],
    metrics: dict[str, float],
    tracking_uri: str | None = None,
    experiment: str = DEFAULT_EXPERIMENT,
) -> str:
    """Log a training run's parameters and metrics to MLflow.

    Args:
        model_name: Identifier used as the run name.
        params: Hyperparameters to record.
        metrics: Evaluation metrics to record.
        tracking_uri: Optional tracking URI override.
        experiment: Experiment name.

    Returns:
        The MLflow run ID.
    """
    configure_tracking(tracking_uri, experiment)
    with mlflow.start_run(run_name=model_name) as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        return str(run.info.run_id)


def _flatten_scalar_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    """Extract numeric scalar metrics, expanding a confusion_matrix mapping.

    Args:
        metrics: Extended metric mapping (may contain nested dicts).

    Returns:
        Flat mapping of metric name to float, suitable for MLflow.
    """
    flat: dict[str, float] = {}
    for key, value in metrics.items():
        if isinstance(value, dict) and key == "confusion_matrix":
            flat.update({f"cm_{name}": float(count) for name, count in value.items()})
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            flat[key] = float(value)
    return flat


def log_evaluation(
    metrics: dict[str, Any],
    artifacts: list[str] | None = None,
    model_name: str = "evaluation",
    tracking_uri: str | None = None,
    experiment: str = DEFAULT_EXPERIMENT,
) -> str:
    """Log evaluation metrics and diagnostic artifacts to MLflow.

    Args:
        metrics: Extended metric mapping (from ``extended_metrics``).
        artifacts: Paths of plot files to attach (ROC/PR/confusion/calibration).
        model_name: Run name.
        tracking_uri: Optional tracking URI override.
        experiment: Experiment name.

    Returns:
        The MLflow run ID.
    """
    configure_tracking(tracking_uri, experiment)
    with mlflow.start_run(run_name=model_name) as run:
        mlflow.log_metrics(_flatten_scalar_metrics(metrics))
        for path in artifacts or []:
            mlflow.log_artifact(path)
        return str(run.info.run_id)


def log_drift_report(
    drift_report: dict[str, Any],
    tracking_uri: str | None = None,
    experiment: str = DEFAULT_EXPERIMENT,
) -> str:
    """Log dataset-level drift metrics to MLflow.

    Args:
        drift_report: Report returned by ``detect_drift``.
        tracking_uri: Optional tracking URI override.
        experiment: Experiment name.

    Returns:
        The MLflow run ID.
    """
    configure_tracking(tracking_uri, experiment)
    with mlflow.start_run(run_name="data_drift") as run:
        mlflow.log_metrics(
            {
                "drift_share": float(drift_report.get("drift_share", 0.0)),
                "n_drifted": float(drift_report.get("n_drifted", 0)),
            }
        )
        mlflow.log_param("dataset_drift", drift_report.get("dataset_drift", False))
        return str(run.info.run_id)
