"""Unit tests for online feature serving from the Feast store."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.feature_store.feast_repo.feature_definitions import ALL_FEATURE_REFS
from src.feature_store.serve import fetch_feature_vector, get_online_features_df


def _store_returning(df: pd.DataFrame) -> MagicMock:
    """Build a mock FeatureStore whose online response converts to df."""
    store = MagicMock()
    store.get_online_features.return_value.to_df.return_value = df
    return store


def test_get_online_features_df_defaults_to_all_refs() -> None:
    """Without explicit refs, every registered feature must be requested."""
    df = pd.DataFrame({"loan_id": ["loan-1"], "int_rate": [13.5]})
    store = _store_returning(df)

    result = get_online_features_df(store, ["loan-1"])

    assert result.equals(df)
    _, kwargs = store.get_online_features.call_args
    assert kwargs["features"] == ALL_FEATURE_REFS
    assert kwargs["entity_rows"] == [{"loan_id": "loan-1"}]


def test_get_online_features_df_batch_and_custom_refs() -> None:
    """Custom refs and multiple loan ids must be passed through."""
    df = pd.DataFrame({"loan_id": ["a", "b"], "dti_eff": [10.0, 20.0]})
    store = _store_returning(df)
    refs = ["loan_features:dti_eff"]

    result = get_online_features_df(store, ["a", "b"], feature_refs=refs)

    assert len(result) == 2
    _, kwargs = store.get_online_features.call_args
    assert kwargs["features"] == refs
    assert kwargs["entity_rows"] == [{"loan_id": "a"}, {"loan_id": "b"}]


def test_get_online_features_df_rejects_empty_ids() -> None:
    """An empty loan id list must raise instead of querying."""
    store = MagicMock()
    with pytest.raises(ValueError, match="must not be empty"):
        get_online_features_df(store, [])
    store.get_online_features.assert_not_called()


def test_fetch_feature_vector_returns_mapping() -> None:
    """A present entity must yield a feature-name → value mapping."""
    df = pd.DataFrame({"loan_id": ["loan-1"], "int_rate": [13.5], "home_ownership": ["RENT"]})
    store = _store_returning(df)

    vector = fetch_feature_vector(store, "loan-1")

    assert vector == {"int_rate": 13.5, "home_ownership": "RENT"}
    assert "loan_id" not in vector


def test_fetch_feature_vector_missing_entity_returns_none() -> None:
    """An absent entity (all-null features) must return None."""
    df = pd.DataFrame({"loan_id": ["ghost"], "int_rate": [np.nan], "dti_eff": [np.nan]})
    store = _store_returning(df)

    assert fetch_feature_vector(store, "ghost") is None
