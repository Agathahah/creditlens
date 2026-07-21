"""Live integration test for Feast materialization + online reads.

Skipped unless PostgreSQL and Redis are reachable (they run in
docker-compose, not in the lightweight CI/test env). On a developer
machine with the stack up and the warehouse materialized, this exercises
the real online-read path the API depends on.
"""

from __future__ import annotations

import socket

import pytest

from src.common.config import get_settings


def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    """Return True when a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _infra_available() -> bool:
    """Check that both PostgreSQL and Redis are reachable."""
    settings = get_settings()
    pg_ok = _port_open("localhost", 5432)
    redis_ok = _port_open("localhost", 6379)
    return pg_ok and redis_ok and settings is not None


pytestmark = pytest.mark.skipif(
    not _infra_available(),
    reason="PostgreSQL/Redis not reachable — Feast online integration skipped",
)


def test_apply_and_incremental_materialize() -> None:
    """Applying definitions and running an incremental materialization must succeed."""
    from src.feature_store.materialize import apply_definitions, get_feature_store, run

    store = get_feature_store()
    apply_definitions(store)
    start, end = run(incremental=True)
    assert start is None
    assert end is not None


def test_online_store_read_after_materialize() -> None:
    """After materialization, online reads must return a usable structure."""
    from src.feature_store.materialize import get_feature_store
    from src.feature_store.serve import get_online_features_df

    store = get_feature_store()
    # A non-existent entity must still yield a well-formed (all-null) row.
    df = get_online_features_df(store, ["__integration_probe__"])
    assert "loan_id" in df.columns
    assert len(df) == 1
