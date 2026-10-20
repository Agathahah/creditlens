"""Synthetic backup/restore integrity, private boundaries and append-only persistence contracts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from scripts.research_journal_backup import (
    assert_preserved,
    backup_journal,
    inspect_journal,
    restore_journal,
)
from src.research.freddie_monitoring import AuditStore

NOW = datetime(2026, 10, 20, tzinfo=UTC)
KEY = b"synthetic-separated-link-key-32bytes"


def add_event(store: AuditStore) -> str:
    """Append one toy committed score without source data or actual credentials."""
    request_id = str(uuid4())
    store.record(request_id, NOW, "POST", "/score", 200, 1.0, "toy", "a" * 64, 0.1)
    return request_id


@pytest.fixture
def journal(tmp_path: Path) -> tuple[AuditStore, Path]:
    tmp_path.chmod(0o700)
    store = AuditStore(tmp_path / "audit.sqlite")
    request_id = add_event(store)
    store.link(request_id, "toy-loan", "202609", NOW, KEY)
    key = tmp_path / "link_key.bin"
    key.write_bytes(KEY)
    key.chmod(0o600)
    return store, key


def test_backup_restore_preserves_rows_key_and_original_then_allows_new_events(
    journal: tuple[AuditStore, Path], tmp_path: Path
) -> None:
    store, key = journal
    original = hashlib.sha256(store.path.read_bytes()).hexdigest()
    before = inspect_journal(store.path)
    manifest = backup_journal(store.path, key, tmp_path / "backup")
    assert manifest["snapshot"] == before
    assert hashlib.sha256(store.path.read_bytes()).hexdigest() == original
    recovered = tmp_path / "recovered"
    assert restore_journal(tmp_path / "backup", recovered) == before
    assert (recovered / "link_key.bin").read_bytes() == KEY
    assert not (recovered / "state/link_key.bin").exists()
    restored = AuditStore(recovered / "state/audit.sqlite")
    retry = add_event(restored)
    assert (
        restored.link(retry, "toy-loan", "202609", NOW, (recovered / "link_key.bin").read_bytes())
        != retry
    )
    assert_preserved(restored.path, before)
    with pytest.raises(ValueError, match="Fresh directory"):
        restore_journal(tmp_path / "backup", recovered)
    assert_preserved(restored.path, before)
    assert all(p.stat().st_mode & 0o077 == 0 for p in recovered.rglob("*"))
    assert not any(p.suffix in (".joblib", ".zip") for p in (tmp_path / "backup").iterdir())


@pytest.mark.parametrize("target", ["journal.sqlite", "link_key.bin", "backup_manifest.json"])
def test_corrupt_backup_components_rejected_before_creating_restore_target(
    journal: tuple[AuditStore, Path], tmp_path: Path, target: str
) -> None:
    store, key = journal
    backup = tmp_path / "backup"
    backup_journal(store.path, key, backup)
    path = backup / target
    if target == "backup_manifest.json":
        data = json.loads(path.read_text())
        data["snapshot"]["tables"]["events"]["rows"] += 1
        path.write_text(json.dumps(data))
    else:
        with path.open("ab") as handle:
            handle.write(b"corrupt")
    with pytest.raises(ValueError):
        restore_journal(backup, tmp_path / "recovery")
    assert not (tmp_path / "recovery").exists()


@pytest.mark.parametrize("mutation", ["schema", "columns", "foreign_key", "key", "permissions"])
def test_unknown_schema_broken_identity_and_private_permissions_cannot_publish_backup(
    journal: tuple[AuditStore, Path], tmp_path: Path, mutation: str
) -> None:
    store, key = journal
    if mutation == "key":
        key.write_bytes(b"wrong-key-that-is-still-long-enough-to-be-valid")
    elif mutation == "permissions":
        key.chmod(0o644)
    else:
        with sqlite3.connect(store.path) as connection:
            if mutation == "schema":
                connection.execute("PRAGMA user_version=7")
            elif mutation == "columns":
                connection.execute("ALTER TABLE events ADD COLUMN invalid TEXT")
            else:
                connection.execute("DELETE FROM events")
    with pytest.raises(ValueError):
        backup_journal(store.path, key, tmp_path / "backup")
    assert not (tmp_path / "backup/backup_manifest.json").exists()


def test_changed_or_deleted_prior_row_fails_persistence_gate(
    journal: tuple[AuditStore, Path],
) -> None:
    store, _ = journal
    before = inspect_journal(store.path)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE events SET probability=0.9")
    with pytest.raises(ValueError, match="changed or disappeared"):
        assert_preserved(store.path, before)


def test_snapshot_is_consistent_while_another_client_appends(
    journal: tuple[AuditStore, Path], tmp_path: Path
) -> None:
    store, key = journal
    for _ in range(100):
        add_event(store)
    errors: list[BaseException] = []
    active = threading.Event()

    def writer() -> None:
        try:
            active.set()
            for _ in range(30):
                add_event(store)
                time.sleep(0.002)
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=writer)
    thread.start()
    assert active.wait(2)
    try:
        manifest = backup_journal(store.path, key, tmp_path / "live-backup")
    finally:
        thread.join(timeout=5)
    assert not thread.is_alive() and not errors
    assert 101 <= manifest["snapshot"]["tables"]["events"]["rows"] <= 131
    assert manifest["snapshot"]["tables"]["contexts"]["rows"] == 1
    assert restore_journal(tmp_path / "live-backup", tmp_path / "recovered") == manifest["snapshot"]


def test_invalid_bounds_and_symlink_cannot_be_used(
    journal: tuple[AuditStore, Path], tmp_path: Path
) -> None:
    store, key = journal
    with pytest.raises(ValueError, match="watermarks"):
        inspect_journal(store.path, {"events": -1})
    link = tmp_path / "linked.sqlite"
    link.symlink_to(store.path)
    with pytest.raises(ValueError, match="Regular owner-only"):
        backup_journal(link, key, tmp_path / "backup")


def test_audited_container_mount_does_not_expose_key_and_preserves_readonly_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.smoke_research_api import _start
    from scripts.smoke_research_journal import READONLY_PROBE

    compile(READONLY_PROBE, "readonly-probe", "exec")

    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr("scripts.smoke_research_api._docker", lambda *args: calls.append(args))
    _start("sha256:toy", tmp_path / "package", "owned", "owner", tmp_path / "state")
    args = calls[0]
    assert f"type=bind,src={tmp_path / 'state'},dst=/run/audit" in args
    assert f"type=bind,src={tmp_path / 'package'},dst=/run/research,readonly" in args
    assert "--audit-db" in args and "--no-healthcheck" in args
    assert "link_key.bin" not in " ".join(str(a) for a in args)


def test_failed_drill_preserves_original_and_never_writes_a_pass_receipt(
    journal: tuple[AuditStore, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.smoke_research_journal import run_journal_acceptance

    store, key = journal
    original = hashlib.sha256(store.path.read_bytes()).hexdigest()
    receipt = tmp_path / "monitoring_receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "status": "PASS_REAL_INFERENCE_SYNTHETIC_MONITORING",
                "purpose": "SYNTHETIC_MONITORING_PLUMBING_ONLY",
                "operational_quality_verified": False,
                "journal_sha256": original,
            }
        )
    )
    receipt.chmod(0o600)
    monkeypatch.setattr("scripts.smoke_research_journal.os.getuid", lambda: 501)
    monkeypatch.setattr(
        "scripts.smoke_research_journal.shutil.disk_usage",
        lambda _: type("Disk", (), {"free": 10 * 1024**3})(),
    )
    for name in ("bundle", "token", "snapshot"):
        artifact = tmp_path / name
        artifact.write_text("synthetic fixture input")
        artifact.chmod(0o600)

    def staged_fixture(*args: Any) -> float:
        output = args[-1]
        output.mkdir(mode=0o700)
        (output / "bundle_manifest.json").write_text(json.dumps({"candidate_sha256": "a" * 64}))
        return 0.1

    monkeypatch.setattr("scripts.smoke_research_journal.stage_bundle", staged_fixture)

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("synthetic image failure")

    monkeypatch.setattr("scripts.smoke_research_journal._docker", fail)
    output = tmp_path / "failed"
    with pytest.raises(ValueError, match="image failure"):
        run_journal_acceptance(
            "toy", tmp_path / "bundle", tmp_path / "token", tmp_path / "snapshot", receipt, output
        )
    result = json.loads((output / "receipt.json").read_text())
    assert result["status"] == "FAILED"
    assert result["test_owned_containers_removed"] is True
    assert hashlib.sha256(store.path.read_bytes()).hexdigest() == original
    assert key.read_bytes() == KEY
