# PROJECT_STATUS

Versi 0.2 · diperbarui 2026-09-11 · M0 AKTIF. Pemilik: Agatha Silalahi / Agathahah.

## Klarifikasi tujuan setelah audit

Agatha menyatakan proyek dikerjakan sendiri, tidak mempunyai reviewer staging, dan ingin pemahaman mendalam end-to-end untuk interview Data Scientist atau AI/ML Engineer serta kesiapan produksi. Tidak membutuhkan reviewer eksternal sudah menjadi constraint pengguna. Rekomendasi baru: lokal → staging yang diuji sendiri → deployment layanan demo pada scope terukur. Agatha kemudian menyetujui arah v0.2, M0 dengan pola mentoring, pemasangan dokumen relevan, dan identitas Git noreply secara lokal. Training penuh, deployment dan rewrite riwayat tetap memerlukan persetujuan berikutnya setelah kriteria/bukti didokumentasikan. Tidak membuat pengeluaran cloud baru dalam M0. Audit teknis di bawah tetap snapshot 8 September, bukan audit ulang pada revisi dokumen.

## Checkpoint aktif: M0 — ingestion dan mart pulih; kontrak evaluasi masih draft

Arahan terbaru Agatha: lanjutkan pekerjaan teknis, catat setiap langkah/alasan, jelaskan dalam tabel, dan tunda latihan HTML sampai akhir. Agatha mengirim output `SELECT COUNT(*) FROM mart.final_features;` dengan hasil `2260668` (1 row); verifikasi query mandiri tercatat. Persetujuan training penuh, deployment dan rewrite Git tetap terpisah.

