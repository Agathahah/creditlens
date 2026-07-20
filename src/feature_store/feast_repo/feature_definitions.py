"""Feast feature definitions for CreditLens (ADR-006).

Declares the loan entity, the loan-level and macro-level feature views
sourced from ``mart.final_features`` (PostgreSQL offline store), and the
feature service used by the scoring API. The online store is Redis; see
``feature_store.yaml`` in this directory.
"""

from __future__ import annotations

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)
from feast.types import Float64, String
from feast.value_type import ValueType

# Loan-level numeric features engineered in the dbt mart layer
LOAN_NUMERIC_FEATURES: list[str] = [
    "loan_amnt",
    "term_months",
    "int_rate",
    "installment",
    "annual_inc",
    "dti_eff",
    "installment_to_income_ratio",
    "revol_bal",
    "revol_util_clean",
    "total_acc",
    "open_acc",
    "credit_history_age_months",
    "has_delinq",
    "has_public_record",
    "inq_last_6mths",
]

# Loan-level categorical features (served as raw strings)
LOAN_CATEGORICAL_FEATURES: list[str] = [
    "home_ownership",
    "verification_status",
    "purpose",
    "addr_state",
    "grade",
    "sub_grade",
]

# Macro-economic context features joined from FRED indicators
MACRO_FEATURES: list[str] = [
    "unemployment_rate",
    "unrate_lag3",
    "unrate_lag6",
    "cpi",
    "cpi_lag3",
    "cpi_lag6",
    "fed_funds_rate",
    "fedfunds_lag3",
    "fedfunds_lag6",
]

loan = Entity(
    name="loan",
    join_keys=["loan_id"],
    value_type=ValueType.STRING,
    description="A Lending Club loan application",
)

final_features_source = PostgreSQLSource(
    name="final_features_source",
    query="SELECT * FROM mart.final_features",
    timestamp_field="issue_d",
)

loan_features_view = FeatureView(
    name="loan_features",
    entities=[loan],
    ttl=timedelta(days=3650),
    schema=(
        [Field(name=feature, dtype=Float64) for feature in LOAN_NUMERIC_FEATURES]
        + [Field(name=feature, dtype=String) for feature in LOAN_CATEGORICAL_FEATURES]
    ),
    source=final_features_source,
    online=True,
    description="Loan-level features engineered in mart.loan_features",
)

macro_features_view = FeatureView(
    name="macro_features",
    entities=[loan],
    ttl=timedelta(days=3650),
    schema=[Field(name=feature, dtype=Float64) for feature in MACRO_FEATURES],
    source=final_features_source,
    online=True,
    description="FRED macro context features joined at loan issue month",
)

credit_scoring_service = FeatureService(
    name="credit_scoring_v1",
    features=[loan_features_view, macro_features_view],
    description="Feature set served to the credit scoring API",
)

ALL_DEFINITIONS: list[object] = [
    loan,
    loan_features_view,
    macro_features_view,
    credit_scoring_service,
]

ALL_FEATURE_REFS: list[str] = [
    f"loan_features:{feature}" for feature in LOAN_NUMERIC_FEATURES + LOAN_CATEGORICAL_FEATURES
] + [f"macro_features:{feature}" for feature in MACRO_FEATURES]
