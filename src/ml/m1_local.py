"""Bounded local M1 training and evaluation workflow.

This module implements the approved retrospective 36-month accepted-loan
cohort. It keeps preprocessing inside a scikit-learn pipeline so every fitted
statistic comes only from the training vintage.
"""

from __future__ import annotations

import hashlib
import json
import platform
import resource
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.stats import ks_2samp
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sqlalchemy import create_engine, text

from src.common.config import get_settings

SEED = 42
NUMERIC_FEATURES: tuple[str, ...] = (
    "annual_inc",
    "dti",
    "dti_missing",
    "revol_bal",
    "revol_util",
    "total_acc",
    "open_acc",
    "credit_history_age_months",
    "credit_history_missing",
    "delinq_2yrs",
    "pub_rec",
    "inq_last_6mths",
)
CATEGORICAL_FEATURES: tuple[str, ...] = ("home_ownership", "purpose")
FEATURES: tuple[str, ...] = NUMERIC_FEATURES + CATEGORICAL_FEATURES
FORBIDDEN_FEATURES: frozenset[str] = frozenset(
    {
        "loan_id",
        "issue_date",
        "loan_status",
        "target",
        "term",
        "grade",
        "sub_grade",
        "int_rate",
        "installment",
        "verification_status",
        "total_pymnt",
        "recoveries",
        "last_pymnt_d",
    }
)

COHORT_SQL = """
SELECT
    loan_id,
    issue_date,
    term,
    loan_status,
    annual_inc,
    dti,
    revol_bal,
    revol_util,
    total_acc,
    open_acc,
    earliest_cr_line,
    delinq_2yrs,
    pub_rec,
    inq_last_6mths,
    home_ownership,
    purpose,
    addr_state
FROM raw.lc_loans
WHERE trim(term) = '36 months'
  AND issue_date >= DATE '2011-01-01'
  AND issue_date < DATE '2016-01-01'
ORDER BY issue_date, loan_id
"""


@dataclass(frozen=True)
class M1Data:
    """Prepared M1 records and their reproducibility manifest."""

    eligible: pd.DataFrame
    membership: pd.DataFrame
    manifest: dict[str, Any]


def _sync_postgres_url(postgres_url: str | None) -> str:
    """Return a synchronous PostgreSQL URL without logging credentials."""
    url = postgres_url or get_settings().POSTGRES_URL
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def load_m1_cohort(postgres_url: str | None = None) -> pd.DataFrame:
    """Load only the columns and vintages approved for local M1.

    Args:
        postgres_url: Optional SQLAlchemy PostgreSQL connection URL.

    Returns:
        Raw cohort records ordered deterministically by date and loan ID.
    """
    engine = create_engine(_sync_postgres_url(postgres_url))
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(text(COHORT_SQL), connection)
    finally:
        engine.dispose()