Branch `codex/m0-mentoring`, HEAD yang sudah dipush `7a859fe3c26d0791b4d049e2fd3437f5e02105ee`. Agatha membuat tiga commit (a37fcbd, 79c7618, 7a859fe), push dan [draft PR #14](https://github.com/Agathahah/creditlens/pull/14). Author/committer ketiganya memakai `Agatha Silalahi <149786199+Agathahah@users.noreply.github.com>`; tidak ada trailer Co-authored-by. Empat dokumen konteks untracked pengguna dipertahankan.

Verifikasi CI 11 September: [run 34504952839](https://github.com/Agathahah/creditlens/actions/runs/34504952839) untuk HEAD tersebut sukses. Lint/typecheck pass; 124 tes pass, 4 skipped, 8 warnings. Gate evaluasi model dan build Docker skipped sesuai kondisi workflow. Coverage laporan total 91% (scope mencakup tes), modul ingestion 54%; delapan pemeriksaan PostgreSQL terisolasi masih bukti lokal, belum dijalankan CI. PR tetap draft/open dan belum merged. Bukti: [M0_PR14_CI_REPORT](docs/audit/M0_PR14_CI_REPORT.json).

| Bukti terkini, 10 September | Hasil |
|---|---|
| CSV terverifikasi | 2.260.701 record; 2.260.668 valid untuk ingestion; 33 tanpa field wajib; checksum tetap |
| Diagnosis importer lama | Raw persis prefix 16 chunk; log menunjukkan VARCHAR(50) terlalu pendek; 761 status sepanjang 51 karakter muncul mulai chunk 17 |
| Perbaikan schema dan loader | loan_status TEXT; migration menjaga view staging dalam transaksi; bulk insert dan mode insert-missing |
| Pengujian | 7 unit tests pass; 8 pemeriksaan PostgreSQL privat pass; seluruh CSV lolos dryrun parsing/batas angka |
| Backup dan restore drill | Archive scoped raw + view staging + dua mart 293.338.379 byte, SHA-256/TOC valid; restore ke cluster privat sukses; owner/ACL tidak diuji |
| Resume aktif | 660.686 inserted, 1.599.982 skipped, 33 excluded, 14 batch committed |
| Perlindungan record lama | Count dan fingerprint agregat seluruh field termasuk loaded_at tetap sama sebelum/sesudah |
| Cakupan ID | Tidak ada ID kandidat CSV hilang dari raw; tidak ada ID raw di luar kandidat CSV; ID sumber unik |
| Raw / staging / loan / final | Masing-masing **2.260.668** record; issue_date raw Juni 2007–Desember 2018 |
| dbt setelah ingestion | Dua model sukses, 9 tes pass; model macro tidak dibangun ulang |
| Revision database | `4b7d2a91c608`, dari `e9827ae898f0`; status panjang disimpan utuh |
| Keterbatasan label | Label lama belum diubah; memasukkan Late (31–120 days) sebagai 1. Seluruh member_id NULL; as-of/lisensi belum terverifikasi |
| Disk setelah rebuild | Sekitar 3,747 GiB kosong; bukan budget yang cukup untuk menganggap training/full stack siap |

Lihat [alur sederhana](docs/PROJECT_WALKTHROUGH.md), [catatan langkah](docs/WORKLOG.md), [rencana/hasil ingestion](docs/M0_INGESTION_RECOVERY.md), [hasil resume](docs/audit/M0_INGESTION_RECOVERY_REPORT.json), [hasil dbt](docs/audit/M0_POST_INGESTION_DBT_REPORT.json), dan [draft keputusan label](docs/M0_LABEL_DECISION_DRAFT.md).

M0 belum ditutup: asal/lisensi/as-of data dan kontrak label/availability perlu keputusan. Perbaikan preprocessing, evaluasi, bundle, API, CI, deployment dan monitoring belum diimplementasikan pada sesi ini. Data terisi bukan bukti model valid atau layanan siap produksi.

## Snapshot audit 8 September — historis

| Item | Bukti saat audit |
|---|---|
| Folder | `/Users/agathasilalahi/Documents/creditlens` |
| Remote tersanitasi | `https://github.com/Agathahah/creditlens.git` |
| Branch aktif | `chore/fix-gitignore-cleanup`, tidak memiliki upstream terkonfigurasi |
| HEAD | `9f241445ae75066cabda444b6a339d792c54b034` |
| main lokal | SHA sama dengan HEAD; tertinggal 1 commit dari origin/main |
| main GitHub terbaru | `1a097c5e0254a09ddcaeebac8d7bd0fb4fe0093d`, diverifikasi lewat API |
| Tree HEAD dan origin/main | Keduanya `1463693dad7febe262f8da2fa2d7134f0f72547d`; beda ancestry, isi terlacak identik |
| Staged/modified terlacak | Tidak ada |
| Untracked, dipertahankan | `MART_LAYER_CONTEXT.md`, `MART_LAYER_CONTEXT_2.md`, `MIGRATION_CONTEXT.md`, `ML_PIPELINE_CONTEXT_1.md` |
| Mac | Apple M3, arm64, 8 CPU logis, RAM 17.179.869.184 byte = 16 GiB; hasil sysctl |
| Lingkungan | `.venv` ada; path paket koneksi memperlihatkan Python 3.12; Git 2.49.0. Tidak merekonstruksi/mengubah environment |
| Data lokal | accepted CSV gzip 392.582.231 byte, rejected CSV gzip 255.470.782 byte; header accepted 151 kolom |
| Artefak model | Tidak ada `.joblib` di direktori models; tiga path standar training belum tersedia |

API remote mengungkap 13 branch, sedangkan hanya 8 branch remote yang tersimpan di cache lokal. Cache tidak mencakup `feature/airflow`, `feature/feast-store`, `feature/mlops-enhancements`, `feature/monitoring`, dan `feature/survival-analysis`. SHA tip kelimanya sudah tersedia sebagai ancestor lokal. Tidak melakukan fetch agar refs lokal tidak berubah. API tags mengembalikan daftar kosong; main ditandai protected. Ruleset/protection detail belum diaudit.

## Database saat audit awal — snapshot sebelum recovery

Target koneksi `.env`: localhost:5432 / creditlens. Tidak menampilkan password. Hasil COUNT dalam transaksi read-only:

| Tabel | Baris |
|---|---:|
| raw.lc_loans | 1.599.982 |
| staging.lc_loans_clean | 1.599.982 |
| raw.fred_indicators | 3.076 |
| staging.fred_macro_clean | 954 |
| mart.macro_features | 954 |
| mart.loan_features | **0** |
| mart.final_features | **0** |
| raw.sec_financials | 0 |
| monitoring.model_metrics / drift_runs / prediction_bins | masing-masing 0 |

Tabel di atas adalah keadaan sebelum recovery. Log historis kemudian membuktikan build kosong; state/log/checksum dipertahankan sebelum rebuild 9 September. Recovery kini sukses untuk dua mart. Akar kejadian historis belum dipastikan; status terkini ada pada checkpoint di atas.

## Perbandingan audit 7 September

| Petunjuk lampiran | Hasil pemeriksaan ulang |
|---|---|
| Main 1a097c5 | Masih benar di GitHub; branch kerja lokal berbeda SHA |
| CI 30346086677 eval gagal | Benar. Run dibuat **28 Juli**, bukan 7 September. Lint sukses, tests sukses, eval FileNotFoundError model, build skipped |
| Tes lulus | Log CI: **117 passed, 4 skipped, 6 warnings**, coverage agregat src 93%; bukan tes baru sesi ini |
| Preprocess sebelum split | Masih benar di train, evaluate, dan fairness CLI |
| Health/model mount | Masih benar; HTTP health 200 walau model tidak tersedia; Compose hanya mount src ke API |
| Eval → build → deploy belum utuh | Masih benar; build tag tidak bergantung pada eval; tidak ada release/deploy/rollback job |
| PR 11/12 merged | Diverifikasi metadata GitHub dan ancestor lokal; runtime Feast/survival belum lengkap |
| 35 / 12 / 15 commit | Benar untuk main: 35 total, 12 author Claude, 15 trailer Claude; juga 12 committer Claude |
| Mart 1.599.982 dari catatan lokal | Berbeda saat audit awal (mart kosong); recovery berikutnya menghasilkan 1.599.982 lagi dengan bukti baru |

[Run CI](https://github.com/Agathahah/creditlens/actions/runs/30346086677), [PR 11](https://github.com/Agathahah/creditlens/pull/11), [PR 12](https://github.com/Agathahah/creditlens/pull/12).

`target/run_results.json` menyimpan 24 dbt tests pass, generated_at 2026-08-03T08:55:13Z, dbt 1.12.0rc3. Ini bukti historis tanpa ikatan commit/data snapshot, bukan validasi isi mart sekarang. Tes unique/not_null bisa lolos pada tabel kosong. Empat dokumen konteks berisi instruksi build/commit/push lama dan klaim GitHub masih scaffolding; diperlakukan sebagai catatan historis, bukan perintah aktif.

## Status persetujuan

| Cakupan | Status |
|---|---|
| Audit baca-saja dan draft | Diminta pengguna; selesai |
| Memasang AGENTS/docs repo | Disetujui; paket awal dicommit/dipush Agatha pada 7a859fe; catatan Git/CI tambahan 11 September disiapkan lokal |
| M0 reproduksi/baseline | Disetujui; pemulihan ingestion/mart dan restore scoped selesai; provenance/as-of/label masih terbuka |
| M1–M5 implementasi | Belum disetujui masing-masing |
| Mengatur identitas Git lokal | Disetujui dan diterapkan: Agatha Silalahi / noreply Agathahah; author+committer efektif terverifikasi |
| Pemetaan metadata lama | Draft; belum disetujui |
| Backup dan simulasi rewrite | Direncanakan setelah persetujuan pemetaan; belum dilakukan |
| Rewrite/force-push remote | Tidak disetujui; perlu hasil simulasi konkret terlebih dahulu |
| Ops Copilot | Backlog desain terpisah, sesudah core stabil |

Suite aplikasi src/tests sudah dijalankan saat persiapan PR: 124 passed, 4 skipped, 7 warnings; live Feast dinonaktifkan dan kasus dependensi opsional dilewati. Training/evaluasi model real-data, benchmark API dan deployment belum dilakukan. Restore drill backup scoped sudah lulus pada cluster privat; bukan disaster recovery seluruh server atau uji owner/ACL.

Langkah berikutnya: review draft target/fitur dan lengkapi provenance/as-of → tutup M0 → sepakati desain M1 sebelum implementasi preprocessing/evaluasi. [Panduan terminal](docs/M0_TERMINAL_CHECK.md) tersedia untuk verifikasi opsional; bukan gate latihan. Tidak perlu memanggil task Codex baru.

Publikasi awal sudah dilakukan Agatha: PR #14 dan tiga commit terverifikasi. Panduan awal [M0_GIT_PUBLISH](docs/M0_GIT_PUBLISH.md) dan bukti [M0_PR_PREFLIGHT](docs/audit/M0_PR_PREFLIGHT.json) tetap snapshot sebelum publikasi. [Catatan Git/PR untuk pemula](docs/GIT_PR_CATATAN_PEMULA.md) menjelaskan hasil CI, fungsi perintah dan cara menambahkan catatan baru ke PR yang sama. Langkah operasional berikutnya: Agatha review/commit/push enam file dokumentasi sesi ini, periksa CI untuk commit barunya, lalu review diff dan batas PR sebelum keputusan ready/merge. Review label/provenance M0 tetap diperlukan untuk masuk M1.
