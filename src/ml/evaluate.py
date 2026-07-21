"""Model evaluation and regression-gate CLI for CreditLens.

Loads a trained model, scores the temporal test split, computes the full
metric set (ROC-AUC, PR-AUC, KS, best threshold, confusion matrix,
calibration), optionally enforces a PR-AUC regression threshold, and can
log metrics + diagnostic artifacts to MLflow — used by the CI eval gate,
the Airflow retraining DAG, and the monitoring DAG.

    python src/ml/evaluate.py --threshold-check --pr-auc-min 0.25
    python src/ml/evaluate.py --track --artifacts --output results/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.common.logging import configure_logging
from src.features.features import (
    prepare_ml_dataset,
    preprocess_features,
    temporal_train_test_split,
)
from src.ml.eval_metrics import extended_metrics, save_evaluation_artifacts
from src.ml.train import compute_credit_metrics, load_model_artifact

configure_logging()

DEFAULT_MODEL_PATH = "models/xgboost_credit.joblib"
DEFAULT_PR_AUC_MIN = 0.25


def evaluate_predictions(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series
) -> dict[str, float]:
    """Compute the core credit evaluation metrics for a set of predictions.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.

    Returns:
        Dictionary of credit metrics (pr_auc, roc_auc, recall_at_p80, ks_statistic).
    """
    return compute_credit_metrics(y_true, y_prob)


def passes_threshold(metrics: dict[str, Any], pr_auc_min: float) -> bool:
    """Check whether metrics satisfy the PR-AUC regression gate.

    Args:
        metrics: Metric dictionary containing ``pr_auc``.
        pr_auc_min: Minimum acceptable PR-AUC.

    Returns:
        True if the PR-AUC meets or exceeds the threshold.
    """
    return float(metrics.get("pr_auc", 0.0)) >= pr_auc_min


def score_test_split(
    model_path: str, postgres_url: str | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Load a model and score the temporal test split.

    Args:
        model_path: Path to the serialized model artifact.
        postgres_url: Optional database URL override for feature loading.

    Returns:
        Tuple of (y_true, y_prob) arrays for the test split.
    """
    from src.features.features import load_feature_data

    model = load_model_artifact(model_path)
    df = preprocess_features(load_feature_data(postgres_url))
    _, test_df = temporal_train_test_split(df)
    x_test, y_test = prepare_ml_dataset(test_df)
    y_prob = model.predict_proba(x_test)[:, 1]
    return np.asarray(y_test, dtype=int), np.asarray(y_prob, dtype=float)


def run_evaluation(
    model_path: str = DEFAULT_MODEL_PATH,
    postgres_url: str | None = None,
    output_dir: str | None = None,
    track: bool = False,
    artifacts: bool = False,
    persist: bool = False,
    experiment: str = "creditlens",
) -> dict[str, Any]:
    """Evaluate a saved model on the temporal test split.

    Args:
        model_path: Path to the serialized model artifact.
        postgres_url: Optional database URL override for feature loading.
        output_dir: Optional directory for metrics.json and artifacts.
        track: When True, log metrics and artifacts to MLflow.
        artifacts: When True, render ROC/PR/confusion/calibration plots.
        persist: When True, write metrics + score histogram to PostgreSQL.
        experiment: MLflow experiment name.

    Returns:
        The extended metric mapping.
    """
    y_true, y_prob = score_test_split(model_path, postgres_url)
    metrics = extended_metrics(y_true, y_prob)
    model_name = Path(model_path).stem

    art_dir = output_dir or (tempfile.mkdtemp(prefix="creditlens_eval_") if artifacts else None)
    artifact_paths: list[str] = []
    if artifacts and art_dir is not None:
        artifact_paths = save_evaluation_artifacts(
            y_true, y_prob, metrics["confusion_matrix"], art_dir
        )
    if output_dir is not None:
        _write_metrics(metrics, output_dir)
    if track:
        from src.monitoring.tracking import log_evaluation

        log_evaluation(metrics, artifact_paths, model_name=model_name, experiment=experiment)
    if persist:
        from src.monitoring.store import persist_evaluation

        persist_evaluation(metrics, model_name, y_prob=y_prob, postgres_url=postgres_url)
    return metrics


def _write_metrics(metrics: dict[str, Any], output_dir: str) -> None:
    """Persist metrics to ``<output_dir>/metrics.json``.

    Args:
        metrics: Metric dictionary to serialize.
        output_dir: Destination directory (created if missing).
    """
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "metrics.json"), "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for model evaluation and the PR-AUC gate.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        Process exit code (1 when the threshold gate fails).
    """
    parser = argparse.ArgumentParser(description="Evaluate a CreditLens model.")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", default=None, help="Directory for metrics.json/artifacts")
    parser.add_argument("--threshold-check", action="store_true")
    parser.add_argument("--pr-auc-min", type=float, default=DEFAULT_PR_AUC_MIN)
    parser.add_argument("--track", action="store_true", help="Log metrics/artifacts to MLflow")
    parser.add_argument("--artifacts", action="store_true", help="Render diagnostic plots")
    parser.add_argument("--persist", action="store_true", help="Write metrics to PostgreSQL")
    args = parser.parse_args(argv)

    metrics = run_evaluation(
        args.model_path,
        output_dir=args.output,
        track=args.track,
        artifacts=args.artifacts,
        persist=args.persist,
    )
    print(json.dumps(metrics, indent=2))

    if args.threshold_check and not passes_threshold(metrics, args.pr_auc_min):
        print(
            f"PR-AUC {metrics['pr_auc']:.4f} below minimum {args.pr_auc_min:.4f}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
