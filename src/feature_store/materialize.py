"""Batch materialization of features from PostgreSQL into Redis.

Applies the Feast feature definitions and moves feature values from the
offline store (mart.final_features in PostgreSQL) into the Redis online
store so the API can serve them at low latency (ADR-006).

Run as a module for a one-off materialization:
    python -m src.feature_store.materialize
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from feast import FeatureStore

from src.common.logging import configure_logging
from src.feature_store.feast_repo.feature_definitions import ALL_DEFINITIONS

configure_logging()

REPO_PATH: Path = Path(__file__).resolve().parent / "feast_repo"
DEFAULT_LOOKBACK_DAYS: int = 3650


def get_feature_store(repo_path: str | Path = REPO_PATH) -> FeatureStore:
    """Build a FeatureStore bound to the CreditLens feast repository.

    Args:
        repo_path: Directory containing feature_store.yaml.

    Returns:
        Configured Feast FeatureStore instance.
    """
    return FeatureStore(repo_path=str(repo_path))


def apply_definitions(store: FeatureStore) -> None:
    """Register entities, feature views, and services in the registry.

    Args:
        store: Target FeatureStore.
    """
    store.apply(list(ALL_DEFINITIONS))


def materialize_features(
    store: FeatureStore,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Materialize offline features into the online store for a window.

    Args:
        store: Target FeatureStore (definitions must be applied).
        start_date: Window start. Defaults to end_date minus
            DEFAULT_LOOKBACK_DAYS.
        end_date: Window end. Defaults to now (UTC).

    Returns:
        The (start_date, end_date) window that was materialized.
    """
    if end_date is None:
        end_date = datetime.now(UTC)
    if start_date is None:
        start_date = end_date - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    if start_date >= end_date:
        raise ValueError("start_date must be before end_date.")
    store.materialize(start_date=start_date, end_date=end_date)
    return start_date, end_date


def materialize_incremental(store: FeatureStore, end_date: datetime | None = None) -> datetime:
    """Incrementally materialize features up to ``end_date``.

    Feast tracks the last materialization checkpoint per feature view, so
    this only moves rows newer than the previous run into the online store.

    Args:
        store: Target FeatureStore (definitions must be applied).
        end_date: Upper bound for materialization. Defaults to now (UTC).

    Returns:
        The end_date that was materialized up to.
    """
    if end_date is None:
        end_date = datetime.now(UTC)
    store.materialize_incremental(end_date=end_date)
    return end_date


def run(
    repo_path: str | Path = REPO_PATH,
    incremental: bool = False,
    end_date: datetime | None = None,
) -> tuple[datetime | None, datetime]:
    """Apply definitions and materialize features.

    Args:
        repo_path: Directory containing feature_store.yaml.
        incremental: When True, run an incremental materialization.
        end_date: Optional upper bound for the materialization window.

    Returns:
        The (start_date, end_date) window; start_date is None for
        incremental runs.
    """
    store = get_feature_store(repo_path)
    apply_definitions(store)
    if incremental:
        return None, materialize_incremental(store, end_date)
    return materialize_features(store, end_date=end_date)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for full or incremental Feast materialization.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Materialize CreditLens features into Feast.")
    parser.add_argument("--incremental", action="store_true", help="Incremental materialization")
    parser.add_argument("--end-date", default=None, help="ISO end date (default: now)")
    args = parser.parse_args(argv)

    end_date = datetime.fromisoformat(args.end_date) if args.end_date else None
    start, end = run(incremental=args.incremental, end_date=end_date)
    scope = "incremental" if args.incremental else f"from {start.isoformat() if start else '-'}"
    print(f"Materialized features ({scope}) up to {end.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
