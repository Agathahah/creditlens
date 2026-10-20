"""One-shot v4 mortgage test using the locked model, history reader and consumed-vintage ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from src.research.freddie_history_train import (
    MODULES,
    PROTOCOL_SHA,
    _collect_archive,
    require_admission,
)
from src.research.freddie_independent_test import score_without_fit
from src.research.freddie_metrics import bootstrap_ap_lift, evaluate_predictions, validation_gates
from src.research.freddie_preflight import read_object, sha256
from src.research.freddie_release import assess_validation_candidate
from src.research.freddie_train import supervise, write_private_json

# Replaced by the hash of a concrete candidate-bound contract only after validation acceptance.
EXECUTION_SHA = "2d75ed29d0b955c1e6642d800b28d879051886c84b32b41e6f3ecc888f480899"


def execution_code_hash() -> str:
    """Hash executor code with its contract-hash literal normalized to avoid a hash cycle.

    Returns:
        SHA256 binding all executor logic, excluding only the literal contract hash.
    """
    code = Path(__file__).read_text()
    normalized, count = re.subn(
        r'^EXECUTION_SHA = "[^"]+"$',
        'EXECUTION_SHA = "NORMALIZED_CONTRACT_HASH"',
        code,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError("Ambiguous executor contract-hash declaration")
    return hashlib.sha256(normalized.encode()).hexdigest()


def authorize_access(run: Path, protocol: Path, execution: Path, manifest: Path) -> dict[str, Any]:
    """Recompute validation and verify identities/runtime before loading weights or test records.

    Args:
        run: Completed private development run.
        protocol: Locked v4 experiment.
        execution: Candidate-bound immutable one-shot test contract.
        manifest: Admitted source receipt with unconsumed test.

    Returns:
        Verified execution contract, with no test member opened.

    Raises:
        ValueError: Changed/unaccepted candidate, schema, source, code, runtime or protocol.
    """
    if sha256(protocol) != PROTOCOL_SHA or sha256(execution) != EXECUTION_SHA:
        raise ValueError("Locked v4 and candidate-bound independent contracts required")
    source = require_admission(manifest, protocol)
    contract, config = read_object(execution), read_object(protocol)
    report = read_object(run / "validation_report.json")
    if (
        contract["scope"] != "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY"
        or contract["normalized_executor_sha256"] != execution_code_hash()
        or contract["fit_or_threshold_mutations_allowed"] is not False
        or contract["all_test_vintage_contents_consumed_on_first_access"] is not True
        or contract["public_scoring_authorized"] is not False
        or contract["experiment_protocol_sha256"] != PROTOCOL_SHA
        or contract["validation_report_sha256"] != sha256(run / "validation_report.json")
        or contract["candidate_sha256"] != sha256(run / "candidate_pipeline.joblib")
        or contract["candidate_sha256"] != report["candidate_sha256"]
        or contract["development_identity_sha256"] != sha256(run / "development_loan_ids.txt")
        or contract["source_manifest_sha256"] != sha256(manifest)
        or contract["source_manifest_sha256"] != report["source_manifest_sha256"]
        or contract["test_source_sha256"] != source["sources"]["frozen_test"]["sha256"]
        or contract["test_window"] != config["split"]["frozen_test"]
        or contract["resource_budget"] != config["resource_budget"]
        or contract["features"] != config["features"]
        or contract["feature_dtype"] != config["feature_dtype"]
        or report["software"]["features"] != config["features"]
        or report["software"]["feature_dtype"] != "float32"
        or not assess_validation_candidate(run, protocol)["eligible_for_test_consideration"]
    ):
        raise ValueError("Independent-test prerequisite failed before source access")
    if (
        report["software"]["sklearn"] != sklearn.__version__
        or report["software"]["numpy"] != np.__version__
    ):
        raise ValueError("Candidate runtime version differs")
    selected = max(
        ("logistic_regression", "hist_gradient_boosting"),
        key=lambda name: report["candidates"][name]["ap"],
    )
    if report["selected_candidate"] != selected:
        raise ValueError("Selected candidate does not follow locked validation policy")
    for name, digest in report["software"]["module_sha256"].items():
        if sha256(Path(__file__).with_name(name + ".py")) != digest:
            raise ValueError("Development feature/metric code changed before test")
    for name, digest in contract["test_module_sha256"].items():
        if sha256(Path(__file__).with_name(name + ".py")) != digest:
            raise ValueError("Independent feature/metric code changed before test")
    return contract


def consume_test(marker: Path, contract: dict[str, Any]) -> None:
    """Record vintage2022 consumed before first member access; never overwrite on retries.

    Args:
        marker: Global private vintage consumption path.
        contract: Verified candidate-bound execution.
    """
    repo = Path(__file__).resolve().parents[2]
    if marker.resolve() == repo or repo in marker.resolve().parents:
        raise ValueError("Consumption ledger must remain private")
    write_private_json(
        marker,
        {
            "test_vintage": 2022,
            "consumed": True,
            "opened_at": datetime.now(UTC).isoformat(),
            "execution_sha256": EXECUTION_SHA,
            "candidate_sha256": contract["candidate_sha256"],
            "test_source_sha256": contract["test_source_sha256"],
            "reason": (
                "Source access occurs after this ledger; " "retain consumption on rejection/abort"
            ),
        },
    )


def independent_worker(
    run: Path, protocol: Path, execution: Path, manifest: Path, output: Path
) -> None:
    """Predict on newly consumed test once, without model/preprocessing/calibrator fitting.

    Args:
        run: Accepted development candidate.
        protocol: Locked v4 protocol.
        execution: Locked independent-test contract.
        manifest: Unmodified source admission.
        output: Private new directory with resource supervision.
    """
    contract = authorize_access(run, protocol, execution, manifest)
    source, config = read_object(manifest), read_object(protocol)
    archive = Path(source["sources"]["frozen_test"]["path"])
    ledger = read_object(archive.parent / "frozen_test_consumed_2022.json")
    if ledger["execution_sha256"] != EXECUTION_SHA or ledger["consumed"] is not True:
        raise ValueError("Consumption ledger required before test access")
    cohort = _collect_archive(
        archive, 2022, {"frozen_test": config["split"]["frozen_test"]}, config
    )["frozen_test"]
    # Read development identity sets stored at candidate lock, never source2020 records.
    old_keys = set((run / "development_loan_ids.txt").read_text().splitlines())
    if set(cohort.frame["loan_id"]) & old_keys:
        raise ValueError("Independent loan identity overlaps development")
    validation = read_object(run / "validation_report.json")
    counts, gates = cohort.counts, config["proposed_research_gates"]
    common = {
        "protocol_sha256": PROTOCOL_SHA,
        "execution_sha256": EXECUTION_SHA,
        "candidate_sha256": contract["candidate_sha256"],
        "test_source_sha256": contract["test_source_sha256"],
        "scope": contract["scope"],
        "model_evaluation": "INDEPENDENT_TEST_ONCE",
        "frozen_test_opened": True,
        "test_vintage_consumed": 2022,
        "counts": counts,
        "loan_identity_overlap": 0,
        "point_in_time_verified": False,
        "scoring_release": "HOLD",
        "limitations": [
            "Corrected retrospective mortgage study, not operational/fintech validation",
            "Complete-label selection/censoring; fixed-model loan-cluster uncertainty",
        ],
    }
    if (
        counts["unique_adverse_loans"] < gates["minimum_unique_adverse_loans"]["frozen_test"]
        or cohort.frame["label"].nunique() != 2
    ):
        write_private_json(
            output / "test_report.json",
            {**common, "test_decision": "REJECT_SUPPORT", "weights_deserialized": False},
        )
        return
    if sha256(run / "candidate_pipeline.joblib") != contract["candidate_sha256"]:
        raise ValueError("Candidate changed before deserialization")
    model = joblib.load(run / "candidate_pipeline.joblib")  # Own hash-verified candidate only.
    with threadpool_limits(limits=2):
        scores = score_without_fit(model, cohort.features)
        metrics = evaluate_predictions(
            cohort.frame,
            scores,
            validation["train_constant_prevalence"],
            config["alert_policy"]["fraction"],
        )
        baseline = float(
            np.mean(
                (validation["calibration_constant_prevalence"] - cohort.frame["label"].to_numpy())
                ** 2
            )
        )
        metrics["calibration_constant_brier"] = baseline
        metrics["calibration_constant_brier_skill"] = 1 - metrics["brier"] / baseline
        uncertainty = bootstrap_ap_lift(cohort.frame, scores, 1000, 42)
    test_gates = dict(gates)
    test_gates["minimum_unique_adverse_loans"] = {
        "validation": gates["minimum_unique_adverse_loans"]["frozen_test"]
    }
    checks = validation_gates(metrics, uncertainty, counts["unique_adverse_loans"], test_gates)
    if (
        sha256(archive) != contract["test_source_sha256"]
        or sha256(run / "candidate_pipeline.joblib") != contract["candidate_sha256"]
    ):
        raise ValueError("Candidate or source changed during test")
    np.savez_compressed(
        output / "test_predictions.npz",
        loan_id=cohort.frame["loan_id"].to_numpy(dtype=str),
        as_of=cohort.frame["as_of"].to_numpy(dtype=str),
        label=cohort.frame["label"].to_numpy(),
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
    """Supervise one independent attempt; no scoring promotion follows a research result."""
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("run", "protocol", "execution", "manifest", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents:
        raise ValueError("Private test outputs must remain outside Git")
    contract = authorize_access(args.run, args.protocol, args.execution, args.manifest)
    if args.worker:
        independent_worker(args.run, args.protocol, args.execution, args.manifest, output)
        return
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    source = read_object(args.manifest)
    archive = Path(source["sources"]["frozen_test"]["path"])
    consume_test(archive.parent / "frozen_test_consumed_2022.json", contract)
    snapshot = output / "code_snapshot"
    snapshot.mkdir(mode=0o700)
    for name in (*MODULES, "freddie_history_test", "freddie_release", "freddie_independent_test"):
        path = snapshot / (name + ".py")
        path.write_bytes(Path(__file__).with_name(name + ".py").read_bytes())
        path.chmod(0o600)
    write_private_json(output / "source_manifest_at_test_start.json", source)
    env = dict(os.environ)
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        env[key] = "2"
    result = supervise(
        [sys.executable, "-m", "src.research.freddie_history_test", *sys.argv[1:], "--worker"],
        output,
        15,
        2,
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
                "test_vintage_consumed": 2022,
                "scoring_release": "HOLD",
                **result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
