"""Run the approved bounded mortgage validation experiment without opening frozen test."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.research.freddie_panel import FEATURES, LABEL_VERSION, month_index
from src.research.freddie_preflight import assess_admission, read_object, sha256

if TYPE_CHECKING:
    import pandas as pd

APPROVED_PROTOCOL_SHA = "c17999bce05357b4ef937eee474b0549702c811de91ccd43a8017a1f5eb696b7"

APPROVED_PROTOCOL_SHAS = {
    APPROVED_PROTOCOL_SHA,
    "f4eef57a25e638f9a4c694a16f3d93d2bd8ee8f50440d5c9758cbd440eee0411",
    "01f06de390b6b64503e23f5926f3f143d1d86cdcd3cee221e0dd9853c8f2c975",
}


def write_private_json(path: Path, value: dict[str, Any]) -> None:
    """Create a JSON artifact without overwrite and restrict it to the owner.

    Args:
        path: New private file path.
        value: JSON-safe evidence, excluding raw source records.
    """
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
    path.chmod(0o600)


def require_training_admission(manifest: Path, protocol: Path) -> dict[str, Any]:
    """Reject unmet admission or a changed v1 protocol before loading panel data.

    Args:
        manifest: Privately reviewed source manifest.
        protocol: Exact approved immutable experiment configuration.

    Returns:
        The accepted source manifest.

    Raises:
        ValueError: A prerequisite fails or a source is not admitted for research.
    """
    report = assess_admission(manifest, protocol)
    source = read_object(manifest)
    if (
        sha256(protocol) not in APPROVED_PROTOCOL_SHAS
        or report["blockers"]
        or source.get("source_admitted_for_training") is not True
    ):
        raise ValueError("Approved research source/protocol admission is required")
    return source


def load_window(panel: Path, split: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read only a planned development window and validate label availability.

    Args:
        panel: Read-only research SQLite database.
        split: Locked vintage, as-of range and last permissible outcome month.

    Returns:
        Labeled rows and explicit labeled/censored/unique-event counts.

    Raises:
        ValueError: Empty/duplicate cohort, wrong vintage or invalid label horizon.
    """
    import numpy as np
    import pandas as pd

    columns = (
        "loan_id,as_of,vintage,"
        + ",".join(FEATURES)
        + ",label,label_reason,label_observed_period,horizon_months"
    )
    with sqlite3.connect(panel.resolve().as_uri() + "?mode=ro", uri=True) as db:
        frame = pd.read_sql_query(
            f"SELECT {columns} FROM loan_month WHERE as_of BETWEEN ? AND ? ORDER BY as_of,loan_id",
            db,
            params=(split["as_of_start"], split["as_of_end"]),
        )
    if frame.empty or frame.duplicated(["loan_id", "as_of"]).any() or frame["loan_id"].isna().any():
        raise ValueError("Empty or invalid loan-month cohort")
    if not frame["vintage"].eq(split["vintage"]).all() or not frame["horizon_months"].eq(3).all():
        raise ValueError("Wrong panel contract")
    partition = split.get("loan_partition")
    if partition is not None:
        if (
            partition.get("method") != "sha256_mod_2"
            or type(partition.get("bucket")) is not int
            or partition.get("bucket") not in (0, 1)
            or not isinstance(partition.get("salt"), str)
            or not partition["salt"]
        ):
            raise ValueError("Invalid deterministic loan partition")
        buckets = {
            key: int(hashlib.sha256((partition["salt"] + ":" + key).encode()).hexdigest(), 16) % 2
            for key in frame["loan_id"].unique()
        }
        frame = frame.loc[frame["loan_id"].map(buckets).eq(partition["bucket"])].copy()
        if frame.empty:
            raise ValueError("Empty loan partition")
    labeled = frame.loc[frame["label"].notna()].copy()
    if not labeled["label"].isin([0, 1]).all() or labeled["label_observed_period"].isna().any():
        raise ValueError("Invalid labels or missing establishment dates")
    current = np.array([month_index(str(value)) for value in labeled["as_of"]])
    observed = np.array([month_index(str(value)) for value in labeled["label_observed_period"]])
    negative = labeled["label"].eq(0).to_numpy()
    if (
        (observed <= current)
        | (observed > current + 3)
        | (observed > month_index(split["last_outcome"]))
        | (negative & (observed != current + 3))
    ).any():
        raise ValueError("Label timing exceeds the locked window")
    x = labeled[list(FEATURES)].to_numpy(dtype=float)
    if np.isinf(x).any():
        raise ValueError("Infinite feature values")
    summary = {
        "eligible_observations": len(frame),
        "labeled": len(labeled),
        "censored": int(frame["label"].isna().sum()),
        "unique_loans": int(labeled["loan_id"].nunique()),
        "adverse_observations": int(labeled["label"].sum()),
        "unique_adverse_loans": int(labeled.loc[labeled["label"].eq(1), "loan_id"].nunique()),
        "censoring_reasons": {
            str(k): int(v)
            for k, v in frame.loc[frame["label"].isna(), "label_reason"].value_counts().items()
        },
        "monthly": [
            {
                "as_of": str(month),
                "eligible": len(group),
                "labeled": int(group["label"].notna().sum()),
                "censored": int(group["label"].isna().sum()),
            }
            for month, group in frame.groupby("as_of", sort=True)
        ],
    }
    return labeled, summary


