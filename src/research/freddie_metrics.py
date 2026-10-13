"""Evaluate a locked mortgage candidate; cluster bootstrap retains loan-month dependence."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


def capacity_metrics(
    frame: pd.DataFrame, scores: np.ndarray[Any, Any], fraction: float
) -> dict[str, Any]:
    """Measure a deterministic monthly top-fraction policy on labeled observations.

    Args:
        frame: Loan ID, as-of and binary label columns for the evaluation cohort.
        scores: Aligned finite probabilities.
        fraction: Monthly alert capacity as a fraction of labeled rows.

    Returns:
        Alert counts, precision, recall and per-month denominators.
    """
    if not 0 < fraction <= 1 or len(scores) != len(frame):
        raise ValueError("Invalid capacity or alignment")
    alerts = hits = positives = 0
    monthly = []
    data = frame[["loan_id", "as_of", "label"]].copy()
    data["probability"] = scores
    for month, group in data.groupby("as_of", sort=True):
        ordered = group.sort_values(["probability", "loan_id"], ascending=[False, True])
        count = max(1, math.ceil(len(group) * fraction))
        caught = int(ordered.head(count)["label"].sum())
        events = int(group["label"].sum())
        alerts += count
        hits += caught
        positives += events
        monthly.append(
            {
                "as_of": str(month),
                "labeled": len(group),
                "adverse": events,
                "alerts": count,
                "true_positive_alerts": caught,
            }
        )
    prevalence = float(data["label"].mean())
    precision = hits / alerts if alerts else 0.0
    return {
        "alerts": alerts,
        "true_positive_alerts": hits,
        "precision": precision,
        "recall": hits / positives if positives else 0.0,
        "precision_lift": precision / prevalence if prevalence else None,
        "monthly": monthly,
    }


def evaluate_predictions(
    frame: pd.DataFrame, scores: np.ndarray[Any, Any], train_prevalence: float, fraction: float
) -> dict[str, Any]:
    """Report ranking, squared probability error, reliability and alert policy.

    Args:
        frame: Labeled evaluation rows.
        scores: Probabilities aligned to those rows.
        train_prevalence: Frozen constant baseline estimated exclusively on train.
        fraction: Locked monthly alert fraction.

    Returns:
        Metrics on the identical labeled cohort and descriptive reliability bins.
    """
    y = frame["label"].to_numpy(dtype=float)
    if (
        len(y) == 0
        or len(y) != len(scores)
        or not np.isfinite(scores).all()
        or ((scores < 0) | (scores > 1)).any()
    ):
        raise ValueError("Invalid probability vector")
    prevalence = float(y.mean())
    if not 0 < prevalence < 1:
        raise ValueError("Evaluation requires both classes")
    baseline_brier = float(np.mean((train_prevalence - y) ** 2))
    brier = float(np.mean((scores - y) ** 2))
    ap = float(average_precision_score(y, scores))
    edges = np.unique(np.quantile(scores, np.linspace(0, 1, 11)))
    bins = np.searchsorted(edges[1:-1], scores, side="right")
    reliability = []
    for index in np.unique(bins):
        keep = bins == index
        reliability.append(
            {
                "count": int(keep.sum()),
                "mean_probability": float(scores[keep].mean()),
                "observed_rate": float(y[keep].mean()),
            }
        )
    return {
        "labeled": len(y),
        "adverse_observations": int(y.sum()),
        "prevalence": prevalence,
        "ap": ap,
        "ap_lift": ap / prevalence,
        "roc_auc": float(roc_auc_score(y, scores)),
        "brier": brier,
        "constant_train_brier": baseline_brier,
        "brier_skill": 1 - brier / baseline_brier,
        "mean_probability": float(scores.mean()),
        "reliability_quantile_bins": reliability,
        "capacity": capacity_metrics(frame, scores, fraction),
    }


def weighted_ap(
    y_sorted: np.ndarray[Any, Any],
    weights_sorted: np.ndarray[Any, Any],
    tie_ends: np.ndarray[Any, Any],
) -> float | None:
    """Calculate non-interpolated AP with tied scores and zero-weight observations.

    Args:
        y_sorted: Labels ordered by decreasing fixed prediction.
        weights_sorted: Integer multiplicity for every loan-month in a bootstrap draw.
        tie_ends: Last index of each prediction tie group.

    Returns:
        Weighted AP or None when a resample has no positive observations.
    """
    tp = np.cumsum(y_sorted * weights_sorted)[tie_ends]
    count = np.cumsum(weights_sorted)[tie_ends]
    if tp[-1] <= 0:
        return None
    precision = np.divide(tp, count, out=np.zeros_like(tp, dtype=float), where=count > 0)
    return float(np.sum(np.diff(np.r_[0.0, tp]) / tp[-1] * precision))


def bootstrap_ap_lift(
    frame: pd.DataFrame, scores: np.ndarray[Any, Any], replicates: int, seed: int
) -> dict[str, Any]:
    """Resample loans, retaining all their rows, and compare AP to paired prevalence.

    Args:
        frame: Fixed labeled cohort containing private loan IDs.
        scores: Aligned fixed candidate probabilities.
        replicates: Number of cluster-bootstrap draws.
        seed: Reproducible random seed.

    Returns:
        Percentile 95% AP-lift interval and valid/invalid draw counts.
    """
    if replicates < 1 or len(frame) != len(scores):
        raise ValueError("Invalid bootstrap parameters")
    loans, inverse = np.unique(frame["loan_id"].to_numpy(dtype=str), return_inverse=True)
    y = frame["label"].to_numpy(dtype=float)
    order = np.argsort(-scores, kind="stable")
    sorted_scores = scores[order]
    ends = np.r_[np.flatnonzero(np.diff(sorted_scores)), len(scores) - 1]
    rng = np.random.default_rng(seed)
    lifts = []
    for _ in range(replicates):
        multiplicities = np.bincount(
            rng.integers(0, len(loans), size=len(loans)), minlength=len(loans)
        )
        weights = multiplicities[inverse].astype(float)
        prevalence = float(np.dot(y, weights) / weights.sum())
        ap = weighted_ap(y[order], weights[order], ends)
        if ap is not None and prevalence > 0:
            lifts.append(ap / prevalence)
    interval = np.quantile(lifts, [0.025, 0.975]).tolist() if lifts else [None, None]
    return {
        "method": "paired_cluster_bootstrap_by_loan",
        "replicates": replicates,
        "valid_replicates": len(lifts),
        "invalid_replicates": replicates - len(lifts),
        "ap_lift_95pct_interval": interval,
    }


def validation_gates(
    metrics: dict[str, Any], uncertainty: dict[str, Any], unique_events: int, gates: dict[str, Any]
) -> dict[str, bool]:
    """Apply the approved research criteria without changing thresholds after evaluation.

    Args:
        metrics: Candidate metrics computed on validation.
        uncertainty: Loan-cluster bootstrap report.
        unique_events: Distinct validation loans with positive labels.
        gates: Immutable research gate configuration.

    Returns:
        Named boolean results; any false result prevents opening frozen test.
    """
    lower = uncertainty["ap_lift_95pct_interval"][0]
    return {
        "unique_event_support": unique_events
        >= gates["minimum_unique_adverse_loans"]["validation"],
        "ap_lift": metrics["ap_lift"] >= gates["ap_lift_over_prevalence_minimum"],
        "ap_uncertainty": uncertainty["invalid_replicates"] == 0
        and lower is not None
        and lower > gates["ap_lift_loan_bootstrap_95pct_lower_bound_exceeds"],
        "brier_skill": metrics["brier_skill"]
        > gates["brier_skill_over_train_constant_minimum_exclusive"],
        "capacity_recall": metrics["capacity"]["recall"]
        >= gates["recall_at_monthly_top_1pct_minimum"],
        "capacity_precision_lift": metrics["capacity"]["precision_lift"] is not None
        and metrics["capacity"]["precision_lift"]
        >= gates["alert_precision_lift_over_prevalence_minimum"],
        "nonempty_alerts": metrics["capacity"]["alerts"] > 0,
    }
