"""Verify that FastAPI can read features from the Feast online store.

Post-materialization smoke test: builds the Feast online-store fetcher the
API uses, fetches a sample loan's feature vector, and reports whether the
online read succeeds. Requires a running PostgreSQL + Redis + a
materialized Feast store.

    python scripts/verify_online_features.py --loan-id 12345
"""

from __future__ import annotations

import argparse
import json
import sys

from src.common.logging import configure_logging
from src.feature_store.materialize import get_feature_store
from src.feature_store.serve import fetch_feature_vector

configure_logging()


def main(argv: list[str] | None = None) -> int:
    """Fetch a loan's online features and report readiness.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        Process exit code (1 when the loan is absent from the online store).
    """
    parser = argparse.ArgumentParser(description="Verify Feast online feature reads.")
    parser.add_argument("--loan-id", required=True, help="Loan entity key to fetch")
    args = parser.parse_args(argv)

    store = get_feature_store()
    vector = fetch_feature_vector(store, args.loan_id)
    if vector is None:
        print(f"No online features for loan '{args.loan_id}' — is the store materialized?")
        return 1
    print(json.dumps({"loan_id": args.loan_id, "features": vector}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
