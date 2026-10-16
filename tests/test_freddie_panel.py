"""Synthetic monthly-window contracts; never read private samples in CI."""

from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

import pytest

from src.research.freddie_panel import Observation, build_panel, label_window, month_index


def obs(period: str, dq: int | None = 0, **kwargs: str | float) -> Observation:
    """Create a synthetic record for label boundary tests."""
    return Observation(
        "synthetic",
        period,
        float(kwargs.get("upb", 100)),
        dq,
        zero_balance_code=str(kwargs.get("zero_balance_code", "")),
    )


def test_three_calendar_months_and_event_boundary() -> None:
    history = [obs("201911"), obs("201912", 1), obs("202001", 2), obs("202002", 3)]
    assert label_window(history, 0) == (1, "observed_adverse", "202002")
    history[-1] = obs("202002", 2)
    history.append(obs("202003", 3))
    assert label_window(history, 0) == (0, "complete_non_adverse", "202002")


@pytest.mark.parametrize(
    "history,reason",
    [
        ([obs("202001"), obs("202003")], "missing_month"),
        ([obs("202001"), obs("202002")], "incomplete_followup"),
        ([obs("202001"), obs("202002", None)], "unknown_status"),
        (
            [obs("202001"), obs("202002", zero_balance_code="01", upb=0)],
            "termination_before_horizon",
        ),
    ],
)
def test_censoring_never_becomes_negative(history: list[Observation], reason: str) -> None:
    assert label_window(history, 0) == (None, reason, None)


def test_adverse_before_termination_and_ineligible_population() -> None:
    assert label_window([obs("202001"), obs("202002", 100, upb=0)], 0)[0] == 1
    assert label_window([obs("202001", 1)], 0)[1] == "ineligible_as_of"
    with pytest.raises(ValueError):
        label_window([obs("202001"), obs("202001")], 0)


def test_private_panel_reconciles_and_cannot_admit_scoring(tmp_path: Path) -> None:
    source = tmp_path / "sample_2018.zip"
    orig = [""] * 31
    orig[19] = "synthetic"
    rows = []
    for period, dq in [("201901", "00"), ("201902", "01"), ("201903", "02"), ("201904", "03")]:
        row = [""] * 35
        row[:6] = ["synthetic", period, "100", dq, "12", "348"]
        row[10] = "4.5"
        rows.append("|".join(row))
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("sample_orig_2018.txt", "|".join(orig) + "\n")
        archive.writestr("sample_perf_2018.txt", "\n".join(rows) + "\n")
    report = build_panel(source, tmp_path / "private")
    assert report["counts"]["source_months"] == 4
    assert report["counts"]["observed_adverse"] == 1
    assert report["source_admitted_for_training"] is False
    assert report["scoring_release"] == "HOLD"
    with sqlite3.connect(tmp_path / "private/panel.sqlite") as db:
        assert db.execute("SELECT label FROM loan_month").fetchall() == [(1,)]
        assert db.execute("SELECT prior_dq_1 FROM loan_month").fetchone() == (None,)
    with pytest.raises(FileExistsError):
        build_panel(source, tmp_path / "private")
    assert month_index("202001") - month_index("201912") == 1
    with pytest.raises(ValueError):
        month_index("202013")


def test_frozen_vintage_and_repository_outputs_are_rejected(tmp_path: Path) -> None:
    """Development paths must not open test data or write borrower records into Git."""
    with pytest.raises(ValueError, match="Frozen-test"):
        build_panel(tmp_path / "missing.zip", tmp_path / "test-output", vintage=2020)
    with pytest.raises(ValueError, match="outside the repository"):
        build_panel(tmp_path / "missing.zip", Path(__file__).resolve().parents[1] / "panel")


def test_unknown_tokens_and_missing_history_are_not_zero() -> None:
    """Sentinel delinquency must remain unknown and earlier gaps must censor outcomes."""
    from src.research.freddie_panel import delinquency

    assert delinquency("999") is None
    assert delinquency("") is None
    assert delinquency("00") == 0
    assert delinquency("RA") == 100
    assert label_window([obs("202001"), obs("202003", 3)], 0)[0] is None
