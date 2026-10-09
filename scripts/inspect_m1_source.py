"""Inspect private candidate source files without training or database access."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

KNOWN_SNAPSHOT_SHA256 = "55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d"
PENDING_EVIDENCE = (
    "provenance_and_usage_rights",
    "outcome_snapshot_as_of",
    "36_month_event_timing",
    "application_time_feature_availability",
    "maturity_and_exclusions",
    "independent_split_membership",
    "locked_evaluation_protocol",
)


def discover_sources(directory: Path) -> list[Path]:
    """List CSV candidates in the designated private directory.

    Args:
        directory: Private source directory, excluding unrelated Downloads.

    Returns:
        Sorted CSV and CSV gzip paths, without reading their records.
    """
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.name.lower().endswith((".csv", ".csv.gz"))
    )


def inspect_source(path: Path) -> dict[str, Any]:
    """Compute byte identity and read only the CSV header of a candidate.

    Args:
        path: Existing UTF-8 CSV or gzip-compressed CSV file.

    Returns:
        Private inspection evidence with training readiness always false.

    Raises:
        ValueError: Unsupported format, empty/ambiguous header or changing source.
        OSError: File is missing, unreadable or corrupt.
    """
    if not path.is_file():
        raise ValueError("File belum tersedia; pilih file nyata sebelum pemeriksaan.")
    if not path.name.lower().endswith((".csv", ".csv.gz")):
        raise ValueError("Pemeriksa ini hanya menerima .csv atau .csv.gz.")
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    if path.name.lower().endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
            columns = next(csv.reader(handle), [])
    else:
        with path.open("rt", encoding="utf-8-sig", newline="") as handle:
            columns = next(csv.reader(handle), [])
    if not columns or any(not column.strip() for column in columns):
        raise ValueError("Header CSV kosong atau mempunyai nama kolom kosong.")
    if len(set(column.strip() for column in columns)) != len(columns):
        raise ValueError("Nama kolom CSV duplikat; pemetaan skema harus diperbaiki dahulu.")
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ino,
    ):
        raise ValueError("File berubah selama pemeriksaan; ulangi setelah unduhan selesai.")
    known = digest.hexdigest() == KNOWN_SNAPSHOT_SHA256
    return {
        "status": "KNOWN_OLD_SNAPSHOT" if known else "FILE_INSPECTED_PENDING_REVIEW",
        "source_name": path.name,
        "bytes": after.st_size,
        "sha256": digest.hexdigest(),
        "column_count": len(columns),
        "columns": columns,
        "row_count": None,
        "full_csv_integrity_checked": False,
        "known_old_snapshot": known,
        "source_admitted": False,
        "ready_for_training": False,
        "pending_evidence": list(PENDING_EVIDENCE),
        "limits": [
            "Only file bytes and CSV header inspected; records are not profiled.",
            "A new checksum does not establish independent loans or updated outcomes.",
            "last_pymnt_d and filesystem dates are not verified default/as-of dates.",
            "Header inspection does not validate all gzip records or the full CSV.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """List private candidates or inspect one explicitly selected file.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Zero for inspection awaiting review; two for unavailable/old source;
        one for invalid input. Successful inspection never authorizes training.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path.home() / "Documents" / "creditlens-private" / "holdout",
        help="Private directory searched when --file is absent",
    )
    parser.add_argument("--file", type=Path, help="One real CSV/CSV gzip path")
    args = parser.parse_args(argv)
    if args.file is None:
        files = discover_sources(args.directory.expanduser())
        report = {
            "status": "CANDIDATES_FOUND" if files else "MISSING_SOURCE",
            "candidates": [str(path) for path in files],
            "ready_for_training": False,
            "next_step": "Choose a real file for --file; review provenance and outcome timing.",
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if files else 2
    try:
        report = inspect_source(args.file.expanduser())
    except (OSError, ValueError, EOFError, csv.Error, UnicodeError) as error:
        print(json.dumps({"status": "INVALID_SOURCE", "reason": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 2 if report["known_old_snapshot"] else 0


if __name__ == "__main__":
    sys.exit(main())
