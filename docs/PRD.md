# PRD — CreditLens public-data pilot

> Status pemasangan 2026-09-08: arah v0.2 dan M0 disetujui. Detail implementasi di luar M0 tetap draft; ini bukan izin training penuh, deployment, atau rewrite.

v0.2 · Arah produk dan M0 disetujui. Detail target/label, acceptance numeric dan implementasi M1–M5 belum disetujui; keputusan label akhir adalah prasyarat M1.

## Masalah dan pengguna

Agatha membutuhkan proyek risiko kredit yang bisa direproduksi, ditelusuri, dan dijelaskan saat interview. Agatha bertindak sebagai developer, operator, dan penguji penerimaan proyek sendiri. Calon pewawancara adalah pembaca bukti kemudian; reviewer eksternal bukan prasyarat staging atau kelulusan milestone. Belum ada lender, pengguna produksi, atau manfaat bisnis terukur yang diverifikasi.

Pilot membantu pengguna menelusuri satu pinjaman publik dan memahami keluaran model historis beserta keterbatasannya. Hasil tidak digunakan untuk persetujuan, penolakan, harga, atau limit kredit nyata. Klaim API `approved` saat ini perlu diganti/dibatasi menjadi hasil simulasi dalam perubahan kontrak yang disetujui.

## MVP yang diusulkan

- Snapshot data accepted Lending Club yang teridentifikasi, izin pemakaian tercatat, SQL/dbt dengan kontrak grain/label/waktu fitur.
- Baseline sederhana dan kandidat XGBoost; preprocessing train-only dan satu artefak berversi yang digunakan evaluator dan API.
- Endpoint score dan explain dengan schema input yang jelas, versi model, threshold simulasi dan readiness bermakna.
- Evaluasi temporal dengan validation terpisah, test terkunci, calibration/error analysis; laporan bisa direproduksi.
- CI yang membedakan tes software dari quality gate model, rilis yang mengikat checksum model, smoke test, dan rollback lokal/staging sesuai persetujuan.
- Monitoring dasar request/error/latency, distribusi fitur dan prediksi, delayed-label performance bila label tersedia; runbook dan demonstrasi kegagalan.
- Walkthrough Indonesia/Inggris yang menjelaskan kontribusi Agatha dan bantuan AI secara jujur.

Scope awal yang direkomendasikan: pilot lokal dengan Agatha sebagai operator, score satu record per request, lalu staging terisolasi yang Agatha uji sendiri sebelum deployment yang disetujui. Mac terukur M3/16 GiB; ukuran subset dan concurrency ditetapkan lewat M0, bukan memakai seluruh stack sekaligus.

## Makna kesiapan produksi untuk proyek mandiri

Target akhir adalah layanan demonstrasi risiko kredit berbasis data publik yang siap dioperasikan pada lingkungan, beban, dan batas penggunaan yang disepakati. Mulai lokal untuk memahami core, lalu staging (lingkungan latihan rilis terpisah) dan deployment setelah bukti siap. Staging dapat lokal terisolasi dahulu; cloud dan biaya bukan keputusan wajib sekarang. Tidak membutuhkan reviewer eksternal: Agatha menjalankan acceptance tests dan memberi keputusan rilis; Codex membantu review source dan hasil, sementara tests, manifests dan recovery drill menjadi bukti yang dapat diperiksa ulang. Sebutkan keterbatasan self-review secara jujur.

Kesiapan mensyaratkan data/evaluasi valid untuk klaim yang dipilih, reproduksi, parity training-serving, readiness, pengujian beban, logging/monitoring, kontrol akses sesuai eksposur, rilis berversi, backup/restore bila ada state, rollback, dan runbook yang dapat Agatha jalankan. Hosting saja tidak membuktikan siap operasi; artefak lokal saja belum membuktikan deployment produksi. Penggunaan untuk keputusan kredit nyata memerlukan scope dan validasi terpisah.

## Data dan target

File accepted/rejected tersedia lokal, tetapi sumber unduhan, lisensi dataset, tanggal snapshot/as-of dan checksum belum lengkap. MIT repo tidak otomatis memberi izin redistribusi data. MVP menggunakan accepted loans saja setelah provenance disepakati. Rejected bukan label negatif dan tidak boleh digabung sebagai non-default. Data accepted menimbulkan selection bias; hasil tidak mewakili semua pelamar.

