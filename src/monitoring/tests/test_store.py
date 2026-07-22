"""Unit tests for monitoring metric persistence."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np

from src.monitoring import store
from src.monitoring.store import _histogram_rows, persist_drift, persist_evaluation


def _engine_with_conn() -> tuple[MagicMock, MagicMock]:
    """Build a mock engine whose begin() yields a recording connection."""
    conn = MagicMock()
    engine = MagicMock()

    @contextmanager
    def _begin() -> Any:
        yield conn

    engine.begin = _begin
    return engine, conn


def test_histogram_rows_none_returns_empty() -> None:
    """No probabilities means no prediction-bin rows."""
    assert _histogram_rows(None, "xgboost") == []


def test_histogram_rows_partition_full_range() -> None:
    """Bins must span [0, 1] and their counts must sum to the sample size."""
    rows = _histogram_rows(np.array([0.05, 0.5, 0.95]), "xgboost", bins=10)
    assert len(rows) == 10
    assert rows[0]["bin_lo"] == 0.0
    assert rows[-1]["bin_hi"] == 1.0
    assert sum(r["count"] for r in rows) == 3
    assert all(r["model_name"] == "xgboost" for r in rows)


def test_persist_evaluation_inserts_metrics_and_bins() -> None:
    """persist_evaluation must write one metrics row plus histogram rows."""
    engine, conn = _engine_with_conn()
    metrics = {"roc_auc": 0.8, "pr_auc": 0.4, "ks_statistic": 0.5, "best_threshold": 0.3}
    persist_evaluation(metrics, "xgboost", y_prob=np.array([0.1, 0.9]), engine=engine)

    statements = [call.args[0].text for call in conn.execute.call_args_list]
    assert any("monitoring.model_metrics" in s for s in statements)
    assert any("monitoring.prediction_bins" in s for s in statements)
    # 1 metrics insert + 20 default histogram bins
    assert conn.execute.call_count == 21


def test_persist_evaluation_without_probs() -> None:
    """Without probabilities only the metrics row is written."""
    engine, conn = _engine_with_conn()
    persist_evaluation({"pr_auc": 0.4}, "lightgbm", engine=engine)
    assert conn.execute.call_count == 1


def test_persist_drift_inserts_run_and_features() -> None:
    """persist_drift must write the run summary and one row per feature."""
    engine, conn = _engine_with_conn()
    report = {
        "dataset_drift": True,
        "drift_share": 0.5,
        "n_drifted": 1,
        "n_features": 2,
        "features": {
            "int_rate": {"psi": 0.4, "ks_statistic": 0.3, "drifted": True},
            "dti_eff": {"psi": 0.05, "ks_statistic": 0.1, "drifted": False},
        },
    }
    persist_drift(report, engine=engine)

    statements = [call.args[0].text for call in conn.execute.call_args_list]
    assert sum("monitoring.drift_runs" in s for s in statements) == 1
    assert sum("monitoring.feature_drift" in s for s in statements) == 2


def test_get_sync_engine_normalizes_async_url() -> None:
    """The async driver prefix must be rewritten to the sync driver."""
    with patch("sqlalchemy.create_engine", side_effect=lambda url: url) as create_engine:
        store.get_sync_engine("postgresql+asyncpg://u:p@h:5432/db")

    create_engine.assert_called_once_with("postgresql://u:p@h:5432/db")
