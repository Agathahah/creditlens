"""Synthetic training and negative release contracts; no private source is used by CI."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from src.research.freddie_metrics import (
    bootstrap_ap_lift,
    capacity_metrics,
    weighted_ap,
)
from src.research.freddie_panel import FEATURES, LABEL_VERSION
from src.research.freddie_preflight import SCOPE, assess_admission, sha256
from src.research.freddie_train import (
    APPROVED_PROTOCOL_SHA,
    load_window,
    require_training_admission,
    supervise,
    validation_worker,
)

ROOT = Path(__file__).resolve().parents[1]


def test_weighted_ap_matches_sklearn_with_ties_and_cluster_multiplicity() -> None:
    """Weighted computation must agree with an independent standard implementation."""
    y = np.array([1, 0, 1, 0, 1, 0])
    scores = np.array([0.9, 0.9, 0.4, 0.2, 0.2, 0.1])
    weights = np.array([2, 2, 0, 3, 3, 1], dtype=float)
    ends = np.r_[np.flatnonzero(np.diff(scores)), len(scores) - 1]
    assert weighted_ap(y, weights, ends) == pytest.approx(
        average_precision_score(y, scores, sample_weight=weights)
    )


def test_cluster_bootstrap_is_reproducible_and_constant_lift_is_one() -> None:
    """All months of a resampled loan share multiplicity; constant AP equals prevalence."""
    frame = pd.DataFrame(
        {
            "loan_id": np.repeat([f"loan-{i}" for i in range(60)], 3),
            "label": np.repeat([0, 1] * 30, 3),
        }
    )
    scores = np.full(len(frame), 0.25)
    one = bootstrap_ap_lift(frame, scores, 100, 42)
    assert one == bootstrap_ap_lift(frame, scores, 100, 42)
    assert one["ap_lift_95pct_interval"] == pytest.approx([1.0, 1.0])
    assert one["invalid_replicates"] == 0


def test_monthly_capacity_recomputes_counts_and_uses_stable_loan_ties() -> None:
    """Two months each receive ceil(capacity*cohort); constant-score ties are deterministic."""
    frame = pd.DataFrame(
        {
            "loan_id": ["b", "a", "c", "a", "b"],
            "as_of": ["202001"] * 3 + ["202002"] * 2,
            "label": [0, 1, 0, 0, 1],
        }
    )
    report = capacity_metrics(frame, np.full(5, 0.1), 0.1)
    assert report["alerts"] == 2
    assert report["true_positive_alerts"] == 1
    assert report["recall"] == 0.5
    assert [row["alerts"] for row in report["monthly"]] == [1, 1]


@pytest.fixture
def admitted_files(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    """Declare synthetic reviewed artifacts and copy the exact frozen v1 configuration."""
    protocol = tmp_path / "protocol.json"
    protocol.write_bytes((ROOT / "config/research/freddie_experiment_v1.json").read_bytes())
    assert sha256(protocol) == APPROVED_PROTOCOL_SHA
    sources = {}
    for role, vintage in [("train", 2018), ("validation", 2019), ("frozen_test", 2020)]:
        path = tmp_path / f"{role}.zip"
        path.write_bytes(b"opaque synthetic bytes; not a readable loan ZIP" + str(vintage).encode())
        sources[role] = {
            "vintage": vintage,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    data: dict[str, Any] = {
        "schema_version": 1,
        "scope": SCOPE,
        "protocol_sha256": sha256(protocol),
        "owner_review": {
            "release_binding_confirmed": True,
            "internal_research_terms_acknowledged": True,
            "retrospective_limitations_acknowledged": True,
            "experiment_protocol_approved": True,
            "reviewed_at": "2026-10-09",
        },
        "release": {"number": 47, "date": "2026-07-29", "performance_cutoff": "2026-03-31"},
        "sources": sources,
        "structural_intake": {
            "train_passed": True,
            "validation_passed": True,
            "loan_id_overlap": 0,
        },
        "point_in_time_verified": False,
        "frozen_test_opened": False,
        "validation_outcomes_inspected": False,
        "source_admitted_for_training": True,
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(data))
    return manifest, protocol, data


def test_admission_rejects_unaccepted_terms_and_changed_protocol(
    admitted_files: tuple[Path, Path, dict[str, Any]],
) -> None:
    """Source reviews and the immutable v1 configuration are mandatory before fitting."""
    manifest, protocol, data = admitted_files
    data["owner_review"]["internal_research_terms_acknowledged"] = False
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        require_training_admission(manifest, protocol)
    data["owner_review"]["internal_research_terms_acknowledged"] = True
    manifest.write_text(json.dumps(data))
    protocol.write_text(protocol.read_text() + "\n")
    with pytest.raises(ValueError):
        require_training_admission(manifest, protocol)


def test_validation_lifecycle_permits_only_opening_under_approved_hash(
    admitted_files: tuple[Path, Path, dict[str, Any]],
) -> None:
    """Post-lock validation access is distinguishable from pre-lock contamination."""
    manifest, protocol, data = admitted_files
    data.update(
        validation_outcomes_inspected=True,
        validation_opened_under_protocol_sha256=sha256(protocol),
        validation_opened_at_local_date="2026-10-13",
    )
    manifest.write_text(json.dumps(data))
    assert not assess_admission(manifest, protocol)["blockers"]
    data["validation_opened_under_protocol_sha256"] = "changed"
    manifest.write_text(json.dumps(data))
    assert (
        "validation_inspected_before_protocol_lock"
        in assess_admission(manifest, protocol)["blockers"]
    )


def make_panel(directory: Path, vintage: int, digest: str, positives: int, total: int) -> Path:
    """Create a synthetic SQLite panel with legitimate horizon dates and numeric features."""
    directory.mkdir()
    path = directory / "panel.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE loan_month (
            loan_id TEXT, as_of TEXT, vintage INTEGER, upb REAL, loan_age REAL,
            remaining_months REAL, interest_rate REAL, prior_dq_1 REAL, prior_dq_2 REAL,
            label INTEGER, label_reason TEXT, label_observed_period TEXT, horizon_months INTEGER
            )""")
        month = "201901" if vintage == 2018 else "202001"
        year = month[:4]
        for index in range(total):
            positive = int(index < positives)
            db.execute(
                "INSERT INTO loan_month VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"{vintage}-{index}",
                    month,
                    vintage,
                    10000 + index,
                    None if index == 0 else 12,
                    348,
                    3 + positive * 3,
                    0,
                    0,
                    positive,
                    "synthetic_fixture",
                    year + ("03" if positive else "04"),
                    3,
                ),
            )
    (directory / "panel_report.json").write_text(
        json.dumps(
            {
                "source_sha256": digest,
                "label_version": LABEL_VERSION,
                "feature_whitelist": list(FEATURES),
            }
        )
    )
    return path


