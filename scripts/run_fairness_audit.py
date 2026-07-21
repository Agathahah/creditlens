"""CLI entrypoint for the CreditLens fairness audit.

Scores the temporal test split with a trained model and runs the AIF360
disparate-impact / equal-opportunity / demographic-parity audit over the
protected proxies (home_ownership, addr_state). Invoked by the Airflow
retraining DAG after the evaluation gate.

    python scripts/run_fairness_audit.py
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from src.common.logging import configure_logging
from src.fairness.fairness_audit import audit_model
from src.features.features import (
    TARGET_COLUMN,
    load_feature_data,
    prepare_ml_dataset,
    preprocess_features,
    temporal_train_test_split,
)
from src.ml.train import load_model_artifact

configure_logging()

DEFAULT_MODEL_PATH = "models/xgboost_credit.joblib"
APPROVAL_THRESHOLD = 0.20
PROTECTED_ATTRIBUTES: dict[str, list[str]] = {
    "home_ownership": ["MORTGAGE", "OWN"],
    "addr_state": ["CA", "NY", "TX"],
}


def build_audit_frame(raw_test: pd.DataFrame, y_pred: pd.Series) -> pd.DataFrame:
    """Assemble the frame consumed by ``audit_model``.

    Args:
        raw_test: Test rows with raw (unencoded) protected attributes and target.
        y_pred: Predicted binary rejection labels aligned with ``raw_test``.

    Returns:
        DataFrame with the true label, predicted label, and protected columns.
    """
    frame = pd.DataFrame(
        {
            TARGET_COLUMN: raw_test[TARGET_COLUMN].astype(int).to_numpy(),
            "pred_default": y_pred.to_numpy(),
        }
    )
    for attr in PROTECTED_ATTRIBUTES:
        frame[attr] = raw_test[attr].to_numpy()
    return frame


def run_audit(model_path: str = DEFAULT_MODEL_PATH, postgres_url: str | None = None) -> dict:
    """Run the fairness audit for a trained model on the test split.

    Args:
        model_path: Path to the serialized model artifact.
        postgres_url: Optional database URL override for feature loading.

    Returns:
        Fairness report dictionary produced by ``audit_model``.
    """
    model = load_model_artifact(model_path)
    raw = load_feature_data(postgres_url)
    _, raw_test = temporal_train_test_split(raw)

    processed = preprocess_features(raw)
    _, proc_test = temporal_train_test_split(processed)
    x_test, _ = prepare_ml_dataset(proc_test)

    y_prob = model.predict_proba(x_test)[:, 1]
    y_pred = pd.Series((y_prob >= APPROVAL_THRESHOLD).astype(int), index=x_test.index)

    frame = build_audit_frame(raw_test.loc[x_test.index], y_pred)
    return audit_model(frame, TARGET_COLUMN, "pred_default", PROTECTED_ATTRIBUTES)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint returning non-zero when the audit fails the policy.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        Process exit code (1 when the disparate-impact policy is violated).
    """
    parser = argparse.ArgumentParser(description="Run the CreditLens fairness audit.")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    args = parser.parse_args(argv)

    report = run_audit(args.model_path)
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
