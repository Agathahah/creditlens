"""Join audited static mortgage attributes without treating sentinel values as zero."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


def enrich_origination(
    frame: pd.DataFrame, archive: Path, vintage: int, specification: dict[str, Any]
) -> pd.DataFrame:
    """Add private origination values with validated keys, layout, bounds and sentinels.

    Args:
        frame: Existing development loan-month cohort.
        archive: The admitted source ZIP; only its origination member is inspected.
        vintage: Development vintage, restricted to 2018/2019.
        specification: Locked field positions and missing/range rules.

    Returns:
        Same loan-month rows, with ordered raw static numeric attributes.

    Raises:
        ValueError: Unsupported vintage, layout, key, range or unexpected column.
    """
    if vintage not in (2018, 2019):
        raise ValueError("Frozen-test origination is sealed in development")
    expected = {
        "credit_score": (1, 9999, 300, 850),
        "orig_cltv": (9, 999, 1, 998),
        "orig_dti": (10, 999, 0.000001, 65),
        "orig_ltv": (12, 999, 1, 998),
    }
    if set(specification) != set(expected):
        raise ValueError("Unsupported origination features")
    for name, (position, sentinel, lower, upper) in expected.items():
        field = specification[name]
        if (field.get("column"), field.get("sentinel"), field.get("range")) != (
            position,
            sentinel,
            [lower, upper],
        ):
            raise ValueError("Origination field mapping changed")
    values: dict[str, dict[str, float | None]] = {}
    with zipfile.ZipFile(archive) as source:
        with source.open(f"sample_orig_{vintage}.txt") as raw:
            for row in csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="|"):
                if len(row) != 31 or not row[19] or row[19] in values:
                    raise ValueError("Invalid origination layout or loan key")
                item: dict[str, float | None] = {}
                for name, (position, sentinel, lower, upper) in expected.items():
                    token = row[position - 1]
                    number = float(token) if token else None
                    if number == sentinel or number is None:
                        item[name] = None
                    elif not lower <= number <= upper:
                        raise ValueError("Invalid origination value")
                    else:
                        item[name] = number
                values[row[19]] = item
    if not set(frame["loan_id"]).issubset(values):
        raise ValueError("Cohort key missing from origination")
    result = frame.copy()
    for name in specification:
        lookup = {key: value[name] for key, value in values.items()}
        result[name] = result["loan_id"].map(lookup)
    return result
