"""Temporal, identity and frozen-preprocessing contracts for calibrated mortgage research."""

from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pytest

from src.research.freddie_calibrated import (
    PROTOCOL_SHA,
    fit_sigmoid,
    make_base,
    validate_temporal_plan,
)
from src.research.freddie_metrics import validation_gates
from src.research.freddie_preflight import sha256
from src.research.freddie_train import load_window
from tests.test_freddie_train import make_panel

ROOT = Path(__file__).resolve().parents[1]


def protocol() -> dict[str, Any]:
    """Read the exact locked configuration without touching any private data."""
    path = ROOT / "config/research/freddie_experiment_v3.json"
    assert sha256(path) == PROTOCOL_SHA
    return json.loads(path.read_text())


def test_v3_keeps_primary_quality_gates_and_budget() -> None:
    """New calibration must not lower the prior fixed recall, AP or resource criteria."""
    previous = json.loads((ROOT / "config/research/freddie_experiment_v2.json").read_text())
    current = protocol()
    validate_temporal_plan(current)
    assert current["resource_budget"] == previous["resource_budget"]
    for key, value in previous["proposed_research_gates"].items():
        assert current["proposed_research_gates"][key] == value
    assert current["features"] == previous["features"]


@pytest.mark.parametrize("bad_role", ["calibration", "validation", "frozen_test"])
def test_label_maturity_must_precede_next_role(bad_role: str) -> None:
    """Even disjoint loan identities cannot excuse future labels crossing a temporal role."""
    config = protocol()
    roles = ["train", "calibration", "validation", "frozen_test"]
    previous = roles[roles.index(bad_role) - 1]
    config["split"][bad_role]["as_of_start"] = config["split"][previous]["last_outcome"]
    with pytest.raises(ValueError, match="maturity"):
        validate_temporal_plan(config)


def test_same_partition_is_not_independent_calibration_validation() -> None:
    """Changing only the date must not allow the same loan family in two roles."""
    config = protocol()
    config["split"]["validation"]["loan_partition"]["bucket"] = 0
    with pytest.raises(ValueError, match="partitions"):
        validate_temporal_plan(config)


def test_partition_preserves_months_and_reconciles_censoring(tmp_path: Path) -> None:
    """Loan hash buckets are complementary and censoring remains explicit after filtering."""
    panel = make_panel(tmp_path / "panel", 2019, "fixture", 80, 200)
    with sqlite3.connect(panel) as db:
        db.execute(
            "UPDATE loan_month SET label=NULL,label_observed_period=NULL WHERE loan_id='2019-199'"
        )
    split = {
        "vintage": 2019,
        "as_of_start": "202001",
        "as_of_end": "202001",
        "last_outcome": "202004",
    }
    full, summary = load_window(panel, split)
    cohorts, counts = [], []
    for bucket in (0, 1):
        selected, count = load_window(
            panel,
            {
                **split,
                "loan_partition": {
                    "method": "sha256_mod_2",
                    "salt": "fixed-before-labels",
                    "bucket": bucket,
                },
            },
        )
        cohorts.append(set(selected["loan_id"]))
        counts.append(count)
        assert count["eligible_observations"] == count["labeled"] + count["censored"]
    assert not cohorts[0] & cohorts[1]
    assert cohorts[0] | cohorts[1] == set(full["loan_id"])
    assert sum(c["censored"] for c in counts) == summary["censored"] == 1
    assert sum(c["eligible_observations"] for c in counts) == 200


def test_sigmoid_does_not_refit_base_preprocessing_or_coefficients(tmp_path: Path) -> None:
    """Large calibration-distribution changes cannot mutate train-fitted median/scaler/model."""
    config = protocol()
    rng = np.random.default_rng(42)
    x = pd.DataFrame(rng.normal(size=(300, len(config["features"]))), columns=config["features"])
    x.iloc[0, 0] = np.nan
    y = pd.Series((x.iloc[:, 1] > 0.5).astype(int))
    base = make_base("logistic_regression", config)
    base.fit(x, y)
    medians = base.named_steps["imputer"].statistics_.copy()
    coefficients = base.named_steps["model"].coef_.copy()
    scaler = base.named_steps["scaler"].mean_.copy()
    cal_x = x.copy() + 100
    model = fit_sigmoid(base, cal_x, y)
    np.testing.assert_array_equal(base.named_steps["imputer"].statistics_, medians)
    np.testing.assert_array_equal(base.named_steps["model"].coef_, coefficients)
    np.testing.assert_array_equal(base.named_steps["scaler"].mean_, scaler)
    scores = model.predict_proba(x)[:, 1]
    assert np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()
    path = tmp_path / "own-calibrated.joblib"
    joblib.dump(model, path)
    np.testing.assert_allclose(joblib.load(path).predict_proba(x)[:, 1], scores, rtol=0, atol=1e-12)
    with pytest.raises(ValueError, match="both classes"):
        fit_sigmoid(base, cal_x, pd.Series(np.zeros(len(y))))


