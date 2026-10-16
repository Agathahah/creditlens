"""Bounded v4 mortgage development: past-only history, newer disjoint calibration, sealed test."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from src.research.freddie_calibrated import fit_sigmoid, make_base
from src.research.freddie_history_audit import past_features
from src.research.freddie_metrics import bootstrap_ap_lift, evaluate_predictions, validation_gates
from src.research.freddie_panel import (
    LABEL_VERSION,
    Observation,
    iter_histories,
    label_window,
    month_index,
)
from src.research.freddie_preflight import SCOPE, read_object, sha256
from src.research.freddie_train import supervise, write_private_json

PROTOCOL_SHA = "2b034c94ca49445793a9c5e3f1d598cdbbdd9f45aa12070b2fc544051202535b"
SOURCE_HASHES = {
    2018: "87e4d7ecad71ab0ad536d18fc078f51201077f602e35f49eccb7ea70cf01b2a8",
    2021: "38ced6b1e5ec155b51f0049fc44e4022db6cd5c98f5b559338c6791009faca9b",
    2022: "d0d33da246a318ee43639f19aad904e9208076143381a40f0666452cb5de6964",
}
MODULES = (
    "freddie_history_train",
    "freddie_history_audit",
    "freddie_calibrated",
    "freddie_panel",
    "freddie_metrics",
    "freddie_preflight",
    "freddie_train",
)


def validate_plan(config: dict[str, Any]) -> None:
    """Validate temporal maturity, disjoint identities and unchanged research safeguards.

    Args:
        config: Locked protocol or synthetic contract fixture.

    Raises:
        ValueError: Overlap, unsupported vintage, feature or research safeguard change.
    """
    previous = -1
    for role, vintage in (
        ("train", 2018),
        ("calibration", 2021),
        ("validation", 2021),
        ("frozen_test", 2022),
    ):
        split = config["split"][role]
        start, end, outcome = (
            month_index(split[key]) for key in ("as_of_start", "as_of_end", "last_outcome")
        )
        if split["vintage"] != vintage or not previous < start <= end or outcome != end + 3:
            raise ValueError("Invalid vintage or overlapping label maturity")
        previous = outcome
    cal, val = (config["split"][role]["loan_partition"] for role in ("calibration", "validation"))
    if (
        cal["method"] != "sha256_mod_2"
        or val["method"] != "sha256_mod_2"
        or not cal["salt"]
        or cal["salt"] != val["salt"]
        or cal["bucket"] != 0
        or val["bucket"] != 1
    ):
        raise ValueError("Calibration/validation partitions must be complementary")
    if (
        config["horizon_months"] != 3
        or config["label_version"] != LABEL_VERSION
        or config["feature_dtype"] != "float32"
        or config["public_scoring_authorized"] is not False
        or config["split"]["frozen_test"]["last_outcome"]
        > config["source_constraints"]["expected_performance_cutoff"]
    ):
        raise ValueError("Changed research horizon, schema, scope or cutoff")


def require_admission(manifest: Path, protocol: Path) -> dict[str, Any]:
    """Verify the locked private v4 source binding before any source member is opened.

    Args:
        manifest: Source receipt carrying prior private research terms acceptance.
        protocol: Immutable v4 configuration.

    Returns:
        Accepted private source manifest; not a scoring or point-in-time approval.

    Raises:
        ValueError: Identity/scope/terms/hash/consumption prerequisite fails.
    """
    source, config = read_object(manifest), read_object(protocol)
    if (
        sha256(protocol) != PROTOCOL_SHA
        or source.get("protocol_sha256") != PROTOCOL_SHA
        or source.get("scope") != SCOPE
        or source.get("source_admitted_for_training") is not True
        or source.get("admission_scope") != "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY"
        or source.get("frozen_test_opened") is not False
        or source.get("public_data_or_model_distribution_authorized") is not False
        or not all(
            source.get("owner_review", {}).get(k) is True
            for k in (
                "internal_research_terms_acknowledged",
                "retrospective_limitations_acknowledged",
            )
        )
    ):
        raise ValueError("Locked private v4 admission required; test must be unconsumed")
    validate_plan(config)
    for role, vintage in (
        ("train", 2018),
        ("calibration", 2021),
        ("validation", 2021),
        ("frozen_test", 2022),
    ):
        item = source["sources"][role]
        if (
            item["vintage"] != vintage
            or item["sha256"] != SOURCE_HASHES[vintage]
            or Path(item["path"]).name != f"sample_{vintage}.zip"
        ):
            raise ValueError("Source vintage/checksum binding changed")
    seen: set[Path] = set()
    for item in source["sources"].values():
        path = Path(item["path"])
        if path not in seen:
            if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                raise ValueError("Source size/checksum mismatch")
            seen.add(path)
    return source


def _static_values(
    archive: Path, vintage: int, config: dict[str, Any]
) -> dict[str, list[float | None]]:
    """Validate the locked legacy origination layout without publishing any records."""
    result: dict[str, list[float | None]] = {}
    with zipfile.ZipFile(archive) as z:
        if sorted(z.namelist()) != [f"sample_orig_{vintage}.txt", f"sample_perf_{vintage}.txt"]:
            raise ValueError("Unexpected archive members; new layout requires a separate audit")
        with z.open(f"sample_orig_{vintage}.txt") as raw:
            for row in csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="|"):
                if len(row) != 31 or not row[19] or row[19] in result:
                    raise ValueError("Invalid origination key/layout")
                values: list[float | None] = []
                for spec in config["origination_features"].values():
                    token = row[spec["column"] - 1]
                    value = float(token) if token else None
                    if value == spec["sentinel"]:
                        value = None
                    if value is not None and (
                        not math.isfinite(value)
                        or not spec["range"][0] <= value <= spec["range"][1]
                    ):
                        raise ValueError("Invalid static feature bounds")
                    values.append(value)
                result[row[19]] = values
    if not 0 < len(result) <= config["source_constraints"]["maximum_sample_loans"]:
        raise ValueError("Sample loan capacity exceeded or source empty")
    return result


@dataclass
class Cohort:
    """Private labeled rows/features plus explicit eligible/censored denominators."""

    frame: pd.DataFrame
    features: pd.DataFrame
    counts: dict[str, Any]


class _Buffer:
    """Preallocate bounded float32 arrays instead of holding millions of Python tuples."""

    def __init__(self, capacity: int, names: list[str]) -> None:
        self.names = names
        self.values = np.full((capacity, len(names)), np.nan, dtype=np.float32)
        self.loans = np.empty(capacity, dtype=object)
        self.periods = np.empty(capacity, dtype=object)
        self.labels = np.zeros(capacity, dtype=np.int8)
        self.n = 0
        self.monthly: dict[str, Counter[str]] = {}
        self.censoring: Counter[str] = Counter()

    def finish(self) -> Cohort:
        frame = pd.DataFrame(
            {
                "loan_id": self.loans[: self.n],
                "as_of": self.periods[: self.n],
                "label": self.labels[: self.n],
            }
        )
        if frame.duplicated(["loan_id", "as_of"]).any():
            raise ValueError("Duplicate loan-month")
        monthly: list[dict[str, Any]] = [
            {"as_of": month, **dict(values)} for month, values in sorted(self.monthly.items())
        ]
        counts: dict[str, Any] = {
            "eligible_observations": sum(c["eligible"] for c in monthly),
            "labeled": self.n,
            "censored": sum(c["censored"] for c in monthly),
            "unique_loans": int(frame["loan_id"].nunique()),
            "adverse_observations": int(frame["label"].sum()),
            "unique_adverse_loans": int(frame.loc[frame["label"].eq(1), "loan_id"].nunique()),
            "monthly": monthly,
            "censoring_reasons": dict(self.censoring),
        }
        if counts["eligible_observations"] != counts["labeled"] + counts["censored"]:
            raise ValueError("Cohort reconciliation failed")
        return Cohort(frame, pd.DataFrame(self.values[: self.n], columns=self.names), counts)


def _collect_archive(
    archive: Path, vintage: int, splits: dict[str, dict[str, Any]], config: dict[str, Any]
) -> dict[str, Cohort]:
    """Stream exact locked windows; independent execution must authorize test access first."""
    before = archive.stat()
    source_hash = sha256(archive)
    static = _static_values(archive, vintage, config)
    buffers = {
        role: _Buffer(
            len(static) * (month_index(split["as_of_end"]) - month_index(split["as_of_start"]) + 1),
            config["features"],
        )
        for role, split in splits.items()
    }
    minimum, maximum = "999999", "000000"
    histories = 0
    for history in iter_histories(archive, vintage):
        histories += 1
        minimum, maximum = min(minimum, history[0].period), max(maximum, history[-1].period)
        key = history[0].loan_id
        active_roles = []
        for role, split in splits.items():
            partition = split.get("loan_partition")
            if partition:
                bucket = (
                    int(hashlib.sha256((partition["salt"] + ":" + key).encode()).hexdigest(), 16)
                    % 2
                )
                if bucket != partition["bucket"]:
                    continue
            active_roles.append(role)
        previous: dict[int, Observation] = {}
        for index, current in enumerate(history):
            month = month_index(current.period)
            for role in active_roles:
                split, buffer = splits[role], buffers[role]
                if (
                    not split["as_of_start"] <= current.period <= split["as_of_end"]
                    or not current.active_current
                ):
                    continue
                label, reason, observed = label_window(history, index)
                stats = buffer.monthly.setdefault(
                    current.period, Counter(eligible=0, labeled=0, censored=0)
                )
                stats["eligible"] += 1
                if label is None:
                    stats["censored"] += 1
                    buffer.censoring[reason] += 1
                    continue
                if observed is None or observed > split["last_outcome"]:
                    raise ValueError("Label availability exceeds locked window")
                stats["labeled"] += 1
                past = past_features(current, previous)
                features: dict[str, float | None] = {
                    "upb": current.upb,
                    "loan_age": current.loan_age,
                    "remaining_months": current.remaining_months,
                    "interest_rate": current.interest_rate,
                    **{
                        f"prior_dq_{lag}": (
                            previous[month - lag].dq
                            if month - lag in previous and previous[month - lag].dq is not None
                            else None
                        )
                        for lag in (1, 2)
                    },
                    **dict(zip(config["origination_features"], static[key], strict=True)),
                    **past,
                }
                if buffer.n >= len(buffer.labels):
                    raise ValueError("Preallocated sample capacity exceeded")
                buffer.values[buffer.n] = [features[name] for name in config["features"]]
                buffer.loans[buffer.n], buffer.periods[buffer.n] = key, sys.intern(current.period)
                buffer.labels[buffer.n] = label
                buffer.n += 1
            previous[month] = current
    if (
        histories != len(static)
        or maximum != config["source_constraints"]["expected_performance_cutoff"]
        or (before.st_size, before.st_mtime_ns)
        != (archive.stat().st_size, archive.stat().st_mtime_ns)
        or source_hash != sha256(archive)
    ):
        raise ValueError("Source identity, cutoff or loan reconciliation mismatch")
    cohorts = {role: buffer.finish() for role, buffer in buffers.items()}
    for cohort in cohorts.values():
        if np.isinf(cohort.features.to_numpy()).any():
            raise ValueError("Non-finite feature after float32 conversion")
        cohort.counts["source_period_min"] = minimum
        cohort.counts["source_period_max"] = maximum
        cohort.counts["source_loans"] = histories
    return cohorts


def collect_development(
    archive: Path, vintage: int, splits: dict[str, dict[str, Any]], config: dict[str, Any]
) -> dict[str, Cohort]:
    """Collect development only; reject consumed or frozen vintages before source access.

    Args:
        archive: Private admitted development ZIP.
        vintage: 2018 or 2021; all other vintages are sealed here.
        splits: Development-only role calendars.
        config: Locked feature/source/label specification.

    Returns:
        Labeled cohorts with past-only domain features and censoring counts.

    Raises:
        ValueError: Unsupported vintage/role or invalid source/cohort contract.
    """
    if vintage not in (2018, 2021) or not set(splits) <= {"train", "calibration", "validation"}:
        raise ValueError("Only development sources/roles allowed; test is sealed")
    if any(split["vintage"] != vintage for split in splits.values()):
        raise ValueError("Wrong development vintage")
    return _collect_archive(archive, vintage, splits, config)


def development_worker(manifest: Path, protocol: Path, output: Path) -> None:
    """Fit one locked bounded attempt on train, calibrate separately, evaluate validation.

    Args:
        manifest: Private admitted sources and source-use roles.
        protocol: Immutable v4 configuration.
        output: New private owner-only directory.
    """
    source = require_admission(manifest, protocol)
    config = read_object(protocol)
    cohorts = collect_development(
        Path(source["sources"]["train"]["path"]), 2018, {"train": config["split"]["train"]}, config
    )
    cohorts.update(
        collect_development(
            Path(source["sources"]["calibration"]["path"]),
            2021,
            {role: config["split"][role] for role in ("calibration", "validation")},
            config,
        )
    )
    keys = {role: set(cohort.frame["loan_id"]) for role, cohort in cohorts.items()}
    if any(
        keys[a] & keys[b]
        for a, b in (
            ("train", "calibration"),
            ("train", "validation"),
            ("calibration", "validation"),
        )
    ):
        raise ValueError("Development loan identity overlaps")
    common = {
        "protocol_sha256": PROTOCOL_SHA,
        "scope": SCOPE,
        "source_manifest_sha256": sha256(manifest),
        "source_hashes": {role: item["sha256"] for role, item in source["sources"].items()},
        "counts": {role: cohort.counts for role, cohort in cohorts.items()},
        "label_version": LABEL_VERSION,
        "frozen_test_opened": False,
        "scoring_release": "HOLD",
        "point_in_time_verified": False,
        "loan_identity_overlap": 0,
        "created_at": datetime.now(UTC).isoformat(),
        "cohort_loan_sha256": {
            role: hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()
            for role, ids in keys.items()
        },
        "software": {
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "features": config["features"],
            "feature_dtype": "float32",
            "module_sha256": {
                name: sha256(Path(__file__).with_name(name + ".py")) for name in MODULES
            },
        },
        "limitations": [
            "Corrected retrospective mortgage snapshot; no operational availability proof",
            "Changed development cohorts/features; not causal feature ablation",
            "Complete-label selection and loan-conditional uncertainty",
            "No source2020 access; no source2022 members opened in development",
        ],
    }
    gates = config["proposed_research_gates"]
    minima = {
        "train": gates["minimum_unique_adverse_loans"]["train"],
        "calibration": config["calibration"]["minimum_unique_adverse_loans"],
        "validation": gates["minimum_unique_adverse_loans"]["validation"],
    }
    support = {
        role: cohorts[role].counts["unique_adverse_loans"] >= minimum
        and cohorts[role].frame["label"].nunique() == 2
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
    train, calibration, validation = (
        cohorts[role] for role in ("train", "calibration", "validation")
    )
    pi, cal_pi = float(train.frame["label"].mean()), float(calibration.frame["label"].mean())
    cal_brier = float(np.mean((cal_pi - validation.frame["label"].to_numpy()) ** 2))
    fraction = config["alert_policy"]["fraction"]
    metrics = {
        "constant": evaluate_predictions(
            validation.frame, np.full(len(validation.frame), pi), pi, fraction
        )
    }
    diagnostics = {}
    models, probabilities = {}, {}
    with threadpool_limits(limits=2):
        for name in ("logistic_regression", "hist_gradient_boosting"):
            base = make_base(name, config)
            base.fit(train.features, train.frame["label"])
            raw = base.predict_proba(validation.features)[:, 1]
            diagnostics[name + "_uncalibrated"] = evaluate_predictions(
                validation.frame, raw, pi, fraction
            )
            model = fit_sigmoid(base, calibration.features, calibration.frame["label"])
            scores = model.predict_proba(validation.features)[:, 1]
            models[name], probabilities[name] = model, scores
            metrics[name] = evaluate_predictions(validation.frame, scores, pi, fraction)
            metrics[name]["calibration_constant_brier"] = cal_brier
            metrics[name]["calibration_constant_brier_skill"] = (
                1 - metrics[name]["brier"] / cal_brier
            )
            print("Completed bounded v4", name, flush=True)
        selected = max(
            ("logistic_regression", "hist_gradient_boosting"), key=lambda name: metrics[name]["ap"]
        )
        uncertainty = bootstrap_ap_lift(validation.frame, probabilities[selected], 1000, 42)
    checks = validation_gates(
        metrics[selected], uncertainty, validation.counts["unique_adverse_loans"], gates
    )
    candidate = output / "candidate_pipeline.joblib"
    joblib.dump(models[selected], candidate)
    candidate.chmod(0o600)
    digest = sha256(candidate)
    reloaded = joblib.load(candidate)  # Own newly produced artifact only.
    delta = float(
        np.max(
            np.abs(
                reloaded.predict_proba(validation.features.head(16))[:, 1]
                - models[selected].predict_proba(validation.features.head(16))[:, 1]
            )
        )
    )
    if digest != sha256(candidate) or delta > 1e-12:
        raise ValueError("Candidate checksum or roundtrip mismatch")
    np.savez_compressed(
        output / "validation_predictions.npz",
        loan_id=validation.frame["loan_id"].to_numpy(dtype=str),
        as_of=validation.frame["as_of"].to_numpy(dtype=str),
        label=validation.frame["label"].to_numpy(),
        probability=probabilities[selected],
    )
    (output / "validation_predictions.npz").chmod(0o600)
    if require_admission(manifest, protocol) != source:
        raise ValueError("Admission changed during development")
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
    """Supervise one private v4 attempt and preserve its ledger, hashes and resource evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("manifest", "protocol", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents:
        raise ValueError("Private outputs must remain outside Git")
    source = require_admission(args.manifest, args.protocol)
    if args.worker:
        development_worker(args.manifest, args.protocol, output)
        return
    archive = Path(source["sources"]["frozen_test"]["path"])
    if (archive.parent / "frozen_test_consumed_2022.json").exists():
        raise ValueError("New test vintage already consumed")
    import shutil

    if shutil.disk_usage(output.parent).free < 2 * 1024**3:
        raise ValueError("At least2GiB disk required for bounded research outputs")
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    write_private_json(
        args.manifest.parent / "training_attempt_v4.json",
        {
            "protocol_sha256": PROTOCOL_SHA,
            "output": str(output),
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    write_private_json(output / "source_manifest_at_start.json", source)
    snapshot = output / "code_snapshot"
    snapshot.mkdir(mode=0o700)
    for name in MODULES:
        target = snapshot / (name + ".py")
        target.write_bytes(Path(__file__).with_name(name + ".py").read_bytes())
        target.chmod(0o600)
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
        [sys.executable, "-m", "src.research.freddie_history_train", *sys.argv[1:], "--worker"],
        output,
        15,
        2,
        env,
    )
    write_private_json(output / "resource_report.json", result)
    if result["exit_code"] != 0 or result["abort_reason"]:
        print(json.dumps({"validation_decision": "FAILED_OR_ABORTED", **result}))
        raise SystemExit(2)
    report = read_object(output / "validation_report.json")
    print(
        json.dumps(
            {
                "validation_decision": report["validation_decision"],
                "scoring_release": "HOLD",
                "new_test_members_opened": False,
                **result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