Target sementara untuk diskusi: adverse observed outcome pada cohort pinjaman historis. Usulan definisi inti ialah Charged Off/Default versus Fully Paid; keterlambatan dan pinjaman current diperlakukan terpisah. Ini **bukan** keputusan final atau izin langsung mengubah label. Jika data tidak punya tanggal event/as-of yang cukup, hanya klaim analisis retrospektif outcome teramati; jangan klaim probabilitas default 12/24/36 bulan. Audit feasibility M0 harus menyelesaikan horizon dan label maturity sebelum evaluasi M1 dinyatakan sah.

Grade, sub_grade, int_rate, installment, dan verification_status hanya boleh masuk bila tersedia pada waktu penggunaan yang disepakati. Untuk scoring sebelum keputusan lender, fitur yang dihasilkan keputusan tersebut dikeluarkan. FRED ditunda dari baseline sampai publikasi/vintage dapat dibuktikan point-in-time. SEC tidak punya join sah ke pinjaman individu pada source sekarang dan berada di luar MVP.

## Non-goals

Keputusan kredit nyata, penggunaan data privat, klaim kepatuhan regulasi/fairness menyeluruh, high availability publik, retraining/promosi otomatis, survival production, DiCE actionable advice production, SEC enrichment ke borrower, UI kompleks, multi-agent/swarm, Hermes, Graphify baru, serta Ops Copilot. Modul yang sudah ada tetap dipertahankan dan diberi status integrasi yang akurat.

## Acceptance criteria

| ID | Kriteria | Bukti selesai |
|---|---|---|
| AC01 | Data snapshot dan label/waktu fitur jelas | Provenance, manifest, dictionary, keputusan eligibility dan maturity disetujui; row reconciliation/nonempty pass |
| AC02 | Evaluasi tidak mempelajari test | Regression test transform invariant terhadap perubahan test; temporal train/val/test manifest dan larangan tuning test |
| AC03 | Baseline dan kandidat dapat dibandingkan | Metrik pada cohort yang sama, denominator/prevalence/CI disebut, baseline dicatat; threshold/calibration memakai validation |
| AC04 | Training-serving konsisten | Record mentah yang sama menghasilkan probabilitas batch dan HTTP dalam toleransi usulan 1e-6; kategori unseen/null/kolom salah diuji |
| AC05 | API readiness jujur | Bundle absent/corrupt/incompatible -> readiness 503; loaded valid -> 200; score/explain sesuai bundle; liveness terpisah |
| AC06 | Release dapat diaudit/dipulihkan | Source SHA, dataset ID, bundle checksum, image digest dan hasil gate terikat; smoke dan rollback ke versi sebelumnya terbukti |
| AC07 | Monitoring mengukur penggunaan nyata | Event inference berversi; metrik traffic/latency/error serta contoh drift dan runbook dengan respons manusia |
| AC08 | Batas sumber daya eksplisit | Latency/load/RSS di Mac dan target staging yang disetujui; biaya aktual tercatat bila cloud digunakan |
| AC10 | Operasi mandiri dan pemahaman mendalam | Agatha dapat setup dari instruksi, melacak satu record, mengubah satu requirement, mendiagnosis failure baru, melakukan rollback dan menjelaskan trade-off tanpa menyalin jawaban AI; hasil dicatat |
| AC09 | Kontribusi Agatha bermakna | Minimal satu perubahan SQL/kode/tes per milestone, hasil review/tes, penjelasan kembali dan bukti commit setelah review |

Target PR-AUC minimum 0.25 dan latency <100ms berasal dari konfigurasi/dokumen lama, bukan hasil yang dijanjikan. Angka quality gate final, minimum n subgroup, target precision/recall, p95 latency dan load disahkan setelah baseline, sebelum kandidat/test release dievaluasi.

Persetujuan PRD tidak memberi izin deployment atau metadata rewrite remote. Scope milestone dan versi desain yang terkait tetap harus disetujui.
