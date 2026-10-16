"""Check the public Tableau export's grain and population boundaries."""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.export_tableau_aggregates import export_tableau_aggregates


def test_public_tables_reconcile_without_loan_level_fields(tmp_path: Path) -> None:
    """Each export stays aggregate-only and preserves its own denominator."""
    files = export_tableau_aggregates(tmp_path)
    assert len(files) == 4
    tables: dict[str, list[dict[str, str]]] = {}
    for path in files:
        with path.open(encoding="utf-8", newline="") as handle:
            tables[path.name] = list(csv.DictReader(handle))
        fields = set(tables[path.name][0])
        assert not fields.intersection({"id", "loan_id", "member_id", "name", "address"})
    vintages = tables["vintage_tenor.csv"]
    assert sum(int(row["loans"]) for row in vintages) == 2_260_668
    assert sum(int(row["unresolved"]) for row in vintages) == 915_318
    assert sum(int(row["eligible"]) for row in tables["m1_cohorts.csv"]) == 603_587
