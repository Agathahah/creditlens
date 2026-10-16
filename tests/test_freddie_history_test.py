"""V4 test consumption and immutable candidate guards, using only synthetic evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.research.freddie_history_test import (
    authorize_access,
    consume_test,
    execution_code_hash,
)

ROOT = Path(__file__).resolve().parents[1]


def test_consumption_is_global_private_and_never_reset_on_failure(tmp_path: Path) -> None:
    """A retry cannot restore the independence of a consumed vintage."""
    marker = tmp_path / "frozen_test_consumed_2022.json"
    contract = {"candidate_sha256": "synthetic", "test_source_sha256": "opaque"}
    consume_test(marker, contract)
    before = marker.read_bytes()
    x = json.loads(before)
    assert x["test_vintage"] == 2022 and x["consumed"] is True
    assert marker.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        consume_test(marker, contract)
    assert marker.read_bytes() == before


def test_changed_execution_is_rejected_before_source_or_candidate_read(tmp_path: Path) -> None:
    """An arbitrary contract cannot open any archive, even with a valid v4 protocol."""
    execution = tmp_path / "execution.json"
    execution.write_text("{}")
    with pytest.raises(ValueError, match="contracts"):
        authorize_access(
            tmp_path / "never-read-run",
            ROOT / "config/research/freddie_experiment_v4.json",
            execution,
            tmp_path / "never-read-manifest.json",
        )
    assert not (tmp_path / "frozen_test_consumed_2022.json").exists()


def test_execution_logic_hash_is_stable_and_sha256_shaped() -> None:
    """Executor code is bound separately from the literal hash it checks."""
    x = execution_code_hash()
    assert len(x) == 64 and int(x, 16) >= 0
    assert execution_code_hash() == x


def test_ledger_under_repository_is_rejected_before_creation() -> None:
    marker = ROOT / "test-ledger-should-not-exist.json"
    with pytest.raises(ValueError, match="private"):
        consume_test(marker, {"candidate_sha256": "fixture", "test_source_sha256": "fixture"})
    assert not marker.exists()
