"""Contracts for private M1 source inspection, using tiny synthetic files."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from scripts import inspect_m1_source
from scripts.inspect_m1_source import discover_sources, inspect_source, main


def test_no_source_returns_explicit_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing data must be visible and stop a chained workflow."""
    assert main(["--directory", str(tmp_path)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "MISSING_SOURCE"
    assert report["ready_for_training"] is False


def test_missing_selected_file_is_controlled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing path produces structured failure rather than an uncaught traceback."""
    assert main(["--file", str(tmp_path / "missing.csv.gz")]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "INVALID_SOURCE"
    assert "sha256" not in report


def test_inventory_only_lists_supported_candidates(tmp_path: Path) -> None:
    """Inventory is limited to the selected directory and supported files."""
    (tmp_path / "a.csv").touch()
    (tmp_path / "b.csv.gz").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "nested.csv").mkdir()
    assert [path.name for path in discover_sources(tmp_path)] == ["a.csv", "b.csv.gz"]


@pytest.mark.parametrize("compressed", [False, True])
def test_valid_header_never_admits_source(tmp_path: Path, compressed: bool) -> None:
    """Correct byte identity/header evidence must not imply data or training acceptance."""
    raw = "\ufeffloan_id,issue_d,loan_status\n1,2016-01,private_fixture_value\n".encode()
    path = tmp_path / ("new.csv.gz" if compressed else "new.csv")
    path.write_bytes(gzip.compress(raw) if compressed else raw)
    report = inspect_source(path)
    assert report["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert report["column_count"] == 3
    assert report["source_admitted"] is False
    assert report["ready_for_training"] is False
    assert report["row_count"] is None
    assert "private_fixture_value" not in json.dumps(report)


@pytest.mark.parametrize("raw", [b"", b"id,id\n", b"id,\n"])
def test_ambiguous_header_is_rejected(tmp_path: Path, raw: bytes) -> None:
    """Empty or ambiguous headers cannot be used as valid schema evidence."""
    path = tmp_path / "invalid.csv"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        inspect_source(path)


def test_corrupt_gzip_is_controlled(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Corrupt compression cannot produce a successful inspection."""
    path = tmp_path / "corrupt.csv.gz"
    path.write_bytes(b"not a gzip file")
    assert main(["--file", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "INVALID_SOURCE"


def test_renamed_old_snapshot_remains_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Renaming a known snapshot must not make it an independent source."""
    path = tmp_path / "apparently_new.csv"
    path.write_bytes(b"id,issue_d\n1,2015-01\n")
    monkeypatch.setattr(
        inspect_m1_source, "KNOWN_SNAPSHOT_SHA256", hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert main(["--file", str(path)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "KNOWN_OLD_SNAPSHOT"
    assert report["ready_for_training"] is False