def test_calibration_baseline_is_additional_not_replacement_gate() -> None:
    """A positive skill against train alone cannot hide failure against the later constant."""
    gates = protocol()["proposed_research_gates"]
    metrics = {
        "ap_lift": 3.0,
        "brier_skill": 0.01,
        "calibration_constant_brier_skill": -0.02,
        "capacity": {"recall": 0.25, "precision_lift": 10.0, "alerts": 100},
    }
    checks = validation_gates(
        metrics, {"invalid_replicates": 0, "ap_lift_95pct_interval": [2.0, 4.0]}, 50, gates
    )
    assert checks["brier_skill"] is True
    assert checks["calibration_constant_brier_skill"] is False
    assert not all(checks.values())
    clone = copy.deepcopy(metrics)
    clone["calibration_constant_brier_skill"] = 0.01
    assert all(
        validation_gates(
            clone, {"invalid_replicates": 0, "ap_lift_95pct_interval": [2.0, 4.0]}, 50, gates
        ).values()
    )


def test_synthetic_v3_worker_keeps_test_opaque_and_calibration_disjoint(tmp_path: Path) -> None:
    """Exercise the saved calibrated candidate with synthetic admitted origination/panels."""
    import zipfile

    from src.research.freddie_calibrated import calibrated_worker
    from tests.test_freddie_train import admitted_files

    manifest, config_path, admission = admitted_files.__wrapped__(tmp_path)
    config_path.write_bytes((ROOT / "config/research/freddie_experiment_v3.json").read_bytes())
    admission["protocol_sha256"] = sha256(config_path)
    for role, vintage, total in (("train", 2018, 240), ("validation", 2019, 1000)):
        archive = Path(admission["sources"][role]["path"])
        rows = []
        for i in range(total):
            row = [""] * 31
            row[0], row[8], row[9], row[11], row[19] = "700", "80", "30", "70", f"{vintage}-{i}"
            rows.append("|".join(row))
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr(f"sample_orig_{vintage}.txt", "\n".join(rows) + "\n")
        admission["sources"][role].update(bytes=archive.stat().st_size, sha256=sha256(archive))
    manifest.write_text(json.dumps(admission))
    train = make_panel(tmp_path / "train", 2018, admission["sources"]["train"]["sha256"], 60, 240)
    later = make_panel(
        tmp_path / "later", 2019, admission["sources"]["validation"]["sha256"], 250, 1000
    )
    with sqlite3.connect(later) as db:
        db.execute(
            "UPDATE loan_month SET as_of='202101', "
            "label_observed_period=CASE WHEN label=1 THEN '202103' ELSE '202104' END"
        )
        db.execute(
            "INSERT INTO loan_month SELECT loan_id,'202204',vintage,upb,loan_age,remaining_months,"
            "interest_rate,prior_dq_1,prior_dq_2,label,label_reason,"
            "CASE WHEN label=1 THEN '202206' ELSE '202207' END,horizon_months FROM loan_month"
        )
    output = tmp_path / "result"
    output.mkdir()
    calibrated_worker(manifest, config_path, train, later, output)
    result = json.loads((output / "validation_report.json").read_text())
    assert result["model_evaluation"] == "VALIDATION_ONLY"
    assert result["loan_identity_overlap"] == 0
    assert result["frozen_test_opened"] is False
    assert result["validation_decision"] == "REJECT_VALIDATION"
    assert result["support_checks"]["calibration"] is True
    assert result["roundtrip_max_absolute_difference"] <= 1e-12
