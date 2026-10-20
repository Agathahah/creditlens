"""One-shot independent retrospective test; consume vintage before access and never fit."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from src.research.freddie_calibrated import PROTOCOL_SHA, validate_temporal_plan
from src.research.freddie_metrics import bootstrap_ap_lift, evaluate_predictions, validation_gates
from src.research.freddie_origination import _join_audited_origination
from src.research.freddie_panel import _build_monthly_panel
from src.research.freddie_preflight import read_object, sha256
from src.research.freddie_release import assess_validation_candidate
from src.research.freddie_train import (
    load_window,
    require_training_admission,
    supervise,
    write_private_json,
)

EXECUTION_SHA = "b79cd44176c05aac59159ee62cb6d5f19ae9dd936a716586797afdc280fc9726"


def authorize_test_access(
    run: Path, protocol: Path, execution: Path, manifest: Path
) -> dict[str, Any]:
    """Verify source, exact candidate and recomputed validation before any ZIP member access.

    Args:
        run: Trusted locally completed validation run.
        protocol: Exact locked v3 experiment.
        execution: Exact one-shot test execution contract.
        manifest: Unchanged admitted private source manifest.

    Returns:
        Verified execution contract with no weights or test contents deserialized.

    Raises:
        ValueError: Any hash, scope, temporal or validation prerequisite fails.
    """
    if sha256(protocol) != PROTOCOL_SHA or sha256(execution) != EXECUTION_SHA:
        raise ValueError("Locked experiment and independent-test contracts required")
    config, contract = read_object(protocol), read_object(execution)
    validate_temporal_plan(config)
    source = require_training_admission(manifest, protocol)
    report = read_object(run / "validation_report.json")
    if (
        contract["scope"] != "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY"
        or contract["fit_or_threshold_mutations_allowed"] is not False
        or contract["selection_and_calibration_locked"] is not True
        or contract["all_test_vintage_contents_consumed_on_first_access"] is not True
        or contract["experiment_protocol_sha256"] != sha256(protocol)
        or contract["validation_report_sha256"] != sha256(run / "validation_report.json")
        or contract["candidate_sha256"] != sha256(run / "candidate_pipeline.joblib")
        or contract["source_manifest_sha256"] != sha256(manifest)
        or contract["source_manifest_sha256"] != report["source_manifest_sha256"]
        or contract["test_source_sha256"] != source["sources"]["frozen_test"]["sha256"]
        or contract["test_window"] != config["split"]["frozen_test"]
        or contract["resource_budget"] != config["resource_budget"]
        or not assess_validation_candidate(run, protocol)["eligible_for_test_consideration"]
    ):
        raise ValueError("Independent-test prerequisite failed before source access")
    if (
        report["software"]["sklearn"] != sklearn.__version__
        or report["software"]["numpy"] != np.__version__
    ):
        raise ValueError("Test runtime differs from fitted candidate runtime")
    return contract


def record_consumption(marker: Path, contract: dict[str, Any]) -> None:
    """Create a non-overwritable private ledger before first test contents can be read.

    Args:
        marker: Global private source-vintage consumption marker.
        contract: Verified immutable test contract.
    """
    repository = Path(__file__).resolve().parents[2]
    if marker.resolve() == repository or repository in marker.resolve().parents:
        raise ValueError("Consumption evidence must remain outside Git")
    write_private_json(
        marker,
        {
            "test_vintage": 2020,
            "consumed": True,
            "opened_at": datetime.now(UTC).isoformat(),
            "execution_sha256": EXECUTION_SHA,
            "candidate_sha256": contract["candidate_sha256"],
            "test_source_sha256": contract["test_source_sha256"],
            "reason": (
                "First source access follows this ledger; "
                "retain consumption if intake/evaluation fails"
            ),
        },
    )


def score_without_fit(model: Any, features: pd.DataFrame) -> np.ndarray[Any, Any]:
    """Score raw ordered features using the already fitted base+calibration bundle.

    Args:
        model: Trusted hash-verified own candidate, never a remote model.
        features: Frozen test domain features in the locked order.

    Returns:
        Finite probabilities; no transform/model/calibration fit occurs.
    """
    scores = np.asarray(model.predict_proba(features)[:, 1], dtype=float)
    if (
        len(scores) != len(features)
        or not np.isfinite(scores).all()
        or ((scores < 0) | (scores > 1)).any()
    ):
        raise ValueError("Invalid locked-model test probabilities")
    return scores


def independent_worker(
    run: Path,
    protocol: Path,
    execution: Path,
    manifest: Path,
    output: Path,
    train_panel: Path,
    later_panel: Path,
) -> None:
    """Build/audit the consumed test panel and evaluate the fixed candidate once.

    Args:
        run: Completed accepted validation candidate path.
        protocol: Locked v3 experiment.
        execution: Locked one-shot execution.
        manifest: Private source manifest.
        output: Private test directory.
        train_panel: Earlier development panel for identity-overlap checks only.
        later_panel: Calibration/validation panel for identity-overlap checks only.
    """
    contract = authorize_test_access(run, protocol, execution, manifest)
    source, config = read_object(manifest), read_object(protocol)
    archive = Path(source["sources"]["frozen_test"]["path"])
    marker = archive.parent / "frozen_test_consumed_2020.json"
    if read_object(marker)["execution_sha256"] != EXECUTION_SHA:
        raise ValueError("One-shot consumption ledger required before test access")
    panel_report = _build_monthly_panel(archive, output / "panel", 2020)
    if panel_report["source_sha256"] != contract["test_source_sha256"]:
        raise ValueError("Test source changed during intake")
    frame, counts = load_window(output / "panel/panel.sqlite", config["split"]["frozen_test"])
    old_keys: set[str] = set()
    for panel in (train_panel, later_panel):
        with sqlite3.connect(panel.resolve().as_uri() + "?mode=ro", uri=True) as db:
            old_keys.update(row[0] for row in db.execute("SELECT DISTINCT loan_id FROM loan_month"))
    if set(frame["loan_id"]) & old_keys:
        raise ValueError("Independent test loan overlaps a development source")
    common = {
        "protocol_sha256": PROTOCOL_SHA,
        "execution_sha256": EXECUTION_SHA,
        "candidate_sha256": contract["candidate_sha256"],
        "test_source_sha256": contract["test_source_sha256"],
        "scope": contract["scope"],
        "model_evaluation": "INDEPENDENT_TEST_ONCE",
        "frozen_test_opened": True,
        "test_vintage_consumed": 2020,
        "scoring_release": "HOLD",
        "point_in_time_verified": False,
        "counts": counts,
        "loan_identity_overlap": 0,
        "software": {
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "code_sha256": sha256(Path(__file__)),
        },
        "limitations": [
            "Corrected historical mortgage test; not fintech or operational validation",
            "Complete-label cohort/censoring bias",
            "Fixed-model conditional cluster uncertainty",
        ],
    }
    gates = config["proposed_research_gates"]
    if (
        counts["unique_adverse_loans"] < gates["minimum_unique_adverse_loans"]["frozen_test"]
        or frame["label"].nunique() != 2
    ):
        write_private_json(
            output / "test_report.json",
            {**common, "test_decision": "REJECT_SUPPORT", "weights_deserialized": False},
        )
        return
    frame = _join_audited_origination(frame, archive, 2020, config["origination_features"])
    validation = read_object(run / "validation_report.json")
    # Loading own artifact is permitted only after identity/validation contracts are verified.
    candidate_path = run / "candidate_pipeline.joblib"
    if sha256(candidate_path) != contract["candidate_sha256"]:
        raise ValueError("Candidate changed before test inference")
    model = joblib.load(candidate_path)
    with threadpool_limits(limits=config["resource_budget"]["threads"]):
        scores = score_without_fit(model, frame[config["features"]])
        metrics = evaluate_predictions(
            frame,
            scores,
            validation["train_constant_prevalence"],
            config["alert_policy"]["fraction"],
        )
        cal_brier = float(
            np.mean(
                (validation["calibration_constant_prevalence"] - frame["label"].to_numpy()) ** 2
            )
        )
        metrics["calibration_constant_brier"] = cal_brier
        metrics["calibration_constant_brier_skill"] = 1 - metrics["brier"] / cal_brier
        uncertainty = bootstrap_ap_lift(
            frame, scores, gates["uncertainty"]["replicates"], config["resource_budget"]["seed"]
        )
    test_gates = dict(gates)
    test_gates["minimum_unique_adverse_loans"] = {
        "validation": gates["minimum_unique_adverse_loans"]["frozen_test"]
    }
    checks = validation_gates(metrics, uncertainty, counts["unique_adverse_loans"], test_gates)
    if (
        sha256(archive) != contract["test_source_sha256"]
        or sha256(candidate_path) != contract["candidate_sha256"]
    ):
        raise ValueError("Source or candidate changed during test")
    np.savez_compressed(
        output / "test_predictions.npz",
        loan_id=frame["loan_id"].to_numpy(dtype=str),
        as_of=frame["as_of"].to_numpy(dtype=str),
        label=frame["label"].to_numpy(dtype=int),
        probability=scores,
    )
    (output / "test_predictions.npz").chmod(0o600)
    write_private_json(
        output / "test_report.json",
        {
            **common,
            "selected_candidate": validation["selected_candidate"],
            "metrics": metrics,
            "uncertainty": uncertainty,
            "test_gates": checks,
            "weights_deserialized": True,
            "test_decision": "PASS_RESEARCH_TEST" if all(checks.values()) else "REJECT_TEST",
        },
    )


def main() -> None:
    """Supervise the one-shot test and keep scoring HOLD regardless of research quality."""
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("run", "protocol", "execution", "manifest", "output", "train-panel", "later-panel"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    contract = authorize_test_access(args.run, args.protocol, args.execution, args.manifest)
    if args.worker:
        independent_worker(
            args.run,
            args.protocol,
            args.execution,
            args.manifest,
            args.output,
            args.train_panel,
            args.later_panel,
        )
        return
    repo = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Test results must remain outside Git")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    source = read_object(args.manifest)
    archive = Path(source["sources"]["frozen_test"]["path"])
    record_consumption(archive.parent / "frozen_test_consumed_2020.json", contract)
    env = dict(os.environ)
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        env[key] = str(contract["resource_budget"]["threads"])
    result = supervise(
        [sys.executable, "-m", "src.research.freddie_independent_test", *sys.argv[1:], "--worker"],
        output,
        contract["resource_budget"]["max_elapsed_minutes"],
        contract["resource_budget"]["max_rss_gib"],
        env,
    )
    write_private_json(output / "resource_report.json", result)
    if result["exit_code"] != 0 or result["abort_reason"]:
        print(json.dumps({"test_decision": "FAILED_EXECUTION_TEST_CONSUMED", **result}))
        raise SystemExit(2)
    report = read_object(output / "test_report.json")
    print(
        json.dumps(
            {
                "test_decision": report["test_decision"],
                "scoring_release": "HOLD",
                "test_vintage_consumed": 2020,
                **result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
