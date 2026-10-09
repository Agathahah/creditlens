"""Admission gate contracts; fixtures contain no real loan records or trained model."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from src.research.freddie_preflight import ROLES, SCOPE, assess_admission, read_object


@pytest.fixture
def admission_files(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    """Write private synthetic byte sources; the frozen source is not a ZIP."""
    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps({"scope": SCOPE, "horizon_months": 3}))
    sources = {}
    for role, vintage in ROLES.items():
        path = tmp_path / f"sample_{vintage}.zip"
        path.write_bytes(f"opaque synthetic bytes {vintage}".encode())
        sources[role] = {
            "vintage": vintage,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "scope": SCOPE,
        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "owner_review": {
            "release_binding_confirmed": True,
            "internal_research_terms_acknowledged": True,
            "retrospective_limitations_acknowledged": True,
            "experiment_protocol_approved": True,
            "reviewed_at": "2026-10-07",
        },
        "release": {"number": 47, "date": "2026-07-29", "performance_cutoff": "2026-03-31"},
        "sources": sources,
        "structural_intake": {
            "train_passed": True,
            "validation_passed": True,
            "loan_id_overlap": 0,
        },
        "point_in_time_verified": False,
        "frozen_test_opened": False,
        "validation_outcomes_inspected": False,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path, protocol, manifest


def test_complete_admission_never_releases_scoring_or_opens_zip(
    admission_files: tuple[Path, Path, dict[str, Any]],
) -> None:
    """Hash-only checks accept opaque bytes and cannot authorize model promotion."""
    path, protocol, _ = admission_files
    result = assess_admission(path, protocol)
    assert result["training_preflight"] == "ELIGIBLE_FOR_REVIEW"
    assert result["scoring_release"] == "HOLD"
    assert result["model_evaluation"] == "NOT_RUN"
    assert result["frozen_test_contents_opened_by_preflight"] is False


@pytest.mark.parametrize(
    "key,value",
    [
        ("release_binding_confirmed", False),
        ("experiment_protocol_approved", "true"),
        ("internal_research_terms_acknowledged", 1),
        ("retrospective_limitations_acknowledged", None),
    ],
)
def test_review_requires_explicit_booleans(
    admission_files: tuple[Path, Path, dict[str, Any]], key: str, value: Any
) -> None:
    """Implicit truthy values cannot satisfy the recorded owner review."""
    path, protocol, manifest = admission_files
    manifest["owner_review"][key] = value
    path.write_text(json.dumps(manifest))
    assert key in assess_admission(path, protocol)["blockers"]


@pytest.mark.parametrize("role", list(ROLES))
def test_changed_source_is_blocked(
    admission_files: tuple[Path, Path, dict[str, Any]], role: str
) -> None:
    """Changing any source, including opaque frozen bytes, invalidates identity."""
    path, protocol, manifest = admission_files
    Path(manifest["sources"][role]["path"]).write_bytes(b"changed")
    assert f"{role}_hash_mismatch" in assess_admission(path, protocol)["blockers"]


def test_changed_protocol_and_overlap_block_admission(
    admission_files: tuple[Path, Path, dict[str, Any]],
) -> None:
    """The exact approved protocol and loan isolation are prerequisites."""
    path, protocol, manifest = admission_files
    protocol.write_text(json.dumps({"scope": SCOPE, "horizon_months": 6}))
    manifest["structural_intake"]["loan_id_overlap"] = 1
    path.write_text(json.dumps(manifest))
    blockers = assess_admission(path, protocol)["blockers"]
    assert "protocol_hash_mismatch" in blockers
    assert "unsupported_protocol_scope" in blockers
    assert "structural_intake_or_loan_overlap_unresolved" in blockers


@pytest.mark.parametrize(
    "change,blocker",
    [
        ({"frozen_test_opened": True}, "frozen_test_not_sealed"),
        ({"validation_outcomes_inspected": True}, "validation_inspected_before_protocol_lock"),
        ({"point_in_time_verified": True}, "retrospective_scope_requires_explicit_pit_limitation"),
        ({"release": {}}, "release_metadata_mismatch"),
        ({"owner_review": {"reviewed_at": "2100-01-01"}}, "owner_review_date_in_future"),
    ],
)
def test_scope_and_time_claims_fail_closed(
    admission_files: tuple[Path, Path, dict[str, Any]], change: dict[str, Any], blocker: str
) -> None:
    """Opened outcomes or unsupported claims cannot silently pass review."""
    path, protocol, original = admission_files
    manifest = copy.deepcopy(original)
    manifest.update(change)
    path.write_text(json.dumps(manifest))
    assert blocker in assess_admission(path, protocol)["blockers"]


@pytest.mark.parametrize("raw", ['{"scope":1,"scope":2}', '{"value":NaN}', "[]"])
def test_ambiguous_json_is_rejected(tmp_path: Path, raw: str) -> None:
    """Malformed approval JSON must not be interpreted permissively."""
    path = tmp_path / "invalid.json"
    path.write_text(raw)
    with pytest.raises(ValueError):
        read_object(path)
