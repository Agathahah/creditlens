"""Validate the research dashboard without data access or model training."""

from __future__ import annotations

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_discloses_failed_gate_and_updates_split() -> None:
    """The rendered UI must keep failure disclosure and display the selected cohort."""
    app = AppTest.from_file(str(ROOT / "src/dashboard/app.py")).run(timeout=15)
    assert not app.exception
    assert "gagal gate" in app.warning[0].value
    assert "terpakai" in app.error[0].value
    assert app.metric[0].value == "0.2197"
    app.selectbox[0].select("Validation").run(timeout=15)
    assert not app.exception
    assert app.selectbox[0].value == "Validation"


def test_snapshot_reconciles_counts_and_preserves_failure_status() -> None:
    """The public aggregate snapshot must not silently relabel the failed experiment."""
    snapshot = json.loads((ROOT / "docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json").read_text())
    for cohort in snapshot["cohorts"]:
        assert cohort["eligible"] == cohort["non_adverse"] + cohort["adverse"]
    assert snapshot["model_release_passed"] is False
    assert snapshot["test_consumed"] is True
    assert snapshot["test"]["average_precision"] < snapshot["test"]["historical_ap_gate"]
