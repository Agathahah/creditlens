"""Bounded temporal mortgage development with disjoint sigmoid calibration; no test access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from src.research.freddie_metrics import bootstrap_ap_lift, evaluate_predictions, validation_gates
from src.research.freddie_origination import enrich_origination
from src.research.freddie_panel import FEATURES, LABEL_VERSION, month_index
from src.research.freddie_preflight import read_object, sha256
from src.research.freddie_train import (
    load_window,
    require_training_admission,
    supervise,
    write_private_json,
)

PROTOCOL_SHA = "f4eef57a25e638f9a4c694a16f3d93d2bd8ee8f50440d5c9758cbd440eee0411"


def validate_temporal_plan(config: dict[str, Any]) -> None:
    """Reject overlapping label maturity and calibration/validation loan partitions.

    Args:
        config: Immutable v3 configuration or a synthetic negative contract fixture.

    Raises:
        ValueError: A period, horizon, vintage or disjoint-partition contract is invalid.
    """
    previous = -1
    splits = config["split"]
    for role in ("train", "calibration", "validation", "frozen_test"):
        split = splits[role]
        start, end, outcome = (
            month_index(split[key]) for key in ("as_of_start", "as_of_end", "last_outcome")
        )
        if not previous < start <= end or outcome != end + 3:
            raise ValueError("Label maturity overlaps the next temporal role")
        previous = outcome
    calibration, validation = splits["calibration"], splits["validation"]
    one, two = calibration.get("loan_partition", {}), validation.get("loan_partition", {})
    if (
        calibration["vintage"] != 2019
        or validation["vintage"] != 2019
        or splits["train"]["vintage"] != 2018
        or splits["frozen_test"]["vintage"] != 2020
        or one.get("method") != "sha256_mod_2"
        or two.get("method") != "sha256_mod_2"
        or not one.get("salt")
        or one.get("salt") != two.get("salt")
        or one.get("bucket") != 0
        or two.get("bucket") != 1
    ):
        raise ValueError("Calibration and validation need complementary fixed loan partitions")


def fit_sigmoid(base: Pipeline, features: pd.DataFrame, labels: pd.Series) -> Any:
    """Fit only a sigmoid mapping while the train-fitted preprocessing/model stays frozen.

    Args:
        base: Already fitted trusted train pipeline.
        features: Distinct later calibration cohort using domain feature columns.
        labels: Both calibration classes; never validation or test labels.

    Returns:
        Fitted calibrated classifier, retaining the frozen base estimator.
    """
    if labels.nunique() != 2:
        raise ValueError("Calibration needs both classes")
    calibrated = CalibratedClassifierCV(
        FrozenEstimator(base), method="sigmoid", ensemble=False, n_jobs=1
    )
    calibrated.fit(features, labels)
    return calibrated


def make_base(name: str, config: dict[str, Any]) -> Pipeline:
    """Construct one fixed baseline candidate without any hyperparameter search.

    Args:
        name: Logistic or histogram candidate name.
        config: Locked model parameters and seed.

    Returns:
        Unfitted train-only preprocessing/model pipeline.
    """
    steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True))
    ]
    if name == "logistic_regression":
        steps.extend(
            [
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(**config["candidates"][name], random_state=42)),
            ]
        )
    elif name == "hist_gradient_boosting":
        steps.append(
            (
                "model",
                HistGradientBoostingClassifier(
                    **config["candidates"][name], early_stopping=False, random_state=42
                ),
            )
        )
    else:
        raise ValueError("Unsupported candidate")
    return Pipeline(steps)


def calibrated_worker(
    manifest: Path, protocol: Path, train_panel: Path, later_panel: Path, output: Path
) -> None:
    """Run v3 once on admitted development panels and quarantine its candidate.

    Args:
        manifest: Private accepted source/protocol record.
        protocol: Exact v3 locked bytes.
        train_panel: Development vintage 2018 SQLite.
        later_panel: Vintage 2019 SQLite for hash-disjoint calibration/validation.
        output: Private new output directory owned by the caller.
    """
    if sha256(protocol) != PROTOCOL_SHA:
        raise ValueError("Only the locked v3 development protocol is supported")
    source = require_training_admission(manifest, protocol)
    config = read_object(protocol)
    validate_temporal_plan(config)
    for role, panel in (("train", train_panel), ("validation", later_panel)):
        provenance = read_object(panel.parent / "panel_report.json")
        if (
            provenance["source_sha256"] != source["sources"][role]["sha256"]
            or provenance["label_version"] != LABEL_VERSION
            or provenance["feature_whitelist"] != list(FEATURES)
        ):
            raise ValueError("Panel does not match admitted source")
    frames, counts = {}, {}
    for role, panel in (
        ("train", train_panel),
        ("calibration", later_panel),
        ("validation", later_panel),
    ):
        frames[role], counts[role] = load_window(panel, config["split"][role])
    keys = {role: set(frame["loan_id"]) for role, frame in frames.items()}
    if any(
        keys[a] & keys[b]
        for a, b in (
            ("train", "calibration"),
            ("train", "validation"),
            ("calibration", "validation"),
        )
    ):
        raise ValueError("Loan identity overlaps development roles")
    common = {
        "protocol_sha256": sha256(protocol),
        "scope": config["scope"],
        "label_version": LABEL_VERSION,
        "source_manifest_sha256": sha256(manifest),
        "source_hashes": {role: item["sha256"] for role, item in source["sources"].items()},
        "counts": counts,
        "frozen_test_opened": False,
        "scoring_release": "HOLD",
        "point_in_time_verified": False,
        "created_at": datetime.now(UTC).isoformat(),
        "loan_identity_overlap": 0,
        "cohort_loan_sha256": {
            role: hashlib.sha256("\n".join(sorted(items)).encode()).hexdigest()
            for role, items in keys.items()
        },
        "software": {
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "code_sha256": sha256(Path(__file__)),
            "features": config["features"],
            "module_sha256": {
                name: sha256(Path(__file__).with_name(name + ".py"))
                for name in (
                    "freddie_train",
                    "freddie_metrics",
                    "freddie_origination",
                    "freddie_preflight",
                )
            },
        },
        "limitations": [
            "Corrected retrospective snapshot; no operational point-in-time proof",
            "Complete-label selection/censoring bias",
            "Development validation is not final independent test",
            "Conditional cluster CI excludes calibration-fit and common-calendar uncertainty",
        ],
    }
    gates = config["proposed_research_gates"]
    minima = {
        "train": gates["minimum_unique_adverse_loans"]["train"],
        "calibration": config["calibration"]["minimum_unique_adverse_loans"],
        "validation": gates["minimum_unique_adverse_loans"]["validation"],
    }
    support = {
        role: counts[role]["unique_adverse_loans"] >= minimum
        and frames[role]["label"].nunique() == 2
        for role, minimum in minima.items()
    }
    if not all(support.values()):
        write_private_json(
            output / "validation_report.json",
            {
                **common,
                "support_checks": support,
                "validation_decision": "REJECT_SUPPORT",
                "model_evaluation": "NOT_FIT_SUPPORT_FAILURE",
            },
        )
        return
    for role in frames:
        archive_role = "train" if role == "train" else "validation"
        frames[role] = enrich_origination(
            frames[role],
            Path(source["sources"][archive_role]["path"]),
            config["split"][role]["vintage"],
            config["origination_features"],
        )
    feature_names = config["features"]
    train, calibration, validation = (
        frames[role] for role in ("train", "calibration", "validation")
    )
    x_train, x_calibration, x_validation = (
        frame[feature_names] for frame in (train, calibration, validation)
    )
    pi, cal_pi = float(train["label"].mean()), float(calibration["label"].mean())
    baseline_cal_brier = float(np.mean((cal_pi - validation["label"].to_numpy()) ** 2))
    fraction = config["alert_policy"]["fraction"]
    metrics = {
        "constant": evaluate_predictions(validation, np.full(len(validation), pi), pi, fraction)
    }
    diagnostics = {
        "calibration_constant": evaluate_predictions(
            validation, np.full(len(validation), cal_pi), pi, fraction
        )
    }
    models, probabilities = {}, {}
    with threadpool_limits(limits=config["resource_budget"]["threads"]):
        for name in ("logistic_regression", "hist_gradient_boosting"):
            base = make_base(name, config)
            base.fit(x_train, train["label"].astype(int))
            raw = base.predict_proba(x_validation)[:, 1]
            diagnostics[name + "_uncalibrated"] = evaluate_predictions(
                validation, raw, pi, fraction
            )
            model = fit_sigmoid(base, x_calibration, calibration["label"].astype(int))
            scores = model.predict_proba(x_validation)[:, 1]
            models[name], probabilities[name] = model, scores
            metrics[name] = evaluate_predictions(validation, scores, pi, fraction)
            metrics[name]["calibration_constant_brier"] = baseline_cal_brier
            metrics[name]["calibration_constant_brier_skill"] = (
                1 - metrics[name]["brier"] / baseline_cal_brier
            )
            print("Completed frozen-base sigmoid", name, flush=True)
        selected = max(
            ("logistic_regression", "hist_gradient_boosting"), key=lambda name: metrics[name]["ap"]
        )
        uncertainty = bootstrap_ap_lift(
            validation, probabilities[selected], gates["uncertainty"]["replicates"], 42
        )
    checks = validation_gates(
        metrics[selected], uncertainty, counts["validation"]["unique_adverse_loans"], gates
    )
    model_path = output / "candidate_pipeline.joblib"
    joblib.dump(models[selected], model_path)
    model_path.chmod(0o600)
    digest = sha256(model_path)
    reloaded = joblib.load(model_path)  # Own freshly created model, not external weights.
    delta = float(
        np.max(
            np.abs(
                reloaded.predict_proba(x_validation.head(16))[:, 1]
                - models[selected].predict_proba(x_validation.head(16))[:, 1]
            )
        )
    )
    if digest != sha256(model_path) or delta > 1e-12:
        raise ValueError("Calibrated pipeline save-reload mismatch")
    np.savez_compressed(
        output / "validation_predictions.npz",
        loan_id=validation["loan_id"].to_numpy(dtype=str),
        as_of=validation["as_of"].to_numpy(dtype=str),
        label=validation["label"].to_numpy(dtype=int),
        probability=probabilities[selected],
    )
    (output / "validation_predictions.npz").chmod(0o600)
    if require_training_admission(manifest, protocol) != source:
        raise ValueError("Source admission changed during execution")
    write_private_json(
        output / "validation_report.json",
        {
            **common,
            "support_checks": support,
            "model_evaluation": "VALIDATION_ONLY",
            "candidates": metrics,
            "diagnostics": diagnostics,
            "train_constant_prevalence": pi,
            "calibration_constant_prevalence": cal_pi,
            "selected_candidate": selected,
            "uncertainty": uncertainty,
            "validation_gates": checks,
            "candidate_sha256": digest,
            "roundtrip_max_absolute_difference": delta,
            "validation_decision": (
                "PASS_CANDIDATE" if all(checks.values()) else "REJECT_VALIDATION"
            ),
        },
    )


def main() -> None:
    """Launch one monitored v3 development attempt; never read a frozen-test ZIP member."""
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("manifest", "protocol", "train-panel", "later-panel", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sha256(args.protocol) != PROTOCOL_SHA:
        raise ValueError("Locked v3 protocol required")
    source = require_training_admission(args.manifest, args.protocol)
    config = read_object(args.protocol)
    validate_temporal_plan(config)
    if args.worker:
        calibrated_worker(
            args.manifest, args.protocol, args.train_panel, args.later_panel, args.output
        )
        return
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents:
        raise ValueError("Private research outputs must be outside Git")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_private_json(
        args.manifest.parent / "training_attempt_v3.json",
        {
            "protocol_sha256": PROTOCOL_SHA,
            "output": str(output),
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    write_private_json(output / "source_manifest_at_start.json", source)
    env = dict(os.environ)
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        env[key] = str(config["resource_budget"]["threads"])
    result = supervise(
        [sys.executable, "-m", "src.research.freddie_calibrated", *sys.argv[1:], "--worker"],
        output,
        config["resource_budget"]["max_elapsed_minutes"],
        config["resource_budget"]["max_rss_gib"],
        env,
    )
    write_private_json(output / "resource_report.json", result)
    if result["exit_code"] != 0 or result["abort_reason"]:
        print(json.dumps({"run_status": "FAILED_OR_ABORTED", **result}))
        raise SystemExit(2)
    report = read_object(output / "validation_report.json")
    print(
        json.dumps(
            {
                "validation_decision": report["validation_decision"],
                "selected_candidate": report.get("selected_candidate"),
                "scoring_release": "HOLD",
                "frozen_test_opened": False,
                **result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
