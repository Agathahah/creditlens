"""Boundary checks for the raw Lending Club import contract."""

from datetime import date

import pandas as pd
import pytest

from src.ingestion.lending_club import SOURCE_TO_RAW, normalize_chunk

LONG_STATUS = "Does not meet the credit policy. Status:Charged Off"


def fixture_frame(**changes: object) -> pd.DataFrame:
    """Construct a synthetic loan without personal information."""
    row: dict[str, object] = dict.fromkeys(SOURCE_TO_RAW)
    row.update(id="1", loan_amnt="1000", issue_d="Jan-2015", loan_status=LONG_STATUS)
    row.update(changes)
    return pd.DataFrame([row])


def test_full_status_and_dates_survive_mapping() -> None:
    rows, excluded = normalize_chunk(fixture_frame(earliest_cr_line="Dec-2001"))
    mapped = dict(zip(SOURCE_TO_RAW.values(), rows[0], strict=True))
    assert len(mapped["loan_status"]) == 51
    assert mapped["loan_status"] == LONG_STATUS
    assert mapped["issue_date"] == date(2015, 1, 1)
    assert mapped["earliest_cr_line"] == date(2001, 12, 1)
    assert mapped["last_pymnt_date"] is None
    assert mapped["member_id"] is None
    assert excluded == 0


def test_missing_required_fields_are_counted_not_loaded() -> None:
    frame = pd.concat([fixture_frame(), fixture_frame(id=None, issue_d=None)])
    rows, excluded = normalize_chunk(frame)
    assert len(rows) == 1
    assert excluded == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"issue_d": "not-a-date"},
        {"loan_amnt": "not-a-number"},
        {"id": "1.5"},
        {"annual_inc": "inf"},
    ],
)
def test_present_invalid_values_are_not_silently_coerced(changes: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        normalize_chunk(fixture_frame(**changes))


def test_existing_raw_missingness_mapping_is_preserved() -> None:
    rows, _ = normalize_chunk(fixture_frame(dti="-5"))
    mapped = dict(zip(SOURCE_TO_RAW.values(), rows[0], strict=True))
    assert mapped["dti"] is None
    assert mapped["annual_inc"] == 0
    assert mapped["funded_amnt"] is None
