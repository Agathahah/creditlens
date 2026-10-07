# Freddie Mac — protokol panel bulanan dan evaluasi terpisah

Tanggal: 7 Oktober 2026. Permintaan melanjutkan panel, label, evaluasi independen dan kontrol layanan mengizinkan implementasi lokal riset serta pembaruan GitHub. Training belum dijalankan: source admission dan vintage tambahan belum lengkap. Data Freddie tetap privat; tidak ada promosi model atau deployment scoring.

## Tujuan dan kecocokan

Mempelajari rancangan prioritas tinjauan risiko setelah pencairan pada **hipotek AS**. Ini menguji pola engineering yang dapat dipakai pada panel operator fintech: loan-month → quality checks → fitur pada as-of → outcome ke depan → evaluasi temporal → bundle dan pengamanan layanan. Produk, populasi dan ekonomi hipotek berbeda dari pinjaman fintech. Freddie tidak menggantikan holdout LendingClub dan tidak mengesahkan model untuk operator Indonesia.

LendingClub tetap menjadi bukti warehouse historis dan eksperimen gagal; test 2015 sudah terpakai. Tidak ada penghapusan dataset, backup, PostgreSQL atau artefak historis dalam perubahan ini.

## Kontrak label riset v1

- Grain: satu `(loan_id, as_of)` bulanan; `as_of` memakai bulan laporan, **bukan** tanggal data benar-benar diterima operator.
- Populasi: status 0/00 (lancar atau <30 hari), UPB positif, tanpa zero-balance code pada as-of.
- Target: teramati status >=3 bulan tunggakan (90+ hari) atau `RA` (REO acquisition, properti diperoleh lender) pada tiga bulan kalender **setelah** as-of.
- Horizon primer **3 bulan**, ditetapkan untuk siklus pemantauan triwulanan. Ini pilihan desain riset, bukan horizon yang terbukti optimal atau janji mempercepat kelulusan model. Horizon 6 bulan ditunda; jangan mengganti horizon untuk meloloskan hasil test.
- Label 1: adverse event teramati pada follow-up berurutan sebelum data berhenti. Event adverse yang bersamaan dengan terminasi tetap positif.
- Label 0: ketiga bulan tersedia berurutan, status diketahui, tidak adverse dan tidak terjadi terminasi/saldo nol. Status 1/2 belum adverse untuk target ini.
- Label NULL: follow-up kurang, celah bulan, status tidak dikenal, atau terminasi sebelum outcome lengkap. Pelunasan/terminasi adalah *censoring* (observasi berhenti), bukan otomatis negatif. Estimasi pada subset label lengkap memiliki potensi bias; laporkan jumlah dan alasan censoring.
- Jendela tidak memasukkan bulan as-of, tidak memasukkan event setelah bulan ketiga, dan menangani pergantian tahun.

## Fitur dan batas informasi

Whitelist awal: saldo UPB, loan age, remaining months, current interest rate, status satu dan dua bulan sebelumnya (NULL bila bulan tidak tersedia). Loan ID, waktu event, kode terminasi masa depan dan label dilarang sebagai fitur. VantageScore tidak digunakan; audit awal seluruh field ini sentinel.

Parser menerima layout sampel yang telah diaudit: 31 field origination, 35 performance; minimal mapping performance posisi 1–6, 9, 11. Layout baru gagal dan memerlukan audit baru. Sumber resmi: [User Guide](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf) serta [layout efektif Juli 2026](https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx). Snapshot historis dapat dikoreksi. Tidak ada publication timestamp/riwayat release dalam berkas lokal, sehingga **point-in-time belum terverifikasi** dan hasilnya belum boleh disebut backtest operasional bebas kebocoran.

## Rancangan split sebelum training

| Split | Vintage sumber | As-of yang direncanakan | Outcome terakhir | Penggunaan |
|---|---|---|---|---|
| Train | sample_2018 | Jan–Sep 2019 | Des 2019 | Fit preprocessing/model |
| Validation | sample_2019 | Jan–Sep 2020 | Des 2020 | Pemilihan kandidat, kalibrasi dan simulasi kapasitas |
| Frozen test | sample_2020 | Jan–Sep 2021 | Des 2021 | Satu evaluasi akhir setelah kandidat dikunci |

Ini **rancangan sementara yang dikunci sebelum melihat validation/test outcome**; kelayakan waktu dan dukungan event harus diaudit sebelum fit. Cohort pinjaman harus disjoint lintas split. Vintage baru dari sumber yang sama memberikan holdout temporal/pinjaman berbeda, bukan validasi eksternal terhadap fintech. Bulan Oktober–Desember tidak dipakai sebagai as-of agar label primer selesai sebelum tahun evaluasi berikutnya. COVID/perubahan kebijakan servicing dapat mengubah prevalence dan censoring; catat regime shift dan koreksi, jangan menyingkirkan periode sulit berdasarkan hasil test.

Builder saat ini hanya menerima vintage 2018/2019. Vintage 2020 ditolak supaya pemeriksaan ad hoc tidak membuka outcome frozen test. Simpan arsip test tanpa mengekstrak, profil outcome, membuat label atau tuning. Jalur pembukaan test hanya dibuat setelah source admission, kandidat, whitelist, kalibrasi dan gate final dikunci. Tidak ada hasil test baru pada perubahan ini.

## Metrik dan gate sebelum membuka test

