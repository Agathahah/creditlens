"""Bounded private request audit and explicitly synthetic delayed-outcome monitoring."""

from __future__ import annotations

import hashlib
import hmac
import math
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from src.research.freddie_panel import LABEL_VERSION, Observation, label_window, month_index

ROOT = Path(__file__).resolve().parents[2]
MAX_EVENTS = 100000
MAX_BYTES = 64 * 1024**2


def utc(value: datetime) -> str:
    """Normalize an explicitly aware timestamp for ordered SQLite comparisons.

    Args:
        value: Timestamp with an actual timezone offset.

    Returns:
        Canonical UTC ISO timestamp.

    Raises:
        ValueError: Naive timestamp.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _period_end(period: str) -> datetime:
    year, month = divmod(month_index(period) + 1, 12)
    return datetime(year, month + 1, 1, tzinfo=UTC)


def private_file(path: Path) -> None:
    """Require a regular owner-only local file outside the repository.

    Args:
        path: Existing private input file.

    Raises:
        ValueError: Unsafe path, symlink, missing file or group/world permissions.
    """
    resolved = path.resolve()
    if (
        ROOT == resolved
        or ROOT in resolved.parents
        or path.is_symlink()
        or not path.is_file()
        or path.stat().st_mode & 0o077
    ):
        raise ValueError("Regular owner-only file outside Git required")


class FollowupRecord(BaseModel):
    """Synthetic follow-up observation; unknown delinquency remains explicit."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    period: str = Field(pattern=r"^[0-9]{6}$")
    available_at: AwareDatetime
    dq: int | None = Field(ge=0, le=100)
    upb: float = Field(ge=0, le=1e10)
    zero_balance_code: str = Field(default="", max_length=3)


class SyntheticOutcome(BaseModel):
    """Declared synthetic evidence; not admission of real future servicing outcomes."""

    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str
    loan_key: str = Field(min_length=1, max_length=100)
    as_of_period: str = Field(pattern=r"^[0-9]{6}$")
    source_kind: Literal["synthetic"]
    report_as_of: AwareDatetime
    followup: list[FollowupRecord] = Field(max_length=3)


