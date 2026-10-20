"""Private artifact staging and fail-closed container acceptance on synthetic fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from scripts.smoke_research_api import _require_score, run_acceptance, stage_bundle
from src.research.freddie_monthly_adapter import DEFAULT_PROTOCOL
from src.research.freddie_preflight import sha256
from src.research.freddie_shadow_api import RESEARCH_SCOPE


def private_json(path: Path, data: dict[str, Any]) -> Path:
    """Write an owner-only fixture without any live credential or actual loan."""
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    return path


@pytest.fixture
def artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    config = json.loads(DEFAULT_PROTOCOL.read_text())
    run = tmp_path / "validation"
    test = tmp_path / "test"
    run.mkdir()
    test.mkdir()
    candidate = run / "candidate_pipeline.joblib"
    candidate.write_bytes(b"synthetic-weights-never-deserialized")
    report = private_json(run / "validation_report.json", {"synthetic": True})
    test_report = private_json(test / "test_report.json", {"synthetic": True})
    (test / "do-not-copy.zip").write_bytes(b"must-not-stage")
    bundle = {
        "features": config["features"],
        "validation_run": str(run),
        "test_run": str(test),
        "candidate_sha256": sha256(candidate),
        "validation_report_sha256": sha256(report),
        "test_report_sha256": sha256(test_report),
        "scope": RESEARCH_SCOPE,
    }

    class Model:
        def predict_proba(self, frame: Any) -> np.ndarray[Any, Any]:
            assert list(frame.columns) == config["features"]
            assert set(frame.dtypes) == {np.dtype("float32")}
            return np.array([[0.8, 0.2]])

    monkeypatch.setattr("scripts.smoke_research_api.verify_bundle", lambda _: (bundle, Model()))
    bundle_path = private_json(tmp_path / "bundle.json", bundle)
    token = tmp_path / "token.txt"
    token.write_text("synthetic-nonsecret-fixture-credential")
    token.chmod(0o600)
    snapshot = private_json(
        tmp_path / "snapshot.json",
        {
            "loan_key": "synthetic",
            "as_of_period": "202312",
            "prediction_time": "2024-01-15T00:00:00Z",
            "origination": {
                "available_at": "2021-01-01T00:00:00Z",
                "credit_score": 700,
                "orig_cltv": 80,
                "orig_ltv": 80,
                "orig_dti": 35,
            },
            "records": [
                {
                    "loan_key": "synthetic",
                    "period": "202312",
                    "available_at": "2024-01-05T00:00:00Z",
                    "upb": 100000,
                    "dq": 0,
                    "loan_age": 36,
                    "remaining_months": 324,
                    "interest_rate": 6,
                }
            ],
        },
    )
    return bundle_path, token, snapshot


def test_stage_is_minimal_private_relocated_and_original_preserved(
    artifacts: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    bundle, token, snapshot = artifacts
    original = bundle.read_bytes()
    output = tmp_path / "package"
    assert stage_bundle(bundle, token, snapshot, output) == 0.2
    assert bundle.read_bytes() == original
    files = {str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()}
    assert files == {
        "bundle_manifest.json",
        "features.json",
        "api_token.txt",
        "validation/candidate_pipeline.joblib",
        "validation/validation_report.json",
        "test/test_report.json",
    }
    assert all(path.stat().st_mode & 0o077 == 0 for path in output.rglob("*"))
    staged = json.loads((output / "bundle_manifest.json").read_text())
    assert staged["validation_run"] == "/run/research/validation"
    assert staged["candidate_sha256"] == sha256(output / "validation/candidate_pipeline.joblib")
    assert "loan_key" not in json.loads((output / "features.json").read_text())["features"]
    with pytest.raises(FileExistsError):
        stage_bundle(bundle, token, snapshot, output)


def test_public_file_permission_is_rejected_before_staging(
    artifacts: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    bundle, token, snapshot = artifacts
    token.chmod(0o644)
    with pytest.raises(ValueError, match="Owner-only"):
        stage_bundle(bundle, token, snapshot, tmp_path / "package")
    assert not (tmp_path / "package").exists()


def test_source_checksum_mismatch_cannot_stage_a_usable_package(
    artifacts: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    bundle, token, snapshot = artifacts
    source = json.loads(bundle.read_text())
    candidate = Path(source["validation_run"]) / "candidate_pipeline.joblib"
    candidate.write_bytes(b"tampered-fixture")
    output = tmp_path / "package"
    with pytest.raises(ValueError, match="checksum"):
        stage_bundle(bundle, token, snapshot, output)
    assert not (output / "bundle_manifest.json").exists()


@pytest.mark.parametrize(
    "change", ["probability", "model", "scope", "production", "horizon", "nan", "status"]
)
def test_parity_gate_rejects_output_scope_identity_and_probability_changes(change: str) -> None:
    result: dict[str, Any] = {
        "status": 200,
        "body": {
            "model_id": "fixture",
            "scope": RESEARCH_SCOPE,
            "horizon_months": 3,
            "production_scoring_release": "HOLD",
            "public_scoring_authorized": False,
            "probability": 0.2,
        },
    }
    _require_score(result, 0.2, "fixture")
    if change == "probability":
        result["body"]["probability"] = 0.21
    elif change == "model":
        result["body"]["model_id"] = "changed"
    elif change == "scope":
        result["body"]["scope"] = "PRODUCTION"
    elif change == "production":
        result["body"]["production_scoring_release"] = "READY"
    elif change == "horizon":
        result["body"]["horizon_months"] = 6
    elif change == "nan":
        result["body"]["probability"] = float("nan")
    else:
        result["status"] = 503
    with pytest.raises(ValueError, match="parity"):
        _require_score(result, 0.2, "fixture")


def test_failed_container_run_retains_failed_receipt_without_success(
    artifacts: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, token, snapshot = artifacts
    monkeypatch.setattr("scripts.smoke_research_api.os.getuid", lambda: 501)
    monkeypatch.setattr(
        "scripts.smoke_research_api.shutil.disk_usage",
        lambda _: type("Disk", (), {"free": 10 * 1024**3})(),
    )

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("synthetic-image-failure")

    monkeypatch.setattr("scripts.smoke_research_api._docker", fail)
    output = tmp_path / "failed-run"
    with pytest.raises(ValueError, match="synthetic-image"):
        run_acceptance("fixture", bundle, token, snapshot, output)
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "FAILED"
    assert receipt["production_scoring_release"] == "HOLD"
    assert receipt["model_fitting_performed"] is False
    assert receipt["test_owned_containers_removed"] is True


@pytest.mark.parametrize("changed", ["source", "scope"])
def test_stale_or_wrong_scope_image_rejected_before_container_start(
    artifacts: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed: str,
) -> None:
    from scripts.research_image_source_hash import source_tree_sha256
    from scripts.smoke_research_api import ROOT

    bundle, token, snapshot = artifacts
    monkeypatch.setattr("scripts.smoke_research_api.os.getuid", lambda: 501)
    monkeypatch.setattr(
        "scripts.smoke_research_api.shutil.disk_usage",
        lambda _: type("Disk", (), {"free": 10 * 1024**3})(),
    )
    labels = {
        "org.creditlens.scope": "private-mortgage-research",
        "org.creditlens.source-tree-sha256": source_tree_sha256(ROOT),
    }
    labels[
        "org.creditlens.source-tree-sha256" if changed == "source" else "org.creditlens.scope"
    ] = "wrong"
    calls = []

    def inspect_only(*args: Any, **kwargs: Any) -> Any:
        calls.append(args)
        assert args == ("image", "inspect", "fixture")
        return type(
            "Result",
            (),
            {"stdout": json.dumps([{"Id": "sha256:" + "1" * 64, "Config": {"Labels": labels}}])},
        )()

    monkeypatch.setattr("scripts.smoke_research_api._docker", inspect_only)
    output = tmp_path / "wrong-image"
    with pytest.raises(ValueError, match="source identity"):
        run_acceptance("fixture", bundle, token, snapshot, output)
    assert len(calls) == 1
    assert json.loads((output / "receipt.json").read_text())["status"] == "FAILED"
