"""Fairness audit module for CreditLens using AIF360.

Audits credit scoring models for disparate treatment across protected
groups. Computes Disparate Impact Ratio (target band 0.8-1.25 per project
policy), Statistical/Demographic Parity Difference, and Equal Opportunity
Difference using AIF360 metric implementations.

Protected attributes are proxies available in Lending Club data:
``addr_state`` (geographic proxy) and ``home_ownership``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from aif360.datasets import BinaryLabelDataset
from aif360.metrics import ClassificationMetric

from src.common.logging import configure_logging

configure_logging()

# Favorable outcome in credit scoring is NON-default (label 0)
FAVORABLE_LABEL: float = 0.0
UNFAVORABLE_LABEL: float = 1.0

# Fairness policy band for Disparate Impact Ratio
DI_LOWER_BOUND: float = 0.8
DI_UPPER_BOUND: float = 1.25


def binarize_protected_attribute(series: pd.Series, privileged_values: list[Any]) -> pd.Series:
    """Binarize a protected attribute column into privileged (1) vs not (0).

    Args:
        series: Raw protected attribute values (e.g. home_ownership).
        privileged_values: Values considered the privileged group
            (e.g. ["MORTGAGE", "OWN"]).

    Returns:
        Series of 1 (privileged) / 0 (unprivileged) integers.
    """
    return series.isin(privileged_values).astype(int)


def build_binary_label_dataset(
    df: pd.DataFrame,
    label_col: str,
    protected_col: str,
) -> BinaryLabelDataset:
    """Build an AIF360 BinaryLabelDataset from a labels + protected frame.

    Args:
        df: DataFrame containing the label column and the already-binarized
            protected attribute column.
        label_col: Name of the binary label column (1 = default).
        protected_col: Name of the binarized protected attribute column.

    Returns:
        AIF360 BinaryLabelDataset.
    """
    subset = df[[label_col, protected_col]].astype(float).copy()
    return BinaryLabelDataset(
        df=subset,
        label_names=[label_col],
        protected_attribute_names=[protected_col],
        favorable_label=FAVORABLE_LABEL,
        unfavorable_label=UNFAVORABLE_LABEL,
    )


def compute_fairness_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    protected: pd.Series | np.ndarray,
) -> dict[str, float]:
    """Compute fairness metrics for one binarized protected attribute.

    Args:
        y_true: True binary labels (1 = default).
        y_pred: Predicted binary labels (1 = predicted default / rejection).
        protected: Binarized protected attribute (1 = privileged group).

    Returns:
        Dict with disparate_impact_ratio, statistical_parity_difference
        (demographic parity), and equal_opportunity_difference.
    """
    frame = pd.DataFrame(
        {
            "label": np.asarray(y_true, dtype=float),
            "protected": np.asarray(protected, dtype=float),
        }
    )
    dataset_true = build_binary_label_dataset(frame, "label", "protected")
    dataset_pred = dataset_true.copy()
    dataset_pred.labels = np.asarray(y_pred, dtype=float).reshape(-1, 1)

    metric = ClassificationMetric(
        dataset_true,
        dataset_pred,
        privileged_groups=[{"protected": 1}],
        unprivileged_groups=[{"protected": 0}],
    )
    return {
        "disparate_impact_ratio": float(metric.disparate_impact()),
        "statistical_parity_difference": float(metric.statistical_parity_difference()),
        "equal_opportunity_difference": float(metric.equal_opportunity_difference()),
    }


def is_within_di_policy(disparate_impact_ratio: float) -> bool:
    """Check whether a Disparate Impact Ratio satisfies the policy band.

    Args:
        disparate_impact_ratio: Ratio of favorable outcome rates
            (unprivileged / privileged).

    Returns:
        True if the ratio falls within [0.8, 1.25].
    """
    if not np.isfinite(disparate_impact_ratio):
        return False
    return DI_LOWER_BOUND <= disparate_impact_ratio <= DI_UPPER_BOUND


def audit_model(
    df: pd.DataFrame,
    y_true_col: str,
    y_pred_col: str,
    protected_attributes: dict[str, list[Any]],
    model_name: str = "xgboost",
) -> dict[str, Any]:
    """Run a full fairness audit across multiple protected attributes.

    Args:
        df: DataFrame containing true labels, predicted labels, and raw
            protected attribute columns.
        y_true_col: Column name of true binary labels.
        y_pred_col: Column name of predicted binary labels.
        protected_attributes: Mapping of protected attribute column name to
            the list of privileged values,
            e.g. {"home_ownership": ["MORTGAGE", "OWN"]}.
        model_name: Identifier of the audited model.

    Returns:
        Fairness report dict with per-attribute metrics and policy verdicts.
    """
    attributes_report: dict[str, Any] = {}
    for attr, privileged_values in protected_attributes.items():
        protected = binarize_protected_attribute(df[attr], privileged_values)
        metrics = compute_fairness_metrics(df[y_true_col], df[y_pred_col], protected)
        attributes_report[attr] = {
            "privileged_values": [str(v) for v in privileged_values],
            "metrics": metrics,
            "di_within_policy": is_within_di_policy(metrics["disparate_impact_ratio"]),
        }
    overall_pass = all(item["di_within_policy"] for item in attributes_report.values())
    return {
        "model_name": model_name,
        "policy_band": {"lower": DI_LOWER_BOUND, "upper": DI_UPPER_BOUND},
        "attributes": attributes_report,
        "overall_pass": overall_pass,
    }
