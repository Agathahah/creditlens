"""Audit private source admission without fitting models or opening test ZIP members."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

SCOPE = "freddie_mortgage_retrospective_research"
ROLES = {"train": 2018, "validation": 2019, "frozen_test": 2020}


def read_object(path: Path) -> dict[str, Any]:
    """Read a JSON object, rejecting duplicate keys and non-finite constants.

    Args:
        path: JSON manifest or protocol path.

    Returns:
        Decoded object.

    Raises:
        ValueError: Ambiguous keys, non-finite constants or a non-object root.
        OSError: File cannot be read.
    """

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> Any:
        raise ValueError("Non-finite JSON value")

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=invalid_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def sha256(path: Path) -> str:
    """Hash bytes without decompressing or inspecting an archive's records.

    Args:
        path: Source file to hash.

    Returns:
        SHA-256 hexadecimal digest.
    """
    before = path.stat()
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("File changed during hashing")
    return digest


def assess_admission(manifest_path: Path, protocol_path: Path) -> dict[str, Any]:
    """Check prerequisites for a bounded retrospective mortgage experiment.

    This advisory report is not a model-quality gate, trusted bundle signature,
    API readiness flag or deployment authorization. Owner acknowledgements are
    recorded assertions, not independent proof of licensing or source identity.

    Args:
        manifest_path: Private source and owner-review manifest.
        protocol_path: Proposed experiment JSON to be approved before training.

    Returns:
        Blockers and advisory training eligibility; scoring always remains HOLD.
    """
    manifest = read_object(manifest_path)
    protocol = read_object(protocol_path)
    blockers: list[str] = []
    if manifest.get("schema_version") != 1 or manifest.get("scope") != SCOPE:
        blockers.append("unsupported_manifest_scope")
    if protocol.get("scope") != SCOPE or protocol.get("horizon_months") != 3:
        blockers.append("unsupported_protocol_scope")
    if manifest.get("protocol_sha256") != sha256(protocol_path):
        blockers.append("protocol_hash_mismatch")
    review = manifest.get("owner_review", {})
    if not isinstance(review, dict):
        review = {}
    for key in (
        "release_binding_confirmed",
        "internal_research_terms_acknowledged",
        "retrospective_limitations_acknowledged",
        "experiment_protocol_approved",
    ):
        if review.get(key) is not True:
            blockers.append(key)
    try:
        reviewed_at = date.fromisoformat(str(review.get("reviewed_at")))
        if reviewed_at > date.today():
            blockers.append("owner_review_date_in_future")
    except ValueError:
        blockers.append("owner_review_date_missing_or_invalid")
    if manifest.get("frozen_test_opened") is not False:
        blockers.append("frozen_test_not_sealed")
    if manifest.get("validation_outcomes_inspected") is not False:
        blockers.append("validation_inspected_before_protocol_lock")
    if manifest.get("point_in_time_verified") is not False:
        blockers.append("retrospective_scope_requires_explicit_pit_limitation")
    release = manifest.get("release", {})
    if not isinstance(release, dict) or (
        release.get("number"),
        release.get("date"),
        release.get("performance_cutoff"),
    ) != (47, "2026-07-29", "2026-03-31"):
        blockers.append("release_metadata_mismatch")
    sources = manifest.get("sources", {})
    if not isinstance(sources, dict):
        sources = {}
    for role, vintage in ROLES.items():
        source = sources.get(role, {})
        if not isinstance(source, dict):
            source = {}
        if source.get("vintage") != vintage:
            blockers.append(f"{role}_vintage_mismatch")
        try:
            archive = Path(source["path"])
            if archive.stat().st_size != source.get("bytes"):
                blockers.append(f"{role}_size_mismatch")
            if sha256(archive) != source.get("sha256"):
                blockers.append(f"{role}_hash_mismatch")
        except (KeyError, TypeError, OSError, ValueError):
            blockers.append(f"{role}_source_unreadable")
    intake = manifest.get("structural_intake", {})
    if not isinstance(intake, dict) or (
        intake.get("train_passed") is not True
        or intake.get("validation_passed") is not True
        or type(intake.get("loan_id_overlap")) is not int
        or intake.get("loan_id_overlap") != 0
    ):
        blockers.append("structural_intake_or_loan_overlap_unresolved")
    return {
        "scope": SCOPE,
        "protocol_sha256": sha256(protocol_path),
        "manifest_sha256": sha256(manifest_path),
        "training_preflight": "BLOCKED" if blockers else "ELIGIBLE_FOR_REVIEW",
        "blockers": blockers,
        "scoring_release": "HOLD",
        "model_evaluation": "NOT_RUN",
        "frozen_test_contents_opened_by_preflight": False,
        "limitations": [
            "Owner review and intake fields are recorded assertions, not signatures",
            "Corrected snapshot; point-in-time operational validity is not established",
            "Model evaluation, support, bundle parity and service acceptance remain separate",
        ],
    }


def main() -> None:
    """Print advisory source admission; exit 2 when a prerequisite is unmet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = assess_admission(args.manifest, args.protocol)
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"training_preflight": "BLOCKED", "error": type(error).__name__}))
        raise SystemExit(2) from error
    print(json.dumps(report, indent=2))
    if report["blockers"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