def validation_worker(
    manifest: Path, protocol: Path, train_panel: Path, validation_panel: Path, output: Path
) -> None:
    """Fit the three locked candidates and quarantine the selected private pipeline.

    Args:
        manifest: Accepted source manifest.
        protocol: Exact v1 configuration.
        train_panel: Audited 2018 development panel.
        validation_panel: Audited 2019 validation panel.
        output: New private run directory created by the resource supervisor.
    """
    import joblib
    import numpy as np
    import sklearn
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits

    from src.research.freddie_metrics import (
        bootstrap_ap_lift,
        evaluate_predictions,
        validation_gates,
    )

    if sha256(protocol) == "f4eef57a25e638f9a4c694a16f3d93d2bd8ee8f50440d5c9758cbd440eee0411":
        raise ValueError("V3 requires the separate calibrated research executor")
    source = require_training_admission(manifest, protocol)
    config = read_object(protocol)
    for role, panel in (("train", train_panel), ("validation", validation_panel)):
        panel_report = read_object(panel.parent / "panel_report.json")
        if (
            panel_report["source_sha256"] != source["sources"][role]["sha256"]
            or panel_report["label_version"] != LABEL_VERSION
            or panel_report["feature_whitelist"] != list(FEATURES)
        ):
            raise ValueError("Panel provenance does not match admitted source")
    train, train_counts = load_window(train_panel, config["split"]["train"])
    validation, validation_counts = load_window(validation_panel, config["split"]["validation"])
    if set(train["loan_id"]) & set(validation["loan_id"]):
        raise ValueError("Loan overlap between train and validation")
    gates = config["proposed_research_gates"]
    common = {
        "protocol_sha256": sha256(protocol),
        "source_manifest_sha256": sha256(manifest),
        "source_hashes": {k: v["sha256"] for k, v in source["sources"].items()},
        "scope": config["scope"],
        "label_version": LABEL_VERSION,
        "counts": {"train": train_counts, "validation": validation_counts},
        "created_at": datetime.now(UTC).isoformat(),
        "frozen_test_opened": False,
        "scoring_release": "HOLD",
        "point_in_time_verified": False,
        "software": {
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "code_sha256": sha256(Path(__file__)),
            "metrics_code_sha256": sha256(Path(__file__).with_name("freddie_metrics.py")),
            "features": config["features"],
        },
        "limitations": [
            "Corrected retrospective snapshot, not operational point-in-time validation",
            "Complete-label subset can have censoring bias",
            "Mortgage study is not fintech scoring acceptance",
        ],
    }
    minimums = gates["minimum_unique_adverse_loans"]
    if (
        train_counts["unique_adverse_loans"] < minimums["train"]
        or validation_counts["unique_adverse_loans"] < minimums["validation"]
        or train["label"].nunique() != 2
        or validation["label"].nunique() != 2
    ):
        write_private_json(
            output / "validation_report.json",
            {
                **common,
                "validation_decision": "REJECT_SUPPORT",
                "model_evaluation": "NOT_FIT_SUPPORT_FAILURE",
            },
        )
        return
    write_private_json(
        output / "validation_opened.json",
        {
            "opened_at": datetime.now(UTC).isoformat(),
            "under_approved_protocol_sha256": sha256(protocol),
        },
    )
    feature_names = config["features"]
    if config.get("origination_features"):
        from src.research.freddie_origination import enrich_origination

        train = enrich_origination(
            train, Path(source["sources"]["train"]["path"]), 2018, config["origination_features"]
        )
        validation = enrich_origination(
            validation,
            Path(source["sources"]["validation"]["path"]),
            2019,
            config["origination_features"],
        )
    x_train, y_train = train[feature_names], train["label"].astype(int)
    x_validation = validation[feature_names]
    pi = float(y_train.mean())
    fraction = config["alert_policy"]["fraction"]
    metrics = {
        "constant": evaluate_predictions(validation, np.full(len(validation), pi), pi, fraction)
    }
    pipelines: dict[str, Any] = {}
    predictions: dict[str, Any] = {}
    with threadpool_limits(limits=config["resource_budget"]["threads"]):
        for name in ("logistic_regression", "hist_gradient_boosting"):
            steps: list[tuple[str, Any]] = [
                (
                    "imputer",
                    SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                )
            ]
            if name == "logistic_regression":
                steps.extend(
                    [
                        ("scaler", StandardScaler()),
                        (
                            "model",
                            LogisticRegression(
                                **config["candidates"][name],
                                random_state=config["resource_budget"]["seed"],
                            ),
                        ),
                    ]
                )
            else:
                steps.append(
                    (
                        "model",
                        HistGradientBoostingClassifier(
                            **config["candidates"][name],
                            early_stopping=False,
                            random_state=config["resource_budget"]["seed"],
                        ),
                    )
                )
            pipeline = Pipeline(steps)
            pipeline.fit(x_train, y_train)
            scores = pipeline.predict_proba(x_validation)[:, 1]
            predictions[name] = scores
            pipelines[name] = pipeline
            metrics[name] = evaluate_predictions(validation, scores, pi, fraction)
            print(f"Completed {name}", flush=True)
        selected = max(
            ("logistic_regression", "hist_gradient_boosting"), key=lambda name: metrics[name]["ap"]
        )
        uncertainty = bootstrap_ap_lift(
            validation,
            predictions[selected],
            gates["uncertainty"]["replicates"],
            config["resource_budget"]["seed"],
        )
    results = validation_gates(
        metrics[selected], uncertainty, validation_counts["unique_adverse_loans"], gates
    )
    model_path = output / "candidate_pipeline.joblib"
    joblib.dump(pipelines[selected], model_path)
    model_path.chmod(0o600)
    model_hash = sha256(model_path)
    reloaded = joblib.load(model_path)  # Own locally produced artifact only, after hashing.
    probe = x_validation.head(16)
    delta = float(
        np.max(
            np.abs(
                reloaded.predict_proba(probe)[:, 1] - pipelines[selected].predict_proba(probe)[:, 1]
            )
        )
    )
    if sha256(model_path) != model_hash or delta > 1e-12:
        raise ValueError("Candidate round-trip parity failed")
    np.savez_compressed(
        output / "validation_predictions.npz",
        loan_id=validation["loan_id"].to_numpy(dtype=str),
        as_of=validation["as_of"].to_numpy(dtype=str),
        label=validation["label"].to_numpy(dtype=int),
        probability=predictions[selected],
    )
    (output / "validation_predictions.npz").chmod(0o600)
    final = {
        **common,
        "model_evaluation": "VALIDATION_ONLY",
        "train_constant_prevalence": pi,
        "candidates": metrics,
        "selected_candidate": selected,
        "uncertainty": uncertainty,
        "validation_gates": results,
        "validation_decision": "PASS_CANDIDATE" if all(results.values()) else "REJECT_VALIDATION",
        "candidate_sha256": model_hash,
        "roundtrip_max_absolute_difference": delta,
        "independent_test_evaluation": "NOT_RUN",
    }
    require_training_admission(manifest, protocol)  # Reconcile source/protocol after the run.
    write_private_json(output / "validation_report.json", final)


