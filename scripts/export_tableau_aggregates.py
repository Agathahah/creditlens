"""Export public, aggregate CreditLens evidence for Tableau Public."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a homogeneous aggregate table with stable column order.

    Args:
        path: Public aggregate CSV destination.
        rows: Nonempty rows sharing the same keys.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def export_tableau_aggregates(output_dir: Path) -> list[Path]:
    """Export dated, separate-grain public aggregate tables.

    Args:
        output_dir: Destination for the four CSV tables.

    Returns:
        Created CSV paths. No borrower-level fields are included.

    Raises:
        ValueError: If the warehouse or cohort aggregates do not reconcile.
    """
    evidence = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    warehouse = evidence["warehouse"]
    vintages = warehouse["vintages"]
    if sum(row["rows"] for row in vintages) != warehouse["rows"]:
        raise ValueError("Vintage rows do not reconcile with warehouse total")
    if any(row["rows"] != row["labeled"] + row["unresolved"] for row in vintages):
        raise ValueError("Vintage label counts do not reconcile")
    paths: list[Path] = []
    tables = {
        "vintage_tenor.csv": [
            {
                "issue_year": row["year"],
                "term_months": row["term"],
                "loans": row["rows"],
                "labeled": row["labeled"],
                "unresolved": row["unresolved"],
                "adverse": row["adverse"],
                "non_adverse": row["non_adverse"],
                "unresolved_pct": round(100 * row["unresolved"] / row["rows"], 4),
                "evidence_date": warehouse["profile_reported_at"],
            }
            for row in vintages
        ],
        "m1_cohorts.csv": [
            {
                **row,
                "adverse_pct": round(100 * row["adverse"] / row["eligible"], 4),
                "evidence_date": evidence["data_as_of_report"],
            }
            for row in evidence["cohorts"]
        ],
        "m1_validation.csv": [
            {**row, "evidence_date": evidence["data_as_of_report"]}
            for row in evidence["validation"]
        ],
        "m1_vintage_profile.csv": [
            {**row, "evidence_date": evidence["experiment_profile"]["source_checked_at"]}
            for row in evidence["experiment_profile"]["vintage_summary"]
        ],
    }
    for filename, rows in tables.items():
        destination = output_dir / filename
        _write_csv(destination, rows)
        paths.append(destination)
    return paths


if __name__ == "__main__":
    for exported in export_tableau_aggregates(ROOT / "outputs/tableau-public"):
        print(exported)
