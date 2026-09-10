# CreditLens — paket review awal

Versi 0.2 · diperbarui 9 September 2026 · **Arah dan M0 disetujui; M0 sedang berjalan**.

Audit awal dilakukan baca-saja dan hasilnya disimpan di luar repo. Setelah persetujuan Agatha, dokumen dipasang di repo, identitas Git repo-local diterapkan, dan branch codex/m0-mentoring dibuat. AGENTS.md sekarang menjadi aturan aktif. Belum ada commit/push, instalasi, training, deployment atau rewrite. Reproduksi dbt dan dua tes baru lulus; setelah disk dilonggarkan, recovery dua mart development sukses dengan 9 tes pass. Snapshot audit dibedakan dari bukti terbaru.

CreditLens belum siap pilot ujung ke ujung: staging dan kedua mart kini berisi 1.599.982 pinjaman, tetapi 660.686 ID kandidat CSV belum dimuat ke raw. Artefak model standar belum ada; preprocessing, kontrak fitur, dan jalur rilis belum memenuhi bukti kesiapan. Klaim README lama “production-grade” bukan hasil verifikasi; README kini menyatakan status M0.

Versi 0.2 memperbarui rencana berdasarkan tujuan proyek mandiri; snapshot audit v0.1 dipisahkan dari hasil M0 terkini. Salinan v0.1 dipertahankan.

## Urutan review

1. [PROJECT_STATUS.md](../PROJECT_STATUS.md): kondisi aktual, pembanding audit lama, status persetujuan.
2. [AUDIT_FINDINGS.md](audit/AUDIT_FINDINGS.md): masalah berprioritas dan sumber buktinya.
3. [PRD.md](PRD.md): batas pilot dan acceptance criteria.
4. [DATA_DESIGN.md](DATA_DESIGN.md): ERD, dictionary, label dan waktu fitur.
5. [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md): alur aktual/target dan satu record.
6. [EVALUATION_RELEASE_PLAN.md](EVALUATION_RELEASE_PLAN.md): evaluasi dan bukti rilis.
7. [MILESTONES_ADR.md](MILESTONES_ADR.md): tugas Agatha/Codex dan keputusan.
8. [AGENTS.md](../AGENTS.md): aturan mentoring aktif.
9. [GIT_ATTRIBUTION_PLAN.md](GIT_ATTRIBUTION_PLAN.md): identitas, scope metadata, backup/simulasi/remote.
10. [LEARNING_LOG.md](../LEARNING_LOG.md): bukti pembelajaran tanpa klaim kontribusi fiktif.

Lampiran bukti: [GIT_COMMIT_INVENTORY.md](audit/GIT_COMMIT_INVENTORY.md), [GIT_EVIDENCE.json](audit/GIT_EVIDENCE.json), [REPO_FILE_HASHES.json](audit/REPO_FILE_HASHES.json).

## Keputusan berikutnya

Baca [ringkasan keputusan](DECISIONS.md) terlebih dahulu. Rekomendasi: tujuan akhir layanan demo data publik siap dioperasikan, lokal dahulu, staging diuji Agatha sendiri, Git noreply untuk commit berikutnya, rewrite history ditunda. Persetujuan sekarang dibatasi pada M0 dan pengaturan identitas repo-local; milestone berikutnya memiliki checkpoint terpisah.

Tidak ada reviewer eksternal yang diwajibkan. PRD, technical design, evaluation/release, milestone, AGENTS draft, status dan learning log sudah direvisi ke v0.2. Audit findings/data dictionary/Git plan tetap bukti/rencana v0.1; keputusan label detail masih menunggu M0. Pemasangan dokumen/identitas dan dua tes SQL M0 sudah dilakukan. Latihan ditunda sampai akhir sesuai arahan terbaru; tidak lagi menunggu M0.1/COUNT.

## Ringkasan terbaru

- [Alur proyek dan status](PROJECT_WALKTHROUGH.md)
- [Mengapa kandidat model dipertimbangkan](MODEL_DECISIONS.md)
- [Catatan tiap langkah](WORKLOG.md)
- [Rencana isolasi](M0_ISOLATION_PLAN.md) dan [rencana pemulihan mart](M0_MART_RECOVERY.md)
- [Hasil pengujian terisolasi](audit/M0_ISOLATED_TEST_REPORT.json) dan [recovery development](audit/M0_MART_RECOVERY_REPORT.json)
- [Cakupan sumber dan provenance](DATA_PROVENANCE.md) serta [panduan pemeriksaan terminal](M0_TERMINAL_CHECK.md)

HTML latihan awal adalah draft; paket latihan akhir akan mengikuti implementasi akhir, bukan ditugaskan sekarang.

Pembaruan M0 10 September: [pemulihan ingestion](M0_INGESTION_RECOVERY.md), [draft keputusan target](M0_LABEL_DECISION_DRAFT.md), [pemeriksaan terminal terbaru](M0_TERMINAL_CHECK.md), [catatan langkah](WORKLOG.md).

Publikasi bersama: [perintah commit/push/draft PR](M0_GIT_PUBLISH.md) dan [deskripsi PR siap review](M0_PR_BODY.md).
