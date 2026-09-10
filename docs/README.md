# CreditLens — paket review awal

Versi 0.2 · diperbarui 11 September 2026 · **Arah dan M0 disetujui; M0 sedang berjalan**.

Audit awal dilakukan baca-saja. Setelah persetujuan Agatha, dokumen dipasang, identitas Git repo-local diterapkan dan M0 dijalankan. Ingestion/mart telah dipulihkan dengan backup/restore teruji. Agatha membuat tiga commit, push dan draft PR #14; CI pada 7a859fe lulus lint/typecheck serta 124 tes, dengan 4 tes dilewati. Evaluasi model/build Docker dilewati sesuai workflow PR. AGENTS.md adalah aturan aktif; training penuh, deployment dan rewrite belum dilakukan.

CreditLens belum siap pilot ujung ke ujung: raw, staging dan kedua mart kini masing-masing berisi 2.260.668 pinjaman dan seluruh ID kandidat CSV tercakup. Provenance/as-of/label belum diputuskan, artefak model standar belum ada, preprocessing/kontrak fitur/jalur rilis belum memenuhi bukti kesiapan. Status M0 dan hasil lama selalu dibaca bersama tanggalnya.

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

Sesudah PR dibuat: [catatan Git/PR pemula dan langkah berikutnya](GIT_PR_CATATAN_PEMULA.md), [bukti Git dan CI PR #14](audit/M0_PR14_CI_REPORT.json). Catatan ini mencakup pager (END), staging Git, commit/push, PR, CI, serta batas menuju produksi.