def test_real_worker_on_synthetic_panels_preserves_train_only_imputation_and_hold(
    admitted_files: tuple[Path, Path, dict[str, Any]], tmp_path: Path
) -> None:
    """End-to-end fixed candidates save/reload, while failed capacity prevents promotion."""
    manifest, protocol, data = admitted_files
    train_panel = make_panel(tmp_path / "train", 2018, data["sources"]["train"]["sha256"], 60, 240)
    validation_panel = make_panel(
        tmp_path / "validation", 2019, data["sources"]["validation"]["sha256"], 40, 160
    )
    with sqlite3.connect(validation_panel) as db:
        db.execute("UPDATE loan_month SET loan_age=1000")
    output = tmp_path / "output"
    output.mkdir()
    validation_worker(manifest, protocol, train_panel, validation_panel, output)
    report = json.loads((output / "validation_report.json").read_text())
    assert set(report["candidates"]) == {
        "constant",
        "logistic_regression",
        "hist_gradient_boosting",
    }
    assert report["scoring_release"] == "HOLD"
    assert report["frozen_test_opened"] is False
    assert report["validation_decision"] == "REJECT_VALIDATION"
    assert report["validation_gates"]["capacity_recall"] is False
    assert report["roundtrip_max_absolute_difference"] <= 1e-12
    pipeline = joblib.load(output / "candidate_pipeline.joblib")
    assert pipeline.named_steps["imputer"].statistics_[1] == 12
    assert sha256(output / "candidate_pipeline.joblib") == report["candidate_sha256"]


