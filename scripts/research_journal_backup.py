"""Bounded owner-only SQLite snapshot and fresh-directory restore for research journals."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.research.freddie_monitoring import MAX_BYTES, MAX_EVENTS, ROOT, private_file

COLUMNS = {
    "events": [
        "request_id",
        "started_at",
        "method",
        "route",
        "status",
        "latency_ms",
        "model_id",
        "model_sha",
        "probability",
    ],
    "contexts": [
        "request_id",
        "model_sha",
        "key_id",
        "loan_ref",
        "as_of_period",
        "prediction_time",
        "linked_at",
        "source_kind",
    ],
    "outcomes": [
        "sequence",
        "request_id",
        "evidence_sha",
        "label",
        "reason",
        "label_available_at",
        "report_as_of",
    ],
}


def _fresh_directory(path: Path) -> None:
    resolved = path.resolve()
    if (
        ROOT == resolved
        or ROOT in resolved.parents
        or path.exists()
        or path.is_symlink()
        or not path.parent.is_dir()
        or path.parent.stat().st_mode & 0o077
    ):
        raise ValueError("Fresh directory below an owner-only parent outside Git required")
    path.mkdir(mode=0o700)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> sqlite3.Connection:
    private_file(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Journal exceeds database size limit")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    connection.execute("PRAGMA query_only=ON")
    return connection


def inspect_journal(path: Path, bounds: dict[str, int] | None = None) -> dict[str, Any]:
    """Fingerprint a consistent read transaction and optionally an earlier append-only prefix.

    Args:
        path: Existing bounded owner-only SQLite journal outside Git.
        bounds: Optional earlier rowid watermarks for the three fixed journal tables.

    Returns:
        Schema, logical row fingerprints, counts, watermarks and HMAC key identities.

    Raises:
        ValueError: Unknown schema, integrity/foreign-key failure, capacity or invalid bounds.
        sqlite3.Error: Invalid or unavailable SQLite source.
    """
    if bounds is not None and (
        set(bounds) != set(COLUMNS) or any(type(v) is not int or v < 0 for v in bounds.values())
    ):
        raise ValueError("Exact nonnegative table watermarks required")
    with closing(_read(path)) as connection:
        connection.execute("BEGIN")
        tables = {
            r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if connection.execute("PRAGMA user_version").fetchone()[0] != 1 or tables != set(COLUMNS):
            raise ValueError("Unsupported journal schema")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Journal integrity failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Journal foreign-key integrity failed")
        result: dict[str, Any] = {"schema_version": 1, "tables": {}}
        for table, expected in COLUMNS.items():
            columns = [r[1] for r in connection.execute(f"PRAGMA table_info({table})")]
            if columns != expected:
                raise ValueError("Journal column contract mismatch")
            maximum = connection.execute(f"SELECT COALESCE(MAX(rowid),0) FROM {table}").fetchone()[
                0
            ]
            watermark = bounds[table] if bounds is not None else maximum
            digest = hashlib.sha256()
            count = 0
            for row in connection.execute(
                f"SELECT rowid,* FROM {table} WHERE rowid<=? ORDER BY rowid", (watermark,)
            ):
                digest.update(
                    json.dumps(list(row), allow_nan=False, separators=(",", ":")).encode()
                )
                digest.update(b"\n")
                count += 1
            if table == "events" and count > MAX_EVENTS:
                raise ValueError("Journal event capacity exceeded")
            result["tables"][table] = {
                "rows": count,
                "watermark": watermark,
                "sha256": digest.hexdigest(),
            }
        result["key_ids"] = sorted(
            r[0] for r in connection.execute("SELECT DISTINCT key_id FROM contexts")
        )
        return result


def assert_preserved(path: Path, earlier: dict[str, Any]) -> None:
    """Require every earlier row to remain identical while permitting later append-only events.

    Args:
        path: Current journal after restart or recovery.
        earlier: Earlier full logical snapshot from inspect_journal.

    Raises:
        ValueError: Any earlier row or its identity/count changed or disappeared.
    """
    bounds = {table: int(item["watermark"]) for table, item in earlier["tables"].items()}
    current = inspect_journal(path, bounds)
    if current["tables"] != earlier["tables"]:
        raise ValueError("Earlier journal rows changed or disappeared")


def _copy_database(source: Path, target: Path) -> None:
    # Exclusive destination creation and owner permissions precede SQLite access.
    with target.open("xb"):
        target.chmod(0o600)
    deadline = time.monotonic() + 20

    def progress(status: int, remaining: int, total: int) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError("SQLite backup time limit reached")

    with closing(_read(source)) as src, closing(sqlite3.connect(target, timeout=2)) as dst:
        src.backup(dst, pages=64, progress=progress, sleep=0.05)


def _key(path: Path, snapshot: dict[str, Any]) -> bytes:
    private_file(path)
    if not 32 <= path.stat().st_size <= 4096:
        raise ValueError("Bounded separate HMAC key required")
    key = path.read_bytes()
    if snapshot["key_ids"] and snapshot["key_ids"] != [hashlib.sha256(key).hexdigest()]:
        raise ValueError("HMAC key does not cover all journal contexts")
    return key


def backup_journal(database: Path, key_file: Path, output: Path) -> dict[str, Any]:
    """Create a verified consistent snapshot and matching HMAC key in a fresh private directory.

    Args:
        database: Existing private journal, potentially used by a live API.
        key_file: Separate owner-only linking key, never an API bearer credential.
        output: New private backup directory outside Git.

    Returns:
        Verified manifest; completion follows integrity, logical schema and key validation.

    Raises:
        ValueError: Boundary, schema or key mismatch; existing output is never overwritten.
        sqlite3.Error: Snapshot operation or source integrity failure.
    """
    inspect_journal(database)
    private_file(key_file)
    _fresh_directory(output)
    started = datetime.now(UTC).isoformat()
    destination = output / "journal.sqlite"
    _copy_database(database, destination)
    snapshot = inspect_journal(destination)
    key = _key(key_file, snapshot)
    copied_key = output / "link_key.bin"
    with copied_key.open("xb") as handle:
        copied_key.chmod(0o600)
        handle.write(key)
    manifest = {
        "status": "VERIFIED_SQLITE_BACKUP",
        "backup_version": 1,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "database_sha256": _hash(destination),
        "key_sha256": _hash(copied_key),
        "snapshot": snapshot,
        "production_scoring_release": "HOLD",
    }
    target = output / "backup_manifest.json"
    with target.open("x") as handle:
        target.chmod(0o600)
        handle.write(json.dumps(manifest, indent=2) + "\n")
    return manifest


def restore_journal(backup: Path, output: Path) -> dict[str, Any]:
    """Verify a trusted owner backup and restore only into a new private state directory.

    Args:
        backup: Existing directory containing the fixed manifest/database/key filenames.
        output: New recovery directory; no active or previous journal can be overwritten.

    Returns:
        Restored logical fingerprint, matching the verified backup before new requests.

    Raises:
        ValueError: Tampering, incomplete backup, key/schema mismatch or unsafe destination.
        sqlite3.Error: Corrupt backup or failed restore.
    """
    manifest_path = backup / "backup_manifest.json"
    private_file(manifest_path)
    if manifest_path.stat().st_size > 65536:
        raise ValueError("Bounded backup manifest required")
    manifest = json.loads(manifest_path.read_text())
    database, key_file = backup / "journal.sqlite", backup / "link_key.bin"
    for path in (database, key_file):
        private_file(path)
    if database.stat().st_size > MAX_BYTES or not 32 <= key_file.stat().st_size <= 4096:
        raise ValueError("Bounded database and HMAC key required")
    if (
        manifest.get("status") != "VERIFIED_SQLITE_BACKUP"
        or manifest.get("backup_version") != 1
        or manifest.get("database_sha256") != _hash(database)
        or manifest.get("key_sha256") != _hash(key_file)
    ):
        raise ValueError("Backup checksum or version mismatch")
    snapshot = inspect_journal(database)
    if snapshot != manifest.get("snapshot"):
        raise ValueError("Backup logical manifest mismatch")
    key = _key(key_file, snapshot)
    _fresh_directory(output)
    (output / "state").mkdir(mode=0o700)
    target = output / "state/audit.sqlite"
    _copy_database(database, target)
    restored = inspect_journal(target)
    if restored != snapshot:
        raise ValueError("Restored journal differs from backup")
    copied_key = output / "link_key.bin"
    with copied_key.open("xb") as handle:
        copied_key.chmod(0o600)
        handle.write(key)
    return restored


def main() -> None:
    """Perform explicit private backup/restore without printing state, keys or credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    backup = actions.add_parser("backup")
    backup.add_argument("--database", required=True, type=Path)
    backup.add_argument("--link-key-file", required=True, type=Path)
    restore = actions.add_parser("restore")
    restore.add_argument("--backup", required=True, type=Path)
    for command in (backup, restore):
        command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "backup":
        backup_journal(args.database, args.link_key_file, args.output)
    else:
        restore_journal(args.backup, args.output)
    print("Verified private journal operation:", args.action, args.output)


if __name__ == "__main__":
    main()