class AuditStore:
    """SQLite local evidence with bounded traffic and model-specific canonical links."""

    def __init__(self, path: Path) -> None:
        """Initialize a private journal without changing an active warehouse.

        Args:
            path: SQLite file under an owner-only directory outside Git.

        Raises:
            ValueError: Private boundary, size or schema mismatch.
        """
        self.path = path
        resolved = path.resolve()
        if ROOT == resolved or ROOT in resolved.parents or path.is_symlink():
            raise ValueError("Private database outside Git required")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.parent.stat().st_mode & 0o077:
            raise ValueError("Owner-only journal directory required")
        if path.exists():
            private_file(path)
        with self.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if version not in (0, 1) or (version == 0 and tables):
                raise ValueError("Unrecognized journal schema")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    request_id TEXT PRIMARY KEY, started_at TEXT NOT NULL,
                    method TEXT NOT NULL, route TEXT NOT NULL, status INTEGER NOT NULL,
                    latency_ms REAL NOT NULL, model_id TEXT NOT NULL, model_sha TEXT NOT NULL,
                    probability REAL, CHECK(probability IS NULL OR probability BETWEEN 0 AND 1)
                );
                CREATE TABLE IF NOT EXISTS contexts (
                    request_id TEXT PRIMARY KEY REFERENCES events(request_id),
                    model_sha TEXT NOT NULL, key_id TEXT NOT NULL, loan_ref TEXT NOT NULL,
                    as_of_period TEXT NOT NULL, prediction_time TEXT NOT NULL,
                    linked_at TEXT NOT NULL,
                    source_kind TEXT NOT NULL CHECK(source_kind='synthetic'),
                    UNIQUE(model_sha,key_id,loan_ref,as_of_period)
                );
                CREATE TABLE IF NOT EXISTS outcomes (
                    sequence INTEGER PRIMARY KEY,
                    request_id TEXT NOT NULL REFERENCES contexts(request_id),
                    evidence_sha TEXT NOT NULL, label INTEGER, reason TEXT NOT NULL,
                    label_available_at TEXT, report_as_of TEXT NOT NULL,
                    UNIQUE(request_id,evidence_sha), CHECK(label IS NULL OR label IN (0,1))
                );
                PRAGMA user_version=1;
            """)
        path.chmod(0o600)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Open a bounded local transaction and always close its connection.

        Yields:
            Connection with foreign-key checks and full synchronous durability enabled.
        """
        if self.path.exists() and self.path.stat().st_size > MAX_BYTES:
            raise ValueError("Journal size limit reached")
        connection = sqlite3.connect(self.path, timeout=2)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            page_size = connection.execute("PRAGMA page_size").fetchone()[0]
            connection.execute(f"PRAGMA max_page_count={MAX_BYTES // page_size}")
            with connection:
                yield connection
        finally:
            connection.close()

    def record(
        self,
        request_id: str,
        started_at: datetime,
        method: str,
        route: str,
        status: int,
        latency_ms: float,
        model_id: str,
        model_sha: str,
        probability: float | None,
    ) -> None:
        """Commit one actual API outcome without raw input or caller-controlled identifiers.

        Args:
            request_id: Server-generated UUID.
            started_at: Actual server UTC request start.
            method: Sanitized GET/POST/OTHER class.
            route: Sanitized /ready,/score or /other class.
            status: HTTP response status.
            latency_ms: Time to response construction, excluding audit commit latency.
            model_id: Accepted research model identity.
            model_sha: Accepted candidate checksum.
            probability: Successful score only; otherwise NULL.

        Raises:
            ValueError: Invalid metadata or bounded journal capacity reached.
        """
        UUID(request_id)
        if (
            method not in ("GET", "POST", "OTHER")
            or route not in ("/ready", "/score", "/other")
            or not 100 <= status <= 599
            or not math.isfinite(latency_ms)
            or latency_ms < 0
            or len(model_sha) != 64
            or not all(c in "0123456789abcdef" for c in model_sha)
            or (route == "/score" and status == 200 and probability is None)
            or (
                probability is not None
                and (
                    route != "/score"
                    or status != 200
                    or not math.isfinite(probability)
                    or not 0 <= probability <= 1
                )
            )
        ):
            raise ValueError("Invalid audit metadata")
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] >= MAX_EVENTS:
                raise ValueError("Journal event limit reached")
            connection.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    request_id,
                    utc(started_at),
                    method,
                    route,
                    status,
                    latency_ms,
                    model_id,
                    model_sha,
                    probability,
                ),
            )

    def link(
        self,
        request_id: str,
        loan_key: str,
        as_of_period: str,
        prediction_time: datetime,
        key: bytes,
    ) -> str:
        """Link declared synthetic context using a separate HMAC key and canonical grain.

        Args:
            request_id: Actual successful audited score ID returned by the API.
            loan_key: Private synthetic loan key; never stored or sent to the server.
            as_of_period: Complete reporting month at prediction.
            prediction_time: Supplied aware decision time, no later than server scoring.
            key: Separate local random HMAC key of at least32bytes.

        Returns:
            Canonical request ID; exact retries retain the first linked observation.

        Raises:
            ValueError: Missing score, invalid time, mismatched replay or conflicting context.
        """
        UUID(request_id)
        if not loan_key or len(loan_key) > 100 or len(key) < 32:
            raise ValueError("Bounded loan key and separate HMAC key required")
        prediction = utc(prediction_time)
        if _period_end(as_of_period) > prediction_time:
            raise ValueError("Incomplete reporting period")
        key_id = hashlib.sha256(key).hexdigest()
        reference = hmac.new(key, loan_key.encode(), hashlib.sha256).hexdigest()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            event = connection.execute(
                "SELECT * FROM events WHERE request_id=?", (request_id,)
            ).fetchone()
            if (
                event is None
                or event["route"] != "/score"
                or event["status"] != 200
                or event["probability"] is None
            ):
                raise ValueError("Successful persisted score required")
            if prediction > event["started_at"]:
                raise ValueError("Prediction time exceeds actual scoring time")
            existing = connection.execute(
                """SELECT c.*,e.probability FROM contexts c
                JOIN events e USING(request_id) WHERE c.model_sha=? AND c.key_id=?
                AND c.loan_ref=? AND c.as_of_period=?""",
                (event["model_sha"], key_id, reference, as_of_period),
            ).fetchone()
            if existing is not None:
                if (
                    existing["prediction_time"] != prediction
                    or abs(existing["probability"] - event["probability"]) > 1e-12
                ):
                    raise ValueError("Canonical loan-month context changed; review required")
                return str(existing["request_id"])
            if connection.execute(
                "SELECT 1 FROM contexts WHERE request_id=?", (request_id,)
            ).fetchone():
                raise ValueError("Request already linked to another context")
            connection.execute(
                "INSERT INTO contexts VALUES (?,?,?,?,?,?,?,?)",
                (
                    request_id,
                    event["model_sha"],
                    key_id,
                    reference,
                    as_of_period,
                    prediction,
                    utc(datetime.now(UTC)),
                    "synthetic",
                ),
            )
        return request_id

    def ingest(self, outcome: SyntheticOutcome, key: bytes) -> dict[str, Any]:
        """Append synthetic label evidence using the unchanged three-month label function.

        Args:
            outcome: Explicit synthetic follow-up evidence and report cutoff.
            key: Same separate key used to pseudonymize the original loan context.

        Returns:
            Label/reason and idempotency status, without a raw loan key.

        Raises:
            ValueError: Context, timing, identity, conflicting evidence or maturity error.
        """
        UUID(outcome.request_id)
        if len(key) < 32:
            raise ValueError("Separate HMAC key required")
        start = month_index(outcome.as_of_period)
        records: dict[int, FollowupRecord] = {}
        seen: set[int] = set()
        for record in outcome.followup:
            month = month_index(record.period)
            if month not in range(start + 1, start + 4) or month in seen:
                raise ValueError("Exact next three reporting months required")
            seen.add(month)
            if record.available_at < _period_end(record.period):
                raise ValueError("Outcome available before reporting month completed")
            if record.available_at <= outcome.report_as_of:
                records[month] = record
        history = [Observation("synthetic", outcome.as_of_period, 1.0, 0)] + [
            Observation(
                "synthetic",
                record.period,
                record.upb,
                record.dq,
                zero_balance_code=record.zero_balance_code,
            )
            for _, record in sorted(records.items())
        ]
        label, reason, observed = label_window(history, 0)
        available = None
        if label is not None:
            used = [
                record.available_at
                for month, record in records.items()
                if month <= month_index(str(observed))
            ]
            available = utc(max(used))
        digest = hashlib.sha256(outcome.model_dump_json().encode()).hexdigest()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            context = connection.execute(
                """SELECT c.*,e.started_at FROM contexts c
                JOIN events e USING(request_id) WHERE c.request_id=?""",
                (outcome.request_id,),
            ).fetchone()
            if (
                context is None
                or context["as_of_period"] != outcome.as_of_period
                or context["key_id"] != hashlib.sha256(key).hexdigest()
                or context["loan_ref"]
                != hmac.new(key, outcome.loan_key.encode(), hashlib.sha256).hexdigest()
            ):
                raise ValueError("Synthetic context/HMAC identity mismatch")
            if utc(outcome.report_as_of) < context["started_at"]:
                raise ValueError("Report cutoff precedes actual scoring")
            if available is not None and available <= context["started_at"]:
                raise ValueError("Outcome must become available after actual scoring")
            if connection.execute(
                "SELECT 1 FROM outcomes WHERE request_id=? AND evidence_sha=?",
                (outcome.request_id, digest),
            ).fetchone():
                return {"label": label, "reason": reason, "idempotent_replay": True}
            if connection.execute(
                "SELECT 1 FROM outcomes WHERE request_id=? AND label IS NOT NULL",
                (outcome.request_id,),
            ).fetchone():
                raise ValueError("Resolved evidence cannot be replaced; review required")
            connection.execute(
                "INSERT INTO outcomes(request_id,evidence_sha,label,reason,"
                "label_available_at,report_as_of) VALUES (?,?,?,?,?,?)",
                (
                    outcome.request_id,
                    digest,
                    label,
                    reason,
                    available,
                    utc(outcome.report_as_of),
                ),
            )
        return {"label": label, "reason": reason, "idempotent_replay": False}

    def report(self, as_of: datetime) -> dict[str, Any]:
        """Summarize actual traffic and explicitly synthetic canonical outcome diagnostics.

        Args:
            as_of: Aware reporting cutoff; future simulation is labelled as synthetic.

        Returns:
            Traffic plus pending/censored/resolved counts and diagnostic Brier per model.
        """
        cutoff = utc(as_of)
        with self.connection() as connection:
            traffic = [
                dict(row)
                for row in connection.execute(
                    """SELECT model_id,model_sha,route,status,COUNT(*) AS requests,
                AVG(latency_ms) AS mean_response_construction_ms FROM events
                WHERE started_at<=? GROUP BY model_id,model_sha,route,status""",
                    (cutoff,),
                )
            ]
            rows = connection.execute(
                """SELECT e.model_id,e.model_sha,e.probability,o.label,o.reason
                FROM contexts c JOIN events e USING(request_id)
                LEFT JOIN outcomes o ON o.sequence=(SELECT MAX(x.sequence) FROM outcomes x
                    WHERE x.request_id=c.request_id AND x.report_as_of<=?)
                WHERE e.started_at<=? AND c.linked_at<=?""",
                (cutoff, cutoff, cutoff),
            ).fetchall()
        models: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = models.setdefault(
                row["model_sha"],
                {
                    "model_id": row["model_id"],
                    "model_sha": row["model_sha"],
                    "linked_unique_loan_months": 0,
                    "pending": 0,
                    "censored": 0,
                    "resolved": 0,
                    "adverse": 0,
                    "squared_error_sum": 0.0,
                    "resolved_probability_sum": 0.0,
                },
            )
            item["linked_unique_loan_months"] += 1
            if row["reason"] is None:
                item["pending"] += 1
            elif row["label"] is None:
                item["censored"] += 1
            else:
                item["resolved"] += 1
                item["adverse"] += row["label"]
                item["squared_error_sum"] += (row["probability"] - row["label"]) ** 2
                item["resolved_probability_sum"] += row["probability"]
        for item in models.values():
            count = item["resolved"]
            item["brier_diagnostic"] = item.pop("squared_error_sum") / count if count else None
            item["mean_resolved_prediction"] = (
                item.pop("resolved_probability_sum") / count if count else None
            )
            item["observed_adverse_fraction"] = item["adverse"] / count if count else None
        return {
            "report_as_of": cutoff,
            "traffic": traffic,
            "synthetic_outcome_diagnostics": list(models.values()),
            "label_version": LABEL_VERSION,
            "quality_grain": "first_linked_model_key_loan_month",
            "purpose": "SYNTHETIC_MONITORING_PLUMBING_ONLY",
            "operational_quality_verified": False,
            "production_scoring_release": "HOLD",
        }