def test_future_negative_label_is_rejected_before_fit(
    admitted_files: tuple[Path, Path, dict[str, Any]], tmp_path: Path
) -> None:
    """A negative label outside its exact three-month maturity cannot enter train."""
    _, protocol, data = admitted_files
    panel = make_panel(tmp_path / "wrong", 2018, data["sources"]["train"]["sha256"], 1, 3)
    with sqlite3.connect(panel) as db:
        db.execute("UPDATE loan_month SET label_observed_period='201912' WHERE label=0")
    with pytest.raises(ValueError, match="Label timing"):
        load_window(panel, json.loads(protocol.read_text())["split"]["train"])


@pytest.mark.parametrize(
    "minutes,memory,reason", [(0.005, 2.0, "WALL_TIME_BUDGET"), (1.0, 0.000001, "RSS_BUDGET")]
)
def test_supervisor_stops_its_worker_when_budget_exceeded(
    tmp_path: Path, minutes: float, memory: float, reason: str
) -> None:
    """Timeout and resident-memory limits must abort an owned sleeping subprocess."""
    result = supervise(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        tmp_path,
        minutes,
        memory,
        dict(os.environ),
    )
    assert result["abort_reason"] == reason
    assert result["exit_code"] != 0
    assert result["elapsed_seconds"] < 5


def test_resource_monitor_failure_aborts_instead_of_running_unbounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable memory probe must stop the owned worker and retain a failure reason."""
    import subprocess

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("monitor unavailable")

    monkeypatch.setattr(subprocess, "run", denied)
    result = supervise(
        [sys.executable, "-c", "import time; time.sleep(10)"], tmp_path, 1.0, 2.0, dict(os.environ)
    )
    assert result["abort_reason"] == "RESOURCE_MONITOR_UNAVAILABLE"
    assert result["exit_code"] != 0


def test_origination_join_uses_documented_positions_and_preserves_missing(tmp_path: Path) -> None:
    """Sentinels remain missing; an unmapped cohort key cannot silently drop a row."""
    import zipfile

    from src.research.freddie_origination import enrich_origination

    spec = json.loads((ROOT / "config/research/freddie_experiment_v2.json").read_text())[
        "origination_features"
    ]
    row = [""] * 31
    row[0], row[8], row[9], row[11], row[19] = "9999", "90", "999", "80", "loan-1"
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("sample_orig_2018.txt", "|".join(row) + "\n")
    frame = pd.DataFrame({"loan_id": ["loan-1"], "as_of": ["201901"]})
    enriched = enrich_origination(frame, source, 2018, spec)
    assert pd.isna(enriched.loc[0, "credit_score"])
    assert pd.isna(enriched.loc[0, "orig_dti"])
    assert enriched.loc[0, "orig_ltv"] == 80
    assert enriched.loc[0, "orig_cltv"] == 90
    assert len(enriched) == len(frame)
    with pytest.raises(ValueError, match="missing"):
        enrich_origination(pd.DataFrame({"loan_id": ["other"]}), source, 2018, spec)
    with pytest.raises(ValueError, match="sealed"):
        enrich_origination(frame, source, 2020, spec)


def test_invalid_origination_score_is_not_zero_or_imputed(tmp_path: Path) -> None:
    """An out-of-range known score is a data failure, not a valid zero-valued feature."""
    import zipfile

    from src.research.freddie_origination import enrich_origination

    spec = json.loads((ROOT / "config/research/freddie_experiment_v2.json").read_text())[
        "origination_features"
    ]
    row = [""] * 31
    row[0], row[8], row[9], row[11], row[19] = "100", "90", "40", "80", "loan-1"
    source = tmp_path / "bad.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("sample_orig_2018.txt", "|".join(row) + "\n")
    with pytest.raises(ValueError, match="Invalid origination value"):
        enrich_origination(pd.DataFrame({"loan_id": ["loan-1"]}), source, 2018, spec)
