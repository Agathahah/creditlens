"""Feature engineering and dataset splitting module for CreditLens.

Extracts features from mart.final_features table in PostgreSQL,
applies feature preprocessing/encoding, and performs temporal train/test split.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import create_engine

from src.common.config import get_settings
from src.common.logging import configure_logging

configure_logging()

# Selected feature columns for credit scoring ML model
NUMERICAL_FEATURES: list[str] = [
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

CATEGORICAL_FEATURES: list[str] = [
    "home_ownership",
    "verification_status",
    "purpose",
    "addr_state",
    "grade",
    "sub_grade",
]

TARGET_COLUMN: str = "is_default"


def load_feature_data(postgres_url: str | None = None) -> pd.DataFrame:
    """Load data from mart.final_features table in PostgreSQL.

    Args:
        postgres_url: PostgreSQL connection string. If None, loaded from settings.

    Returns:
        pd.DataFrame containing feature data.
    """
    if postgres_url is None:
        settings = get_settings()
        postgres_url = settings.POSTGRES_URL

    # Ensure standard synchronous driver for pandas read_sql
    if postgres_url.startswith("postgresql+asyncpg://"):
        postgres_url = postgres_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    engine = create_engine(postgres_url)
    query = "SELECT * FROM mart.final_features;"
    df = pd.read_sql(query, con=engine)
    return df


def preprocess_features(
    df: pd.DataFrame,
    categorical_cols: list[str] | None = None,
    numerical_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Preprocess raw feature DataFrame by imputing missing values and encoding categoricals.

    Args:
        df: Input DataFrame containing raw features.
        categorical_cols: List of categorical feature names.
        numerical_cols: List of numerical feature names.

    Returns:
        Preprocessed pd.DataFrame ready for model ingestion.
    """
    if categorical_cols is None:
        categorical_cols = CATEGORICAL_FEATURES
    if numerical_cols is None:
        numerical_cols = NUMERICAL_FEATURES

    processed_df = df.copy()

    # Fill missing values for numerical features
    for col in numerical_cols:
        if col in processed_df.columns:
            processed_df[col] = pd.to_numeric(processed_df[col], errors="coerce")
            median_val = processed_df[col].median()
            processed_df[col] = processed_df[col].fillna(
                median_val if pd.notna(median_val) else 0.0
            )

    # Encode categorical features as category codes / one-hot
    for col in categorical_cols:
        if col in processed_df.columns:
            processed_df[col] = processed_df[col].astype(str).fillna("MISSING")
            processed_df[col] = processed_df[col].astype("category").cat.codes

    return processed_df


def temporal_train_test_split(
    df: pd.DataFrame,
    split_date: str | date = "2017-12-31",
    target_col: str = TARGET_COLUMN,
    date_col: str = "issue_d",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Perform temporal train/test split to prevent data leakage (ADR-003).

    Filters out rows with NULL targets (ongoing loans without outcome).

    Args:
        df: Feature DataFrame.
        split_date: Cutoff date for train set (inclusive).
        target_col: Name of target column.
        date_col: Name of loan issue date column.

    Returns:
        Tuple of (train_df, test_df).
    """
    # Exclude ongoing loans without definitive outcome for ML training
    valid_df = df.dropna(subset=[target_col]).copy()
    valid_df[target_col] = valid_df[target_col].astype(int)

    # Ensure date column is datetime
    valid_df[date_col] = pd.to_datetime(valid_df[date_col])
    cutoff = pd.to_datetime(split_date)

    train_df = valid_df[valid_df[date_col] <= cutoff].copy()
    test_df = valid_df[valid_df[date_col] > cutoff].copy()

    return train_df, test_df


def prepare_ml_dataset(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    target_col: str = TARGET_COLUMN,
) -> tuple[pd.DataFrame, pd.Series]:
    """Extract feature matrix X and target vector y from preprocessed DataFrame.

    Args:
        df: Preprocessed DataFrame.
        feature_cols: List of feature column names. If None, uses NUMERICAL + CATEGORICAL.
        target_col: Name of target column.

    Returns:
        Tuple of (X, y).
    """
    if feature_cols is None:
        feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

    available_features = [col for col in feature_cols if col in df.columns]
    X = df[available_features].copy()
    y = df[target_col].astype(int)

    return X, y
