"""Optional Evidently AI drift report generation for CreditLens.

Evidently is used only for the rich, shareable HTML drift report; the
gating drift signal comes from ``src.monitoring.drift`` (PSI/KS). Evidently
is imported lazily and failures degrade gracefully, so a version mismatch
or a missing optional dependency never breaks the monitoring pipeline.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd

from src.common.logging import configure_logging

configure_logging()
logger = logging.getLogger("creditlens.monitoring.evidently")


def generate_drift_report(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    output_path: str,
) -> str | None:
    """Generate an Evidently data-drift HTML report (best effort).

    Args:
        reference_df: Reference (training-time) feature frame.
        current_df: Current (recent) feature frame.
        output_path: Destination HTML file path.

    Returns:
        The written report path, or None when Evidently is unavailable or
        report generation fails.
    """
    try:
        report = _build_report(reference_df, current_df)
    except Exception as exc:  # noqa: BLE001 - report generation is best effort
        logger.warning("Evidently drift report skipped: %s", exc)
        return None

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    report.save_html(output_path)
    return output_path


def _build_report(reference_df: pd.DataFrame, current_df: pd.DataFrame) -> Any:
    """Build and run an Evidently data-drift report object.

    Args:
        reference_df: Reference feature frame.
        current_df: Current feature frame.

    Returns:
        A run Evidently ``Report`` instance ready to serialize.
    """
    from evidently.metric_preset import DataDriftPreset
    from evidently.report import Report

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference_df, current_data=current_df)
    return report