def supervise(
    command: list[str], output: Path, minutes: float, rss_gib: float, env: dict[str, str]
) -> dict[str, Any]:
    """Bound a single research worker's time and resident memory; stop only its group.

    Args:
        command: Worker command without shell interpolation.
        output: Private directory for logs and supervision evidence.
        minutes: Wall-clock budget.
        rss_gib: Maximum worker RSS in GiB.
        env: Explicit child environment including thread limits.

    Returns:
        Exit code, measured peak sampled RSS, duration and abort reason.
    """
    started = time.monotonic()
    peak = 0
    reason = None
    with (output / "worker.log").open("x") as log:
        (output / "worker.log").chmod(0o600)
        process = subprocess.Popen(
            command, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True
        )
        try:
            while process.poll() is None:
                try:
                    rss = subprocess.run(
                        ["ps", "-o", "rss=", "-p", str(process.pid)],
                        capture_output=True,
                        text=True,
                        timeout=2,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    reason = "RESOURCE_MONITOR_UNAVAILABLE"
                    break
                if rss.returncode != 0 and process.poll() is None:
                    reason = "RESOURCE_MONITOR_UNAVAILABLE"
                    break
                if rss.returncode == 0 and rss.stdout.strip():
                    peak = max(peak, int(rss.stdout.strip()) * 1024)
                if time.monotonic() - started > minutes * 60:
                    reason = "WALL_TIME_BUDGET"
                elif peak > rss_gib * 1024**3:
                    reason = "RSS_BUDGET"
                if reason:
                    break
                time.sleep(0.25)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return {
        "exit_code": process.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "sampled_worker_peak_rss_bytes": peak,
        "abort_reason": reason,
        "memory_measurement": "Worker RSS sampled every 250ms, not guaranteed instantaneous peak",
    }


def main() -> None:
    """Launch a guarded validation run; frozen test is not a supported CLI input."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "protocol", "train-panel", "validation-panel", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sha256(args.protocol) == "f4eef57a25e638f9a4c694a16f3d93d2bd8ee8f50440d5c9758cbd440eee0411":
        raise ValueError("V3 requires the separate calibrated research executor")
    source = require_training_admission(args.manifest, args.protocol)
    if args.worker:
        validation_worker(
            args.manifest, args.protocol, args.train_panel, args.validation_panel, args.output
        )
        return
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents:
        raise ValueError("Research outputs must remain outside Git")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    protocol_hash = sha256(args.protocol)
    if (args.manifest.parent / "training_attempt_v1.json").exists():
        raise ValueError("A previous v1 attempt exists; preserve it before any reviewed retry")
    attempt = args.manifest.parent / f"training_attempt_{protocol_hash[:12]}.json"
    write_private_json(
        attempt,
        {
            "protocol_sha256": protocol_hash,
            "output": str(output),
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    write_private_json(output / "source_manifest_at_start.json", source)
    config = read_object(args.protocol)
    env = dict(os.environ)
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        env[key] = str(config["resource_budget"]["threads"])
    command = [sys.executable, "-m", "src.research.freddie_train", *sys.argv[1:], "--worker"]
    result = supervise(
        command,
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
