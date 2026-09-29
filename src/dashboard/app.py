"""Display published research aggregates without loading data or ML artifacts.

Run from the repository root using ``python -m streamlit run src/dashboard/app.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json"
REPOSITORY_URL = "https://github.com/Agathahah/creditlens"


def main() -> None:
    """Render a read-only, dated dashboard of existing evaluation evidence."""
    st.set_page_config(page_title="CreditLens | Research Evidence", page_icon="📊", layout="wide")
    st.title("CreditLens — data & model evidence")
    st.caption("Demo riset kredit • PostgreSQL/dbt → split waktu → evaluasi → kesiapan API")
    if not SNAPSHOT.is_file():
        st.error("Snapshot agregat tidak ditemukan. Dashboard tidak menampilkan data pengganti.")
        st.stop()
    evidence = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    st.warning(
        "Kandidat M1 gagal gate rilis. Halaman ini adalah laporan riset historis; "
        "tidak menyediakan prediksi atau keputusan kredit."
    )
    st.caption(
        f"Tanggal laporan: {evidence['data_as_of_report']} • "
        "Snapshot statis, bukan monitoring database/API secara langsung."
    )
    cohort_tab, model_tab, release_tab = st.tabs(
        ["Data & vintage", "Evaluasi model", "Jalur menuju rilis"]
    )
    with cohort_tab:
        st.subheader("Vintage: kelompok pinjaman menurut tahun penerbitan")
        cohorts = pd.DataFrame(evidence["cohorts"])
        cohorts["prevalence_pct"] = 100 * cohorts["adverse"] / cohorts["eligible"]
        st.dataframe(cohorts, hide_index=True, use_container_width=True)
        split = st.selectbox("Lihat distribusi outcome", cohorts["split"].tolist())
        selected = cohorts.loc[cohorts["split"] == split].iloc[0]
        counts = pd.DataFrame(
            {"Jumlah": [selected["non_adverse"], selected["adverse"]]},
            index=["Fully Paid (0)", "Charged Off / Default (1)"],
        )
        st.bar_chart(counts)
        st.info(
            "Label ini adalah status outcome retrospektif. Tenor 36 bulan tidak membuktikan "
            "outcome diukur tepat pada horizon 36 bulan. Pinjaman unresolved tidak diberi label 0."
        )
        st.markdown(
            "**Alur preprocessing:** tentukan eligibility → pisahkan train/validation/test "
            "berdasarkan waktu → fit median, scaling, dan kategori hanya pada train → "
            "transform validation/test dengan aturan train yang sama."
        )
        st.write(
            "147 outcome unresolved dan 2 pendapatan tidak valid dikeluarkan pada eksperimen ini. "
            "Split berdasarkan issue date saja belum membuktikan label sudah tersedia "
            "pada waktu pelatihan historis."
        )
    with model_tab:
        st.subheader("Model dipilih menggunakan validation")
        validation = pd.DataFrame(evidence["validation"])
        st.dataframe(validation, hide_index=True, use_container_width=True)
        st.bar_chart(validation.set_index("candidate")[["average_precision"]])
        st.markdown(
            "**Average precision (AP):** merangkum kemampuan menemukan kasus adverse saat "
            "ambang skor berubah; lebih tinggi lebih baik. **ROC-AUC:** kemampuan mengurutkan "
            "adverse di atas non-adverse. **Brier:** rata-rata kuadrat kesalahan probabilitas; "
            "lebih rendah lebih baik. AP berbeda dari luas PR dengan integrasi trapezoid."
        )
        result = evidence["test"]
        left, middle, right = st.columns(3)
        left.metric("AP frozen test historis", f"{result['average_precision']:.4f}")
        middle.metric("Gate AP historis", f"{result['historical_ap_gate']:.2f}")
        right.metric("Predicted-positive pada threshold lama", str(result["predicted_positive"]))
        st.caption(
            f"Interval bootstrap baris 95% AP: {result['ap_ci_low']:.4f}–"
            f"{result['ap_ci_high']:.4f}. Ini bukan interval bootstrap peminjam."
        )
        st.error(
            "Test 2015 sudah dibuka dan terpakai. Tidak boleh dipakai kembali untuk memilih "
            "fitur, model, atau threshold. Angka di halaman ini berasal dari laporan tersimpan."
        )
        st.write(
            "Frozen test adalah data ujian akhir yang dikunci sebelum pemilihan model. "
            "Setelah hasilnya digunakan untuk memutuskan revisi, "
            "diperlukan holdout independen baru."
        )
    with release_tab:
        st.subheader("Bukti yang masih diperlukan")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Tahap": "Sumber & waktu outcome", "Status": "Tertahan: audit belum lengkap"},
                    {"Tahap": "Model & holdout baru", "Status": "Tertahan: kandidat lama gagal"},
                    {
                        "Tahap": "Bundle/API",
                        "Status": "Persiapan lokal; parity/manifest belum selesai",
                    },
                    {"Tahap": "Docker", "Status": "Smoke packaging historis; belum rilis model"},
                    {
                        "Tahap": "Monitoring & rollback",
                        "Status": "Belum dibuktikan pada layanan aktif",
                    },
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.write(
            "API /live memeriksa proses. /ready menolak model yang belum memiliki bundle "
            "terverifikasi. HTTP 200 dari /health hanya melaporkan status proses/artefak."
        )
        st.write("Dashboard, Docker, dan CI hijau tidak membuktikan validitas model.")
        for limitation in evidence["limitations"]:
            st.markdown(f"- {limitation}")
    st.markdown(
        f"[Laporan evaluasi dan asal angka]({REPOSITORY_URL}/blob/"
        f"codex/m0-mentoring/{evidence['source_report']})"
    )


if __name__ == "__main__":
    main()
