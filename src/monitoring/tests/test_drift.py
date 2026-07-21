"""Unit tests for PSI/KS data drift detection."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.monitoring.drift import (
    DEFAULT_PSI_THRESHOLD,
    detect_drift,
    ks_statistic,
    population_stability_index,
)


def test_psi_near_zero_for_same_distribution() -> None:
    """Identical distributions must yield a near-zero PSI."""
    rng = np.random.default_rng(0)
    sample = rng.normal(size=5_000)
    other = rng.normal(size=5_000)
    assert population_stability_index(sample, other) < 0.1


def test_psi_large_for_shifted_distribution() -> None:
    """A clear location shift must push PSI above the action threshold."""
    rng = np.random.default_rng(1)
    reference = rng.normal(loc=0.0, size=5_000)
    current = rng.normal(loc=3.0, size=5_000)
    assert population_stability_index(reference, current) >= 0.25


def test_psi_handles_constant_reference() -> None:
    """A constant reference (single bin edge) must not raise."""
    assert population_stability_index(np.ones(100), np.ones(100)) == 0.0


def test_ks_statistic_bounds_and_empty() -> None:
    """KS statistic must be in [0, 1] and zero for an empty sample."""
    rng = np.random.default_rng(2)
    stat = ks_statistic(rng.normal(size=500), rng.normal(loc=2.0, size=500))
    assert 0.0 <= stat <= 1.0
    assert ks_statistic(np.array([]), np.array([1.0, 2.0])) == 0.0


def _frame(values: dict[str, np.ndarray]) -> pd.DataFrame:
    """Helper building a feature frame from column arrays."""
    return pd.DataFrame(values)


def test_detect_drift_flags_shifted_feature() -> None:
    """detect_drift must flag the shifted feature and report dataset drift."""
    rng = np.random.default_rng(3)
    reference = _frame(
        {"stable": rng.normal(size=2_000), "shifted": rng.normal(loc=0.0, size=2_000)}
    )
    current = _frame({"stable": rng.normal(size=2_000), "shifted": rng.normal(loc=4.0, size=2_000)})
    report = detect_drift(reference, current, ["stable", "shifted"])

    assert report["features"]["shifted"]["drifted"] is True
    assert report["features"]["stable"]["drifted"] is False
    assert report["n_features"] == 2
    assert report["n_drifted"] == 1
    assert report["drift_share"] == 0.5
    assert report["dataset_drift"] is True
    assert report["psi_threshold"] == DEFAULT_PSI_THRESHOLD


def test_detect_drift_ignores_missing_columns() -> None:
    """Features absent from either frame must be skipped, not raise."""
    reference = _frame({"a": np.arange(100.0)})
    current = _frame({"a": np.arange(100.0)})
    report = detect_drift(reference, current, ["a", "missing"])
    assert report["n_features"] == 1
    assert report["dataset_drift"] is False
