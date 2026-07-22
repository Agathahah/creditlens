"""Persistence of monitoring metrics to PostgreSQL for Grafana.

Grafana reads its panels from PostgreSQL, so evaluation metrics, drift
reports, and prediction distributions are written to the ``monitoring``
schema here. All writers accept an optional SQLAlchemy engine to keep them
unit-testable without a live database.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.common.config import get_settings
from src.common.logging import configure_logging

configure_logging()


def get_sync_engine(postgres_url: str | None = None) -> Engine:
    """Build a synchronous SQLAlchemy engine for the warehouse.

    Args:
        postgres_url: Connection URL. Defaults to the ``POSTGRES_URL`` setting.

    Returns:
        A synchronous SQLAlchemy engine.
    """
    from sqlalchemy import create_engine

    url = postgres_url or get_settings().POSTGRES_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return create_engine(url)


def persist_evaluation(
    metrics: dict[str, Any],
    model_name: str,
    y_prob: np.ndarray | pd.Series | None = None,
    engine: Engine | None = None,
    postgres_url: str | None = None,
) -> None:
    """Persist an evaluation run's metrics (and optional score histogram).

    Args:
        metrics: Extended metric mapping from ``extended_metrics``.
        model_name: Identifier of the evaluated model.
        y_prob: Optional predicted probabilities for a distribution histogram.
        engine: Optional SQLAlchemy engine (built from settings if omitted).
        postgres_url: Optional URL override used when engine is omitted.
    """
    engine = engine or get_sync_engine(postgres_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO monitoring.model_metrics "
                "(model_name, roc_auc, pr_auc, ks_statistic, best_threshold, brier_score, ece) "
                "VALUES (:model_name, :roc_auc, :pr_auc, :ks, :thr, :brier, :ece)"
            ),
            {
                "model_name": model_name,
                "roc_auc": metrics.get("roc_auc"),
                "pr_auc": metrics.get("pr_auc"),
                "ks": metrics.get("ks_statistic"),
                "thr": metrics.get("best_threshold"),
                "brier": metrics.get("brier_score"),
                "ece": metrics.get("ece"),
            },
        )
        for row in _histogram_rows(y_prob, model_name):
            conn.execute(
                text(
                    "INSERT INTO monitoring.prediction_bins "
                    "(model_name, bin_lo, bin_hi, count) "
                    "VALUES (:model_name, :bin_lo, :bin_hi, :count)"
                ),
                row,
            )


def _histogram_rows(
    y_prob: np.ndarray | pd.Series | None, model_name: str, bins: int = 20
) -> list[dict[str, Any]]:
    """Bin predicted probabilities into rows for prediction_bins.

    Args:
        y_prob: Predicted probabilities, or None to skip.
        model_name: Model identifier stored on each row.
        bins: Number of equal-width bins over [0, 1].

    Returns:
        List of row dicts (empty when y_prob is None).
    """
    if y_prob is None:
        return []
    counts, edges = np.histogram(np.asarray(y_prob, dtype=float), bins=bins, range=(0.0, 1.0))
    return [
        {
            "model_name": model_name,
            "bin_lo": float(edges[i]),
            "bin_hi": float(edges[i + 1]),
            "count": int(counts[i]),
        }
        for i in range(len(counts))
    ]


def persist_drift(
    report: dict[str, Any],
    engine: Engine | None = None,
    postgres_url: str | None = None,
) -> None:
    """Persist a drift report's run summary and per-feature metrics.

    Args:
        report: Report returned by ``detect_drift``.
        engine: Optional SQLAlchemy engine (built from settings if omitted).
        postgres_url: Optional URL override used when engine is omitted.
    """
    engine = engine or get_sync_engine(postgres_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO monitoring.drift_runs "
                "(dataset_drift, drift_share, n_drifted, n_features) "
                "VALUES (:dataset_drift, :drift_share, :n_drifted, :n_features)"
            ),
            {
                "dataset_drift": bool(report.get("dataset_drift", False)),
                "drift_share": report.get("drift_share"),
                "n_drifted": report.get("n_drifted"),
                "n_features": report.get("n_features"),
            },
        )
        for feature, item in report.get("features", {}).items():
            conn.execute(
                text(
                    "INSERT INTO monitoring.feature_drift "
                    "(feature, psi, ks_statistic, drifted) "
                    "VALUES (:feature, :psi, :ks, :drifted)"
                ),
                {
                    "feature": feature,
                    "psi": item.get("psi"),
                    "ks": item.get("ks_statistic"),
                    "drifted": bool(item.get("drifted", False)),
                },
            )
