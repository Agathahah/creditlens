"""Recompute validation eligibility before considering frozen-test access; never load weights."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from src.research.freddie_metrics import validation_gates
from src.research.freddie_preflight import read_object, sha256


def assess_validation_candidate(run: Path, protocol: Path) -> dict[str, Any]:
    """Check report/artifact identity and recompute gates without trusting a PASS marker.

    This is a private research eligibility check, not a signature validator, model
    promotion, independent evaluation or serving authorization.

    Args:
        run: Private completed validation directory.
        protocol: Immutable protocol associated with that exact candidate.

    Returns:
        Eligibility for test consideration plus blockers; scoring remains HOLD.
    """
    blockers: list[str] = []
    try:
        report = read_object(run / "validation_report.json")
        config = read_object(protocol)
        if report.get("protocol_sha256") != sha256(protocol):
            blockers.append("protocol_identity_mismatch")
        if (
            report.get("scope") != config.get("scope")
            or report.get("model_evaluation") != "VALIDATION_ONLY"
        ):
            blockers.append("evaluation_scope_mismatch")
        if report.get("frozen_test_opened") is not False:
            blockers.append("test_already_opened")
        if report.get("candidate_sha256") != sha256(run / "candidate_pipeline.joblib"):
            blockers.append("candidate_checksum_mismatch")
        candidate = report["selected_candidate"]
        metrics = report["candidates"][candidate]
        uncertainty = report["uncertainty"]
        for key in ("ap", "prevalence", "brier", "constant_train_brier"):
            value = metrics[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                blockers.append("invalid_numeric_metrics")
        if metrics["prevalence"] <= 0 or metrics["constant_train_brier"] <= 0:
            blockers.append("invalid_metric_denominator")
        elif not math.isclose(
            metrics["ap_lift"], metrics["ap"] / metrics["prevalence"], rel_tol=1e-10
        ) or not math.isclose(
            metrics["brier_skill"],
            1 - metrics["brier"] / metrics["constant_train_brier"],
            rel_tol=1e-10,
            abs_tol=1e-12,
        ):
            blockers.append("derived_metric_mismatch")
        if (
            "calibration_constant_brier_skill_minimum_exclusive"
            in config["proposed_research_gates"]
        ):
            calibration = report["counts"]["calibration"]
            cal_pi = calibration["adverse_observations"] / calibration["labeled"]
            baseline = (
                metrics["prevalence"] * (1 - cal_pi) ** 2 + (1 - metrics["prevalence"]) * cal_pi**2
            )
            if (
                calibration["unique_adverse_loans"]
                < config["calibration"]["minimum_unique_adverse_loans"]
                or not report.get("support_checks", {}).get("calibration", False)
                or report.get("loan_identity_overlap") != 0
                or not math.isclose(metrics["calibration_constant_brier"], baseline, rel_tol=1e-10)
                or not math.isclose(
                    metrics["calibration_constant_brier_skill"],
                    1 - metrics["brier"] / baseline,
                    rel_tol=1e-10,
                    abs_tol=1e-12,
                )
            ):
                blockers.append("invalid_calibration_evidence")
        capacity = metrics["capacity"]
        alerts = capacity["alerts"]
        hits = capacity["true_positive_alerts"]
        events = metrics["adverse_observations"]
        labeled = metrics["labeled"]
        if any(type(value) is not int for value in (alerts, hits, events, labeled)) or not (
            0 < events <= labeled and 0 <= hits <= min(alerts, events) and alerts > 0
        ):
            blockers.append("invalid_policy_counts")
        elif (
            not math.isclose(metrics["prevalence"], events / labeled, rel_tol=1e-10)
            or not math.isclose(capacity["precision"], hits / alerts, rel_tol=1e-10)
            or not math.isclose(capacity["recall"], hits / events, rel_tol=1e-10)
            or not math.isclose(
                capacity["precision_lift"],
                capacity["precision"] / metrics["prevalence"],
                rel_tol=1e-10,
            )
        ):
            blockers.append("derived_policy_metric_mismatch")
        interval = uncertainty["ap_lift_95pct_interval"]
        if (
            len(interval) != 2
            or any(value is None or not math.isfinite(value) for value in interval)
            or interval[0] > interval[1]
        ):
            blockers.append("invalid_uncertainty")
        if not blockers:
            checks = validation_gates(
                metrics,
                uncertainty,
                report["counts"]["validation"]["unique_adverse_loans"],
                config["proposed_research_gates"],
            )
            if checks != report.get("validation_gates"):
                blockers.append("declared_gates_do_not_match_recomputed_gates")
            blockers.extend(
                "validation_failed_" + key for key, passed in checks.items() if not passed
            )
        if report.get("validation_decision") != "PASS_CANDIDATE":
            blockers.append("candidate_not_accepted_on_validation")
    except (OSError, ValueError, TypeError, KeyError, IndexError, ZeroDivisionError):
        blockers.append("missing_or_invalid_release_evidence")
    return {
        "eligible_for_test_consideration": not blockers,
        "blockers": blockers,
        "scoring_release": "HOLD",
        "independent_test_evaluation": "NOT_ASSESSED_BY_VALIDATION_CHECKER",
        "weights_deserialized": False,
        "limitations": [
            "Trusted operator evidence, not a cryptographic release attestation",
            "Independent test and service acceptance remain separate; no serving authorization",
        ],
    }


def main() -> None:
    """Print candidate eligibility and exit 2 when validation evidence blocks progress."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    report = assess_validation_candidate(args.run, args.protocol)
    print(json.dumps(report, indent=2))
    if not report["eligible_for_test_consideration"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