Bandingkan constant baseline, Logistic Regression dan satu model pohon berbatas sumber daya, pada cohort sama. Semua imputation/scaling/calibration berasal dari train/validation sesuai perannya. Sebelum fit, audit jumlah **pinjaman unik** dengan adverse event pada jendela train; banyak loan-month tidak menjamin dukungan event memadai. Jika dukungan terlalu kecil untuk kandidat/kalibrasi dan interval yang bermakna, perlu tambahan vintage pengembangan atau scope deskriptif. Jangan memperluas jendela atau membuka test berdasarkan hasil test. Ukur AP dibanding prevalence, ROC-AUC, Brier/reliability dan precision/recall pada kapasitas alert yang ditetapkan. Laporkan counts, censoring, per-bulan/segment dan interval dengan bootstrap pada tingkat pinjaman (loan-month berulang tidak independen).

Gate model Freddie **belum memiliki angka final** karena dukungan event train, kapasitas analis, biaya false alert dan tujuan tindakan belum tersedia. Gate historis LendingClub 0,25 tidak dipindahkan otomatis ke populasi baru. Kriteria minimum sebelum rilis riset: ranking mengungguli baseline dengan uncertainty yang dilaporkan; kalibrasi dan operating point yang bermakna; tidak ada dukungan alert degenerate; evaluasi terikat satu data/model manifest dan holdout baru. Nilai penerimaan bisnis harus disepakati **sebelum** pembukaan test. Tidak melaporkan evaluasi sintetis sebagai kelulusan model.

## Kontrol layanan dan batas rilis

Implementasi saat ini menjaga `/live` terpisah dari `/ready`; model legacy/missing/incomplete ditolak di `/ready`, `/predict` dan `/explain`. Tes menggunakan fixture sintetis untuk kontrak software. Belum ada loader bundle real yang diterima.

| Kontrol berikutnya | Bukti yang wajib ada sebelum scoring publik |
|---|---|
| Source/target | Release/cutoff resmi, hak penggunaan, tanggal informasi tersedia, independensi dan protokol label |
| Bundle | Pipeline lengkap, ordered schema, runtime version, SHA-256, immutable model version dan laporan evaluasi yang cocok |
| Parity | Raw → batch → save/reload → HTTP menghasilkan probabilitas sama dalam toleransi terkunci |
| Akses | HTTPS, secret di environment/store, autentikasi, pembatasan request/payload, origin CORS eksplisit, tanpa PII pada log |
| Operasi | Latency/load/error budget pada host tertentu, event request/model version, delayed-label join, alert dan rollback image+bundle |
| Penggunaan | Endpoint probabilitas riset; tanpa approved/rejected kredit otomatis; scope hipotek dan fintech terpisah |

Autentikasi GitHub/Tableau yang sudah dilakukan tidak mengaktifkan autentikasi API scoring. Flag `bundle_verified` lama adalah pengaman transisi, bukan validator release lengkap. Deploy dashboard/CI hijau tidak melewati kontrol-kontrol tersebut. Status scoring **HOLD**.

## Menjalankan lokal

Panel tersimpan di luar repo; builder menolak path output di dalam repo dan menolak overwrite. ZIP tidak diekstrak. SQLite dan report dibuat dengan izin owner-only; direktori induk privat harus tetap 700. Kegagalan meninggalkan hasil parsial tanpa report sukses; gunakan path baru setelah investigasi, jangan anggap database parsial valid.

```bash
cd "$HOME/Documents/creditlens"
export FREDDIE_PANEL="$HOME/Documents/creditlens-private/freddie/panel_2018_3m_20261007"
.venv/bin/python -m pytest tests/test_freddie_panel.py src/api/tests/test_readiness.py -q
# Jika report ini sudah tersedia, jangan jalankan builder ulang pada path yang sama.
test -f "$FREDDIE_PANEL/panel_report.json" && cat "$FREDDIE_PANEL/panel_report.json"
sqlite3 -header -column "$FREDDIE_PANEL/panel.sqlite" < scripts/sql/freddie_monthly_audit.sql
```

Untuk mesin baru, gunakan output yang belum ada:

```bash
.venv/bin/python -m src.research.freddie_panel \
  --source "$HOME/Documents/creditlens-private/freddie/sample_2018.zip" \
  --output "$HOME/Documents/creditlens-private/freddie/panel_2018_3m_new" \
  --vintage 2018
```

## Pekerjaan yang masih diperlukan

1. Pemilik mencatat release/cutoff resmi dan ketentuan akses yang diterima. Cutoff dari isi file bukan pengganti metadata resmi.
2. Unduh `sample_2019.zip` dan `sample_2020.zip` dari **SFLLD → Standard Dataset Download by Year → Sample File**, simpan privat. File 2019 untuk intake/validation; file 2020 disegel sebagai calon frozen test.
3. Audit sumber validation dan independensi ID; kunci eligibility, split, fitur, budget serta gate numerik. Selesaikan hak penggunaan dan batas point-in-time.
4. Baru jalankan fit bounded serta pemilihan pada validation. Buka test sekali setelah kandidat final; gagal berarti HOLD, bukan tuning pada test.
5. Bila model riset lulus, implementasikan bundle/parity dan staging terisolasi dengan kontrol operasi. Model hipotek tetap tidak menjadi scoring fintech production tanpa panel operator dan evaluasi penggunaan yang sesuai.
