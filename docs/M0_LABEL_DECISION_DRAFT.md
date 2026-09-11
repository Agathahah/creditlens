# M0 — draft keputusan target dan ketersediaan fitur

10 September 2026 · DRAFT untuk review, belum mengubah SQL label atau mengizinkan M1/training. Angka dihitung baca-saja setelah ingestion lengkap; bukti: [M0_LABEL_FEASIBILITY.json](audit/M0_LABEL_FEASIBILITY.json).

## Mengapa ini keputusan berikutnya

Ingestion menjawab “apakah data sumber sudah masuk dengan utuh?”. Label menjawab “hasil apa yang ingin diprediksi?”. Keduanya berbeda: 2.260.668 pinjaman yang berhasil dimuat tidak otomatis menjadi 2.260.668 contoh training yang layak. Kita perlu mendefinisikan target, waktu penggunaan, dan siapa yang diwakili dataset sebelum membandingkan model.

| Status sumber | Jumlah | Perlakuan dalam rekomendasi draft |
|---|---:|---|
| Fully Paid | 1.076.751 | Kandidat label 0, outcome lunas yang teramati |
| Charged Off | 268.559 | Kandidat label 1 |
| Default | 40 | Kandidat label 1; jumlah kecil tetap dilaporkan |
| Current | 878.317 | Belum outcome final; jangan diberi label 0 |
| Late (31–120 days) | 21.467 | Dikeluarkan dari target utama; terlambat belum tentu sama dengan charged off/default |
| In Grace Period | 8.436 | Dikeluarkan dari target utama |
| Late (16–30 days) | 4.349 | Dikeluarkan dari target utama |
| Does not meet credit policy, Fully Paid | 1.988 | Tetap disimpan di raw; terpisah dari cohort utama |
| Does not meet credit policy, Charged Off | 761 | Tetap disimpan utuh di raw; terpisah dari cohort utama |

Usulan mapping menghasilkan **1.345.350 kandidat berlabel** (268.599 positif, 1.076.751 negatif) sebelum pemeriksaan waktu, fitur dan cohort. **915.318** record lain dikeluarkan dari target utama, tetap tersedia di raw untuk audit. Angka ini bukan jumlah training akhir. Label SQL lama saat ini masih 1.076.751 nol, 290.066 satu, 893.851 NULL karena memasukkan keterlambatan panjang sebagai satu.

## Pilihan yang perlu disepakati

| Keputusan | Rekomendasi | Mengapa / batas |
|---|---|---|
| Target pertama | Klasifikasi retrospektif outcome teramati: Fully Paid vs Charged Off/Default, status lain terpisah | Definisi lebih jelas dibanding mencampur terlambat dan default. Seleksi hanya resolved loans menimbulkan bias; belum probabilitas default seluruh pelamar |
| Horizon 12/24/36 bulan | Tunda klaim horizon tetap sampai tanggal snapshot/event tersedia | last_pymnt_date bukan tanggal default; loaded_at bukan waktu label diketahui |
| Waktu fitur | Desain input dari informasi aplikasi yang tersedia pada waktu penggunaan yang dipilih; keluarkan outcome/payment dan keputusan lender dari baseline pra-keputusan | Grade, sub_grade, int_rate, installment dan verification_status perlu keputusan availability eksplisit. Installment-to-income ratio juga mewarisi ketergantungan installment |
| FRED/SEC | Baseline tanpa keduanya | FRED belum punya vintage/publication-time yang sah; SEC tidak punya join borrower yang valid |
| Kandidat model | Constant baseline → Logistic Regression → XGBoost bila memberi peningkatan terukur | Baseline mudah diaudit; kompleksitas harus dibayar oleh hasil evaluasi/calibration/error analysis. Tidak ada pemenang sekarang |

Rekomendasi target retrospektif lebih cocok untuk kondisi bukti saat ini. Bila tujuan akhirnya model keputusan kredit sebelum pemberian pinjaman atau PD pada horizon tertentu, data/as-of/eligibility harus mendukungnya terlebih dahulu. Jangan mengubah nama output saja untuk menutupi keterbatasan.

## Batas evaluasi yang harus dibawa ke desain M1

1. Asal/lisensi/as-of belum terverifikasi. Maksimum last payment Maret 2019 bukan bukti snapshot Maret 2019. Jangan menetapkan tanggal snapshot dari nama file Q4 2018.
2. Seluruh member_id NULL; loan_id adalah unit pinjaman. Tidak dapat menjamin satu borrower hanya berada di satu split.
3. Train/validation/test harus terpisah dan preprocessing hanya fit pada train. Validation dipakai untuk tuning, calibration/threshold sesuai desain; test terkunci sampai keputusan selesai.
4. Mengurutkan issue_date saja belum membuktikan backtest prospektif. Pada satu snapshot, outcome loan train bisa baru diketahui sesudah tanggal loan test. Tanpa label-availability yang cukup, laporkan sebagai evaluasi retrospektif dengan pemisahan waktu penerbitan, dengan batas jelas.
5. Pinjaman 60 bulan dan 36 bulan memiliki peluang observasi berbeda. Eligibility/maturity perlu as-of dan term; jangan mengecualikan late/current lalu menyebut bias censoring sudah selesai.
6. Laporan harus mencantumkan denominator/exclusions/prevalence, cohort per tahun/term, metrik baseline, discrimination, calibration, error analysis serta keterbatasan accepted-only. Tidak ada target bisnis atau klaim kepatuhan yang dibuat dari angka ini.

## Urutan kerja setelah review

Catat keputusan target dan batas penggunaan → lengkapi provenance/as-of atau batasi klaim secara eksplisit → definisikan whitelist fitur dan manifest cohort/split → sepakati desain M1 → implementasi train-only preprocessing dan tes leakage/parity. Training penuh dan deployment tetap keputusan tersendiri.
