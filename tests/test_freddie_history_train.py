"""V4 temporal, memory, source-access and past-only feature contracts on synthetic data."""

from __future__ import annotations

import copy
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from src.research.freddie_history_train import (
    PROTOCOL_SHA,
    collect_development,
    validate_plan,
)
from src.research.freddie_preflight import sha256

ROOT = Path(__file__).resolve().parents[1]


def protocol() -> dict:
    """Read only the locked public configuration, never real source data."""
    path = ROOT / "config/research/freddie_experiment_v4.json"
    assert sha256(path) == PROTOCOL_SHA
    return json.loads(path.read_text())


def make_archive(path: Path, adverse_future: bool) -> None:
    """Create a small synthetic legacy-format source with intentionally unknown origination."""
    row = [""] * 31
    row[0], row[8], row[9], row[11], row[19] = "9999", "80", "35", "80", "synthetic"
    records = []
    for period, dq in (
        ("202212", "01"),
        ("202301", "00"),
        ("202302", "03" if adverse_future else "00"),
        ("202303", "00"),
        ("202304", "00"),
        ("202603", "00"),
    ):
        item = [""] * 35
        item[:6] = ["synthetic", period, "90" if period == "202301" else "100", dq, "12", "348"]
        item[10] = "4.0"
        records.append("|".join(item))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("sample_orig_2021.txt", "|".join(row) + "\n")
        z.writestr("sample_perf_2021.txt", "\n".join(records) + "\n")


def test_v4_keeps_gates_budget_and_consumed_source_excluded() -> None:
    """New features/recent calibration must not lower any v3 gate or admit old test records."""
    current = protocol()
    previous = json.loads((ROOT / "config/research/freddie_experiment_v3.json").read_text())
    validate_plan(current)
    assert current["proposed_research_gates"] == previous["proposed_research_gates"]
    assert current["resource_budget"] == previous["resource_budget"]
    assert current["candidates"] == previous["candidates"]
    assert current["features"] == previous["features"] + current["history_features"]
    assert 2020 not in current["source_constraints"]["supported_vintages"]


@pytest.mark.parametrize("role", ["calibration", "validation", "frozen_test"])
def test_maturity_must_precede_next_role(role: str) -> None:
    """Reporting cohorts cannot overlap labels from the preceding role."""
    config = protocol()
    roles = ["train", "calibration", "validation", "frozen_test"]
    previous = roles[roles.index(role) - 1]
    config["split"][role]["as_of_start"] = config["split"][previous]["last_outcome"]
    with pytest.raises(ValueError, match="maturity"):
        validate_plan(config)


@pytest.mark.parametrize("vintage", [2019, 2020, 2022])
def test_development_rejects_other_vintages_before_any_file_access(vintage: int) -> None:
    """No missing path lookup or outcome opener may run for sealed/unsupported sources."""
    with pytest.raises(ValueError, match="sealed"):
        collect_development(Path("/must-never-open"), vintage, {}, protocol())


def test_new_calendar_features_are_future_invariant_and_missing_explicit(tmp_path: Path) -> None:
    """Future labels can change while the input at the same as-of remains exactly identical."""
    config = protocol()
    splits = {
        "calibration": {
            "vintage": 2021,
            "as_of_start": "202301",
            "as_of_end": "202301",
            "last_outcome": "202304",
        }
    }
    cohorts = []
    for adverse in (False, True):
        path = tmp_path / f"source-{adverse}.zip"
        make_archive(path, adverse)
        cohorts.append(collect_development(path, 2021, splits, config)["calibration"])
    np.testing.assert_array_equal(cohorts[0].features.to_numpy(), cohorts[1].features.to_numpy())
    assert cohorts[0].frame["label"].tolist() == [0]
    assert cohorts[1].frame["label"].tolist() == [1]
    f = cohorts[0].features.iloc[0]
    assert f["prior_dq_1"] == 1
    assert f["months_since_known_dq_12"] == 1
    assert f["complete_status_6"] == 0
    assert np.isnan(f["worst_dq_6"]) and np.isnan(f["credit_score"])
    assert set(cohorts[0].features.dtypes) == {np.dtype("float32")}
    assert cohorts[0].counts["eligible_observations"] == 1
    assert cohorts[0].counts["labeled"] + cohorts[0].counts["censored"] == 1


def test_wrong_cutoff_is_not_silently_accepted(tmp_path: Path) -> None:
    """A metadata binding cannot replace actual streaming source cutoff validation."""
    config = copy.deepcopy(protocol())
    config["source_constraints"]["expected_performance_cutoff"] = "202512"
    path = tmp_path / "source.zip"
    make_archive(path, False)
    split = {
        "train": {
            "vintage": 2021,
            "as_of_start": "202301",
            "as_of_end": "202301",
            "last_outcome": "202304",
        }
    }
    with pytest.raises(ValueError, match="cutoff"):
        collect_development(path, 2021, split, config)


def test_calibration_identity_partition_must_be_complementary() -> None:
    config = protocol()
    config["split"]["validation"]["loan_partition"]["bucket"] = 0
    with pytest.raises(ValueError, match="complementary"):
        validate_plan(config)
