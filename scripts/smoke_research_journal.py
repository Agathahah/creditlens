"""Verify private Docker journal persistence, write failure and backup recovery on toy evidence."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from scripts.research_image_source_hash import source_tree_sha256
from scripts.research_journal_backup import (
    _fresh_directory,
    assert_preserved,
    backup_journal,
    inspect_journal,
    restore_journal,
)
from scripts.smoke_research_api import (
    ROOT,
    _docker,
    _probe,
    _require_score,
    _start,
    _wait_ready,
    _write,
    stage_bundle,
)
from src.research.freddie_monitoring import private_file
from src.research.freddie_preflight import sha256

READONLY_PROBE = r"""
import errno
from pathlib import Path
for folder in ('/app', '/run/research'):
    try:
        (Path(folder) / 'must-not-write').touch(exist_ok=False)
    except OSError as error:
        assert error.errno in (errno.EROFS, errno.EACCES)
    else:
        raise RuntimeError('Read-only boundary allowed a write')
assert not Path('/run/audit/link_key.bin').exists()
print('read-only-verified')
"""


def _persisted(path: Path, request_id: str, probability: float) -> None:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT status,probability FROM events WHERE request_id=?", (request_id,)
        ).fetchone()
    if row is None or row[0] != 200 or abs(row[1] - probability) > 1e-12:
        raise ValueError("Successful HTTP request missing from committed journal")


def run_journal_acceptance(
    image: str,
    bundle: Path,
    token: Path,
    snapshot: Path,
    monitoring_receipt: Path,
    output: Path,
    origin: str = "local_command_unverified_identity",
) -> dict[str, Any]:
    """Exercise isolated writable state and recovery without mutating original owner evidence.

    Args:
        image: Existing software-only image ID or locally resolved tag.
        bundle: Accepted owner-only private model manifest, never modified.
        token: Existing bearer credential file, never printed or backed up with the journal.
        snapshot: Explicitly synthetic monthly model input.
        monitoring_receipt: Successful toy monitoring receipt and sibling journal/link key.
        output: Fresh private evidence directory outside Git.
        origin: Assistant check or an unverified local command identity.

    Returns:
        Acceptance receipt only after persistence, negative write and recovery checks pass.

    Raises:
        ValueError: Scope, metadata, persistence, parity, restore or ownership mismatch.
        sqlite3.Error: Invalid journal or snapshot.
    """
    private_file(monitoring_receipt)
    prior = json.loads(monitoring_receipt.read_text())
    original = monitoring_receipt.parent / "audit.sqlite"
    key = monitoring_receipt.parent / "link_key.bin"
    private_file(original)
    private_file(key)
    if (
        prior.get("status") != "PASS_REAL_INFERENCE_SYNTHETIC_MONITORING"
        or prior.get("purpose") != "SYNTHETIC_MONITORING_PLUMBING_ONLY"
        or prior.get("operational_quality_verified") is not False
        or sha256(original) != prior.get("journal_sha256")
        or os.getuid() == 0
        or shutil.disk_usage(ROOT).free < 8 * 1024**3
    ):
        raise ValueError("Matching completed synthetic evidence, non-root and free space required")
    _fresh_directory(output)
    receipt: dict[str, Any] = {
        "status": "RUNNING",
        "started_at": datetime.now(UTC).isoformat(),
        "production_scoring_release": "HOLD",
        "operational_quality_verified": False,
        "source_archives_opened": False,
        "training_or_test_rerun": False,
        "purpose": "LOCAL_SYNTHETIC_JOURNAL_RECOVERY_ONLY",
        "monitoring_receipt_sha256": sha256(monitoring_receipt),
        "original_journal_sha256": sha256(original),
        "original_key_sha256": sha256(key),
        "verification_script_sha256": sha256(Path(__file__)),
        "backup_implementation_sha256": sha256(ROOT / "scripts/research_journal_backup.py"),
    }
    owner, names = uuid4().hex, []
    live = output / "seed-state/state/audit.sqlite"
    try:
        native = stage_bundle(bundle, token, snapshot, output / "package")
        receipt.update(
            container_helper_sha256=sha256(ROOT / "scripts/smoke_research_api.py"),
            original_bundle_sha256=sha256(bundle),
            synthetic_snapshot_sha256=sha256(snapshot),
            candidate_sha256=json.loads((output / "package/bundle_manifest.json").read_text())[
                "candidate_sha256"
            ],
        )
        inspected = json.loads(_docker("image", "inspect", image).stdout)[0]
        image_id = inspected["Id"]
        labels = inspected["Config"]["Labels"]
        if labels.get("org.creditlens.scope") != "private-mortgage-research" or labels.get(
            "org.creditlens.source-tree-sha256"
        ) != source_tree_sha256(ROOT):
            raise ValueError("Image public source identity mismatch")
        model_id = json.loads((output / "package/bundle_manifest.json").read_text())["model_id"]
        seed = backup_journal(original, key, output / "seed-backup")
        restore_journal(output / "seed-backup", output / "seed-state")
        first = "creditlens-journal-" + owner + "-first"
        names.append(first)
        _start(image_id, output / "package", first, owner, live.parent)
        ready = _wait_ready(first)
        if ready["body"].get("audit_enabled") is not True:
            raise ValueError("Audited readiness required")
        actual = _probe(first, "score")
        _require_score(actual, native, model_id)
        first_id = actual["body"]["request_id"]
        _persisted(live, first_id, native)
        before_restart = inspect_journal(live)
        _docker("stop", "--time", "10", first)
        _docker("rm", first)
        restarted = "creditlens-journal-" + owner + "-recreated"
        names.append(restarted)
        _start(image_id, output / "package", restarted, owner, live.parent)
        _wait_ready(restarted)
        assert_preserved(live, before_restart)
        _persisted(live, first_id, native)
        second = _probe(restarted, "score")
        _require_score(second, native, model_id)
        _persisted(live, second["body"]["request_id"], native)
        runtime = json.loads(_docker("inspect", restarted).stdout)[0]
        binds = {m["Destination"]: m["RW"] for m in runtime["Mounts"] if m["Type"] == "bind"}
        host = runtime["HostConfig"]
        if (
            binds != {"/run/research": False, "/run/audit": True}
            or host["NetworkMode"] != "none"
            or not host["ReadonlyRootfs"]
            or runtime["NetworkSettings"]["Ports"]
            or runtime["Config"]["User"] != f"{os.getuid()}:{os.getgid()}"
            or host["CapDrop"] != ["ALL"]
            or "no-new-privileges" not in host["SecurityOpt"]
            or host["Memory"] != 2 * 1024**3
            or host["NanoCpus"] != 2 * 10**9
            or host["PidsLimit"] != 128
            or runtime["Config"]["Healthcheck"]["Test"] != ["NONE"]
        ):
            raise ValueError("Writable-state container isolation mismatch")
        guards = _docker("exec", restarted, "python", "-c", READONLY_PROBE)
        if guards.stdout.strip() != "read-only-verified":
            raise ValueError("Read-only mount and key-isolation check failed")
        # Docker Desktop bind permissions may not enforce a chmod-only fault.
        # Withdraw only this disposable copy; preserve both the original and fault output.
        held = live.with_name("audit.before-storage-fault.sqlite")
        live.rename(held)
        try:
            blocked = _probe(restarted, "score")
            if blocked["status"] != 503 or "probability" in blocked["body"]:
                raise ValueError("Unavailable journal did not hold successful scoring")
        finally:
            if live.exists():
                failed_file = live.with_name("audit.failed-write.sqlite")
                live.rename(failed_file)
                failed_file.chmod(0o600)
            held.rename(live)
        recovered_write = _probe(restarted, "score")
        _require_score(recovered_write, native, model_id)
        _persisted(live, recovered_write["body"]["request_id"], native)
        backup_started = time.monotonic()
        manifest = backup_journal(live, output / "seed-state/link_key.bin", output / "live-backup")
        backup_seconds = time.monotonic() - backup_started
        after_backup = _probe(restarted, "score")
        _require_score(after_backup, native, model_id)
        after_id = after_backup["body"]["request_id"]
        _persisted(live, after_id, native)
        _docker("stop", "--time", "10", restarted)
        later_events = (
            inspect_journal(live)["tables"]["events"]["rows"]
            - manifest["snapshot"]["tables"]["events"]["rows"]
        )
        recovery_started = time.monotonic()
        restored_snapshot = restore_journal(output / "live-backup", output / "recovered")
        recovered_db = output / "recovered/state/audit.sqlite"
        if restored_snapshot != manifest["snapshot"]:
            raise ValueError("Recovered rows differ from backup recovery point")
        with closing(sqlite3.connect(recovered_db)) as connection:
            if connection.execute(
                "SELECT 1 FROM events WHERE request_id=?", (after_id,)
            ).fetchone():
                raise ValueError("Post-backup request unexpectedly included in recovered state")
        restored = "creditlens-journal-" + owner + "-restored"
        names.append(restored)
        _start(image_id, output / "package", restored, owner, recovered_db.parent)
        _wait_ready(restored)
        assert_preserved(recovered_db, restored_snapshot)
        final = _probe(restored, "score")
        _require_score(final, native, model_id)
        _persisted(recovered_db, final["body"]["request_id"], native)
        recovery_seconds = time.monotonic() - recovery_started
        corrupt = output / "corrupt-backup"
        shutil.copytree(output / "live-backup", corrupt)
        with (corrupt / "journal.sqlite").open("ab") as handle:
            handle.write(b"synthetic-corruption-detection-check")
        rejected = False
        try:
            restore_journal(corrupt, output / "must-not-restore")
        except ValueError:
            rejected = True
        if not rejected or (output / "must-not-restore").exists():
            raise ValueError("Corrupt backup admitted or created recovery target")
        if (
            sha256(original) != receipt["original_journal_sha256"]
            or sha256(key) != receipt["original_key_sha256"]
        ):
            raise ValueError("Original owner evidence changed")
        receipt.update(
            status="PASS_LOCAL_JOURNAL_PERSISTENCE_RECOVERY",
            image_id=image_id,
            public_source_sha256=labels["org.creditlens.source-tree-sha256"],
            seed_snapshot=seed["snapshot"],
            before_restart=before_restart,
            backup_snapshot=manifest["snapshot"],
            final_snapshot=inspect_journal(recovered_db),
            backup_manifest_sha256=sha256(output / "live-backup/backup_manifest.json"),
            earlier_rows_preserved_after_recreation=True,
            readonly_root_and_model_write_rejected=True,
            hmac_key_not_mounted_in_api=True,
            journal_write_failure_http=503,
            writes_resumed_after_storage_repair=True,
            storage_fault="test_copy_journal_temporarily_withdrawn",
            corrupt_backup_rejected=True,
            first_persisted_request_id=first_id,
            post_backup_request_excluded_from_recovery=after_id,
            restored_persisted_request_id=final["body"]["request_id"],
            backup_seconds=backup_seconds,
            local_restore_to_persisted_score_seconds=recovery_seconds,
            backup_point_data_loss_accounted_for=True,
            events_after_backup_not_recovered=later_events,
            zero_data_loss_claimed=False,
            authentic_operational_outcomes_verified=False,
            off_host_disaster_recovery_verified=False,
            execution_origin=origin,
        )
    except BaseException as error:
        receipt.update(status="FAILED", failure_type=type(error).__name__)
        raise
    finally:
        failed = []
        for name in names:
            try:
                found = _docker("inspect", name, check=False)
                if found.returncode:
                    continue
                info = json.loads(found.stdout)[0]
                if info["Config"]["Labels"].get("creditlens.acceptance") != owner:
                    failed.append(name)
                    continue
                logs = _docker("logs", name, check=False)
                safe = (logs.stdout + logs.stderr).replace(token.read_text().strip(), "[REDACTED]")
                log_file = output / (name.rsplit("-", 1)[-1] + ".log")
                log_file.write_text(safe)
                log_file.chmod(0o600)
                if _docker("rm", "--force", name, check=False).returncode:
                    failed.append(name)
            except Exception:
                failed.append(name)
        receipt["test_owned_containers_removed"] = not failed
        if failed:
            receipt["status"] = "FAILED_CLEANUP"
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        _write(output / "receipt.json", receipt)
    if receipt["status"] != "PASS_LOCAL_JOURNAL_PERSISTENCE_RECOVERY":
        raise ValueError("Persistence/recovery or owned cleanup failed")
    return receipt


def main() -> None:
    """Run only explicitly declared synthetic local persistence/recovery acceptance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    for option in ("bundle", "token-file", "snapshot", "monitoring-receipt", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    parser.add_argument("--confirm-synthetic", required=True, action="store_true")
    parser.add_argument("--assistant-check", action="store_true")
    args = parser.parse_args()
    run_journal_acceptance(
        args.image,
        args.bundle,
        args.token_file,
        args.snapshot,
        args.monitoring_receipt,
        args.output,
        "assistant_check" if args.assistant_check else "local_command_unverified_identity",
    )
    print("Berhasil: jurnal Docker persisten, penolakan saat gagal tulis, backup dan restore.")
    print("Bukti privat:", args.output / "receipt.json")


if __name__ == "__main__":
    main()
