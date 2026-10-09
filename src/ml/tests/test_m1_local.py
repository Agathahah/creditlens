"""Contract tests for the bounded M1 local workflow."""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from src.ml.m1_local import (
    FEATURES,
    FORBIDDEN_FEATURES,
    build_candidate,
    choose_threshold,
    prepare_m1_data,
    split_xy,
)


def _raw_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    statuses = ["Fully Paid", "Charged Off", "Fully Paid", "Default"]
    years = [2011, 2012, 2013, 2014, 2014, 2015, 2015]
    for index, year in enumerate(years * 4):
        rows.append(
            {
                "loan_id": index + 1,
                "issue_date": f"{year}-06-01",
                "term": "36 months",
                "loan_status": statuses[index % len(statuses)],
                "annual_inc": 40_000 + index * 1_000,
                "dti": 5.0 + index,
                "revol_bal": 1_000 + index * 100,
                "revol_util": 20.0 + index,
                "total_acc": 10 + index,
                "open_acc": 5 + index,
                "earliest_cr_line": "2005-01-01",
                "delinq_2yrs": index % 2,
                "pub_rec": index % 3,
                "inq_last_6mths": index % 4,
                "home_ownership": "RENT" if index % 2 else "MORTGAGE",
                "purpose": "credit_card" if index % 2 else "debt_consolidation",
                "addr_state": "CA",
            }
        )
    rows.append(rows[-1] | {"loan_id": 10_000, "loan_status": "Current"})
    rows.append(rows[-2] | {"loan_id": 10_001, "annual_inc": 0, "dti": None})
    return pd.DataFrame(rows)


def test_target_eligibility_and_temporal_boundaries() -> None:
    """Unknown outcomes and invalid income stay excluded with named reasons."""
    prepared = prepare_m1_data(_raw_fixture())
    membership = prepared.membership.set_index("loan_id")
    assert membership.loc[10_000, "exclusion_reason"] == "unresolved_outcome"
    assert membership.loc[10_001, "exclusion_reason"] == "invalid_annual_inc"
    assert set(
        prepared.eligible.loc[prepared.eligible["split"] == "train", "issue_date"].dt.year
    ) <= {
        2011,
        2012,
        2013,
    }
    assert set(
        prepared.eligible.loc[prepared.eligible["split"] == "validation", "issue_date"].dt.year
    ) == {2014}
    assert set(
        prepared.eligible.loc[prepared.eligible["split"] == "test", "issue_date"].dt.year
    ) == {2015}


def test_whitelist_blocks_identity_outcome_and_pricing() -> None:
    """Only the approved M1 feature whitelist reaches estimators."""
    prepared = prepare_m1_data(_raw_fixture())
    x_train, _ = split_xy(prepared.eligible, "train")
    assert tuple(x_train.columns) == FEATURES
    assert not FORBIDDEN_FEATURES.intersection(x_train.columns)


def test_preprocessing_is_train_only_and_handles_unseen_category() -> None:
    """Validation values cannot change fitted medians and new categories remain valid."""
    prepared = prepare_m1_data(_raw_fixture())
    x_train, y_train = split_xy(prepared.eligible, "train")
    x_validation, _ = split_xy(prepared.eligible, "validation")
    candidate = build_candidate("logistic_regression")
    candidate.fit(x_train, y_train)
    imputer = (
        candidate.named_steps["preprocessor"].named_transformers_["numeric"].named_steps["imputer"]
    )
    statistics_before = imputer.statistics_.copy()
    changed = x_validation.copy()
    changed["annual_inc"] = 9_999_999_999
    changed["purpose"] = "never_seen_in_train"
    probability = candidate.predict_proba(changed)[:, 1]
    assert np.isfinite(probability).all()
    assert np.array_equal(statistics_before, imputer.statistics_)


def test_artifact_reload_preserves_schema_and_scores(tmp_path: object) -> None:
    """Serialized pipeline preserves feature order and prediction values."""
    prepared = prepare_m1_data(_raw_fixture())
    x_train, y_train = split_xy(prepared.eligible, "train")
    x_validation, _ = split_xy(prepared.eligible, "validation")
    candidate = build_candidate("logistic_regression").fit(x_train, y_train)
    expected = candidate.predict_proba(x_validation)[:, 1]
    path = str(tmp_path) + "/m1.joblib"
    joblib.dump(candidate, path)
    actual = joblib.load(path).predict_proba(x_validation)[:, 1]
    assert np.allclose(expected, actual, atol=1e-12)


def test_threshold_is_selected_from_given_validation_predictions() -> None:
    """Threshold selection returns a deterministic, finite validation rule."""
    decision = choose_threshold(
        np.array([0, 0, 1, 1]),
        np.array([0.1, 0.4, 0.7, 0.9]),
        minimum_precision=0.8,
        minimum_predicted_positive=1,
        minimum_predicted_positive_fraction=0.0,
    )
    assert 0 <= float(decision["threshold"]) <= 1
    assert decision["rule"] == "max_recall_at_precision_gte_0.80"


def test_threshold_constraint_requires_meaningful_support() -> None:
    """A one-case precision point cannot satisfy the default policy constraint."""
    truth = np.zeros(1_000, dtype=int)
    truth[:99] = 1
    truth[-1] = 1
    probability = np.linspace(0.2, 0.9, 1_000)
    probability[:99] = np.linspace(0.0, 0.1, 99)
    probability[-1] = 0.99
    decision = choose_threshold(truth, probability, minimum_precision=0.99)
    assert decision["rule"] == "fallback_max_f1"
    assert int(decision["minimum_predicted_positive"]) == 100
