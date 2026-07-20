"""Unit tests for feature engineering and dataset splitting module."""

from __future__ import annotations

import pandas as pd
import pytest

from src.features.features import (
    prepare_ml_dataset,
    preprocess_features,
    temporal_train_test_split,
)


@pytest.fixture
def sample_raw_dataframe() -> pd.DataFrame:
    """Fixture providing a mock mart.final_features DataFrame."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "loan_amnt": [10000.0, 15000.0, None, 20000.0, 5000.0],
            "term_months": [36, 60, 36, 60, 36],
            "int_rate": [10.5, 12.0, 8.5, None, 15.0],
            "installment": [325.0, 333.0, 200.0, 450.0, 175.0],
            "annual_inc": [70000.0, 85000.0, 50000.0, 120000.0, 30000.0],
            "dti_eff": [15.2, 18.0, 10.0, 22.5, 5.0],
            "installment_to_income_ratio": [0.05, 0.04, 0.04, 0.045, 0.07],
            "revol_bal": [5000.0, 12000.0, 3000.0, 15000.0, 1000.0],
            "revol_util_clean": [0.45, 0.60, 0.25, 0.80, 0.15],
            "total_acc": [15, 20, 10, 25, 8],
            "open_acc": [8, 12, 6, 15, 5],
            "credit_history_age_months": [120, 150, 80, 200, 60],
            "has_delinq": [0, 1, 0, 0, 0],
            "has_public_record": [0, 0, 0, 1, 0],
            "inq_last_6mths": [1, 2, 0, 1, 0],
            "unemployment_rate": [4.5, 4.5, 4.2, 4.2, 4.0],
            "unrate_lag3": [4.6, 4.6, 4.3, 4.3, 4.1],
            "unrate_lag6": [4.8, 4.8, 4.5, 4.5, 4.2],
            "cpi": [240.0, 240.0, 238.0, 238.0, 235.0],
            "cpi_lag3": [239.0, 239.0, 237.0, 237.0, 234.0],
            "cpi_lag6": [238.0, 238.0, 236.0, 236.0, 233.0],
            "fed_funds_rate": [1.25, 1.25, 1.0, 1.0, 0.75],
            "fedfunds_lag3": [1.0, 1.0, 0.75, 0.75, 0.5],
            "fedfunds_lag6": [0.75, 0.75, 0.5, 0.5, 0.25],
            "home_ownership": ["RENT", "MORTGAGE", "RENT", "OWN", "RENT"],
            "verification_status": [
                "Verified",
                "Source Verified",
                "Not Verified",
                "Verified",
                "Not Verified",
            ],
            "purpose": ["debt_consolidation", "credit_card", "car", "home_improvement", "medical"],
            "addr_state": ["CA", "NY", "TX", "FL", "CA"],
            "grade": ["A", "B", "A", "C", "D"],
            "sub_grade": ["A1", "B2", "A3", "C1", "D4"],
            "issue_d": ["2016-03-01", "2017-06-15", "2017-11-20", "2018-02-10", "2018-05-01"],
            "is_default": [0, 1, 0, 1, None],
        }
    )


def test_preprocess_features(sample_raw_dataframe: pd.DataFrame) -> None:
    """Test feature preprocessing and missing value handling."""
    processed = preprocess_features(sample_raw_dataframe)

    # Check missing numerical values are filled
    assert processed["loan_amnt"].isna().sum() == 0
    assert processed["int_rate"].isna().sum() == 0

    # Check categorical features are encoded to integers
    assert pd.api.types.is_numeric_dtype(processed["home_ownership"])
    assert pd.api.types.is_numeric_dtype(processed["purpose"])


def test_temporal_train_test_split(sample_raw_dataframe: pd.DataFrame) -> None:
    """Test temporal train/test split logic and null target filtering."""
    train_df, test_df = temporal_train_test_split(
        sample_raw_dataframe, split_date="2017-12-31", target_col="is_default", date_col="issue_d"
    )

    # Row 5 had is_default = None, so total valid rows = 4
    assert len(train_df) + len(test_df) == 4
    # Train rows: 2016-03-01, 2017-06-15, 2017-11-20 (3 rows)
    assert len(train_df) == 3
    # Test rows: 2018-02-10 (1 row)
    assert len(test_df) == 1
    # Check targets are integer 0 or 1
    assert train_df["is_default"].isin([0, 1]).all()


def test_prepare_ml_dataset(sample_raw_dataframe: pd.DataFrame) -> None:
    """Test extraction of feature matrix X and target vector y."""
    processed = preprocess_features(sample_raw_dataframe)
    valid_df = processed.dropna(subset=["is_default"])

    X, y = prepare_ml_dataset(valid_df)

    assert len(X) == 4
    assert len(y) == 4
    assert "is_default" not in X.columns
    assert "loan_amnt" in X.columns
    assert "home_ownership" in X.columns
