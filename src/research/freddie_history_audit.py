"""Profile past-history features on admitted development sources, without fit or test access."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.research.freddie_panel import Observation, iter_histories, month_index
from src.research.freddie_preflight import SCOPE, read_object, sha256
from src.research.freddie_train import supervise, write_private_json

PROTOCOL_SHA = "f4eef57a25e638f9a4c694a16f3d93d2bd8ee8f50440d5c9758cbd440eee0411"
ROLES = ("train", "calibration", "validation")
DEVELOPMENT_HASHES = {
    2018: "87e4d7ecad71ab0ad536d18fc078f51201077f602e35f49eccb7ea70cf01b2a8",
    2019: "5c145dda5ebb38ed25fe04fe1fe5a73588ca8b43970be71adc30096d8d5f8031",
}


def past_features(
    current: Observation, previous: Mapping[int, Observation]
) -> dict[str, float | None]:
    """Derive features using exact calendar months strictly before the as-of month.

    Args:
        current: Eligible active-current reporting record.
        previous: Records indexed by calendar month; future entries are ignored.

    Returns:
        Completeness, delinquency and balance-change candidates. Incomplete status
        windows return null for counts/worst status, rather than fabricated zeros.
    """
    start = month_index(current.period)
    result: dict[str, float | None] = {}
    for window in (6, 12):
        records = [previous.get(start - lag) for lag in range(1, window + 1)]
        known = [record.dq for record in records if record is not None and record.dq is not None]
        complete = len(known) == window
        result[f"observed_months_{window}"] = float(sum(item is not None for item in records))
        result[f"known_status_months_{window}"] = float(len(known))
        result[f"complete_status_{window}"] = float(complete)
        result[f"worst_dq_{window}"] = float(max(known)) if complete else None
        result[f"dq_months_{window}"] = float(sum(dq > 0 for dq in known)) if complete else None
    lags = [
        lag
        for lag in range(1, 13)
        if (item := previous.get(start - lag)) is not None and item.dq is not None and item.dq > 0
    ]
    result["months_since_known_dq_12"] = float(min(lags)) if lags else None
    for lag in (3, 6, 12):
        item = previous.get(start - lag)
        result[f"upb_change_ratio_{lag}"] = (
            (current.upb - item.upb) / item.upb if item is not None and item.upb > 0 else None
        )
    return result


@dataclass
class Profile:
    """Bounded numeric summary with exact moments and approximate reservoir quantiles."""

    count: int = 0
    missing: int = 0
    zeros: int = 0
    mean: float = 0.0
    m2: float = 0.0
    minimum: float = math.inf
    maximum: float = -math.inf
    sample: list[float] = field(default_factory=list)
    rng: random.Random = field(default_factory=lambda: random.Random(42))

    def add(self, value: float | None) -> None:
        """Update aggregate statistics, keeping at most 2,000 sampled values.

        Args:
            value: Finite candidate feature or missing value.
        """
        if value is None:
            self.missing += 1
            return
        if not math.isfinite(value):
            raise ValueError("Non-finite history feature")
        self.count += 1
        self.zeros += int(value == 0)
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)
        if len(self.sample) < 2000:
            self.sample.append(value)
        else:
            index = self.rng.randrange(self.count)
            if index < 2000:
                self.sample[index] = value

    def summary(self) -> dict[str, Any]:
        """Return aggregates without retaining sampled values in the output.

        Returns:
            Exact counts/moments and explicitly approximate sample quantiles.
        """
        import numpy as np

        total = self.count + self.missing
        return {
            "observations": total,
            "non_missing": self.count,
            "missing": self.missing,
            "missing_fraction": self.missing / total if total else None,
            "zeros": self.zeros,
            "minimum": self.minimum if self.count else None,
            "maximum": self.maximum if self.count else None,
            "mean": self.mean if self.count else None,
            "population_std": math.sqrt(max(0.0, self.m2 / self.count)) if self.count else None,
            "approximate_quantiles": (
                dict(
                    zip(
                        ("p05", "p25", "p50", "p75", "p95"),
                        np.quantile(self.sample, [0.05, 0.25, 0.5, 0.75, 0.95]).tolist(),
                        strict=True,
                    )
                )
                if self.sample
                else {}
            ),
            "quantile_reservoir_size": len(self.sample),
        }


def require_development_sources(manifest: Path, protocol: Path) -> dict[str, Any]:
    """Verify only admitted development sources; consumed test is never inspected.

    Args:
        manifest: Existing private source admission, including historical consumption.
        protocol: Immutable v3 configuration supplying development windows only.

    Returns:
        Accepted manifest. This is not a training or release admission.

    Raises:
        ValueError: Scope, acknowledgements, protocol or development source mismatch.
    """
    source = read_object(manifest)
    review = source.get("owner_review", {})
    if (
        sha256(protocol) != PROTOCOL_SHA
        or source.get("scope") != SCOPE
        or source.get("admission_scope") != "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY"
        or source.get("source_admitted_for_training") is not True
        or source.get("protocol_sha256") != PROTOCOL_SHA
        or not all(
            review.get(key) is True
            for key in (
                "internal_research_terms_acknowledged",
                "retrospective_limitations_acknowledged",
            )
        )
    ):
        raise ValueError("Admitted private development source and locked protocol required")
    # Check both vintages before any source file is opened. Never iterate over frozen_test.
    for role, vintage in (("train", 2018), ("validation", 2019)):
        item = source["sources"][role]
        if (
            item["vintage"] != vintage
            or item["sha256"] != DEVELOPMENT_HASHES[vintage]
            or Path(item["path"]).name != f"sample_{vintage}.zip"
        ):
            raise ValueError("Only admitted development archives 2018/2019 are permitted")
    for role in ("train", "validation"):
        item = source["sources"][role]
        path = Path(item["path"])
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError("Development archive checksum/size mismatch")
    return source


def profile_history(
    history: Sequence[Observation], split: dict[str, Any], profiles: dict[str, Profile]
) -> int:
    """Profile eligible as-of rows without computing or selecting on future labels.

    Args:
        history: One ordered development loan history.
        split: Locked development calendar and optional loan partition.
        profiles: Mutable aggregate profiles, containing no identifiers.

    Returns:
        Number of eligible observations, including future-censored observations.

    Raises:
        ValueError: Mixed loan identities, duplicate or unordered calendar records.
    """
    if not history:
        return 0
    partition = split.get("loan_partition")
    selected = True
    if partition:
        digest = hashlib.sha256((partition["salt"] + ":" + history[0].loan_id).encode())
        selected = int(digest.hexdigest(), 16) % 2 == partition["bucket"]
    previous: dict[int, Observation] = {}
    count = 0
    last = -1
    for current in history:
        month = month_index(current.period)
        if current.loan_id != history[0].loan_id or month <= last:
            raise ValueError("Mixed loan, duplicate or unordered history")
        if selected and split["as_of_start"] <= current.period <= split["as_of_end"]:
            if current.active_current:
                for key, value in past_features(current, previous).items():
                    profiles.setdefault(key, Profile()).add(value)
                count += 1
        previous[month] = current
        last = month
    return count


def audit_worker(manifest: Path, protocol: Path, output: Path) -> None:
    """Stream development ZIPs into private aggregate profiles under the supervisor.

    Args:
        manifest: Accepted private development-source manifest.
        protocol: Immutable development windows; frozen role is ignored.
        output: Existing owner-only directory outside the repository.
    """
    source = require_development_sources(manifest, protocol)
    config = read_object(protocol)
    profiles: dict[str, dict[str, Profile]] = {role: {} for role in ROLES}
    counts = dict.fromkeys(ROLES, 0)
    for archive_role, roles in (("train", ("train",)), ("validation", ROLES[1:])):
        item = source["sources"][archive_role]
        for history in iter_histories(Path(item["path"]), item["vintage"]):
            for role in roles:
                counts[role] += profile_history(history, config["split"][role], profiles[role])
    if any(count == 0 for count in counts.values()):
        raise ValueError("Empty development audit window")
    if require_development_sources(manifest, protocol) != source:
        raise ValueError("Source changed during development audit")
    write_private_json(
        output / "history_profile.json",
        {
            "audit_version": "development_history_candidates_v1",
            "protocol_sha256": PROTOCOL_SHA,
            "source_hashes": {
                role: source["sources"][role]["sha256"] for role in ("train", "validation")
            },
            "runtime_code_sha256": {
                name: sha256(Path(__file__).with_name(name))
                for name in (
                    "freddie_history_audit.py",
                    "freddie_panel.py",
                    "freddie_preflight.py",
                    "freddie_train.py",
                )
            },
            "roles": {
                role: {
                    "eligible_observations": counts[role],
                    "features": {name: value.summary() for name, value in profiles[role].items()},
                }
                for role in ROLES
            },
            "quantile_method": (
                "Seed-42 reservoir sampling, <=2000 non-missing values per role/feature; "
                "approximate, no persisted samples"
            ),
            "label_outcomes_used": False,
            "model_fit_performed": False,
            "test_source_accessed": False,
            "scoring_release": "HOLD",
            "limitations": [
                "No proof of improved model quality; no v4 feature selection or protocol lock",
                "Corrected retrospective snapshot; operational availability is not established",
                "UPB change is a balance stock difference, not an observed cash payment",
                "No known prior delinquency and incomplete history require separate interpretation",
            ],
        },
    )


def main() -> None:
    """Launch a two-thread/15-minute/2-GiB private development audit, without fitting."""
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("manifest", "protocol", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents:
        raise ValueError("Private audit output must remain outside Git")
    require_development_sources(args.manifest, args.protocol)
    if args.worker:
        audit_worker(args.manifest, args.protocol, output)
        return
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
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
        [sys.executable, "-m", "src.research.freddie_history_audit", *sys.argv[1:], "--worker"],
        output,
        15,
        2,
        env,
    )
    write_private_json(output / "resource_report.json", result)
    if result["exit_code"] != 0 or result["abort_reason"]:
        raise SystemExit(2)
    print(
        {
            "audit_status": "COMPLETE",
            "model_fit_performed": False,
            "test_source_accessed": False,
            "scoring_release": "HOLD",
            **result,
        }
    )


if __name__ == "__main__":
    main()
