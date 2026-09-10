# Keputusan untuk CreditLens mandiri

> Status pemasangan 2026-09-08: arah v0.2 dan M0 disetujui. Detail implementasi di luar M0 tetap draft; ini bukan izin training penuh, deployment, atau rewrite.

v0.2 · DRAFT · Revisi berdasarkan klarifikasi Agatha. Arah v0.2 dan M0 disetujui Agatha; izin implementasi terbatas pada M0. Milestone berikutnya memerlukan persetujuan tersendiri.

## Rekomendasi

Bangun CreditLens menjadi layanan demonstrasi risiko kredit berbasis data publik yang siap dioperasikan dalam scope terukur, dengan Agatha memahami dan mampu mengubah seluruh alurnya. Mulai lokal untuk memperbaiki core, lanjut staging terisolasi yang diuji sendiri, kemudian deployment setelah desain, biaya dan bukti rilis disetujui. Penggunaan untuk keputusan kredit nyata berada di luar scope ini.

Staging adalah lingkungan terpisah untuk mencoba kandidat rilis: konfigurasi, schema, model, API, dan rollback. Tidak memerlukan reviewer eksternal. Agatha menjalankan acceptance tests dan menjadi pemilik keputusan rilis; Codex membantu review source dan hasil. Catat bahwa validasi dilakukan secara mandiri, tanpa klaim audit independen.

## Keputusan yang telah disetujui

| Keputusan | Rekomendasi dan alasan | Batas persetujuan |
|---|---|---|
| Arah proyek dan cara belajar | PRD/desain/evaluation/milestone v0.2: kualitas core dan pemahaman mendalam, proyek mandiri sampai layanan demo siap dioperasikan. Metrik, tests, debugging dan recovery menjadi bukti | Menyetujui arah tidak otomatis mengizinkan semua milestone |
| Memulai M0 | Diagnosis mart kosong, lingkungan isolasi lokal, kontrak dataset/label, tes kualitas data dan baseline software. Agatha menulis query/test nonempty dan hipotesis sebelum Codex melengkapi | Tidak melatih model real-data penuh, memodifikasi label/core ML, deploy, atau rewrite history. Perubahan hanya dokumen dan tes/reproduksi M0 yang disepakati; perubahan data development harus dijelaskan pada checkpoint |
| Identitas commit berikutnya | Agatha Silalahi, email 149786199+Agathahah@users.noreply.github.com; cocok dengan akun GitHub terautentikasi dan menghindari mempublikasikan Gmail | Set repo-local setelah disetujui; tanpa AI author/co-author otomatis. Tidak mengubah commit lama. Bantuan AI tetap dicatat naratif |

Agatha telah menyetujui pemasangan AGENTS/dokumen, M0 dengan pola mentoring, dan identitas noreply lokal. Dokumen serta identitas tersebut sudah diterapkan; sesi M0.1 menunggu percobaan Agatha. Untuk merencanakan biaya, rekomendasi tahap M0–M2 memakai perangkat yang sudah ada dan tidak membuat pengeluaran cloud baru. Cloud diputuskan saat kebutuhan dan benchmark diketahui; bukan syarat memulai.

Persetujuan pengguna: “Saya setuju arah v0.2 dan mulai M0 saja dengan pola mentoring, termasuk pemasangan dokumen relevan. Gunakan identitas Git noreply Agathahah secara lokal.” Pengguna akan mempertimbangkan deployment, training penuh, dan rewrite setelah kriteria serta dokumentasinya tercatat; ini bukan persetujuan otomatis ketika checklist selesai.

## Penyesuaian mentoring 2026-09-09

Setelah mengirim bukti koneksi/read-only, Agatha meminta pekerjaan dilanjutkan sambil dicatat, dengan HTML latihan dan materi singkat serta keterlibatan menjalankan perintah terminal. Codex dapat melanjutkan diagnosis independen dalam M0; tidak wajib menunggu jawaban setiap konsep. Praktik terarah dibedakan dari SQL yang ditulis Agatha sendiri; kontribusi tes nonempty tetap disisakan. Buku latihan awal ada di [M0_LATIHAN.html](M0_LATIHAN.html). Ini perubahan cara belajar, bukan izin milestone berikutnya, training penuh, deployment, atau rewrite.

