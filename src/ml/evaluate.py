"""Model evaluation and regression-gate CLI for CreditLens.

Loads a trained model, scores the temporal test split, computes the
credit metrics (PR-AUC primary per ADR-004), and optionally enforces a
PR-AUC regression threshold — used by both the CI eval gate and the
Airflow retraining DAG.

    python src/ml/evaluate.py --threshold-check --pr-auc-min 0.25
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from src.common.logging import configure_logging
from src.features.features import (
    prepare_ml_dataset,
    preprocess_features,
    temporal_train_test_split,
)
from src.ml.train import compute_credit_metrics, load_model_artifact

configure_logging()

DEFAULT_MODEL_PATH = "models/xgboost_credit.joblib"
DEFAULT_PR_AUC_MIN = 0.25


def evaluate_predictions(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series
) -> dict[str, float]:
    """Compute credit evaluation metrics for a set of predictions.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.

    Returns:
        Dictionary of credit metrics (pr_auc, roc_auc, recall_at_p80, ks_statistic).
    """
    return compute_credit_metrics(y_true, y_prob)


def passes_threshold(metrics: dict[str, float], pr_auc_min: float) -> bool:
    """Check whether metrics satisfy the PR-AUC regression gate.

    Args:
        metrics: Metric dictionary containing ``pr_auc``.
        pr_auc_min: Minimum acceptable PR-AUC.

    Returns:
        True if the PR-AUC meets or exceeds the threshold.
    """
    return float(metrics.get("pr_auc", 0.0)) >= pr_auc_min


def run_evaluation(
    model_path: str = DEFAULT_MODEL_PATH,
    postgres_url: str | None = None,
    output_dir: str | None = None,
) -> dict[str, float]:
    """Evaluate a saved model on the temporal test split.

    Args:
        model_path: Path to the serialized model artifact.
        postgres_url: Optional database URL override for feature loading.
        output_dir: Optional directory to write ``metrics.json`` into.

    Returns:
        Computed metric dictionary.
    """
    from src.features.features import load_feature_data

    model = load_model_artifact(model_path)
    df = preprocess_features(load_feature_data(postgres_url))
    _, test_df = temporal_train_test_split(df)
    x_test, y_test = prepare_ml_dataset(test_df)
    y_prob = model.predict_proba(x_test)[:, 1]
    metrics = evaluate_predictions(y_test, y_prob)
    if output_dir is not None:
        _write_metrics(metrics, output_dir)
    return metrics


def _write_metrics(metrics: dict[str, float], output_dir: str) -> None:
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
    parser.add_argument("--output", default=None, help="Directory for metrics.json")
    parser.add_argument("--threshold-check", action="store_true")
    parser.add_argument("--pr-auc-min", type=float, default=DEFAULT_PR_AUC_MIN)
    args = parser.parse_args(argv)

    metrics = run_evaluation(args.model_path, output_dir=args.output)
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
