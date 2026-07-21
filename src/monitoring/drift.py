"""Data drift detection for CreditLens monitoring.

Implements the drift signal used by the monitoring DAG with dependency-light,
deterministic statistics — Population Stability Index (PSI) and the
Kolmogorov-Smirnov two-sample test — so the check is reproducible in CI and
independent of the (fast-moving) Evidently API. Evidently is used separately
for rich HTML reports (see ``evidently_report``).

PSI interpretation (industry convention for credit models):
    < 0.10  : no significant shift
    0.10-0.25: moderate shift (investigate)
    >= 0.25 : significant shift (action required)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from src.common.logging import configure_logging

configure_logging()

DEFAULT_PSI_THRESHOLD: float = 0.25
_EPSILON: float = 1e-6


def population_stability_index(
    expected: np.ndarray | pd.Series,
    actual: np.ndarray | pd.Series,
    bins: int = 10,
) -> float:
    """Compute the Population Stability Index between two samples.

    Bin edges are derived from quantiles of the expected (reference)
    distribution so each reference bin holds a similar mass.

    Args:
        expected: Reference sample values.
        actual: Current sample values.
        bins: Number of quantile bins.

    Returns:
        The PSI value (0.0 when both samples are effectively identical).
    """
    expected_arr = np.asarray(expected, dtype=float)
    actual_arr = np.asarray(actual, dtype=float)
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(expected_arr, quantiles))
    if edges.size < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf

    expected_share = _bin_shares(expected_arr, edges)
    actual_share = _bin_shares(actual_arr, edges)
    return float(np.sum((actual_share - expected_share) * np.log(actual_share / expected_share)))


def _bin_shares(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Compute per-bin proportions with epsilon smoothing.

    Args:
        values: Sample values to bin.
        edges: Monotonic bin edges.

    Returns:
        Array of bin proportions that sum to 1, floored at epsilon.
    """
    counts, _ = np.histogram(values, bins=edges)
    shares = counts / max(counts.sum(), 1)
    clipped: np.ndarray = np.clip(shares, _EPSILON, None)
    return clipped


def ks_statistic(reference: np.ndarray | pd.Series, current: np.ndarray | pd.Series) -> float:
    """Compute the Kolmogorov-Smirnov two-sample statistic.

    Args:
        reference: Reference sample values.
        current: Current sample values.

    Returns:
        The KS statistic (0.0 when a sample is empty).
    """
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    if ref.size == 0 or cur.size == 0:
        return 0.0
    stat, _ = ks_2samp(ref, cur)
    return float(stat)


def detect_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str],
    psi_threshold: float = DEFAULT_PSI_THRESHOLD,
) -> dict[str, Any]:
    """Detect per-feature and dataset-level drift between two frames.

    Args:
        reference_df: Reference (training-time) feature frame.
        current_df: Current (recent) feature frame.
        features: Numeric feature columns to evaluate.
        psi_threshold: PSI value at or above which a feature is drifted.

    Returns:
        Report dict with per-feature PSI/KS/drifted flags and a
        dataset-level summary (drift share and overall boolean).
    """
    feature_report: dict[str, dict[str, float | bool]] = {}
    for feature in features:
        if feature not in reference_df.columns or feature not in current_df.columns:
            continue
        psi = population_stability_index(reference_df[feature], current_df[feature])
        ks = ks_statistic(reference_df[feature], current_df[feature])
        feature_report[feature] = {
            "psi": psi,
            "ks_statistic": ks,
            "drifted": psi >= psi_threshold,
        }

    n_drifted = sum(1 for item in feature_report.values() if item["drifted"])
    n_features = len(feature_report)
    drift_share = n_drifted / n_features if n_features else 0.0
    return {
        "psi_threshold": psi_threshold,
        "features": feature_report,
        "n_features": n_features,
        "n_drifted": n_drifted,
        "drift_share": drift_share,
        "dataset_drift": n_drifted > 0,
    }