## Arahan terbaru — latihan di akhir

Agatha kemudian meminta latihan tiap soal/HTML ditunda sampai akhir dan pekerjaan teknis dilanjutkan dahulu, dengan tabel alur/status serta catatan alasan setiap langkah/model. Ini menggantikan gate percobaan latihan sebelumnya: Codex kini mengerjakan COUNT dan tes M0 dengan atribusi eksplisit. Latihan akhir menggunakan variasi yang tetap membutuhkan kontribusi mandiri, bukan klaim bahwa Agatha menulis solusi Codex. Sasaran tetap layanan demo publik yang siap dioperasikan; persetujuan khusus training penuh/deployment/rewrite tidak otomatis diberikan. Scope label/evaluasi dan perubahan milestone berikutnya tetap harus dibuat konkret sebelum keputusan.

## Yang belum perlu diputuskan

Label/horizon final setelah feasibility M0; threshold/calibration dan tanggal split sebelum M1; Feast mode/bundle/API sebelum M2; platform/budget/exposure/load sebelum M3; monitoring retention/SLO sebelum M4; Ops Copilot sesudah core stabil. Metadata lama memiliki jalur pemetaan → persetujuan → backup/simulasi → review hasil → persetujuan remote tersendiri. Jangan membiarkannya menunda pembelajaran ML.

## Bukti pemahaman end-to-end

| Area | Demonstrasi Agatha | Bukti portfolio |
|---|---|---|
| Masalah/data | Menjelaskan unit loan, target, availability, selection bias dan alasan exclusion | PRD, dictionary, query cohort |
| SQL/dbt | Menelusuri record, menjelaskan join/window/null dan mencegah mart kosong | Perubahan SQL, failing/passing test |
| Modeling/evaluation | Membandingkan baseline, menjelaskan leakage/imbalance/calibration/threshold dan kegagalan model | Manifest split, laporan evaluasi, regression test |
| Serving | Menjelaskan perubahan raw fitur menjadi prediksi yang sama pada training dan HTTP | Bundle contract, parity/readiness tests |
| Operasi | Menjalankan rilis, membaca log, mendiagnosis model hilang atau schema mismatch dan rollback | CI evidence, deployment manifest, runbook dan recovery drill |
| AI engineering tambahan | Membangun retrieval dan satu loop tools yang dibatasi lalu mengevaluasi kualitas buktinya | Ops Copilot PRD/eval tersendiri setelah core; belum merupakan kemampuan yang telah dibuktikan |

Untuk setiap area: konsep singkat → tugas kecil → percobaan Agatha → review → perbaikan → tes → penjelasan kembali → satu variasi masalah baru. Minimal satu kontribusi bermakna per milestone adalah batas minimum, bukan batas maksimum; tingkat bantuan berkurang mengikuti kemampuan yang benar-benar ditunjukkan. Latihan memakai Bahasa Indonesia terlebih dahulu, lalu penyampaian teknis Inggris untuk interview.

Portofolio akhir memuat walkthrough 3–5 menit dan sesi mendalam, peta satu record end-to-end, keputusan model/arsitektur dengan alternatif, eksperimen yang berhasil/gagal, kontribusi Agatha berbukti, dan keterbatasan. Klaim “siap produksi” baru dibuat setelah acceptance criteria terpenuhi pada versi, lingkungan, beban dan scope yang dicatat.

## Checkpoint 10 September 2026

Kelanjutan M0 diminta Agatha. Pemulihan ingestion/mart, tes serta backup/restore scoped telah dijalankan Codex dalam scope pemulihan lokal. loan_status TEXT menjaga sumber utuh; insert-missing menjaga record lama. Hasil/batas ada di M0_INGESTION_RECOVERY.md.

Draft berikutnya: M0_LABEL_DECISION_DRAFT.md mengusulkan Fully Paid vs Charged Off/Default, tanpa late/current/out-of-policy dalam target utama dan tanpa klaim horizon tetap. Belum disetujui; tidak mengubah label atau mengizinkan M1/training. Pertanyaan asal dataset diajukan agar provenance/as-of bisa dilengkapi.
