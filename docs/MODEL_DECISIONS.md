# Mengapa model ini dipertimbangkan?

2026-09-09. Catatan keputusan kandidat; belum ada model pemenang dari evaluasi sah versi perbaikan. Update M0: mart sudah pulih, tetapi perbandingan set ID menunjukkan 660.686 ID kandidat CSV belum ada di raw; lihat [DATA_PROVENANCE.md](DATA_PROVENANCE.md). Pemilihan cohort masih harus dibuat eksplisit sebelum evaluasi.

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

Snapshot 9 September menunjukkan raw berisi 1.599.982 loan dengan issue_date 2014-01-01–2018-12-01; cakupan lebih sempit daripada rentang 2007–2018 yang disebut dokumentasi sumber lama. Kelengkapan ingestion terhadap CSV perlu direkonsiliasi sebelum memakai kata seluruh dataset.

Seluruh member_id NULL: pemisahan berdasarkan borrower tidak dapat dijamin dari kolom ini. Last payment date kosong pada 1.642 loan; tanggal pembayaran terakhir juga bukan otomatis tanggal outcome/label tersedia. loaded_at 2026 mencatat ingestion, bukan kapan hasil pinjaman diketahui oleh pemberi pinjaman.

Fully Paid 730.891, Charged Off 185.294, Default 24. Jika usulan label terminal memakai tiga status itu saja, tersedia 916.209 loan kandidat dengan 185.318 adverse outcomes (sekitar 20,23%). Ini hitungan feasibility sebelum aturan maturity/eligibility final, bukan jumlah training yang sudah disahkan. Current 659.918 dan status keterlambatan/grace tidak boleh otomatis diberi label non-default. Kode lama memasukkan Late 31–120 sebagai positif; perubahan definisi harus dicatat sebelum evaluasi.

## Narasi interview yang boleh dibangun

“Saya mengevaluasi baseline sederhana sebelum memilih model lebih kompleks, menjaga preprocessing agar tidak belajar dari test, dan membandingkan kualitas prediksi dengan biaya operasional.” Kalimat ini baru menjadi klaim kontribusi setelah eksperimen/perubahan dan penjelasan mandiri benar-benar ada. Saat ini yang terbukti adalah audit, diagnosis pipeline, tes M0 dan verifikasi koneksi pengguna. Bantuan Codex dalam penulisan kode dan eksekusi dicatat terpisah di learning log.

Ops Copilot/RAG merupakan usulan tambahan setelah core stabil; LLM tidak ditambahkan ke jalur scoring hanya demi label AI Engineer. Desain dan evaluasinya harus menjawab kebutuhan operasional tersendiri.
