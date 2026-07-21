"""Online feature serving from the Feast Redis store.

Fetches feature vectors for loans at prediction time so the API does not
query PostgreSQL directly (ADR-006). Numeric features are coerced to
float; categorical features are returned as category codes consistent
with the training-time encoding contract (preprocessed numeric inputs).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from feast import FeatureStore

from src.common.logging import configure_logging
from src.feature_store.feast_repo.feature_definitions import ALL_FEATURE_REFS

configure_logging()


def get_online_features_df(
    store: FeatureStore,
    loan_ids: list[str],
    feature_refs: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch online feature rows for a batch of loans.

    Args:
        store: FeatureStore bound to the CreditLens repository.
        loan_ids: Loan entity keys to fetch.
        feature_refs: Feature references ("view:feature"). Defaults to all
            registered CreditLens features.

    Returns:
        DataFrame with one row per loan_id, including the loan_id column.
    """
    if not loan_ids:
        raise ValueError("loan_ids must not be empty.")
    refs = feature_refs if feature_refs is not None else ALL_FEATURE_REFS
    entity_rows = [{"loan_id": loan_id} for loan_id in loan_ids]
    response = store.get_online_features(features=refs, entity_rows=entity_rows)
    return response.to_df()


def fetch_feature_vector(
    store: FeatureStore,
    loan_id: str,
    feature_refs: list[str] | None = None,
) -> dict[str, Any] | None:
    """Fetch a single loan's feature vector from the online store.

    Args:
        store: FeatureStore bound to the CreditLens repository.
        loan_id: Loan entity key.
        feature_refs: Feature references to fetch. Defaults to all.

    Returns:
        Mapping of feature name to value (without the loan_id key), or
        None when the loan is absent from the online store (all feature
        values null).
    """
    df = get_online_features_df(store, [loan_id], feature_refs)
    row = df.iloc[0].drop(labels=["loan_id"], errors="ignore")
    if row.isna().all():
        return None
    return {str(name): value for name, value in row.items()}
