"""Live integration test for Feast materialization + online reads.

Opt-in only: these tests require a *fully provisioned* stack — PostgreSQL
with the dbt ``mart`` materialized, Redis, and an applied Feast registry
(all from docker-compose). CI spins up bare PostgreSQL/Redis services
without the warehouse, so a mere port check is not enough; the tests run
only when ``CREDITLENS_RUN_INTEGRATION=1`` is set explicitly. On a
developer machine with the stack up, this exercises the real online-read
path the API depends on.

    CREDITLENS_RUN_INTEGRATION=1 pytest src/feature_store/tests/test_online_integration.py
"""

from __future__ import annotations

import os

import pytest

RUN_INTEGRATION = os.environ.get("CREDITLENS_RUN_INTEGRATION") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set CREDITLENS_RUN_INTEGRATION=1 with the full stack up to run Feast integration tests",
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
