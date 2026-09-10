# Evaluation dan release plan

> Pembaruan operasional 10 September 2026: ingestion dan rebuild lokal selesai; raw/staging/loan/final masing-masing 2.260.668, schema loan_status TEXT. Snapshot audit lama di bawah dipertahankan sebagai konteks; status aktif ada di PROJECT_STATUS.md. Kontrak label/M1 masih draft: lihat M0_LABEL_DECISION_DRAFT.md.


> Status pemasangan 2026-09-08: arah v0.2 dan M0 disetujui. Detail implementasi di luar M0 tetap draft; ini bukan izin training penuh, deployment, atau rewrite.

v0.2 · DRAFT. Metrik model belum diukur ulang; seluruh acceptance numeric baru di bawah adalah usulan.

## Prasyarat evaluasi

Putuskan prediction_time, adverse event, horizon, maturity, cohort, data-as-of, dan whitelist fitur. M0 harus menunjukkan data cukup untuk klaim yang dipilih. Bila hanya snapshot status tersedia, gunakan bahasa evaluasi retrospektif outcome teramati dan jelaskan bahwa hal tersebut bukan backtest origination point-in-time yang sudah sah. Jangan mengubah current/unknown menjadi non-default.

Manifest menyimpan checksum sumber, versi SQL, daftar loan ID/hash per split, rentang issue date, label counts/prevalence, exclusion reasons dan cutoff availability. Aturan cohort diberlakukan konsisten pada semua model. Accepted-only selection bias harus tercatat; rejected tanpa outcome tidak menjadi test negatif.

## Split dan preprocessing

- Train berasal dari cohort paling awal yang memenuhi label availability pada training_as_of. Validation dari periode sesudahnya; frozen test periode terbaru yang mature. Tanggal konkret diputuskan setelah distribusi cohort/as-of diperiksa, sebelum tuning. Cutoff 2017-12-31 yang ada adalah baseline historis kode, bukan tanggal final yang otomatis benar.
- Jika outcome horizon tumpang tindih batas, gunakan cutoff eligibility/gap yang memenuhi availability. Periksa ulang borrower overlap lewat member_id bila reliabel; tentukan apakah estimand pinjaman baru atau borrower baru. Jangan menganggap nullable member_id cukup untuk jaminan group split.
- Fit median, missing handling, kategori, scaling/feature selection hanya pada train; validation/test/API memakai transform yang sama. Scaling dibutuhkan untuk baseline linear sesuai desain; tidak memaksakan kategori ordinal arbitrer pada Logistic Regression.
- Validation dapat dibagi dalam urutan waktu atau memakai prediksi out-of-fold temporal untuk calibrator/threshold; jangan melatih calibrator pada prediksi in-sample atau frozen test. Train/validation protocol dan besaran data dikunci sebelum evaluasi akhir.
- Test dibuka setelah kandidat, calibration dan policy threshold dipilih. Jika hasil test dipakai untuk revisi model, tandai test telah terpakai dan siapkan evaluasi independen berikutnya.

