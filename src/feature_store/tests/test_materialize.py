"""Unit tests for Feast feature definitions and batch materialization."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.feature_store.feast_repo.feature_definitions import (
    ALL_DEFINITIONS,
    ALL_FEATURE_REFS,
    LOAN_CATEGORICAL_FEATURES,
    LOAN_NUMERIC_FEATURES,
    MACRO_FEATURES,
    credit_scoring_service,
    loan,
    loan_features_view,
    macro_features_view,
)
from src.feature_store.materialize import (
    DEFAULT_LOOKBACK_DAYS,
    REPO_PATH,
    apply_definitions,
    get_feature_store,
    materialize_features,
    run,
)


def test_entity_and_views_definitions() -> None:
    """Entity key, view schemas, and service wiring must match the mart."""
    assert loan.join_key == "loan_id"

    loan_view_fields = {f.name for f in loan_features_view.schema}
    assert loan_view_fields == set(LOAN_NUMERIC_FEATURES + LOAN_CATEGORICAL_FEATURES)

    macro_view_fields = {f.name for f in macro_features_view.schema}
    assert macro_view_fields == set(MACRO_FEATURES)

    assert credit_scoring_service.name == "credit_scoring_v1"
    assert loan in ALL_DEFINITIONS
    assert len(ALL_FEATURE_REFS) == len(loan_view_fields) + len(macro_view_fields)
    assert all(":" in ref for ref in ALL_FEATURE_REFS)


def test_get_feature_store_uses_repo_path() -> None:
    """get_feature_store must bind to the feast_repo directory."""
    with patch("src.feature_store.materialize.FeatureStore") as store_cls:
        get_feature_store()
    store_cls.assert_called_once_with(repo_path=str(REPO_PATH))
    assert (REPO_PATH / "feature_store.yaml").exists()


def test_apply_definitions_registers_all() -> None:
    """apply_definitions must push every definition to the registry."""
    store = MagicMock()
    apply_definitions(store)
    store.apply.assert_called_once_with(list(ALL_DEFINITIONS))


def test_materialize_features_default_window() -> None:
    """Default window must span DEFAULT_LOOKBACK_DAYS up to now."""
    store = MagicMock()
    start, end = materialize_features(store)

    assert end - start == timedelta(days=DEFAULT_LOOKBACK_DAYS)
    assert (datetime.now(UTC) - end).total_seconds() < 60
    store.materialize.assert_called_once_with(start_date=start, end_date=end)


def test_materialize_features_explicit_window() -> None:
    """An explicit window must be passed through unchanged."""
    store = MagicMock()
    start = datetime(2015, 1, 1, tzinfo=UTC)
    end = datetime(2018, 12, 31, tzinfo=UTC)

    result = materialize_features(store, start_date=start, end_date=end)

    assert result == (start, end)
    store.materialize.assert_called_once_with(start_date=start, end_date=end)


def test_materialize_features_rejects_inverted_window() -> None:
    """start_date at or after end_date must raise."""
    store = MagicMock()
    end = datetime(2018, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="before end_date"):
        materialize_features(store, start_date=end, end_date=end)
    store.materialize.assert_not_called()


def test_run_applies_then_materializes() -> None:
    """run must apply definitions before materializing."""
    with patch("src.feature_store.materialize.FeatureStore") as store_cls:
        store = store_cls.return_value
        start, end = run()

    store.apply.assert_called_once_with(list(ALL_DEFINITIONS))
    store.materialize.assert_called_once_with(start_date=start, end_date=end)