def prepare_m1_data(raw: pd.DataFrame) -> M1Data:
    """Apply the approved target, eligibility, features, and temporal split.

    Args:
        raw: DataFrame containing the columns selected by ``COHORT_SQL``.

    Returns:
        Eligible model rows, private membership rows, and aggregate manifest.

    Raises:
        ValueError: If required columns, unique IDs, or split boundaries fail.
    """
    required = {
        "loan_id",
        "issue_date",
        "term",
        "loan_status",
        "annual_inc",
        "dti",
        "revol_bal",
        "revol_util",
        "total_acc",
        "open_acc",
        "earliest_cr_line",
        "delinq_2yrs",
        "pub_rec",
        "inq_last_6mths",
        "home_ownership",
        "purpose",
        "addr_state",
    }
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"Missing M1 input columns: {missing}")

    frame = raw.copy()
    frame["issue_date"] = pd.to_datetime(frame["issue_date"], errors="coerce")
    frame["earliest_cr_line"] = pd.to_datetime(frame["earliest_cr_line"], errors="coerce")
    if frame["loan_id"].isna().any() or frame["loan_id"].duplicated().any():
        raise ValueError("loan_id must be non-null and unique inside the M1 cohort")

    frame["target"] = frame["loan_status"].map({"Fully Paid": 0, "Charged Off": 1, "Default": 1})
    frame["split"] = pd.cut(
        frame["issue_date"],
        bins=[
            pd.Timestamp("2010-12-31"),
            pd.Timestamp("2013-12-31"),
            pd.Timestamp("2014-12-31"),
            pd.Timestamp("2015-12-31"),
        ],
        labels=["train", "validation", "test"],
    ).astype("string")
    if frame["split"].isna().any():
        raise ValueError("Every M1 record must fall inside the approved split boundaries")

    frame["exclusion_reason"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    frame.loc[frame["target"].isna(), "exclusion_reason"] = "unresolved_outcome"
    invalid_income = frame["annual_inc"].isna() | (frame["annual_inc"] <= 0)
    frame.loc[frame["target"].notna() & invalid_income, "exclusion_reason"] = "invalid_annual_inc"
    frame["eligible"] = frame["exclusion_reason"].isna()

    frame["dti_missing"] = frame["dti"].isna().astype("int8")
    age_months = (frame["issue_date"] - frame["earliest_cr_line"]).dt.days / 30.4375
    frame["credit_history_age_months"] = age_months.mask(age_months < 0)
    frame["credit_history_missing"] = frame["credit_history_age_months"].isna().astype("int8")
    for column in CATEGORICAL_FEATURES:
        frame[column] = frame[column].astype("string")

    membership = frame[
        ["loan_id", "issue_date", "split", "target", "eligible", "exclusion_reason"]
    ].copy()
    eligible = frame.loc[frame["eligible"]].copy()
    eligible["target"] = eligible["target"].astype("int8")

    manifest = build_manifest(frame, eligible)
    return M1Data(eligible=eligible, membership=membership, manifest=manifest)


def build_manifest(all_rows: pd.DataFrame, eligible: pd.DataFrame) -> dict[str, Any]:
    """Build aggregate counts and a deterministic cohort membership checksum."""
    split_rows: dict[str, Any] = {}
    for split_name in ("train", "validation", "test"):
        all_split = all_rows.loc[all_rows["split"] == split_name]
        used = eligible.loc[eligible["split"] == split_name]
        split_rows[split_name] = {
            "all_rows": int(len(all_split)),
            "eligible_rows": int(len(used)),
            "adverse": int(used["target"].sum()),
            "non_adverse": int((used["target"] == 0).sum()),
            "prevalence": float(used["target"].mean()),
            "min_issue_date": used["issue_date"].min().date().isoformat(),
            "max_issue_date": used["issue_date"].max().date().isoformat(),
        }
    exclusions = {
        str(key): int(value)
        for key, value in all_rows["exclusion_reason"].dropna().value_counts().items()
    }
    hash_input = "\n".join(
        f"{row.loan_id}|{row.split}|{row.target}|{row.eligible}"
        for row in all_rows.sort_values("loan_id").itertuples()
    )
    return {
        "cohort": "accepted_36m_issue_2011_2015_retrospective_v1",
        "label_contract": "Fully Paid=0; Charged Off/Default=1; other=NULL",
        "splits": split_rows,
        "exclusions": exclusions,
        "membership_sha256": hashlib.sha256(hash_input.encode("utf-8")).hexdigest(),
        "features": list(FEATURES),
        "limitations": [
            "accepted loans only",
            "retrospective observed outcome; outcome as-of is unknown",
            "member_id unavailable, so borrower overlap cannot be checked",
            "public data use rights remain unverified",
        ],
    }


def split_xy(eligible: pd.DataFrame, split_name: str) -> tuple[pd.DataFrame, pd.Series]:
    """Return whitelisted features and labels for one named split."""
    part = eligible.loc[eligible["split"] == split_name]
    features = part.loc[:, list(FEATURES)].copy()
    if FORBIDDEN_FEATURES.intersection(features.columns):
        raise ValueError("A forbidden leakage column entered the feature matrix")
    return features, part["target"].astype(int).copy()


def build_preprocessor() -> ColumnTransformer:
    """Create train-fitted numeric and categorical preprocessing."""
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, list(NUMERIC_FEATURES)),
            ("categorical", categorical, list(CATEGORICAL_FEATURES)),
        ]
    )