Prinsip transform train-only dan konsistensi test/serving didukung [scikit-learn common pitfalls](https://scikit-learn.org/1.8/common_pitfalls.html#data-leakage). Pilihan protokol temporal di atas merupakan usulan desain CreditLens, belum hasil eksperimen.

## Baseline, metrik dan analisis

Bandingkan prediktor konstan berdasarkan prevalence train, Logistic Regression, lalu XGBoost; LightGBM sebagai pembanding setelah jalur inti stabil. Gunakan split yang sama, seed dan resource budget tercatat. Jangan memilih kandidat hanya dari test tertinggi.

| Dimensi | Ukuran dan cara review |
|---|---|
| Ranking | Pertahankan nama jelas: kode sekarang menghitung trapezoidal PR-AUC, bukan average precision. Laporkan keduanya bila berguna, ROC-AUC, KS dan prevalence setiap cohort |
| Operating policy | Threshold dipilih pada validation berdasarkan tujuan simulasi/biaya FP-FN atau precision constraint yang disetujui; confusion matrix dan recall/precision test dihitung pada threshold terkunci |
| Recall@Precision80 | Boleh menjadi ringkasan kurva, tetapi pemindaian threshold test bukan jaminan policy deployed mencapai precision 80%. Laporkan n predicted positive serta confidence interval |
| Calibration | Reliability plot, Brier, ECE dengan definisi bin; bandingkan tanpa calibration versus sigmoid/isotonic bila data memadai; fit hanya validation/OOF |
| Uncertainty | Usulan 95% interval melalui bootstrap yang mempertahankan struktur waktu/borrower relevan; counts dan interval selalu menyertai subgroup kecil |
| Error analysis | False positives/negatives per vintage, term, missingness, purpose, grade inclusion/ablation, state dan ownership; cek perubahan prevalence |
| Fairness eksploratif | Existing AIF360 untuk proxy slices, threshold sama dengan simulasi API; band DI 0.8–1.25 adalah kebijakan kode lama, bukan bukti kepatuhan atau fairness semua kelompok |
| Explanation | Uji additivity pada ruang output yang dinyatakan dan kesamaan score batch/API. Top SHAP bukan sebab kausal atau nasihat kredit |

Quality gate lama PR-AUC>=0.25 tetap dicatat. Usulan release gate menambahkan baseline comparison pada dataset terkunci, schema/maturity/leakage tests, calibration dan policy acceptance yang disahkan sebelum test. Bila gate gagal, kandidat gagal release; jangan menurunkan ambang berdasarkan hasil test atau menghapus gate demi CI hijau.

## Matriks verifikasi yang bermakna

| Tes | Kegagalan yang harus ditangkap | Pemilik latihan |
|---|---|---|
| Mart nonempty + row reconciliation | Tabel kosong yang lolos unique/not_null | Agatha M0 |
| Test-only distribution perturbation | Median/category train berubah karena test | Agatha M1 |
| Outcome availability / late-label boundary | Label dari masa depan atau Late dianggap default tanpa kontrak | Agatha M1 |
| Raw record → saved bundle → reload → HTTP parity | Encoding, feature order, version mismatch | Agatha bagian assert/schema M2; Codex wiring |
| Missing/unseen/invalid features | Kolom di-drop diam-diam, nan/inf/kategori unknown tak terkendali | Agatha satu kasus M2 |
| Model absent/corrupt/incompatible | Healthy padahal score tidak tersedia | Agatha readiness test M2 |
| Real SQL→Feast→score | id vs loan_id, dtype kategori, data kosong, entitas tidak ada/expired | Codex integration setelah Agatha mengerjakan key contract |
| Gate negative case | Candidate invalid lolos build/release | Agatha M3 |
| Rollback + identical fixture score | Kombinasi model/image lama tidak kompatibel | Agatha smoke assertion M3 |
| Traffic and delayed-label join | Dashboard menghitung issue date, drift membuang unlabeled | Agatha SQL/test M4 |

Tidak menjalankan tes yang melatih model secara diam-diam pada audit ini. Dalam M0 lingkungan isolasi baru boleh menjalankan subset tes yang disepakati dan hasilnya disimpan. Tes yang skipped bukan pass integrasi. Coverage agregat tidak menggantikan pengujian kontrak.

## Latency, beban, biaya dan recovery

Usulan benchmark lokal awal: warmup 100 request; 1.000 score request dengan concurrency 1 dan 5; catat p50/p95/p99, HTTP total latency, error rate dan peak RSS. Pisahkan score dari explain, dan cold start dari warm traffic. Target lama <100ms dievaluasi sebagai kandidat p95 score warm concurrency 1 pada lingkungan yang dicatat; nilai SLO akhir menunggu persetujuan. Ukur throughput dan batas batch sebelum mencoba dataset penuh.

CI software: lint + unit + SQL tests pada fixture kecil + artifact roundtrip + readiness. CI model: data/artefak yang versioned dan aksesnya tersedia secara eksplisit; evaluation report/checksum di-upload. Synthetic fixture membuktikan software, bukan kualitas model real data. Gate model tidak mengandalkan DB dev laptop.

Penerimaan mandiri: Agatha menjalankan checklist dan memutuskan release; Codex membantu review diff/hasil, bukan pengganti seluruh validasi. Sediakan failure injection terbatas di staging (misalnya bundle hilang/tidak cocok), hasil negative tests, latihan restore/rollback, dan bukti operasi berulang. Reviewer eksternal bukan prasyarat. Scope beban, exposure, biaya dan toleransi kegagalan disepakati sebelum deployment.

Release: candidate bundle → eval report → human approval → image digest+bundle checksum → staging/local smoke → pilot. Tag build wajib mengacu manifest gate yang sama; model yang berbeda dari evaluasi ditolak. Deployment target, akses pengguna demo, retention, biaya bulanan dan durasi pilot masih keputusan terbuka.

Rollback trigger usulan: readiness gagal, schema mismatch, peningkatan error/latency melewati batas disetujui, atau regresi output fixture. Simpan versi sebelumnya; alihkan pasangan image+bundle; smoke score/explain lalu rekam waktu pemulihan. Schema migration destructive tidak otomatis dibalik; rancang kompatibilitas terlebih dahulu. Backup data/registry/metadata dan restore drill wajib bila pilot bergantung pada state tersebut. Cloud spend awal usulan Rp0; tidak ada pembelian/deploy sekarang.
