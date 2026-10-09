"""Stream a private Freddie sample into a research-only monthly SQLite panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sqlite3
import zipfile
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LABEL_VERSION = "freddie_current_to_90plus_or_reo_3m_v1"
FEATURES = ("upb", "loan_age", "remaining_months", "interest_rate", "prior_dq_1", "prior_dq_2")


def month_index(value: str) -> int:
    """Convert a YYYYMM reporting period to a consecutive month index.

    Args:
        value: Six-digit calendar month.

    Returns:
        Integer suitable for calendar-window arithmetic.

    Raises:
        ValueError: Invalid reporting period.
    """
    if len(value) != 6 or not value.isdigit():
        raise ValueError("Invalid reporting period")
    year, month = int(value[:4]), int(value[4:])
    if not 1900 <= year <= 2100 or not 1 <= month <= 12:
        raise ValueError("Invalid reporting period")
    return year * 12 + month - 1


def delinquency(value: str) -> int | None:
    """Decode monthly delinquency without turning missing/sentinel values into zero.

    Args:
        value: Freddie monthly delinquency status.

    Returns:
        Months delinquent, 100 for REO acquisition, or None when unknown.
    """
    if value == "RA":
        return 100
    if value.isdigit() and 0 <= int(value) <= 99:
        return int(value)
    return None


def optional_number(value: str) -> float | None:
    """Parse a nullable finite numeric field.

    Args:
        value: Source token.

    Returns:
        Finite number or None for a blank.

    Raises:
        ValueError: Non-finite or malformed numeric token.
    """
    if not value:
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite numeric value")
    return number


@dataclass(frozen=True)
class Observation:
    """A minimal monthly record; future outcome fields are never model features."""

    loan_id: str
    period: str
    upb: float
    dq: int | None
    loan_age: float | None = None
    remaining_months: float | None = None
    interest_rate: float | None = None
    zero_balance_code: str = ""

    @property
    def active_current(self) -> bool:
        """Return whether the reporting record belongs to the intended population."""
        return self.dq == 0 and self.upb > 0 and not self.zero_balance_code


def label_window(
    history: Sequence[Observation], index: int, horizon: int = 3
) -> tuple[int | None, str, str | None]:
    """Label the next calendar months conservatively before any split or fit.

    Args:
        history: Strictly increasing records for one loan.
        index: Position of the current active observation.
        horizon: Number of future calendar months; production protocol uses three.

    Returns:
        Label, reason and observation period establishing the label. Positive means
        observed 90+ days delinquent or REO; negative requires the complete window.
        Missing, unknown or terminated follow-up is censored, never labelled zero.

    Raises:
        ValueError: Invalid horizon, loan identity, duplicate or unordered periods.
    """
    if horizon < 1:
        raise ValueError("Horizon must be positive")
    current = history[index]
    if not current.active_current:
        return None, "ineligible_as_of", None
    start = month_index(current.period)
    for offset in range(1, horizon + 1):
        position = index + offset
        if position >= len(history):
            return None, "incomplete_followup", None
        future = history[position]
        actual = month_index(future.period)
        if future.loan_id != current.loan_id or actual <= start + offset - 1:
            raise ValueError("Mixed loan or unordered periods")
        if actual != start + offset:
            return None, "missing_month", None
        if future.dq is None:
            return None, "unknown_status", None
        # An observed adverse event wins over simultaneous terminal metadata.
        if future.dq >= 3:
            return 1, "observed_adverse", future.period
        if future.zero_balance_code or future.upb <= 0:
            return None, "termination_before_horizon", None
    return 0, "complete_non_adverse", history[index + horizon].period


def iter_histories(archive: Path, vintage: int) -> Iterator[list[Observation]]:
    """Read one loan history at a time without extracting or loading the full ZIP.

    Args:
        archive: Private sample ZIP with the audited 31/35-column layout.
        vintage: Origination vintage in member names.

    Yields:
        Ordered histories keyed to a verified origination record.

    Raises:
        ValueError: Unexpected layout, key mismatch, duplicate or unordered record.
    """
    with zipfile.ZipFile(archive) as source:
        orig_name = f"sample_orig_{vintage}.txt"
        perf_name = f"sample_perf_{vintage}.txt"
        if sorted(source.namelist()) != sorted([orig_name, perf_name]):
            raise ValueError("Unexpected ZIP members; audit a new layout before use")
        identities: set[str] = set()
        with source.open(orig_name) as raw:
            for row in csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="|"):
                if len(row) != 31 or not row[19] or row[19] in identities:
                    raise ValueError("Invalid origination layout/key")
                identities.add(row[19])
        seen: set[str] = set()
        history: list[Observation] = []
        with source.open(perf_name) as raw:
            for row in csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="|"):
                if len(row) != 35 or row[0] not in identities:
                    raise ValueError("Invalid performance layout/key")
                month_index(row[1])
                upb = optional_number(row[2])
                if upb is None or upb < 0:
                    raise ValueError("Missing or negative UPB")
                item = Observation(
                    row[0],
                    row[1],
                    upb,
                    delinquency(row[3]),
                    optional_number(row[4]),
                    optional_number(row[5]),
                    optional_number(row[10]),
                    row[8].strip(),
                )
                if history and item.loan_id != history[0].loan_id:
                    seen.add(history[0].loan_id)
                    yield history
                    history = []
                if item.loan_id in seen:
                    raise ValueError("Non-contiguous loan history")
                if history and month_index(item.period) <= month_index(history[-1].period):
                    raise ValueError("Duplicate or unordered reporting period")
                history.append(item)
        if history:
            seen.add(history[0].loan_id)
            yield history
        if seen != identities:
            raise ValueError("Origination/performance identities do not reconcile")


def build_panel(archive: Path, output: Path, vintage: int = 2018) -> dict[str, Any]:
    """Build an owner-only research database and an explicitly non-release report.

    Args:
        archive: Private source ZIP.
        output: New private output directory; existing artifacts are never overwritten.
        vintage: Input sample vintage. Frozen test sources must not be passed here.

    Returns:
        Aggregate private audit report with scoring/training admission false.

    Raises:
        ValueError: Source changed, unexpected layout or output under the repository.
        OSError: Output exists or disk/source cannot be read.
    """
    archive, output = archive.resolve(), output.resolve()
    repository = Path(__file__).resolve().parents[2]
    if output == repository or repository in output.parents:
        raise ValueError("Write loan records outside the repository")
    if vintage not in (2018, 2019):
        raise ValueError("Frozen-test vintage is sealed; only development vintages are allowed")
    before = archive.stat()
    with archive.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    db_path = output / "panel.sqlite"
    counts: Counter[str] = Counter()
    periods: list[str] = []
    with sqlite3.connect(db_path) as db:
        os.chmod(db_path, 0o600)
        db.execute("PRAGMA cache_size=-16384")
        db.execute("""CREATE TABLE loan_month (
            loan_id TEXT NOT NULL, as_of TEXT NOT NULL, vintage INTEGER NOT NULL,
            upb REAL NOT NULL, loan_age REAL, remaining_months REAL, interest_rate REAL,
            prior_dq_1 INTEGER, prior_dq_2 INTEGER, label INTEGER CHECK(label IN (0,1)),
            label_reason TEXT NOT NULL, label_observed_period TEXT,
            horizon_months INTEGER NOT NULL CHECK(horizon_months=3),
            PRIMARY KEY (loan_id, as_of))""")
        for history in iter_histories(archive, vintage):
            counts["loans"] += 1
            counts["source_months"] += len(history)
            periods.extend([history[0].period, history[-1].period])
            batch = []
            for index, item in enumerate(history):
                if not item.active_current:
                    counts["ineligible_as_of"] += 1
                    continue
                label, reason, observed = label_window(history, index)
                counts[reason] += 1
                prior = [
                    (
                        history[index - lag].dq
                        if index >= lag
                        and month_index(history[index - lag].period)
                        == month_index(item.period) - lag
                        else None
                    )
                    for lag in (1, 2)
                ]
                batch.append(
                    (
                        item.loan_id,
                        item.period,
                        vintage,
                        item.upb,
                        item.loan_age,
                        item.remaining_months,
                        item.interest_rate,
                        *prior,
                        label,
                        reason,
                        observed,
                        3,
                    )
                )
            db.executemany("INSERT INTO loan_month VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        if (before.st_size, before.st_mtime_ns) != (
            archive.stat().st_size,
            archive.stat().st_mtime_ns,
        ):
            raise ValueError("Source changed during build")
        db.execute("CREATE INDEX monthly_as_of ON loan_month(as_of)")
        db.execute("""CREATE VIEW monthly_summary AS SELECT as_of,
            COUNT(*) AS eligible_current, SUM(upb) AS eligible_upb,
            SUM(label IS NOT NULL) AS labeled, SUM(label=1) AS adverse,
            SUM(label=0) AS non_adverse, SUM(label IS NULL) AS censored
            FROM loan_month GROUP BY as_of""")
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "source_sha256": digest,
        "source_bytes": before.st_size,
        "vintage": vintage,
        "label_version": LABEL_VERSION,
        "horizon_months": 3,
        "period_min": min(periods),
        "period_max": max(periods),
        "counts": dict(counts),
        "feature_whitelist": list(FEATURES),
        "database_bytes": db_path.stat().st_size,
        "source_admitted_for_training": False,
        "scoring_release": "HOLD",
        "independent_evaluation": "NOT_RUN",
        "point_in_time_verified": False,
        "limitations": [
            "Corrected historical snapshot; actual publication times unavailable",
            "One mortgage vintage, not an independent fintech evaluation",
            "Censoring includes termination and incomplete follow-up",
            "Private derived records; publication rights not established",
        ],
    }
    report_path = output / "panel_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    os.chmod(report_path, 0o600)
    return report


def main() -> None:
    """Build the private panel from explicit source and output CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--vintage", type=int, default=2018)
    args = parser.parse_args()
    report = build_panel(args.source, args.output, args.vintage)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
