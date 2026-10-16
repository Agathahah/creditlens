"""Build locked v4 features from bounded, timestamped private monthly research records."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from src.research.freddie_history_audit import past_features
from src.research.freddie_history_train import PROTOCOL_SHA
from src.research.freddie_panel import Observation, month_index
from src.research.freddie_preflight import read_object, sha256

ADAPTER_VERSION = "freddie_monthly_availability_v1"
DEFAULT_PROTOCOL = (
    Path(__file__).resolve().parents[2] / "config/research/freddie_experiment_v4.json"
)


class OriginationRecord(BaseModel):
    """Original domain values with a supplied availability time, not publisher attestation."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    available_at: AwareDatetime
    credit_score: float | None
    orig_cltv: float | None
    orig_dti: float | None
    orig_ltv: float | None


class MonthlyRecord(BaseModel):
    """A single-loan monthly observation or correction with its supplied availability."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    loan_key: str = Field(min_length=1, max_length=100)
    period: str = Field(pattern=r"^[0-9]{6}$")
    available_at: AwareDatetime
    upb: float = Field(ge=0, le=1e10)
    dq: int | None = Field(ge=0, le=100)
    loan_age: float | None = Field(default=None, ge=0, le=600)
    remaining_months: float | None = Field(default=None, ge=0, le=600)
    interest_rate: float | None = Field(default=None, ge=0, le=100)
    zero_balance_code: str = Field(default="", max_length=3)

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        """Require a valid reporting month.

        Args:
            value: Six-digit reporting month.

        Returns:
            Validated month.
        """
        month_index(value)
        return value


class MonthlySnapshot(BaseModel):
    """Bounded single-loan request; no labels, outcomes or arbitrary feature columns."""

    model_config = ConfigDict(extra="forbid", strict=True)
    loan_key: str = Field(min_length=1, max_length=100)
    as_of_period: str = Field(pattern=r"^[0-9]{6}$")
    prediction_time: AwareDatetime
    origination: OriginationRecord
    records: list[MonthlyRecord] = Field(min_length=1, max_length=256)


def _month_end_exclusive(period: str) -> datetime:
    index = month_index(period) + 1
    year, month = divmod(index, 12)
    return datetime(year, month + 1, 1, tzinfo=UTC)


def build_feature_request(
    snapshot: MonthlySnapshot, protocol_path: Path = DEFAULT_PROTOCOL
) -> dict[str, dict[str, float | None]]:
    """Reconstruct exact v4 features using only records available by prediction time.

    Args:
        snapshot: Supplied availability-tagged domain records for one private loan.
        protocol_path: Existing immutable v4 protocol; never a new training configuration.

    Returns:
        Ordered 19-feature payload for the authenticated research scoring API.

    Raises:
        ValueError: Changed protocol, mixed identities, ambiguous correction, invalid
            availability, absent current record or ineligible population. Supplied
            timestamps are checked, never certified as true operational availability.
    """
    if sha256(protocol_path) != PROTOCOL_SHA:
        raise ValueError("Locked v4 protocol required")
    config = read_object(protocol_path)
    as_of = month_index(snapshot.as_of_period)
    if _month_end_exclusive(snapshot.as_of_period) > snapshot.prediction_time:
        raise ValueError("Reporting month must be complete before prediction")
    if snapshot.origination.available_at > snapshot.prediction_time:
        raise ValueError("Origination values unavailable at prediction time")
    selected: dict[int, MonthlyRecord] = {}
    seen: set[tuple[int, datetime]] = set()
    for record in snapshot.records:
        if record.loan_key != snapshot.loan_key:
            raise ValueError("Mixed loan identities")
        month = month_index(record.period)
        if record.available_at < _month_end_exclusive(record.period):
            raise ValueError("Monthly availability precedes completed reporting month")
        if month > as_of or month < as_of - 12 or record.available_at > snapshot.prediction_time:
            continue
        identity = (month, record.available_at)
        if identity in seen:
            raise ValueError("Ambiguous monthly correction timestamp")
        seen.add(identity)
        if month not in selected or selected[month].available_at < record.available_at:
            selected[month] = record
    observations = {
        month: Observation(
            record.loan_key,
            record.period,
            record.upb,
            record.dq,
            record.loan_age,
            record.remaining_months,
            record.interest_rate,
            record.zero_balance_code,
        )
        for month, record in selected.items()
    }
    current = observations.get(as_of)
    if current is None or not current.active_current:
        raise ValueError("Available active-current reporting record required")
    values: dict[str, float | None] = {
        "upb": current.upb,
        "loan_age": current.loan_age,
        "remaining_months": current.remaining_months,
        "interest_rate": current.interest_rate,
        **{
            f"prior_dq_{lag}": (
                float(item.dq)
                if (item := observations.get(as_of - lag)) is not None and item.dq is not None
                else None
            )
            for lag in (1, 2)
        },
        **past_features(current, observations),
    }
    for name, spec in config["origination_features"].items():
        value = getattr(snapshot.origination, name)
        if value == spec["sentinel"]:
            value = None
        if value is not None and not spec["range"][0] <= value <= spec["range"][1]:
            raise ValueError("Origination value outside locked domain range")
        values[name] = value
    return {"features": {name: values[name] for name in config["features"]}}
