"""Negative candidate gates never deserialize executable weights or imply scoring readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.research.freddie_metrics import validation_gates
from src.research.freddie_preflight import sha256
from src.research.freddie_release import assess_validation_candidate


@pytest.fixture
def candidate_evidence(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    """Create numeric synthetic evidence and opaque bytes that cannot be unpickled."""
    root = Path(__file__).resolve().parents[1]
    protocol = tmp_path / "protocol.json"
    protocol.write_bytes((root / "config/research/freddie_experiment_v2.json").read_bytes())
    weights = tmp_path / "candidate_pipeline.joblib"
    weights.write_bytes(b"opaque synthetic bytes; never load as weights")
    metrics = {
        "ap": 0.03,
        "prevalence": 0.01,
        "ap_lift": 3.0,
        "brier": 0.008,
        "constant_train_brier": 0.01,
        "brier_skill": 0.2,
        "labeled": 100000,
        "adverse_observations": 1000,
        "capacity": {
            "alerts": 1000,
            "true_positive_alerts": 250,
            "precision": 0.25,
            "recall": 0.25,
            "precision_lift": 25.0,
        },
    }
    uncertainty = {"ap_lift_95pct_interval": [2.0, 4.0], "invalid_replicates": 0}
    report: dict[str, Any] = {
        "protocol_sha256": sha256(protocol),
        "scope": "freddie_mortgage_retrospective_research",
        "model_evaluation": "VALIDATION_ONLY",
        "frozen_test_opened": False,
        "candidate_sha256": sha256(weights),
        "selected_candidate": "logistic_regression",
        "candidates": {"logistic_regression": metrics},
        "counts": {"validation": {"unique_adverse_loans": 50}},
        "uncertainty": uncertainty,
        "validation_decision": "PASS_CANDIDATE",
    }
    report["validation_gates"] = validation_gates(
        metrics, uncertainty, 50, json.loads(protocol.read_text())["proposed_research_gates"]
    )
    (tmp_path / "validation_report.json").write_text(json.dumps(report))
    return tmp_path, protocol, report


def test_complete_validation_is_only_eligible_for_test_not_serving(
    candidate_evidence: tuple[Path, Path, dict[str, Any]],
) -> None:
    """Even complete synthetic evidence cannot serve a model or claim independent evaluation."""
    directory, protocol, _ = candidate_evidence
    result = assess_validation_candidate(directory, protocol)
    assert result["eligible_for_test_consideration"] is True
    assert result["scoring_release"] == "HOLD"
    assert result["weights_deserialized"] is False
    assert result["independent_test_evaluation"] == "NOT_ASSESSED_BY_VALIDATION_CHECKER"


def test_false_pass_does_not_override_failed_capacity(
    candidate_evidence: tuple[Path, Path, dict[str, Any]],
) -> None:
    """A manually true PASS marker must not replace recomputation of actual metrics."""
    directory, protocol, report = candidate_evidence
    policy = report["candidates"]["logistic_regression"]["capacity"]
    policy.update(true_positive_alerts=40, precision=0.04, recall=0.04, precision_lift=4.0)
    (directory / "validation_report.json").write_text(json.dumps(report))
    result = assess_validation_candidate(directory, protocol)
    assert result["eligible_for_test_consideration"] is False
    assert "validation_failed_capacity_recall" in result["blockers"]
    assert "declared_gates_do_not_match_recomputed_gates" in result["blockers"]


@pytest.mark.parametrize(
    "change,reason",
    [
        ("candidate", "candidate_checksum_mismatch"),
        ("protocol", "protocol_identity_mismatch"),
        ("evidence", "missing_or_invalid_release_evidence"),
    ],
)
def test_missing_or_changed_identity_blocks_progress(
    candidate_evidence: tuple[Path, Path, dict[str, Any]], change: str, reason: str
) -> None:
    """A different candidate/protocol or absent report cannot reuse a validation decision."""
    directory, protocol, _ = candidate_evidence
    if change == "candidate":
        (directory / "candidate_pipeline.joblib").write_bytes(b"changed")
    elif change == "protocol":
        protocol.write_text(protocol.read_text() + "\n")
    else:
        (directory / "validation_report.json").unlink()
    result = assess_validation_candidate(directory, protocol)
    assert reason in result["blockers"]
    assert result["eligible_for_test_consideration"] is False


@pytest.mark.parametrize("change", ["none", "skill", "support", "overlap"])
def test_v3_calibration_evidence_is_recomputed_before_test_consideration(
    candidate_evidence: tuple[Path, Path, dict[str, Any]], change: str
) -> None:
    """Calibration skill/support/identity cannot be replaced by a fabricated PASS flag."""
    directory, protocol, report = candidate_evidence
    root = Path(__file__).resolve().parents[1]
    protocol.write_bytes((root / "config/research/freddie_experiment_v3.json").read_bytes())
    report["protocol_sha256"] = sha256(protocol)
    metrics = report["candidates"]["logistic_regression"]
    baseline = 0.01 * 0.99**2 + 0.99 * 0.01**2
    metrics.update(
        calibration_constant_brier=baseline, calibration_constant_brier_skill=1 - 0.008 / baseline
    )
    report["counts"]["calibration"] = {
        "adverse_observations": 100,
        "labeled": 10000,
        "unique_adverse_loans": 60,
    }
    report["support_checks"] = {"calibration": True}
    report["loan_identity_overlap"] = 0
    report["validation_gates"] = validation_gates(
        metrics,
        report["uncertainty"],
        50,
        json.loads(protocol.read_text())["proposed_research_gates"],
    )
    if change == "skill":
        metrics["calibration_constant_brier_skill"] = 0.2
    elif change == "support":
        report["counts"]["calibration"]["unique_adverse_loans"] = 10
    elif change == "overlap":
        report["loan_identity_overlap"] = 1
    (directory / "validation_report.json").write_text(json.dumps(report))
    result = assess_validation_candidate(directory, protocol)
    assert result["eligible_for_test_consideration"] is (change == "none")
    if change != "none":
        assert "invalid_calibration_evidence" in result["blockers"]
    assert result["weights_deserialized"] is False
    assert result["scoring_release"] == "HOLD"
