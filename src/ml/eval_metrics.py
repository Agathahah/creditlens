"""Extended evaluation metrics and diagnostic plots for CreditLens.

Builds on the core credit metrics (``src.ml.train.compute_credit_metrics``)
with an operating-point threshold, confusion matrix, and calibration
metrics, plus matplotlib artifacts (ROC/PR/confusion/calibration) suitable
for logging to MLflow. Matplotlib uses the non-interactive Agg backend so
this is safe in headless CI and Airflow workers.
"""

from __future__ import annotations

import os
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    auc,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)

from src.common.logging import configure_logging  # noqa: E402
from src.ml.train import compute_credit_metrics  # noqa: E402

configure_logging()


def best_threshold(y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series) -> float:
    """Find the decision threshold maximizing Youden's J (tpr - fpr).

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.

    Returns:
        The probability threshold at the optimal operating point.
    """
    fpr, tpr, thresholds = roc_curve(np.asarray(y_true), np.asarray(y_prob))
    youden = tpr - fpr
    return float(thresholds[int(np.argmax(youden))])


def confusion_at_threshold(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series, threshold: float
) -> dict[str, int]:
    """Compute the confusion matrix at a probability threshold.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.
        threshold: Probability at/above which a case is predicted positive.

    Returns:
        Mapping with tn, fp, fn, tp counts.
    """
    y_pred = (np.asarray(y_prob) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(np.asarray(y_true), y_pred, labels=[0, 1]).ravel()
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def calibration_metrics(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series, n_bins: int = 10
) -> dict[str, float]:
    """Compute calibration quality: Brier score and expected calibration error.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.
        n_bins: Number of equal-width probability bins for ECE.

    Returns:
        Mapping with brier_score and ece.
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    brier = float(brier_score_loss(y_true_arr, y_prob_arr))
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total = len(y_prob_arr)
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (y_prob_arr >= lo) & (y_prob_arr < hi if hi < 1.0 else y_prob_arr <= hi)
        if not mask.any():
            continue
        ece += abs(y_true_arr[mask].mean() - y_prob_arr[mask].mean()) * (mask.sum() / total)
    return {"brier_score": brier, "ece": float(ece)}


def extended_metrics(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series
) -> dict[str, Any]:
    """Compute the full evaluation metric set for a model.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.

    Returns:
        Credit metrics plus best_threshold, confusion_matrix, and
        calibration metrics (JSON-serializable).
    """
    metrics: dict[str, Any] = dict(compute_credit_metrics(y_true, y_prob))
    threshold = best_threshold(y_true, y_prob)
    metrics["best_threshold"] = threshold
    metrics["confusion_matrix"] = confusion_at_threshold(y_true, y_prob, threshold)
    metrics.update(calibration_metrics(y_true, y_prob))
    return metrics


def _save_fig(fig: Any, output_dir: str, filename: str) -> str:
    """Save a matplotlib figure and return its path.

    Args:
        fig: Figure to save.
        output_dir: Destination directory (created if missing).
        filename: File name for the PNG.

    Returns:
        The written file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, bbox_inches="tight", dpi=100)
    plt.close(fig)
    return path


def plot_roc_curve(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series, output_dir: str
) -> str:
    """Render and save the ROC curve.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.
        output_dir: Destination directory.

    Returns:
        The saved figure path.
    """
    fpr, tpr, _ = roc_curve(np.asarray(y_true), np.asarray(y_prob))
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"AUC = {auc(fpr, tpr):.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    return _save_fig(fig, output_dir, "roc_curve.png")


def plot_pr_curve(
    y_true: np.ndarray | pd.Series, y_prob: np.ndarray | pd.Series, output_dir: str
) -> str:
    """Render and save the precision-recall curve.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.
        output_dir: Destination directory.

    Returns:
        The saved figure path.
    """
    precision, recall, _ = precision_recall_curve(np.asarray(y_true), np.asarray(y_prob))
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(recall, precision, label=f"PR-AUC = {auc(recall, precision):.3f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    ax.legend(loc="upper right")
    return _save_fig(fig, output_dir, "pr_curve.png")


def plot_confusion_matrix(confusion: dict[str, int], output_dir: str) -> str:
    """Render and save a 2x2 confusion-matrix heatmap.

    Args:
        confusion: Mapping with tn, fp, fn, tp.
        output_dir: Destination directory.

    Returns:
        The saved figure path.
    """
    grid = np.array([[confusion["tn"], confusion["fp"]], [confusion["fn"], confusion["tp"]]])
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(grid, cmap="Blues")
    ax.set_xticks([0, 1], labels=["Pred 0", "Pred 1"])
    ax.set_yticks([0, 1], labels=["True 0", "True 1"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(grid[i, j]), ha="center", va="center")
    ax.set_title("Confusion Matrix")
    return _save_fig(fig, output_dir, "confusion_matrix.png")


def plot_calibration_curve(
    y_true: np.ndarray | pd.Series,
    y_prob: np.ndarray | pd.Series,
    output_dir: str,
    n_bins: int = 10,
) -> str:
    """Render and save the reliability (calibration) curve.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.
        output_dir: Destination directory.
        n_bins: Number of calibration bins.

    Returns:
        The saved figure path.
    """
    prob_true, prob_pred = calibration_curve(
        np.asarray(y_true), np.asarray(y_prob), n_bins=n_bins, strategy="uniform"
    )
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(prob_pred, prob_true, marker="o", label="Model")
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey", label="Perfect")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration Curve")
    ax.legend(loc="upper left")
    return _save_fig(fig, output_dir, "calibration_curve.png")


def save_evaluation_artifacts(
    y_true: np.ndarray | pd.Series,
    y_prob: np.ndarray | pd.Series,
    confusion: dict[str, int],
    output_dir: str,
) -> list[str]:
    """Generate all diagnostic plots for an evaluation run.

    Args:
        y_true: True binary default labels.
        y_prob: Predicted default probabilities.
        confusion: Confusion matrix counts at the chosen threshold.
        output_dir: Destination directory.

    Returns:
        Paths of the saved artifacts.
    """
    return [
        plot_roc_curve(y_true, y_prob, output_dir),
        plot_pr_curve(y_true, y_prob, output_dir),
        plot_confusion_matrix(confusion, output_dir),
        plot_calibration_curve(y_true, y_prob, output_dir),
    ]
