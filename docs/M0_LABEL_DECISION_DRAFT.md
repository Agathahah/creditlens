# M0 — kontrak target disetujui dan draft ketersediaan fitur

Pembaruan 11 September 2026 · Mapping label dan batas klaim retrospektif disetujui untuk SQL dan tes terisolasi. SQL lokal sudah diperbaiki dan tes terisolasi lulus; database aktif belum direbuild. Kelayakan fitur/waktu, M1, training, merge dan deployment belum diizinkan oleh persetujuan ini. Angka awal dihitung baca-saja setelah ingestion lengkap; bukti: [M0_LABEL_FEASIBILITY.json](audit/M0_LABEL_FEASIBILITY.json). Profil tahun/tenor dan rincian status lanjutan tercatat dalam [review M0](audit/M0_PR14_REVIEW.md).

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

## Keputusan target dan usulan lanjutan

| Keputusan | Rekomendasi | Mengapa / batas |
|---|---|---|
| Target pertama — disetujui | Klasifikasi retrospektif outcome teramati: Fully Paid vs Charged Off/Default, status lain terpisah | Definisi lebih jelas dibanding mencampur terlambat dan default. Seleksi hanya resolved loans menimbulkan bias; belum probabilitas default seluruh pelamar |
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

### Kontrak target yang disetujui

| Aspek | Kontrak |
|---|---|
| Pertanyaan model | Membedakan status Fully Paid dari Charged Off/Default yang tercatat pada snapshot, dalam populasi kandidat yang dipilih |
| Label 0 | Hanya string Fully Paid |
| Label 1 | Hanya string Charged Off atau Default |
| Status lainnya, termasuk NULL/tidak dikenal | Label model NULL; tidak ikut training target utama, tetap disimpan pada raw dan mart untuk audit |
| Status di luar kebijakan kredit | Dua string panjang dikeluarkan dari target utama sebagai keputusan cakupan; tidak dipotong atau dipetakan ke label melalui pencocokan sebagian string |
| Makna output | Skor klasifikasi retrospektif pada populasi terpilih; belum PD pada horizon tertentu atau dasar keputusan kredit nyata |
| Kelayakan waktu | Belum ditetapkan; tidak menyamakan issue_date, loaded_at atau last_pymnt_date dengan waktu outcome diketahui |
| Unit observasi | Pinjaman berdasarkan loan_id; tidak mengklaim semua peminjam berbeda karena member_id seluruhnya NULL |

### Dampak penerapan label yang perlu diuji

Jika nanti diterapkan pada database aktif dan snapshot tidak berubah, 21.467 record Late (31-120 days) berpindah dari label 1 menjadi NULL. Jumlah label 0 tetap 1.076.751; label 1 berubah dari 290.066 menjadi 268.599; NULL berubah dari 893.851 menjadi 915.318. Jumlah baris raw/staging/mart tetap 2.260.668. Dataset model menyaring label NULL pada langkah terpisah, bukan dengan menghapus record warehouse.

Kriteria verifikasi sebelum perubahan diterapkan pada database aktif:

1. Data sintetis memuat seluruh status sumber, NULL dan status tidak dikenal. Hanya tiga string yang disetujui menghasilkan label non-NULL.
2. Kedua status di luar kebijakan tetap utuh dan tidak ikut label utama. Semua status keterlambatan tetap NULL.
3. SQL staging dan mart yang dibangun ulang menghasilkan label yang sama per ID, tanpa perubahan jumlah atau penggandaan ID.
4. Kasus Late (31-120 days) secara khusus menangkap perilaku lama yang salah terhadap kontrak baru.
5. Jalankan verifikasi terisolasi dahulu; sebelum rebuild aktif, periksa target database, backup, kapasitas disk dan hasil tes. Perubahan label tidak memulai training secara otomatis.

Penanganan NULL pada label berbeda dari kualitas input: source dbt tetap mensyaratkan loan_status tidak kosong. Pemetaan menghasilkan NULL secara aman bila menerima status kosong, tetapi full build tetap ditolak oleh tes kualitas sumber. Tes terisolasi membuktikan kedua perilaku itu; fixture negatif dipulihkan sebelum full build yang sehat. Aturan sumber tidak dihapus demi membuat tes lulus. Bukti: [hasil tes terisolasi](audit/M0_LABEL_ISOLATED_REPORT.json).

### Kandidat fitur untuk rancangan M1 — belum whitelist final

Whitelist berarti daftar kolom yang secara eksplisit boleh masuk ke model. Kandidat berikut diambil dari fitur yang sudah digunakan kode saat ini; keberadaannya belum membuktikan bahwa nilainya tersedia saat aplikasi pinjaman dinilai.

| Kelompok | Kolom / aturan usulan |
|---|---|
| 12 kandidat numerik | loan_amnt, term_months, annual_inc, dti_eff, revol_bal, revol_util_clean, total_acc, open_acc, credit_history_age_months, has_delinq, has_public_record, inq_last_6mths |
| 3 kandidat kategori | home_ownership, purpose, addr_state |
| Dikeluarkan dari baseline pra-keputusan sementara | int_rate, installment, installment_to_income_ratio, grade, sub_grade, verification_status; waktu ketersediaannya belum dipastikan |
| Makro dan SEC | Tidak digunakan pada baseline awal karena masalah waktu publikasi/vintage FRED dan ketiadaan relasi SEC ke peminjam yang sah |
| Dilarang menjadi fitur | loan_status/is_default, pembayaran/recoveries setelah pinjaman, serta ID untuk menghafal record |
| Kolom kendali, bukan input model | loan_id dan issue_date untuk pelacakan/pengelompokan; aturan tanggal tidak otomatis membuktikan ketersediaan label |

Sebelum daftar fitur dibekukan, periksa definisi sumber, satuan, missingness, nilai tidak valid dan waktu tersedia. Misalnya credit_history_age_months menggunakan issue_date sehingga perlu definisi waktu penggunaan yang konsisten. Nilai nol buatan dari missing data pada raw/SQL juga tidak otomatis dapat dipulihkan menjadi missing hanya dengan mengganti preprocessing. Daftar ini adalah rancangan yang perlu diverifikasi, bukan klaim bahwa model pra-keputusan sudah valid.

M1 akan membandingkan prediktor konstan, Logistic Regression dan kandidat XGBoost pada data/split yang sama setelah kontraknya disetujui. Belum dipilih model terbaik atau tanggal pemisahan data.

Catat keputusan target dan batas penggunaan → lengkapi provenance/as-of atau batasi klaim secara eksplisit → definisikan whitelist fitur dan manifest cohort/split → sepakati desain M1 → implementasi train-only preprocessing dan tes leakage/parity. Training penuh dan deployment tetap keputusan tersendiri.
