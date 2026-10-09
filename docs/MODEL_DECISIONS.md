# Mengapa model ini dipertimbangkan?

2026-09-11. Kandidat model belum dibandingkan melalui evaluasi versi perbaikan; belum ada model pemenang. Ingestion lengkap terhadap 2.260.668 kandidat CSV, tetapi cohort/label/as-of masih harus ditetapkan.

## Tujuan prediksi terlebih dahulu

Usulan scope v0.2 adalah analisis retrospektif outcome pinjaman publik, dengan batas penggunaan yang jelas. Label/horizon final belum disahkan. Jangan menyebut model sebagai probabilitas default 12 bulan atau keputusan kredit nyata tanpa data dan evaluasi yang mendukung klaim tersebut.

Implementasi historis menyediakan Logistic Regression, XGBoost dan LightGBM. CLAUDE.md menyebut XGBoost primary dengan alasan explainability dan inference cepat, tetapi itu catatan pemilihan awal, bukan bukti bahwa kandidat tersebut terbaik pada data/pipeline versi sekarang.

| Kandidat | Peran dan alasan dalam rencana kita | Kelemahan/alternatif | Syarat dipilih |
|---|---|---|---|
| Prediksi konstan sesuai proporsi kelas train | Patokan paling sederhana: mengukur apakah fitur/model memberi nilai dibanding menebak peluang yang sama bagi semua loan | Tidak membedakan loan; belum diimplementasikan pada training CLI | Selalu menjadi pembanding, bukan kandidat layanan individual yang dianggap berguna |
| Logistic Regression | Baseline linear dengan regularisasi; mudah menelusuri hubungan fitur dan log-odds. Memastikan model lebih kompleks benar-benar menambah manfaat | Perlu preprocessing numerik/kategori konsisten, scaling sesuai desain; interaksi tidak otomatis tertangkap. Koefisien bukan sebab kausal | Bila ranking/calibration memenuhi kebutuhan dan keuntungan model rumit kecil, kompleksitas yang lebih rendah menjadi pertimbangan |
| XGBoost | Kandidat utama eksperimen untuk fitur tabular; gabungan pohon dapat mempelajari pola nonlinier dan interaksi seperti pendapatan × beban cicilan | Dapat overfit, probabilitas perlu dicek calibration, tuning/serving lebih kompleks; SHAP tidak membuat model kausal atau otomatis memenuhi regulasi | Mengungguli baseline pada validation dengan manfaat yang berarti, calibration/error slices memadai, latency/memori sesuai batas. Belum dinyatakan menang |
| LightGBM | Pembanding opsional karena kode sudah tersedia; berguna menguji trade-off kualitas dan sumber daya setelah baseline/XGBoost sah | Eksperimen tambahan menambah ruang tuning dan waktu; tidak otomatis perlu dilatih | Dilanjutkan hanya bila anggaran dan pertanyaan eksperimen jelas; keputusan memakai pengukuran yang sama |

Rujukan mekanisme: [Logistic Regression](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression), [boosted trees XGBoost](https://xgboost.readthedocs.io/en/stable/tutorials/model.html). Peran/prioritas di atas adalah keputusan desain CreditLens, bukan rekomendasi sumber bahwa satu model pasti terbaik.

## Urutan yang menjaga kejujuran hasil

| Langkah | Mengapa perlu | Bukti yang harus disimpan |
|---|---|---|
| Tetapkan label, waktu prediksi, cohort dan ketersediaan outcome | Mencegah target ambigu atau informasi masa depan dianggap tersedia | Keputusan label, reasons exclusion, checksum snapshot |
| Pisahkan train/validation/test menurut protokol waktu | Mendekati pertanyaan generalisasi ke periode berikutnya; issue date saja belum menjamin outcome tersedia saat training | ID/rentang tiap split, aturan maturity, overlap checks dan keterbatasan |
| Fit preprocessing hanya pada train | Median/kategori tidak boleh mempelajari validation/test | Transform tersimpan, regression test perturbasi test |
| Bandingkan baseline dan kandidat pada cohort yang sama | Perbedaan skor harus berasal dari model, bukan dataset yang berbeda | Seed, parameter, fitur, jumlah label dan versi data |
| Nilai ranking, calibration dan konsekuensi threshold | Urutan risiko yang baik belum berarti peluang terkalibrasi atau keputusan threshold tepat | PR/ROC, Brier/reliability, confusion matrix dan batas biaya simulasi |
| Pilih kandidat dan threshold pada validation | Menghindari test menjadi data untuk memilih solusi | Alasan pemilihan, alternatif yang ditolak, tanggal penguncian |
| Evaluasi final pada test yang belum dipakai memilih | Memberi estimasi akhir dengan batas dan ketidakpastian | Laporan metrik, slice counts, interval dan kegagalan |
| Uji reload/API serta sumber daya | Model terbaik offline belum tentu dapat dilayani konsisten | Bundle checksum, parity, readiness, latency dan peak memory |

Pemisahan sebelum fit sesuai [scikit-learn: data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage). Implementasi historis justru preprocess sebelum split dan menyimpan estimator saja; perbaikan tersebut merupakan pekerjaan berikutnya, belum selesai oleh pemulihan mart.

## Temuan feasibility M0 yang memengaruhi keputusan

Snapshot sesudah recovery berisi 2.260.668 loan dengan issue_date Juni 2007–Desember 2018. Seluruh member_id NULL dan 2.427 last_pymnt_date kosong. Waktu pembayaran terakhir bukan waktu default atau bukti as-of; loaded_at mencatat ingestion.

Fully Paid 1.076.751, Charged Off 268.559 dan Default 40 menghasilkan 1.345.350 kandidat resolved-outcome sebelum aturan waktu/eligibility. Current dan status keterlambatan/grace tidak otomatis menjadi negatif. SQL lama masih memasukkan Late (31–120 days) sebagai positif. Lihat M0_LABEL_DECISION_DRAFT.md dan audit/M0_LABEL_FEASIBILITY.json.

Ops Copilot/RAG merupakan perluasan terpisah setelah core stabil; desain dan evaluasinya harus menjawab kebutuhan operasional yang terukur.
