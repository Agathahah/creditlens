# Keputusan rilis CreditLens — 30 September 2026

## Masalah produk

Use case yang disetujui adalah **membantu analis memprioritaskan review manual pada saat aplikasi,
sebelum grade dan pricing**. Untuk penggunaan nyata, skor harus bermakna pada seluruh populasi
pemohon yang relevan, memakai fitur yang tersedia pada saat itu, dan dapat diaudit. False negative
berisiko melewatkan pinjaman bermasalah; false positive dapat membebani analis atau merugikan
pemohon yang layak. Nilai moneter kedua kesalahan dan kapasitas review belum diberikan, sehingga
tidak ada threshold approve/reject atau ROI yang sah.

Dataset saat ini hanya pinjaman yang sudah diterima oleh pemberi pinjaman asal. Outcome yang ditolak
tidak diketahui. Karena itu, evaluasi pada accepted-only cohort tidak membuktikan performa pada
seluruh aplikasi fintech baru. Hak penggunaan publik raw/model, tanggal as-of outcome, waktu event,
independensi peminjam dan availability label historis juga belum terverifikasi.

## Bukti eksperimen yang sudah ada

| Kandidat pada validation 2014 | Cara kerja | AP | ROC-AUC | Brier | Status |
|---|---|---:|---:|---:|---|
| Konstan | Mengulangi proporsi adverse train untuk setiap pinjaman | 0,1373 | 0,5000 | 0,1186 | Baseline; tidak memberi ranking |
| Logistic Regression | Menimbang fitur yang telah diproses lalu mengubah skor linear menjadi probabilitas | 0,2016 | 0,6291 | 0,1158 | Baseline terlatih, lebih mudah diaudit |
| Bounded XGBoost | Menggabungkan 150 pohon kecil, maksimal kedalaman 4 | 0,2046 | 0,6356 | 0,1155 | AP tertinggi, kenaikan 0,0030 dari Logistic Regression belum terbukti berguna secara operasional |

Semua memakai cohort dan preprocessing train-only yang sama. Tabel di atas hanya **validation**.
Tidak ada hasil frozen test terpisah bagi model konstan dan Logistic Regression pada laporan M1.
Kandidat terpilih menghasilkan AP test 0,2197 (CI bootstrap baris 95% 0,2164–0,2221), di bawah
gate historis 0,25. Threshold lama 0,4829 menghasilkan TN 240.893, FP 0, FN 42.131, TP 0:
tidak satu pun kasus adverse terdeteksi pada operating point itu. Frozen test 2015 sudah terpakai
untuk keputusan ini dan tidak boleh dipakai memilih ulang model/threshold.

## Keputusan yang dapat diaudit

- **Kandidat historis: REJECT untuk scoring.** Penyimpanan hasil riset dan dashboard agregat boleh;
  `model_release_passed` tetap false dan API harus menolak bundle lama/belum terverifikasi.
- **Dashboard publik: demo riset tersendiri.** Publikasi hanya berisi agregat tanpa borrower/model,
  sesudah commit, CI dan verifikasi URL sebenarnya. Pilot tersebut diverifikasi pada 30 September
  di `https://creditlens-risk-evidence.streamlit.app/` dari revisi `084e524`; ini tidak mengubah
  keputusan model.
- **Model/API production: BLOCKED.** Tidak boleh mengaktifkan skor atau keputusan kredit hanya
  untuk memenuhi tenggat portfolio.

## Bukti yang diperlukan untuk keputusan baru

1. **Sumber:** snapshot/dataset baru dengan provenance, rights, as-of, waktu outcome, maturity 36
   bulan, availability fitur saat aplikasi, dan pemisahan loan ID terhadap semua split lama.
2. **Protokol:** train/validation/test temporal dikunci; preprocessing fit pada train; batas sumber
   daya dan kriteria metrik/ketidakpastian ditetapkan sebelum test baru dibuka satu kali.
3. **Kinerja:** baseline konstan/Logistic Regression serta kandidat kecil dibanding pada cohort
   yang sama; AP bersama prevalence, ROC-AUC, Brier, log loss, calibration, recall/precision serta
   fairness ditinjau. Threshold operasional menunggu biaya FP/FN dan kapasitas review yang disetujui.
4. **Artefak:** preprocessing, model, whitelist/schema, library version, checksum dan laporan
   evaluasi terikat satu manifest. Input hilang/rusak/tidak kompatibel → readiness 503. Uji raw→batch
   →save/reload→HTTP parity dan kategori/nilai baru.
5. **Layanan:** dependency/image audit, autentikasi/otorisasi bila API terekspos, rate limit, HTTPS,
   log audit tanpa data sensitif, smoke/load/latency dan rollback di staging; monitoring inferensi
   serta join outcome tertunda. Tetapkan SLO, pemilik operasi, biaya dan prosedur insiden.
6. **Persetujuan rilis:** review bukti dari tahap 1–5 sebelum kandidat dinaikkan menjadi API pilot.
   Layanan penilaian kredit nyata memerlukan validasi populasi, tata kelola dan izin operasional
   tambahan di luar demo pendidikan ini.

Tidak ada sumber holdout baru yang diterima pada tanggal keputusan ini. Tidak ada training penuh,
evaluasi ulang test 2015, bundle rilis, API staging atau deployment scoring dalam perubahan ini.
Referensi: `M1_LOCAL_EVALUATION_2026-09-23.md`, `M1_NEXT_HOLDOUT_DECISION.md`,
`M1_NEXT_EXPERIMENT_SCOPE.md`, `PRODUCTION_READINESS_ROADMAP.md`.
