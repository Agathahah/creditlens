"""Unit tests for the optional Evidently drift report wrapper."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from src.monitoring import evidently_report


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build tiny reference/current frames for the report wrapper."""
    ref = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    cur = pd.DataFrame({"x": [1.5, 2.5, 3.5]})
    return ref, cur


def test_generate_drift_report_writes_html(tmp_path: Path) -> None:
    """A successful build must save the report and return its path."""
    ref, cur = _frames()
    out = str(tmp_path / "nested" / "drift.html")
    fake_report = MagicMock()

    with patch.object(evidently_report, "_build_report", return_value=fake_report):
        result = evidently_report.generate_drift_report(ref, cur, out)

    assert result == out
    fake_report.save_html.assert_called_once_with(out)


def test_generate_drift_report_degrades_gracefully(tmp_path: Path) -> None:
    """When Evidently is unavailable, the wrapper must return None."""
    ref, cur = _frames()
    out = str(tmp_path / "drift.html")

    with patch.object(evidently_report, "_build_report", side_effect=ImportError("no evidently")):
        result = evidently_report.generate_drift_report(ref, cur, out)

    assert result is None
    assert not Path(out).exists()


def test_build_report_uses_evidently_api(tmp_path: Path) -> None:
    """_build_report must construct and run an Evidently Report end to end."""
    ref, cur = _frames()
    fake_report = MagicMock()
    report_cls = MagicMock(return_value=fake_report)

    report_mod = types.ModuleType("evidently.report")
    setattr(report_mod, "Report", report_cls)
    preset_mod = types.ModuleType("evidently.metric_preset")
    setattr(preset_mod, "DataDriftPreset", MagicMock())
    evidently_pkg = types.ModuleType("evidently")

    modules = {
        "evidently": evidently_pkg,
        "evidently.report": report_mod,
        "evidently.metric_preset": preset_mod,
    }
    out = str(tmp_path / "drift.html")
    with patch.dict(sys.modules, modules):
        result = evidently_report.generate_drift_report(ref, cur, out)

    assert result == out
    fake_report.run.assert_called_once()
    fake_report.save_html.assert_called_once_with(out)
