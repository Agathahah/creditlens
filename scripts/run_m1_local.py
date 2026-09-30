"""CLI for the approved bounded local M1 experiment."""

from __future__ import annotations

import argparse
import json
import sys

from src.ml.m1_local import run_m1_local


def main(argv: list[str] | None = None) -> int:
    """Run local M1 and print a compact summary.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Run bounded local CreditLens M1 evaluation")
    parser.add_argument(
        "--output",
        default=".local-backups/m1_local/latest",
        help="Private output directory (must remain outside Git)",
    )
    parser.add_argument(
        "--skip-xgboost",
        action="store_true",
        help="Run only constant and Logistic Regression candidates",
    )
    args = parser.parse_args(argv)
    report = run_m1_local(args.output, include_xgboost=not args.skip_xgboost)
    summary = {
        "status": report["status"],
        "selected_candidate": report["selected_candidate"],
        "locked_threshold": report["locked_threshold"],
        "frozen_test_metrics": report["frozen_test_metrics"],
        "output": args.output,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
