"""Present traceable credit-risk research aggregates without loading borrower records.

Run from the repository root with ``python -m streamlit run src/dashboard/app.py``.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json"
REPOSITORY_URL = "https://github.com/Agathahah/creditlens"
PAGES = (
    "Ringkasan",
    "Masalah bisnis",
    "Profil dataset",
    "Data & vintage",
    "Data engineering",
    "Eksperimen model",
    "API & keamanan",
    "Deployment",
    "Kesimpulan",
)
COLORS = ["#007f79", "#d45858", "#c6983e"]
Evidence = dict[str, Any]


def _number(value: int) -> str:
    """Format a count with Indonesian thousands separators."""
    return f"{value:,}".replace(",", ".")


def _source(evidence: Evidence, key: str, description: str) -> None:
    """Link a chart or claim to its public source."""
    path = evidence["dashboard_sources"][key]
    st.caption(f"{description} · [Sumber]({REPOSITORY_URL}/blob/codex/m0-mentoring/{path})")


def _insight(title: str, body: str) -> None:
    """Render escaped static insight text with a visible reading hierarchy."""
    st.markdown(
        f'<div class="insight"><strong>{escape(title)}</strong><p>{escape(body)}</p></div>',
        unsafe_allow_html=True,
    )


def _flow(steps: list[tuple[str, str]]) -> None:
    """Display ordered stages, including their scope, without executable diagram code."""
    parts = [
        f'<div class="flow-step"><b>{escape(title)}</b><small>{escape(body)}</small></div>'
        for title, body in steps
    ]
    st.markdown(
        '<div class="flow">' + '<span class="flow-arrow">→</span>'.join(parts) + "</div>",
        unsafe_allow_html=True,
    )


def _chart(frame: pd.DataFrame, spec: Evidence, height: int = 250) -> None:
    """Display an aggregate Vega-Lite chart with consistent axes and tooltips."""
    st.vega_lite_chart(
        frame,
        {
            "height": height,
            "config": {
                "view": {"stroke": None},
                "axis": {"labelColor": "#536c7c", "titleColor": "#536c7c", "gridColor": "#edf1f5"},
                "legend": {"orient": "bottom", "labelColor": "#536c7c"},
            },
            **spec,
        },
        use_container_width=True,
        theme=None,
    )


def _validate(evidence: Evidence) -> None:
    """Reject inconsistent aggregates instead of rendering a plausible substitute."""
    warehouse = evidence["warehouse"]
    for row in warehouse["vintages"]:
        if row["labeled"] != row["non_adverse"] + row["adverse"]:
            raise ValueError("Label vintage tidak konsisten.")
        if any(row[key] < 0 for key in ("rows", "labeled", "non_adverse", "adverse", "unresolved")):
            raise ValueError("Jumlah pinjaman tidak boleh negatif.")
        if row["rows"] != row["non_adverse"] + row["adverse"] + row["unresolved"]:
            raise ValueError("Distribusi vintage tidak berekonsiliasi.")
    for key in ("rows", "non_adverse", "adverse", "unresolved"):
        if sum(row[key] for row in warehouse["vintages"]) != warehouse[key]:
            raise ValueError("Total warehouse tidak sesuai dengan vintage.")
    for cohort in evidence["cohorts"]:
        if cohort["eligible"] != cohort["non_adverse"] + cohort["adverse"]:
            raise ValueError("Jumlah cohort eksperimen tidak konsisten.")
    if sum(row["rows"] for row in evidence["experiment_purposes"]) != sum(
        cohort["eligible"] for cohort in evidence["cohorts"]
    ):
        raise ValueError("Distribusi tujuan pinjaman tidak sesuai dengan cohort.")
    if evidence["model_release_passed"] or not evidence["test_consumed"]:
        raise ValueError("Snapshot historis ini harus mempertahankan hasil rilis M1.")
    profile = evidence["experiment_profile"]
    eligible = sum(cohort["eligible"] for cohort in evidence["cohorts"])
    if (
        profile["rows"] != eligible
        or sum(item["rows"] for item in profile["vintage_summary"]) != eligible
    ):
        raise ValueError("Profil eksperimen tidak sesuai dengan cohort.")
    if sum(item["rows"] for item in profile["home_ownership"]) != eligible:
        raise ValueError("Kategori profil tidak sesuai dengan cohort.")
    for item in profile["numeric_summary"]:
        if not item["min"] <= item["p01"] <= item["median"] <= item["p99"] <= item["max"]:
            raise ValueError("Persentil fitur tidak berurutan.")
    release = evidence["release_decision"]
    if release["historical_candidate"] != "REJECT" or release["scoring_api"] != "BLOCKED":
        raise ValueError("Keputusan rilis harus sesuai dengan gate model yang gagal.")
    package = evidence["packaging"]
    if package["public_deployment_verified"]:
        public_url = package.get("verified_public_url")
        if not isinstance(public_url, str) or not public_url.startswith("https://"):
            raise ValueError("Deployment publik memerlukan URL HTTPS yang diverifikasi.")
        if not package.get("public_verified_at") or not package.get("public_verified_revision"):
            raise ValueError("Bukti deployment publik belum lengkap.")
        if not str(package.get("public_ci_run_url", "")).startswith(
            "https://github.com/Agathahah/creditlens/actions/runs/"
        ):
            raise ValueError("Run CI untuk dashboard publik belum tercatat.")
    elif package.get("verified_public_url") is not None:
        raise ValueError("URL publik belum boleh diumumkan tanpa verifikasi.")


def _population(evidence: Evidence) -> pd.DataFrame:
    """Filter only warehouse aggregates, leaving historical evaluation unchanged."""
    frame = pd.DataFrame(evidence["warehouse"]["vintages"])
    left, middle, right = st.columns([1, 1, 2])
    year = left.selectbox(
        "Tahun penerbitan", ["Semua tahun", *map(str, sorted(frame.year.unique()))]
    )
    term = middle.selectbox("Tenor pinjaman", ["Semua tenor", "36 bulan", "60 bulan"])
    right.caption(
        "Filter berlaku pada distribusi warehouse. Angka eksperimen/model memiliki "
        "populasi tersendiri dan tidak dihitung ulang dari filter ini."
    )
    if year != "Semua tahun":
        frame = frame.loc[frame.year == int(year)]
    if term != "Semua tenor":
        frame = frame.loc[frame.term == int(term[:2])]
    if frame.empty:
        st.info("Tidak ada pinjaman untuk kombinasi tahun dan tenor ini.")
        st.stop()
    frame = frame.copy()
    frame["unresolved_pct"] = 100 * frame.unresolved / frame.rows
    return frame


def _population_metrics(frame: pd.DataFrame) -> None:
    """Show counts and a rate with an explicit matching population denominator."""
    rows, labeled, unresolved, adverse = (
        int(frame[key].sum()) for key in ("rows", "labeled", "unresolved", "adverse")
    )
    columns = st.columns(4)
    columns[0].metric("Pinjaman dalam filter", _number(rows))
    columns[1].metric("Outcome berlabel 0 / 1", _number(labeled))
    columns[2].metric("Belum/tidak definitif", _number(unresolved))
    columns[3].metric("Adverse di antara berlabel", f"{100 * adverse / labeled:.2f}%")
    st.caption(
        f"Denominator jumlah: {_number(rows)} pinjaman. Denominator adverse: "
        f"{_number(labeled)} pinjaman berlabel. NULL tidak diperlakukan sebagai label 0."
    )


def _volume_chart(frame: pd.DataFrame) -> None:
    """Show annual warehouse size without confusing volume with model performance."""
    yearly = frame.groupby("year", as_index=False)[["rows", "labeled", "unresolved"]].sum()
    _chart(
        yearly,
        {
            "mark": {
                "type": "bar",
                "color": COLORS[0],
                "cornerRadiusTopLeft": 4,
                "cornerRadiusTopRight": 4,
            },
            "encoding": {
                "x": {
                    "field": "year",
                    "type": "ordinal",
                    "title": "Tahun penerbitan",
                    "axis": {"labelAngle": 0},
                },
                "y": {
                    "field": "rows",
                    "type": "quantitative",
                    "title": "Jumlah pinjaman",
                    "axis": {"format": "~s"},
                },
                "tooltip": [
                    {"field": "year", "title": "Vintage"},
                    {"field": "rows", "title": "Pinjaman", "format": ","},
                    {"field": "unresolved", "title": "Belum/tidak definitif", "format": ","},
                ],
            },
        },
    )


def _label_chart(frame: pd.DataFrame) -> None:
    """Show all three label classes, including unresolved outcomes."""
    counts = pd.DataFrame(
        {
            "Status": [
                "Fully Paid · 0",
                "Charged Off / Default · 1",
                "Belum/tidak definitif · NULL",
            ],
            "Jumlah": [
                int(frame.non_adverse.sum()),
                int(frame.adverse.sum()),
                int(frame.unresolved.sum()),
            ],
        }
    )
    counts["Persentase"] = 100 * counts.Jumlah / counts.Jumlah.sum()
    _chart(
        counts,
        {
            "mark": {"type": "arc", "innerRadius": 65, "outerRadius": 100},
            "encoding": {
                "theta": {"field": "Jumlah", "type": "quantitative"},
                "color": {
                    "field": "Status",
                    "scale": {"domain": counts.Status.tolist(), "range": COLORS},
                    "legend": {"direction": "vertical", "labelLimit": 300},
                },
                "tooltip": [
                    {"field": "Status"},
                    {"field": "Jumlah", "format": ","},
                    {"field": "Persentase", "format": ".2f"},
                ],
            },
        },
    )


def _overview(evidence: Evidence) -> None:
    """Connect the business question, data coverage, experiment, and release decision."""
    st.markdown(
        "**Masalah bisnis yang ingin diuji:** tim risiko fintech perlu memprioritaskan "
        "review manual ketika banyak permohonan masuk. CreditLens meneliti apakah "
        "fitur yang tersedia saat aplikasi dapat membantu mengurutkan risiko. "
        "Kandidat saat ini belum layak dipakai untuk keputusan nyata."
    )
    frame = _population(evidence)
    _population_metrics(frame)
    main, side = st.columns([3, 1])
    with main:
        left, right = st.columns([1.3, 1])
        with left, st.container(border=True, key="panel_01"):
            st.subheader("Seberapa besar data yang tersedia?")
            _volume_chart(frame)
            st.caption(
                "Volume warehouse sesuai filter; lebih banyak data belum menjamin outcome lengkap."
            )
        with right, st.container(border=True, key="panel_02"):
            st.subheader("Apa yang sudah diketahui?")
            _label_chart(frame)
            st.caption("Proporsi terhadap seluruh pinjaman dalam filter, termasuk outcome NULL.")
        _source(evidence, "profile", "Profil agregat 23 Sep 2026; bukan data live")
        with st.container(border=True, key="panel_03"):
            st.subheader("Dari data besar ke keputusan rilis")
            _flow(
                [
                    ("2,26 juta pinjaman", "Warehouse 2007–2018"),
                    ("603.587 eligible", "Eksperimen 36 bulan, 2011–2015"),
                    ("AP test 0,2197", "Di bawah gate 0,25"),
                    ("Tahan scoring", "Holdout independen baru diperlukan"),
                ]
            )
            st.caption(
                "Angka alur adalah cakupan penuh proyek dan tidak mengikuti filter warehouse."
            )
    with side, st.container(border=True, key="panel_04"):
        st.subheader("Insight utama")
        _insight(
            "40,49% belum/tidak definitif",
            "915.318 dari 2.260.668 pinjaman tidak diberi label 0 atau 1.",
        )
        _insight(
            "Model belum layak dirilis",
            "Kandidat memiliki sinyal ranking, tetapi gagal gate AP dan threshold "
            "lama menghasilkan nol prediksi positif.",
        )
        _insight(
            "Manfaat untuk tim fintech",
            "Menemukan batas data dan mencegah model yang belum teruji masuk ke "
            "alur keputusan kredit.",
        )
        st.caption(
            "Insight ini merangkum cakupan penuh; bukan estimasi kerugian atau "
            "dampak bisnis terukur."
        )
    st.markdown(
        '<div class="verdict"><b>Kesimpulan saat ini:</b> pipeline data dan demo agregat '
        "dapat ditinjau. Model scoring masih tertahan; dashboard bukan alat "
        "persetujuan kredit.</div>",
        unsafe_allow_html=True,
    )


def _business_problem(evidence: Evidence) -> None:
    """Explain the proposed lender workflow and distinguish it from measured impact."""
    st.subheader("Masalah yang biasanya dihadapi tim risiko")
    st.write(
        "Fintech pemberi pinjaman menerima permohonan dengan kapasitas review yang terbatas. "
        "Tim perlu menentukan kasus mana yang patut diperiksa lebih dahulu sambil "
        "menghindari kerugian dari risiko yang terlewat dan dampak buruk ketika "
        "pemohon yang layak ditandai keliru. Angka biaya kedua kesalahan belum tersedia."
    )
    left, right = st.columns(2)
    with left, st.container(border=True, key="business_problem"):
        st.subheader("Keputusan yang ingin dibantu")
        _flow(
            [
                ("Aplikasi masuk", "Fitur sebelum pricing"),
                ("Skor risiko", "Jika model lolos gate"),
                ("Analis manusia", "Review lebih dulu"),
            ]
        )
        st.write(
            "Output yang dirancang adalah estimasi risiko untuk prioritas review. "
            "Analis tetap menilai permohonan. Tidak ada aturan otomatis approve/reject "
            "atau rekomendasi suku bunga dalam proyek ini."
        )
    with right, st.container(border=True, key="business_limit"):
        st.subheader("Bukti yang belum dimiliki")
        st.markdown(
            "- Data hanya berisi pinjaman yang **sudah diterima** oleh pemberi pinjaman lama.\n"
            "- Hasil pinjaman yang **ditolak** tidak diketahui.\n"
            "- Tanggal outcome dan horizon 36 bulan belum dapat diaudit.\n"
            "- Biaya review, kerugian kredit, fairness, serta dampak bisnis belum diukur."
        )
        st.caption(
            "Karena itu, hasil riset tidak dapat digeneralisasi ke semua pemohon "
            "atau diklaim telah menurunkan kerugian fintech."
        )
    st.subheader("Apa ukuran keberhasilan untuk use case ini?")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Ukuran": "AP + prevalence",
                    "Mengapa": "Kualitas ranking kasus adverse pada kelas minoritas",
                    "Status": "Historis tersedia; gate gagal",
                },
                {
                    "Ukuran": "Kalibrasi + Brier",
                    "Mengapa": "Apakah probabilitas risiko bisa dipercaya",
                    "Status": "Brier historis tersedia; validasi kalibrasi belum lengkap",
                },
                {
                    "Ukuran": "Recall, precision, beban review",
                    "Mengapa": "Jumlah kasus terdeteksi vs kapasitas analis",
                    "Status": "Threshold lama gagal; biaya bisnis belum ada",
                },
                {
                    "Ukuran": "Fairness, latency, audit & rollback",
                    "Mengapa": "Operasi yang aman dan dapat diperiksa",
                    "Status": "Belum dibuktikan pada layanan aktif",
                },
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.info(
        "Keputusan produk saat ini: lanjutkan penelitian dan siapkan demo baca-saja. "
        "Scoring API tetap tertahan sampai data, evaluasi independen, bundle "
        "dan operasi lolos gate."
    )
    _source(evidence, "model", "Bukti M1 historis dan batas penggunaan")


def _dataset_profile(evidence: Evidence) -> None:
    """Show the accepted-loan experiment's descriptive statistics and modeling consequences."""
    profile = evidence["experiment_profile"]
    st.write(
        "Sheet ini menjelaskan 603.587 pinjaman diterima yang eligible untuk eksperimen M1: "
        "tenor 36 bulan, terbit 2011–2015, outcome 0/1, pendapatan positif. "
        "Angka berasal dari profil baca-saja 23 September 2026, bukan query live."
    )
    columns = st.columns(4)
    columns[0].metric("Eligible M1", _number(profile["rows"]))
    columns[1].metric("Fitur numerik whitelist", "12")
    columns[2].metric("Fitur kategorikal", "2")
    columns[3].metric("Tujuan pinjaman terbesar", "Konsolidasi utang")
    st.caption(
        "Populasi dan fitur ini berbeda dari 2.260.668 baris warehouse. "
        "Kelengkapan fitur pada eligible tidak membuktikan ketersediaannya saat aplikasi historis."
    )
    left, right = st.columns([1.25, 1])
    vintage = pd.DataFrame(profile["vintage_summary"])
    with left, st.container(border=True, key="profile_vintage"):
        st.subheader("Bagaimana komposisi berubah per tahun?")
        _chart(
            vintage,
            {
                "mark": {"type": "line", "point": {"filled": True}, "color": COLORS[0]},
                "encoding": {
                    "x": {"field": "year", "type": "ordinal", "title": "Tahun penerbitan"},
                    "y": {
                        "field": "adverse_pct",
                        "type": "quantitative",
                        "title": "% adverse pada eligible",
                        "scale": {"zero": False},
                    },
                    "tooltip": [
                        {"field": "year", "title": "Vintage"},
                        {"field": "rows", "title": "Eligible", "format": ","},
                        {"field": "adverse_pct", "title": "% adverse", "format": ".3f"},
                        {
                            "field": "annual_inc_median",
                            "title": "Median annual income",
                            "format": ",",
                        },
                    ],
                },
            },
            height=220,
        )
        st.caption(
            "Pembagi tiap titik: eligible berlabel pada vintage itu. "
            "Perubahan proporsi tidak membuktikan perubahan risiko semua pemohon."
        )
    with right, st.container(border=True, key="profile_home"):
        st.subheader("Kepemilikan rumah dalam subset")
        home = pd.DataFrame(profile["home_ownership"]).nlargest(3, "rows")
        _chart(
            home,
            {
                "mark": {"type": "bar", "color": COLORS[0]},
                "encoding": {
                    "y": {"field": "category", "type": "nominal", "sort": "-x", "title": None},
                    "x": {
                        "field": "rows",
                        "type": "quantitative",
                        "title": "Pinjaman",
                        "axis": {"format": "~s"},
                    },
                    "tooltip": [{"field": "category"}, {"field": "rows", "format": ","}],
                },
            },
            height=220,
        )
        st.caption("Tiga kategori terbesar; seluruh kategori dan jumlahnya ada pada tabel unduhan.")
    st.subheader("Angka deskriptif fitur numerik")
    st.write(
        "Median adalah nilai tengah; p01 dan p99 menunjukkan batas persentil 1% dan 99%. "
        "Rentang maksimum yang jauh dari p99 menandai nilai ekstrem yang perlu ditinjau."
    )
    summary = pd.DataFrame(profile["numeric_summary"])
    st.dataframe(
        summary.rename(
            columns={
                "feature": "Fitur",
                "unit": "Satuan",
                "min": "Minimum",
                "p01": "p01",
                "median": "Median",
                "p99": "p99",
                "max": "Maksimum",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.download_button(
        "Unduh sheet deskriptif CSV",
        summary.to_csv(index=False),
        "creditlens-m1-feature-profile.csv",
        "text/csv",
    )
    _insight(
        "Nilai ekstrem perlu ditangani",
        "Pendapatan maksimum 9 juta USD vs p99 250 ribu; DTI maksimum 999; "
        "revolving utilization maksimum 892,3. Median dan RobustScaler fit hanya di train, "
        "tetapi aturan validasi nilai ekstrem untuk penggunaan nyata masih perlu diuji.",
    )
    st.write(
        "Fitur numerik dan dua kategori (home ownership, tujuan pinjaman) masuk ke "
        "preprocessing yang fit hanya pada train. Status akhir, pembayaran, recovery, "
        "grade, pricing, dan ID dikeluarkan karena tidak layak sebagai informasi saat aplikasi."
    )
    _source(evidence, "query", "SQL agregat untuk mereproduksi profil, tanpa baris individual")
    _source(evidence, "model_code", "Daftar fitur dan preprocessing aktual")


def _data(evidence: Evidence) -> None:
    """Expose vintage maturity and the different warehouse and experiment populations."""
    st.write(
        "Vintage adalah kelompok pinjaman berdasarkan tahun penerbitan. Pertanyaan utama: "
        "apakah kelompok yang lebih baru sudah memiliki outcome yang cukup lengkap?"
    )
    frame = _population(evidence)
    _population_metrics(frame)
    left, right = st.columns([1.5, 1])
    with left, st.container(border=True, key="panel_05"):
        st.subheader("Outcome belum definitif menurut vintage & tenor")
        _chart(
            frame,
            {
                "mark": {"type": "rect", "cornerRadius": 3},
                "encoding": {
                    "x": {
                        "field": "year",
                        "type": "ordinal",
                        "title": "Vintage",
                        "axis": {"labelAngle": 0},
                    },
                    "y": {"field": "term", "type": "ordinal", "title": "Tenor (bulan)"},
                    "color": {
                        "field": "unresolved_pct",
                        "type": "quantitative",
                        "title": "% NULL",
                        "scale": {"domain": [0, 100], "range": ["#edf6f5", "#007f79"]},
                    },
                    "tooltip": [
                        {"field": "year"},
                        {"field": "term"},
                        {"field": "rows", "format": ","},
                        {"field": "unresolved_pct", "title": "% NULL", "format": ".2f"},
                    ],
                },
            },
            height=170,
        )
        st.caption("Denominator tiap sel: seluruh pinjaman dengan tahun dan tenor tersebut.")
    with right, st.container(border=True, key="panel_06"):
        st.subheader("Mengapa data terbaru belum menjadi test baru?")
        _insight(
            "2018 / 36 bulan: 88,03% NULL",
            "Mayoritas outcome belum/tidak definitif dalam snapshot. Tahun "
            "penerbitan baru saja belum memenuhi syarat holdout.",
        )
        st.write(
            "Tanggal snapshot outcome dan waktu terjadinya gagal bayar belum "
            "terverifikasi. Tenor 36 bulan tidak otomatis berarti risiko pada "
            "horizon 36 bulan."
        )
    _source(evidence, "profile", "Sel heatmap berasal dari profil warehouse")
    with st.expander("Lihat angka dalam filter / unduh agregat"):
        columns = {
            "year": "Vintage",
            "term": "Tenor",
            "rows": "Pinjaman",
            "labeled": "Berlabel",
            "unresolved": "NULL",
            "adverse": "Adverse",
            "unresolved_pct": "% NULL",
        }
        export = frame[list(columns)].rename(columns=columns)
        st.dataframe(export, hide_index=True, width="stretch")
        st.download_button(
            "Unduh distribusi agregat CSV",
            export.to_csv(index=False),
            "creditlens-vintage-aggregates.csv",
            "text/csv",
        )
    st.subheader("Populasi eksperimen memiliki aturan tersendiri")
    st.write(
        "M1 lokal memakai pinjaman diterima, tenor 36 bulan, outcome 0/1, dan "
        "pendapatan positif. Total eligible 603.587; bukan seluruh warehouse."
    )
    left, right = st.columns(2)
    with left, st.container(border=True, key="panel_07"):
        st.subheader("Pembagian waktu")
        cohorts = pd.DataFrame(evidence["cohorts"])
        cohorts["adverse_pct"] = 100 * cohorts.adverse / cohorts.eligible
        st.dataframe(
            cohorts.rename(
                columns={
                    "split": "Peran",
                    "vintage": "Vintage",
                    "eligible": "Eligible",
                    "adverse": "Adverse",
                    "non_adverse": "Non-adverse",
                    "adverse_pct": "% adverse",
                }
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "147 outcome NULL dan 2 pendapatan tidak valid dikeluarkan dari vintage test 2015."
        )
    with right, st.container(border=True, key="panel_08"):
        st.subheader("Untuk apa pinjaman digunakan?")
        purposes = pd.DataFrame(evidence["experiment_purposes"])
        top = purposes.nlargest(5, "rows").copy()
        top["purpose"] = top.purpose.str.replace("_", " ")
        _chart(
            top,
            {
                "mark": {"type": "bar", "color": COLORS[0], "cornerRadiusEnd": 4},
                "encoding": {
                    "y": {"field": "purpose", "type": "nominal", "sort": "-x", "title": None},
                    "x": {
                        "field": "rows",
                        "type": "quantitative",
                        "title": "Jumlah pinjaman",
                        "axis": {"format": "~s"},
                    },
                    "tooltip": [{"field": "purpose"}, {"field": "rows", "format": ","}],
                },
            },
            height=200,
        )
        st.caption(
            "Lima tujuan terbesar dari seluruh 603.587 eligible M1; grafik ini "
            "tidak mengikuti filter warehouse."
        )
    _source(evidence, "query", "Query read-only untuk mereproduksi distribusi")
    st.info(
        "Distribusi historis ini tidak menunjukkan hubungan sebab-akibat dan bukan "
        "profil semua pemohon: data hanya mencakup pinjaman yang diterima."
    )


def _engineering(evidence: Evidence) -> None:
    """Show lineage, reconciliation, and the data-recovery controls actually exercised."""
    st.write(
        "Tujuan data engineering: membuat setiap pinjaman dapat ditelusuri dari "
        "sumber hingga fitur, dengan label yang konsisten dan pemulihan yang dapat "
        "diuji."
    )
    result = evidence["engineering"]
    _flow(
        [
            ("CSV sumber", "2.260.701 baris"),
            ("raw", "Simpan data sumber"),
            ("staging", "Bersihkan & tetapkan label"),
            ("mart", "Fitur dan kontrak downstream"),
        ]
    )
    columns = st.columns(4)
    columns[0].metric("Baris per layer", _number(2260668))
    columns[1].metric("Dikeluarkan saat ingestion", "33")
    columns[2].metric("Mismatch label setelah rebuild", "0")
    columns[3].metric("Tes dbt pada rollout", str(result["dbt_passed_tests"]))
    st.caption(
        "33 baris sumber tidak memenuhi field dasar wajib. Kesamaan jumlah bukan "
        "bukti semua nilai sudah benar."
    )
    left, right = st.columns(2)
    with left, st.container(border=True, key="panel_09"):
        st.subheader("Rekonsiliasi empat layer")
        st.dataframe(
            pd.DataFrame(
                [{"Layer": key, "Baris": value} for key, value in result["layer_rows"].items()]
            ),
            hide_index=True,
            width="stretch",
        )
        st.write("Kontrak label: Fully Paid → 0; Charged Off/Default → 1; status lainnya → NULL.")
        _insight(
            "21.467 label diperbaiki",
            "Late (31–120 days) dipindahkan dari label adverse ke NULL agar kontrak"
            " label konsisten.",
        )
    with right, st.container(border=True, key="panel_10"):
        st.subheader("Kontrol perubahan yang telah dijalankan")
        st.markdown(
            "- Preflight target, revisi, kapasitas disk, dan hash backup.\n- "
            "Simulasi PostgreSQL terisolasi serta uji restore.\n- Rebuild tiga layer"
            " yang disetujui.\n- Rekonsiliasi label dan hash baris non-label "
            "sebelum/sesudah."
        )
        st.caption(
            "Bukti rollout 22 Sep 2026. Backup mencakup relasi tertentu; pemulihan "
            "owner/ACL seluruh server belum dibuktikan."
        )
    _source(evidence, "warehouse", "Laporan rollout dan keterbatasan pemulihan")
    st.subheader("Pencegahan kebocoran informasi pada model")
    _flow(
        [
            ("Tentukan eligibility", "Tanpa mengubah label NULL menjadi 0"),
            ("Split waktu", "Train → validation → test"),
            ("Fit di train", "Median, scaling, kategori"),
            ("Transform konsisten", "Aturan train untuk validation/test"),
        ]
    )
    st.write(
        "Whitelist fitur mengecualikan status akhir, pembayaran setelah pinjaman, "
        "recoveries, identitas, dan fitur pricing. Split waktu masih memerlukan "
        "bukti bahwa label tersedia pada tanggal pelatihan historis."
    )
    _source(evidence, "model", "Implementasi M1 lokal dan batas validitas waktu")


def _model(evidence: Evidence) -> None:
    """Explain model selection and preserve the consumed test and failed release gate."""
    st.write(
        "Eksperimen menjawab: apakah fitur pada tahap aplikasi memiliki sinyal "
        "untuk mengurutkan outcome adverse? Hasilnya belum membuktikan probabilitas"
        " gagal bayar 36 bulan yang terkalibrasi."
    )
    left, right = st.columns([1.4, 1])
    validation = pd.DataFrame(evidence["validation"])
    with left, st.container(border=True, key="panel_11"):
        st.subheader("1. Pemilihan menggunakan validation 2014")
        _chart(
            validation,
            {
                "mark": {"type": "bar", "color": COLORS[0], "cornerRadiusEnd": 4},
                "encoding": {
                    "y": {"field": "candidate", "type": "nominal", "sort": "-x", "title": None},
                    "x": {
                        "field": "average_precision",
                        "type": "quantitative",
                        "title": "Average precision (AP)",
                        "scale": {"domain": [0, 0.26]},
                    },
                    "tooltip": [
                        {"field": "candidate"},
                        {"field": "average_precision", "format": ".4f"},
                        {"field": "roc_auc", "format": ".4f"},
                        {"field": "brier", "format": ".4f"},
                    ],
                },
            },
            height=180,
        )
        st.caption(
            "AP dipilih karena outcome adverse adalah kelas minoritas. AP lebih tinggi lebih baik."
        )
    with right, st.container(border=True, key="panel_12"):
        st.subheader("Mengapa bounded XGBoost?")
        _insight(
            "AP validation tertinggi: 0,2046",
            "Aturan memilih AP tertinggi, dengan Brier sebagai pembanding jika AP "
            "setara. Training dibatasi sumber daya.",
        )
        st.write(
            "Selisih AP dari logistic regression hanya 0,0030. Ini belum "
            "menunjukkan manfaat bisnis yang terukur atau membenarkan kompleksitas "
            "saat deployment."
        )
    st.subheader("Bagaimana ketiga kandidat bekerja pada data ini?")
    candidates = {row["candidate"]: row for row in evidence["validation"]}
    first, second, third = st.columns(3)
    with first, st.container(border=True, key="model_constant"):
        st.markdown("**1 · Model konstan**")
        st.metric("AP validation", f"{candidates['Constant']['average_precision']:.4f}")
        st.write(
            "Mengulang proporsi adverse pada train untuk setiap pinjaman. Tidak melihat "
            "pendapatan, riwayat kredit, atau kategori."
        )
        st.caption(
            "Baseline wajib: AP 0,1373 ≈ prevalence validation 13,73%; ROC-AUC 0,5. "
            "Model lain harus mengalahkan patokan ini."
        )
    with second, st.container(border=True, key="model_logistic"):
        st.markdown("**2 · Logistic Regression**")
        st.metric("AP validation", f"{candidates['Logistic Regression']['average_precision']:.4f}")
        st.write(
            "Menggabungkan fitur numerik dan kategori menjadi skor linear, lalu "
            "mengubahnya menjadi probabilitas. Median, scaling, dan kategori fit "
            "hanya pada train."
        )
        st.caption(
            "AP 0,2016; ROC-AUC 0,6291; Brier 0,1158. Baseline yang relatif "
            "mudah diaudit, tetapi hubungan kompleks tidak otomatis tertangkap."
        )
    with third, st.container(border=True, key="model_xgb"):
        st.markdown("**3 · Bounded XGBoost**")
        st.metric("AP validation", f"{candidates['Bounded XGBoost']['average_precision']:.4f}")
        st.write(
            "Menggabungkan 150 pohon keputusan kecil (kedalaman maksimal 4) "
            "untuk mempelajari ambang dan interaksi antarfitur dalam whitelist."
        )
        st.caption(
            "AP 0,2046; ROC-AUC 0,6356; Brier 0,1155. Kenaikan AP 0,0030 "
            "dari Logistic Regression terlalu kecil untuk menyimpulkan manfaat operasi."
        )
    st.write(
        "Semua model memakai cohort dan split yang sama. Yang dibandingkan di sini hanya "
        "hasil **validation 2014**; laporan frozen test yang tersedia hanya "
        "untuk kandidat terpilih. "
        "Tidak ada hasil test terpisah untuk model konstan atau Logistic Regression."
    )
    _source(evidence, "model_code", "Implementasi estimator dan preprocessing tiap kandidat")
    with st.expander("Metrik lain dan angka lengkap"):
        st.dataframe(validation, hide_index=True, width="stretch")
        st.write(
            "ROC-AUC menilai ranking adverse dibanding non-adverse; lebih tinggi "
            "lebih baik. Brier mengukur kuadrat kesalahan probabilitas; lebih "
            "rendah lebih baik. AP bukan luas kurva PR dengan integrasi trapezoid."
        )
    result = evidence["test"]
    st.subheader("2. Ujian akhir: frozen test 2015")
    columns = st.columns(4)
    columns[0].metric("AP frozen test historis", f"{result['average_precision']:.4f}")
    columns[1].metric("Gate AP historis", f"{result['historical_ap_gate']:.2f}")
    columns[2].metric("ROC-AUC test", f"{result['roc_auc']:.4f}")
    columns[3].metric("Prediksi positif / threshold lama", str(result["predicted_positive"]))
    st.warning(
        "Kandidat M1 gagal gate rilis: AP 0,2197 < 0,25. Threshold lama "
        "menghasilkan nol prediksi positif dan melewatkan seluruh 42.131 kasus "
        "adverse test."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Kondisi aktual": "Non-adverse",
                    "Prediksi adverse": 0,
                    "Prediksi non-adverse": 240893,
                },
                {"Kondisi aktual": "Adverse", "Prediksi adverse": 0, "Prediksi non-adverse": 42131},
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption("Confusion matrix threshold lama 0,4829: TN=240.893, FP=0, FN=42.131, TP=0.")
    st.caption(
        f"CI bootstrap baris 95% untuk AP: {result['ap_ci_low']:.4f}–"
        f"{result['ap_ci_high']:.4f}. Bukan bootstrap peminjam; "
        "independensi peminjam belum terbukti."
    )
    st.error(
        "Frozen test 2015 sudah terpakai. Hasil ini hanya ditampilkan dari laporan;"
        " test tidak boleh dipakai lagi untuk memilih fitur, model, atau threshold."
    )
    st.write(
        "Frozen test adalah data ujian yang dikunci selama pemilihan model. Begitu "
        "hasilnya memicu revisi, diperlukan holdout independen baru. Memilih "
        "threshold baru pada test yang sama akan membuat penilaian terlalu "
        "optimistis."
    )
    _source(
        evidence,
        "model",
        "Evaluasi historis 23 Sep 2026; tidak menjalankan training atau evaluasi ulang",
    )


def _api(evidence: Evidence) -> None:
    """Separate tested API rejection from unverified operational security controls."""
    st.write(
        "API adalah jalur integrasi untuk aplikasi fintech. Saat ini kontrak "
        "penolakan model tersedia; layanan prediksi dengan bundle yang layak rilis "
        "belum dibuktikan."
    )
    _flow(
        [
            ("Request aplikasi", "Input sesuai schema"),
            ("Cek readiness", "Bundle & daftar fitur"),
            ("Jika belum terverifikasi", "Tolak scoring: HTTP 503"),
            ("Scoring setelah gate", "Parity & rilis masih diperlukan"),
        ]
    )
    left, right = st.columns(2)
    with left, st.container(border=True, key="panel_13"):
        st.subheader("Arti endpoint")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Endpoint": "/live", "Arti": "Proses hidup; bukan model valid"},
                    {
                        "Endpoint": "/health",
                        "Arti": "Status proses/artefak; HTTP 200 bukan persetujuan rilis",
                    },
                    {"Endpoint": "/ready", "Arti": "503 jika model/bundle belum terverifikasi"},
                    {
                        "Endpoint": "Scoring / explanation",
                        "Arti": "Menolak artefak legacy/bundle belum terverifikasi",
                    },
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption("Bukti kontrak dari tes dan kode; halaman ini tidak melakukan probe API live.")
        with st.expander("Contoh kontrak /ready: HTTP 503"):
            st.json({"status": "not_ready", "model_loaded": False, "bundle_verified": False})
            st.caption("Respons pada fixture registry kosong; bukan respons API live.")
        _source(evidence, "api", "Tes readiness, penolakan, dan fixture sintetis")
    with right, st.container(border=True, key="panel_14"):
        st.subheader("Security check: apa yang ada buktinya?")
        st.markdown(
            "- Dashboard hanya membaca snapshot agregat.\n- Image dashboard memakai "
            "user non-root.\n- Smoke test memeriksa tidak adanya lima path aplikasi "
            "terlarang.\n- API menolak scoring pada model legacy/bundle belum "
            "terverifikasi."
        )
        st.caption(
            "Path yang diperiksa: data, models, .git, .env, .local-backups di /app."
            " Pemeriksaan ini terbatas, bukan audit seluruh isi image."
        )
    st.subheader("Kontrol yang belum diverifikasi untuk production")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Kontrol": "Autentikasi, otorisasi, rate limit, TLS",
                    "Status": "Belum dibuktikan pada API aktif",
                },
                {
                    "Kontrol": "Pemindaian dependency/CVE & image",
                    "Status": "Belum ada laporan audit yang ditampilkan",
                },
                {
                    "Kontrol": "Validasi manifest, parity training-serving",
                    "Status": "Belum lengkap untuk bundle rilis",
                },
                {
                    "Kontrol": "Monitoring, alert, rollback & audit log",
                    "Status": "Belum dibuktikan pada layanan aktif",
                },
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.info(
        "Tidak ada skor keamanan keseluruhan. Tes kontrak dan packaging yang lolos "
        "tidak setara dengan penetration test atau persetujuan production."
    )


def _deployment(evidence: Evidence) -> None:
    """Display separate packaging, public-demo and scoring-release evidence."""
    package = evidence["packaging"]
    st.write(
        "Deployment dashboard menyajikan bukti riset agregat. Deployment API "
        "scoring memerlukan model dan kontrol operasional yang lolos gate "
        "tersendiri."
    )
    columns = st.columns(3)
    columns[0].metric("Docker dashboard historis", "LULUS")
    columns[1].metric(
        "Deployment publik",
        "TERVERIFIKASI" if package["public_deployment_verified"] else "BELUM DIVERIFIKASI",
    )
    columns[2].metric("Rilis model scoring", "TERTAHAN")
    st.caption(
        f"Smoke Docker lokal diperiksa {package['evidence_reported_at']} "
        f"untuk revisi {package['code_revision'][:7]}. "
        + (
            f"Desain sembilan halaman lulus CI pada revisi "
            f"{package['public_verified_revision'][:7]} dan URL publik diuji terpisah."
            if package["public_deployment_verified"]
            else "Desain dashboard baru masih perlu build dan CI setelah commit."
        )
    )
    left, right = st.columns(2)
    with left, st.container(border=True, key="panel_15"):
        st.subheader("Bukti Docker & CI")
        checks = package["checks"]
        st.dataframe(
            pd.DataFrame(
                [
                    {"Pemeriksaan": "Container health", "Hasil": checks["docker_health"]},
                    {"Pemeriksaan": "HTTP health", "Hasil": str(checks["http_health"])},
                    {"Pemeriksaan": "User non-root", "Hasil": str(checks["non_root_user"])},
                    {
                        "Pemeriksaan": "Lima path /app terlarang tidak ada",
                        "Hasil": str(checks["forbidden_app_paths_absent"]),
                    },
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        st.markdown(f"[Lihat CI versi {package['ci_head']}]({package['ci_run_url']})")
        if package["public_deployment_verified"]:
            st.markdown(f"[Lihat CI dashboard publik]({package['public_ci_run_url']})")
        with st.expander("Identitas image yang diuji"):
            st.code(package["image_id"], language="text")
        _source(evidence, "packaging", "Prosedur build, smoke test, dan verifikasi publik")
    with right, st.container(border=True, key="panel_16"):
        st.subheader("Di mana dashboard dapat dibuka?")
        if package["public_deployment_verified"]:
            st.link_button("Buka demo publik", package["verified_public_url"])
            st.caption(
                f"Diverifikasi {package['public_verified_at']} pada revisi "
                f"{package['public_verified_revision'][:7]}. Versi lebih baru perlu dicek ulang."
            )
        else:
            st.write(
                "Localhost hanya dapat dibuka di komputer yang menjalankan server. URL "
                "publik belum tercatat sebagai deployment yang terverifikasi dalam "
                "snapshot ini."
            )
        st.write(
            "Untuk demo publik: push desain ini → CI dashboard lolos → deploy "
            "entrypoint src/dashboard/app.py → periksa URL dari browser tanpa login"
            " → catat revisi dan tanggal verifikasi."
        )
        st.caption(
            "Tidak ada URL contoh yang dianggap sudah aktif. Status publik tidak "
            "otomatis berubah hanya karena halaman ini terbuka."
        )
    st.subheader("Urutan menuju layanan scoring")
    _flow(
        [
            ("Sumber holdout baru", "Hak penggunaan, as-of, maturity"),
            ("Evaluasi independen", "Ranking, kalibrasi, threshold, fairness"),
            ("Bundle & API", "Manifest, parity, security"),
            ("Operasi layanan", "Monitoring, rollback, approval"),
        ]
    )
    st.warning(
        "Model lama belum lolos. Hosting dashboard dan CI hijau tidak mengubah "
        "keputusan menahan layanan scoring."
    )
    st.subheader("Keputusan rilis model: apa yang memblokir?")
    release = evidence["release_decision"]
    st.dataframe(
        pd.DataFrame(release["required_gates"]).rename(
            columns={"gate": "Gerbang", "status": "Status", "evidence": "Alasan"}
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        f"Kandidat historis: {release['historical_candidate']}. "
        f"Scoring API: {release['scoring_api']}. "
        "Status dashboard publik adalah keputusan deployment yang terpisah."
    )
    _source(evidence, "release", "Kriteria rinci untuk memulai keputusan rilis baru")


def _conclusion(evidence: Evidence) -> None:
    """State the project value, finding, limitation, and concrete next release requirement."""
    st.subheader("Apa tujuan dan manfaat CreditLens?")
    st.write(
        "CreditLens meneliti kelayakan data dan model risiko kredit pada pinjaman "
        "yang diterima. Pipeline menghubungkan data sumber, fitur, evaluasi, dan "
        "kesiapan API agar keputusan rilis dapat dijelaskan dan diaudit."
    )
    left, right = st.columns(2)
    with left, st.container(border=True, key="panel_17"):
        st.subheader("Yang sudah dipelajari")
        _insight(
            "Dataset besar ≠ label lengkap",
            "2.260.668 pinjaman berhasil direkonsiliasi, tetapi 915.318 outcome "
            "belum/tidak definitif.",
        )
        _insight(
            "Ada sinyal, belum cukup untuk rilis",
            "AP test 0,2197 masih di bawah gate 0,25. Threshold lama gagal "
            "mendeteksi kasus adverse pada test.",
        )
        _insight(
            "Rekayasa mencegah penggunaan prematur",
            "Kontrak label, test, readiness, dan packaging membuat batas rilis "
            "terlihat sebelum scoring digunakan.",
        )
    with right, st.container(border=True, key="panel_18"):
        st.subheader("Manfaat yang dituju")
        st.markdown(
            "- **Tim data:** dapat menelusuri kualitas dan kelengkapan outcome.\n- "
            "**Tim risiko:** dapat menilai hasil model dengan denominator dan waktu"
            " yang jelas.\n- **Tim engineering:** dapat memisahkan demo, kesiapan "
            "artefak, dan rilis layanan."
        )
        st.caption(
            "Pengurangan kerugian, peningkatan approval, dan ROI belum diukur. Data"
            " pinjaman ditolak tidak tersedia; hasil tidak mewakili semua pemohon."
        )
    st.subheader("Keputusan berikutnya")
    st.write(
        "M1 berikutnya menunggu sumber holdout independen yang memenuhi kontrak "
        "waktu, hak penggunaan, maturity, dan pemisahan ID dari seluruh split lama."
        " Setelah itu barulah eksperimen berbatas sumber daya dapat dievaluasi "
        "secara independen."
    )
    st.info(
        "Kesimpulan proyek saat ini: demonstrasi data engineering dan evaluasi "
        "risiko kredit untuk prioritas review manual yang dapat ditelusuri, "
        "dengan kandidat scoring yang secara "
        "eksplisit belum layak rilis."
    )
    summary = (
        "# CreditLens — ringkasan bukti\n\n"
        "Profil data: 23 Sep 2026; packaging historis: 29 Sep 2026, revisi 928acc6.\n"
        "Warehouse: 2.260.668 pinjaman; 1.345.350 berlabel; 915.318 NULL.\n"
        "M1 eligible: 603.587 pinjaman diterima, tenor 36 bulan, vintage 2011–2015.\n"
        "AP frozen test: 0,2197; gate historis: 0,25; gagal. Test 2015 sudah terpakai.\n"
        "Model scoring tertahan. Deployment publik belum diverifikasi dalam snapshot.\n"
        "Dashboard menampilkan agregat historis, bukan monitoring atau keputusan kredit.\n"
        f"\nSumber: {REPOSITORY_URL}/blob/codex/m0-mentoring/{evidence['source_report']}\n"
    )
    st.download_button("Unduh ringkasan temuan", summary, "creditlens-findings.md", "text/markdown")
    _source(evidence, "model", "Laporan evaluasi beserta batas penerapan")


def main() -> None:
    """Render the project story from validated, published historical aggregates."""
    st.set_page_config(page_title="CreditLens | Credit Risk Evidence", page_icon="◈", layout="wide")
    st.markdown(Path(__file__).with_name("styles.css").read_text(), unsafe_allow_html=True)
    try:
        evidence = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        _validate(evidence)
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(f"Bukti agregat tidak dapat ditampilkan: {error}")
        st.stop()
    with st.sidebar:
        st.markdown(
            '<div class="brand"><span class="brand-dot">◈</span> CreditLens</div>',
            unsafe_allow_html=True,
        )
        st.caption("CREDIT RISK • DATA & MODEL EVIDENCE")
        page = st.radio("Jelajahi alur proyek", PAGES, label_visibility="collapsed")
        st.divider()
        st.markdown(
            "**Pertanyaan proyek**\n\nApakah data dan model sudah cukup valid untuk "
            "mendukung integrasi risiko kredit?"
        )
        st.markdown(
            '<p class="side-note">Demo agregat historis<br>Profil: 23 Sep '
            "2026<br>Packaging: 29 Sep 2026<br>Model scoring: tertahan</p>",
            unsafe_allow_html=True,
        )
        st.markdown(f"[Repository & bukti audit]({REPOSITORY_URL})")
    titles = {
        "Ringkasan": "Apakah model risiko kredit sudah layak digunakan?",
        "Masalah bisnis": "Mengapa tim fintech memerlukan bukti risiko yang andal?",
        "Profil dataset": "Apa isi dataset yang dipakai eksperimen?",
        "Data & vintage": "Kenali data sebelum mempercayai model",
        "Data engineering": "Setiap layer memiliki asal dan kontrak yang jelas",
        "Eksperimen model": "Pilih di validation, nilai sekali di test",
        "API & keamanan": "Hanya artefak yang terverifikasi boleh menuju scoring",
        "Deployment": "Tunjukkan bukti build, lalu verifikasi layanan",
        "Kesimpulan": "Apa yang berhasil, apa yang tertahan, dan mengapa",
    }
    st.markdown(
        '<div class="hero"><div class="eyebrow">CreditLens / '
        f"{escape(page)}</div><h1>{escape(titles[page])}</h1>"
        "<p>Riset risiko kredit untuk menghubungkan kualitas data, evaluasi model, dan "
        "kesiapan API. Membantu tim fintech menilai bukti sebelum menggunakan scoring.</p></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "DEMO RISET · MODEL SCORING TERTAHAN · "
        "Snapshot historis, bukan monitoring live · Tidak menyediakan keputusan kredit"
    )
    renderers = {
        "Ringkasan": _overview,
        "Masalah bisnis": _business_problem,
        "Profil dataset": _dataset_profile,
        "Data & vintage": _data,
        "Data engineering": _engineering,
        "Eksperimen model": _model,
        "API & keamanan": _api,
        "Deployment": _deployment,
        "Kesimpulan": _conclusion,
    }
    renderers[page](evidence)
    st.divider()
    st.caption(
        "CreditLens • Pinjaman diterima saja • Outcome retrospektif • Tidak ada "
        "data individual atau model yang dimuat oleh dashboard"
    )


if __name__ == "__main__":
    main()
