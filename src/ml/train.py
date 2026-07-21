"""Model training pipeline for CreditLens credit scoring engine.

Trains XGBoost, LightGBM, and Logistic Regression models on credit loan data,
evaluating performance using credit-specific metrics (PR-AUC, ROC-AUC, Recall@P80, KS Statistic).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.stats import ks_2samp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score
from xgboost import XGBClassifier

from src.common.logging import configure_logging

configure_logging()

DEFAULT_MODEL_PATHS: dict[str, str] = {
    "xgboost": "models/xgboost_credit.joblib",
    "lightgbm": "models/lightgbm_credit.joblib",
    "logistic_regression": "models/logreg_credit.joblib",
}


def compute_credit_metrics(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series
) -> dict[str, float]:
    """Compute credit scoring evaluation metrics.

    Metrics computed:
    - pr_auc: Precision-Recall Area Under Curve (Primary metric per ADR-004)
    - roc_auc: Receiver Operating Characteristic Area Under Curve
    - recall_at_p80: Maximum recall achieved at precision >= 0.80
    - ks_statistic: Kolmogorov-Smirnov separation metric

    Args:
        y_true: True binary target labels (0 or 1).
        y_prob: Predicted default probabilities (0.0 to 1.0).

    Returns:
        Dictionary containing metric scores.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    # 1. ROC-AUC
    roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))

    # 2. PR-AUC
    precisions, recalls, _ = precision_recall_curve(y_true_arr, y_prob_arr)
    pr_auc = float(auc(recalls, precisions))

    # 3. Recall @ Precision 80%
    valid_recalls = recalls[precisions >= 0.80]
    recall_at_p80 = float(np.max(valid_recalls)) if len(valid_recalls) > 0 else 0.0

    # 4. KS-Statistic
    prob_default = y_prob_arr[y_true_arr == 1]
    prob_non_default = y_prob_arr[y_true_arr == 0]
    if len(prob_default) > 0 and len(prob_non_default) > 0:
        ks_stat, _ = ks_2samp(prob_default, prob_non_default)
        ks_statistic = float(ks_stat)
    else:
        ks_statistic = 0.0

    return {
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "recall_at_p80": recall_at_p80,
        "ks_statistic": ks_statistic,
    }


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series | np.ndarray,
    X_test: pd.DataFrame,
    y_test: pd.Series | np.ndarray,
    model_type: str = "xgboost",
    params: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, float]]:
    """Train a credit scoring model and evaluate performance on test set.

    Args:
        X_train: Training feature matrix.
        y_train: Training target labels.
        X_test: Test feature matrix.
        y_test: Test target labels.
        model_type: Classifier architecture ("xgboost", "lightgbm", "logistic_regression").
        params: Optional hyperparameter overrides.

    Returns:
        Tuple of (trained_model, metrics_dict).
    """
    if params is None:
        params = {}

    if model_type == "xgboost":
        xgb_params: dict[str, Any] = {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.05,
            "random_state": 42,
            "eval_metric": "logloss",
        }
        xgb_params.update(params)
        model = XGBClassifier(**xgb_params)
    elif model_type == "lightgbm":
        lgb_params: dict[str, Any] = {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.05,
            "random_state": 42,
            "verbosity": -1,
        }
        lgb_params.update(params)
        model = LGBMClassifier(**lgb_params)
    elif model_type == "logistic_regression":
        lr_params: dict[str, Any] = {
            "max_iter": 1000,
            "random_state": 42,
        }
        lr_params.update(params)
        model = LogisticRegression(**lr_params)
    else:
        raise ValueError(f"Unsupported model_type: {model_type}")

    # Fit model
    model.fit(X_train, y_train)

    # Predict probabilities for test set
    y_prob = model.predict_proba(X_test)[:, 1]

    # Calculate credit metrics
    metrics = compute_credit_metrics(y_test, y_prob)

    return model, metrics


def save_model_artifact(model: Any, filepath: str) -> None:
    """Save trained model artifact to disk.

    Args:
        model: Trained scikit-learn / XGBoost / LightGBM model.
        filepath: Destination file path (e.g., "models/xgboost_credit.joblib").
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    joblib.dump(model, filepath)


def load_model_artifact(filepath: str) -> Any:
    """Load model artifact from disk.

    Args:
        filepath: Path to saved model file.

    Returns:
        Loaded model object.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Model file not found at: {filepath}")
    return joblib.load(filepath)


def run_training(
    model_type: str = "xgboost",
    output_path: str | None = None,
    postgres_url: str | None = None,
) -> tuple[Any, dict[str, float]]:
    """Load features, train a model on the temporal split, and persist it.

    Args:
        model_type: Classifier architecture to train.
        output_path: Destination artifact path. Defaults per model type.
        postgres_url: Optional database URL override for feature loading.

    Returns:
        Tuple of (trained_model, test_metrics).
    """
    from src.features.features import (
        load_feature_data,
        prepare_ml_dataset,
        preprocess_features,
        temporal_train_test_split,
    )

    df = preprocess_features(load_feature_data(postgres_url))
    train_df, test_df = temporal_train_test_split(df)
    x_train, y_train = prepare_ml_dataset(train_df)
    x_test, y_test = prepare_ml_dataset(test_df)
    model, metrics = train_model(x_train, y_train, x_test, y_test, model_type=model_type)
    save_model_artifact(model, output_path or DEFAULT_MODEL_PATHS[model_type])
    return model, metrics


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for training a single model.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Train a CreditLens model.")
    parser.add_argument("--model", default="xgboost", choices=sorted(DEFAULT_MODEL_PATHS))
    parser.add_argument("--output", default=None, help="Artifact output path")
    parser.add_argument("--track", action="store_true", help="Log run to MLflow")
    args = parser.parse_args(argv)

    _, metrics = run_training(args.model, output_path=args.output)
    if args.track:
        from src.monitoring.tracking import log_training_run

        log_training_run(args.model, {"model_type": args.model}, metrics)
    print(f"Trained {args.model}: PR-AUC={metrics['pr_auc']:.4f} ROC-AUC={metrics['roc_auc']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