def build_candidate(model_name: str) -> Pipeline:
    """Create one reproducible model candidate inside its preprocessing pipeline."""
    if model_name == "constant":
        estimator: Any = DummyClassifier(strategy="prior")
    elif model_name == "logistic_regression":
        estimator = LogisticRegression(max_iter=1_000, random_state=SEED)
    elif model_name == "xgboost":
        from xgboost import XGBClassifier

        estimator = XGBClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            min_child_weight=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=SEED,
            n_jobs=2,
            tree_method="hist",
            eval_metric="logloss",
        )
    else:
        raise ValueError(f"Unsupported M1 candidate: {model_name}")
    return Pipeline([("preprocessor", build_preprocessor()), ("model", estimator)])


def choose_threshold(
    y_true: pd.Series | np.ndarray,
    y_prob: np.ndarray,
    minimum_precision: float = 0.80,
    minimum_predicted_positive: int = 100,
    minimum_predicted_positive_fraction: float = 0.005,
) -> dict[str, float | str]:
    """Lock a validation threshold under a precision constraint.

    Falls back to the threshold with the best F1 score if no sufficiently
    supported operating point reaches the requested precision.
    """
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    usable_precision = precision[:-1]
    usable_recall = recall[:-1]
    required_support = max(
        minimum_predicted_positive,
        int(np.ceil(len(y_prob) * minimum_predicted_positive_fraction)),
    )
    sorted_probability = np.sort(np.asarray(y_prob, dtype=float))
    predicted_positive = len(y_prob) - np.searchsorted(sorted_probability, thresholds, side="left")
    feasible = np.flatnonzero(
        (usable_precision >= minimum_precision) & (predicted_positive >= required_support)
    )
    if feasible.size:
        index = int(feasible[np.argmax(usable_recall[feasible])])
        rule = f"max_recall_at_precision_gte_{minimum_precision:.2f}"
    else:
        f1 = np.divide(
            2 * usable_precision * usable_recall,
            usable_precision + usable_recall,
            out=np.zeros_like(usable_precision),
            where=(usable_precision + usable_recall) > 0,
        )
        index = int(np.argmax(f1))
        rule = "fallback_max_f1"
    return {
        "threshold": float(thresholds[index]),
        "validation_precision": float(usable_precision[index]),
        "validation_recall": float(usable_recall[index]),
        "validation_predicted_positive": int(predicted_positive[index]),
        "minimum_predicted_positive": required_support,
        "rule": rule,
    }


def evaluation_metrics(
    y_true: pd.Series | np.ndarray, y_prob: np.ndarray, threshold: float
) -> dict[str, Any]:
    """Compute named ranking, calibration, and locked-threshold metrics."""
    truth = np.asarray(y_true, dtype=int)
    probability = np.asarray(y_prob, dtype=float)
    precision_curve, recall_curve, _ = precision_recall_curve(truth, probability)
    prediction = (probability >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, prediction, average="binary", zero_division=0
    )
    negative = probability[truth == 0]
    positive = probability[truth == 1]
    ks = float(ks_2samp(positive, negative).statistic)
    bins = np.minimum((probability * 10).astype(int), 9)
    ece = 0.0
    for bin_number in range(10):
        selected = bins == bin_number
        if selected.any():
            ece += float(selected.mean()) * abs(
                float(probability[selected].mean()) - float(truth[selected].mean())
            )
    return {
        "n": int(len(truth)),
        "adverse": int(truth.sum()),
        "prevalence": float(truth.mean()),
        "average_precision": float(average_precision_score(truth, probability)),
        "trapezoidal_pr_auc": float(np.trapz(precision_curve[::-1], recall_curve[::-1])),
        "roc_auc": float(roc_auc_score(truth, probability)),
        "ks_statistic": ks,
        "brier_score": float(brier_score_loss(truth, probability)),
        "log_loss": float(log_loss(truth, probability)),
        "ece_10_equal_width": ece,
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "predicted_positive": int(prediction.sum()),
        "confusion_matrix_tn_fp_fn_tp": confusion_matrix(truth, prediction).ravel().tolist(),
    }


def bootstrap_intervals(
    y_true: pd.Series | np.ndarray,
    y_prob: np.ndarray,
    repetitions: int = 30,
) -> dict[str, list[float]]:
    """Estimate simple row-bootstrap 95% intervals for final test metrics."""
    truth = np.asarray(y_true, dtype=int)
    probability = np.asarray(y_prob, dtype=float)
    rng = np.random.default_rng(SEED)
    values: dict[str, list[float]] = {"average_precision": [], "roc_auc": [], "brier_score": []}
    for _ in range(repetitions):
        indexes = rng.integers(0, len(truth), size=len(truth))
        sample_y = truth[indexes]
        sample_p = probability[indexes]
        if np.unique(sample_y).size < 2:
            continue
        values["average_precision"].append(float(average_precision_score(sample_y, sample_p)))
        values["roc_auc"].append(float(roc_auc_score(sample_y, sample_p)))
        values["brier_score"].append(float(brier_score_loss(sample_y, sample_p)))
    return {
        key: [float(v) for v in np.quantile(metric_values, [0.025, 0.975])]
        for key, metric_values in values.items()
    }


