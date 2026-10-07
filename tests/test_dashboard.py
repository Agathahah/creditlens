"""Verify dashboard population boundaries, historical decisions, and navigation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_overview_explains_scope_and_filters_counts() -> None:
    """Year/term filters must change warehouse counts with their correct denominator."""
    app = AppTest.from_file(str(ROOT / "src/dashboard/app.py")).run(timeout=20)
    assert not app.exception
    assert app.metric[0].value == "2.260.668"
    assert app.metric[1].value == "1.345.350"
    assert app.metric[2].value == "915.318"
    assert any("Alur proyek" in item.value for item in app.markdown)
    app.selectbox[0].select("2018")
    app.selectbox[1].select("36 bulan").run(timeout=20)
    assert not app.exception
    assert app.metric[0].value == "344.671"
    assert app.metric[1].value == "41.272"
    assert app.metric[2].value == "303.399"
    assert app.metric[3].value == "13.25%"
    assert any("41.272 pinjaman berlabel" in item.value for item in app.caption)


def test_empty_filter_has_no_fabricated_population() -> None:
    """A year without the selected term must show an empty state, not zero-risk data."""
    app = AppTest.from_file(str(ROOT / "src/dashboard/app.py")).run(timeout=20)
    app.selectbox[0].select("2007")
    app.selectbox[1].select("60 bulan").run(timeout=20)
    assert not app.exception
    assert "Tidak ada pinjaman" in app.info[0].value
    assert len(app.metric) == 0


@pytest.mark.parametrize(
    "page",
    [
        "Masalah bisnis",
        "Profil dataset",
        "Data & vintage",
        "Data engineering",
        "Eksperimen model",
        "API & keamanan",
        "Deployment",
        "Riset panel bulanan",
        "Kesimpulan",
    ],
)
def test_story_pages_render_with_scope_disclosure(page: str) -> None:
    """All navigation destinations must render without training or loading private data."""
    app = AppTest.from_file(str(ROOT / "src/dashboard/app.py")).run(timeout=20)
    app.radio[0].set_value(page).run(timeout=20)
    assert not app.exception
    assert any("Snapshot historis" in item.value for item in app.caption)
    if page == "Masalah bisnis":
        assert any("pemantauan portofolio" in item.value.lower() for item in app.markdown)
    if page == "Profil dataset":
        assert app.metric[0].value == "603.587"
        assert any("9 juta USD" in item.value for item in app.markdown)
    if page == "Eksperimen model":
        assert any("Model konstan" in item.value for item in app.markdown)
        assert any("Logistic Regression" in item.value for item in app.markdown)
        assert any("Bounded XGBoost" in item.value for item in app.markdown)
        assert "gagal gate" in app.warning[0].value
        assert "terpakai" in app.error[0].value
        assert [item.value for item in app.metric[:3]] == ["0.1373", "0.2016", "0.2046"]
        assert any(
            item.label == "AP frozen test historis" and item.value == "0.2197"
            for item in app.metric
        )
    if page == "Deployment":
        assert app.metric[1].value == "TERVERIFIKASI"
        assert any("928acc6" in item.value for item in app.caption)
        assert any("084e524" in item.value for item in app.caption)
    if page == "API & keamanan":
        assert any("tidak melakukan probe API live" in item.value for item in app.caption)
    if page == "Kesimpulan":
        assert "alert untuk pinjaman aktif belum tersedia" in app.info[0].value


def test_snapshot_reconciles_populations_and_preserves_failure() -> None:
    """Warehouse, vintage, purpose, and experiment totals must stay separate and agree."""
    snapshot = json.loads((ROOT / "docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json").read_text())
    warehouse = snapshot["warehouse"]
    assert warehouse["rows"] == sum(warehouse[k] for k in ("non_adverse", "adverse", "unresolved"))
    for key in ("rows", "non_adverse", "adverse", "unresolved"):
        assert sum(row[key] for row in warehouse["vintages"]) == warehouse[key]
    for row in warehouse["vintages"]:
        assert row["labeled"] == row["non_adverse"] + row["adverse"]
        assert row["rows"] == row["labeled"] + row["unresolved"]
    for cohort in snapshot["cohorts"]:
        assert cohort["eligible"] == cohort["non_adverse"] + cohort["adverse"]
    assert sum(p["rows"] for p in snapshot["experiment_purposes"]) == 603587
    assert snapshot["model_release_passed"] is False
    assert snapshot["test_consumed"] is True
    assert snapshot["test"]["average_precision"] < snapshot["test"]["historical_ap_gate"]
    assert snapshot["packaging"]["public_deployment_verified"] is True
    assert (
        snapshot["packaging"]["verified_public_url"]
        == "https://creditlens-risk-evidence.streamlit.app/"
    )
    assert snapshot["packaging"]["public_verified_revision"].startswith("084e524")
    profile = snapshot["experiment_profile"]
    assert profile["rows"] == 603587
    assert sum(item["rows"] for item in profile["home_ownership"]) == 603587
    assert sum(item["rows"] for item in profile["vintage_summary"]) == 603587
    for item in profile["numeric_summary"]:
        assert item["min"] <= item["p01"] <= item["median"] <= item["p99"] <= item["max"]
    assert snapshot["release_decision"]["historical_candidate"] == "REJECT"
    assert snapshot["release_decision"]["scoring_api"] == "BLOCKED"


def test_inconsistent_snapshot_stops_before_displaying_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mismatched label aggregate must fail visibly without rendering risk metrics."""
    original_read = Path.read_text
    snapshot = json.loads(original_read(ROOT / "docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json"))
    snapshot["warehouse"]["vintages"][0]["non_adverse"] += 1

    def read_snapshot(path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        if path.name == "PORTFOLIO_RESEARCH_SNAPSHOT.json":
            return json.dumps(snapshot)
        return original_read(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", read_snapshot)
    app = AppTest.from_file(str(ROOT / "src/dashboard/app.py")).run(timeout=20)
    assert not app.exception
    assert "tidak konsisten" in app.error[0].value
    assert len(app.metric) == 0


def test_monthly_research_never_implies_a_released_model() -> None:
    """New research status must preserve evaluation and scoring holds."""
    app = AppTest.from_file(str(ROOT / "src/dashboard/app.py")).run(timeout=20)
    app.radio[0].set_value("Riset panel bulanan").run(timeout=20)
    assert not app.exception
    assert any("Evaluasi independen belum dijalankan" in item.value for item in app.caption)
    assert any("Horizon 3 bulan" in item.value for item in app.info)
    assert any("tidak mengesahkan model untuk fintech" in item.value for item in app.warning)
