"""CLI drift check for the CreditLens monitoring DAG.

Compares the training-era reference split against the most recent split
using PSI/KS drift (src.monitoring.drift), optionally logs the summary to
MLflow and writes an Evidently HTML report. Exits non-zero when dataset
drift is detected so Airflow surfaces it.

    python scripts/run_drift_check.py --evidently-out reports/drift.html
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from src.common.logging import configure_logging
from src.features.features import (
    NUMERICAL_FEATURES,
    load_feature_data,
    temporal_train_test_split,
)
from src.monitoring.drift import detect_drift

configure_logging()


def load_reference_and_current(
    postgres_url: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the reference (train) and current (test) feature frames.

    Args:
        postgres_url: Optional database URL override.

    Returns:
        Tuple of (reference_df, current_df) from the temporal split.
    """
    df = load_feature_data(postgres_url)
    reference_df, current_df = temporal_train_test_split(df)
    return reference_df, current_df


def main(argv: list[str] | None = None) -> int:
    """Run the drift check and return a drift-based exit code.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        Process exit code (1 when dataset drift is detected).
    """
    parser = argparse.ArgumentParser(description="CreditLens data drift check.")
    parser.add_argument("--evidently-out", default=None, help="HTML drift report path")
    parser.add_argument("--track", action="store_true", help="Log summary to MLflow")
    parser.add_argument("--persist", action="store_true", help="Write drift metrics to PostgreSQL")
    args = parser.parse_args(argv)

    reference_df, current_df = load_reference_and_current()
    report = detect_drift(reference_df, current_df, NUMERICAL_FEATURES)
    print(json.dumps(report, indent=2, default=str))

    if args.evidently_out:
        from src.monitoring.evidently_report import generate_drift_report

        generate_drift_report(reference_df, current_df, args.evidently_out)
    if args.track:
        from src.monitoring.tracking import log_drift_report

        log_drift_report(report)
    if args.persist:
        from src.monitoring.store import persist_drift

        persist_drift(report)

    return 1 if report["dataset_drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