def peak_rss_mb() -> float:
    """Return peak resident memory in MiB on macOS or Unix-like systems."""
    raw = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    divisor = 1024**2 if platform.system() == "Darwin" else 1024
    return raw / divisor


def run_m1_local(
    output_dir: str | Path,
    postgres_url: str | None = None,
    include_xgboost: bool = True,
) -> dict[str, Any]:
    """Run candidate selection on validation and open frozen test once.

    Args:
        output_dir: Private directory for manifest, metrics, membership, and model.
        postgres_url: Optional PostgreSQL connection URL.
        include_xgboost: Whether to run the one approved bounded XGBoost candidate.

    Returns:
        Complete local run report.
    """
    started = time.perf_counter()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    prepared = prepare_m1_data(load_m1_cohort(postgres_url))
    x_train, y_train = split_xy(prepared.eligible, "train")
    x_validation, y_validation = split_xy(prepared.eligible, "validation")
    x_test, y_test = split_xy(prepared.eligible, "test")

    candidate_names = ["constant", "logistic_regression"]
    if include_xgboost:
        candidate_names.append("xgboost")
    candidates: dict[str, Pipeline] = {}
    validation: dict[str, dict[str, Any]] = {}
    for name in candidate_names:
        candidate = build_candidate(name)
        candidate.fit(x_train, y_train)
        probabilities = candidate.predict_proba(x_validation)[:, 1]
        threshold = choose_threshold(y_validation, probabilities)
        validation[name] = evaluation_metrics(
            y_validation, probabilities, float(threshold["threshold"])
        ) | {"threshold_selection": threshold}
        candidates[name] = candidate

    selected_name = max(
        candidate_names,
        key=lambda name: (
            validation[name]["average_precision"],
            -validation[name]["brier_score"],
        ),
    )
    selected = candidates[selected_name]
    locked_threshold = float(validation[selected_name]["threshold_selection"]["threshold"])

    # The frozen test is scored only after the candidate and threshold are locked.
    test_probability = selected.predict_proba(x_test)[:, 1]
    test_metrics = evaluation_metrics(y_test, test_probability, locked_threshold)
    intervals = bootstrap_intervals(y_test, test_probability)

    artifact_path = output / "selected_m1_candidate.joblib"
    joblib.dump(selected, artifact_path)
    reloaded = joblib.load(artifact_path)
    probe_size = min(100, len(x_test))
    reloaded_probability = reloaded.predict_proba(x_test.iloc[:probe_size])[:, 1]
    if not np.allclose(test_probability[:probe_size], reloaded_probability, atol=1e-12):
        raise ValueError("Serialized M1 candidate does not reproduce its test scores")

    prepared.membership.to_csv(output / "cohort_membership_private.csv.gz", index=False)
    artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    report: dict[str, Any] = {
        "status": "local_research_only_not_release_ready",
        "seed": SEED,
        "manifest": prepared.manifest,
        "validation_candidates": validation,
        "selection_rule": "highest validation average precision; lower Brier breaks ties",
        "selected_candidate": selected_name,
        "locked_threshold": locked_threshold,
        "frozen_test_opened_once": True,
        "frozen_test_metrics": test_metrics,
        "frozen_test_row_bootstrap_95pct": intervals,
        "artifact_sha256": artifact_sha256,
        "runtime": {
            "elapsed_seconds": time.perf_counter() - started,
            "peak_rss_mb": peak_rss_mb(),
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "limitations": prepared.manifest["limitations"]
        + [
            "threshold is an exploratory validation rule, not an approved lending policy",
            "bootstrap resamples rows and cannot account for borrower clustering",
            "candidate artifact is not an API or production bundle",
        ],
    }
    (output / "m1_local_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(prepared.manifest, indent=2), encoding="utf-8")
    return report
