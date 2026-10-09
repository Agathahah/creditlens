# Technical worklog

## 2026-09-08 — baseline audit

Raw and staging contained 1,599,982 loans while both loan marts were empty. Source review identified preprocessing before split, estimator-only persistence, incomplete model readiness, evaluation gates without artifacts, and monitoring queries not based on inference events. Findings remain in audit/AUDIT_FINDINGS.md; unchanged findings remain open.

## 2026-09-09 — mart reproduction and recovery

- Reproduced the empty-data failure on a private PostgreSQL cluster. The 24 existing dbt tests passed with empty input.
- Added nonempty_required_models and reconcile_loan_counts. Negative cases detected empty relations and stale staging→loan/loan→final counts.
- Built a two-loan fixture: five models and 26 tests passed. Deleting one final row was detected; rebuilding restored the expected counts.
- Initial active recovery stopped before mutation at the disk preflight. After capacity increased, backed up two empty marts and rebuilt only loan_features/final_features.
- Both marts recovered to 1,599,982 records and nine selected dbt tests passed.
- Source profiling found 660,686 candidate CSV IDs still missing from raw.

Evidence: audit/M0_ISOLATED_TEST_REPORT.json, audit/M0_MART_RECOVERY_PREFLIGHT_REPORT.json, audit/M0_MART_RECOVERY_REPORT.json.

## 2026-09-10 — ingestion recovery

| Change / check | Reason and result |
|---|---|
| Source/log diagnosis | Raw IDs matched the first 16 CSV chunks; 761 statuses of length 51 exceeded VARCHAR(50), beginning in chunk 17 |
| TEXT migration + ORM/init SQL | Preserve complete source strings; recreate the known dependent view transactionally; refuse unsupported metadata/dependencies and unsafe downgrade |
| Batch loader + insert-missing | Resume missing IDs without updating existing rows; rollback failed batches; report exclusions/commits |
| Fixture verification | Seven unit tests and eight private PostgreSQL checks passed, including no-op repeats and downgrade protection |
| Full CSV dryrun | 2,260,668 valid candidates; 33 missing required fields; date/numeric validation passed |
| Scoped backup/restore | Restored raw, staging view and both marts on a private server; counts and five raw indexes verified |
| Restore environment correction | Initial socket path exceeded the macOS limit; a shorter private path allowed the drill to complete |
| Active recovery | 660,686 rows inserted; 1,599,982 skipped; 33 excluded; 14 committed batches |
| Preservation/reconciliation | Existing rows retained count and aggregate fingerprint; source/raw ID differences were zero |
| dbt rebuild | Two models and nine tests passed; raw/staging/loan/final each 2,260,668 |
| Label feasibility | Proposed resolved-outcome mapping gives 1,345,350 candidates before temporal eligibility; no label or model change applied |

Evidence: audit/M0_INGESTION_DIAGNOSIS.json, audit/M0_INGESTION_DRYRUN.json, audit/M0_INGESTION_RESTORE_REPORT.json, audit/M0_INGESTION_RECOVERY_REPORT.json, audit/M0_POST_INGESTION_DBT_REPORT.json, audit/M0_LABEL_FEASIBILITY.json.

## 2026-09-10–11 — pull request validation

PR #14 contains the dbt tests, ingestion fix and supporting documentation. Local application checks passed (124 tests, four skipped); the detailed GitHub run on 7a859fe also passed with 124 tests, four skipped and eight warnings. The subsequent run 34506955747 on 745dd28 passed lint/typecheck and tests; evaluation/build jobs were skipped.

The ingestion module's reported CI coverage on the detailed run is 54%. Private PostgreSQL checks have not been integrated into CI. Model/data inputs to the main-branch evaluation gate remain unresolved.

## 2026-09-11 — documentation scope correction

Consolidated documentation around product scope, implementation, architecture, decisions, runbooks and technical evidence. Removed unrelated documents, corrected outdated status summaries and aligned the proposed PR description with the implementation. Source code, SQL, test behavior and factual validation results are unchanged. Documentation checks cover patch formatting, JSON parsing and internal links.

## 2026-09-11 — review perubahan M0

PR #14 dan commit lokal telah dicocokkan pada 0acd49a. Run 34556669746 lulus pemeriksaan gaya kode/tipe dan tes aplikasi; evaluasi model serta pembuatan image dilewati. Review meliputi parsing/impor lanjutan, migrasi skema, konsistensi ORM/SQL awal, tes dbt dan bukti database terisolasi. Pekerjaan evaluasi pada main belum menyediakan artefak model dan dataset evaluasi; masalah lama ini masih terbuka. Bukti pemulihan M0 tersedia, sedangkan asal data dan keputusan target/ketersediaan fitur belum selesai. Lingkup review, batas bukti dan usulan CI dicatat dalam audit/M0_PR14_REVIEW.md. Tidak dilakukan pemulihan database, training atau rilis selama review ini.

Konfirmasi hasil query pengelompokan target sesuai dengan audit sebelumnya: 1.076.751 kandidat label 0, 268.599 kandidat label 1 dan 915.318 record di luar target utama. Hasil ini dilaporkan dari pemeriksaan baca-saja, bukan eksekusi database baru oleh reviewer. Label SQL belum diubah. Laporan review M0 menggunakan bahasa Indonesia dengan definisi istilah, bukti, batas kesimpulan dan langkah tindak lanjut.

Profil tahun/tenor: 21 baris keluaran query diperiksa ulang secara aritmetika; seluruh jumlah per baris dan total cocok dengan agregat target. Proporsi di luar target pada 2018 adalah 88,03% untuk tenor 36 bulan dan 90,01% untuk 60 bulan. Ini menunjukkan komposisi kandidat sangat berbeda antar-kelompok, tanpa membuktikan penyebab atau tanggal snapshot. Disiapkan query rincian status per periode untuk membedakan status berjalan/terlambat, di luar kebijakan, dan status lain. Belum ada perubahan SQL label atau cutoff dataset.

Rincian status: sepuluh baris keluaran query menjelaskan semua 915.318 record di luar target. Sebanyak 2.749 status di luar kebijakan berada pada 2007–2010; 912.569 lainnya berstatus Current, terlambat atau masa tenggang. Subtotal periode dan agregat status cocok dengan pemeriksaan sebelumnya. Penelusuran dokumentasi serta metadata file lokal belum menemukan asal unduhan atau tanggal snapshot yang dapat diverifikasi. Draft target diperinci menjadi mapping, aturan kandidat fitur dan kriteria tes untuk review sebelum implementasi.

## 2026-09-11 — implementasi kontrak label retrospektif

Kontrak Fully Paid=0, Charged Off/Default=1, status lain=NULL disetujui untuk SQL dan tes PostgreSQL terisolasi. SQL staging serta deskripsi skema diperbarui; ditambahkan tes dbt loan_label_contract pada staging dan dua mart. Skrip verify_m0_dbt.py diperluas dengan 11 kasus label dan pemeriksaan kesamaan ID/status/label serta raw sebelum/sesudah build.

Tes baru terlebih dahulu gagal pada SQL lama dengan tiga pelanggaran. Sesudah perbaikan, pemetaan label lulus; dua label Current/Late yang sengaja dirusak dan satu label Fully Paid yang dikosongkan berhasil dideteksi. Kasus sumber kosong tetap ditolak tes kualitas sumber. Setelah fixture negatif dipulihkan, lima model dan 27 tes lulus, kemudian cluster dihentikan. Bukti: audit/M0_LABEL_ISOLATED_REPORT.json. Database aktif tidak direbuild; tidak ada training, perubahan CI, commit/push, merge atau deployment.

Delapan pemeriksaan regresi ingestion/migrasi juga dijalankan ulang pada cluster privat dan lulus, termasuk pemulihan definisi view staging yang telah berubah. Black, isort, Ruff dan mypy lulus untuk skrip yang diubah; patch, JSON, hash source terhadap laporan tes serta tautan dokumen diperiksa. Kedua cluster pengujian telah dihentikan.

## 2026-09-11 — perbaikan startup tes PostgreSQL

Startup cluster sementara gagal dengan pesan postmaster became multithreaded during startup dan petunjuk LC_ALL. Skrip kini menetapkan LC_ALL=C serta LANG=C hanya pada environment proses anak, serta menampilkan lokasi log server saat startup gagal. Pengujian dengan locale induk yang sengaja tidak valid berhasil sampai akhir: lima model, 27 tes, kasus negatif sesuai harapan, cluster dihentikan. Pemeriksaan gaya kode dan tipe lulus. Bukti serta hash source terbaru: audit/M0_DBT_STARTUP_FIX_REPORT.json. Tidak ada perubahan pada database aktif atau pengaturan shell global.

## 2026-09-11 — preflight penerapan label

Verifikasi ulang Terminal lulus dan hash source dicocokkan. Preflight database aktif memakai transaksi read-only: server 14.22, migrasi 4b7d2a91c608, jumlah 2.260.668 pada empat layer, dengan 21.467 label yang masih berbeda dari kontrak baru pada staging dan kedua mart. Permintaan data_directory tidak diizinkan role aplikasi, sehingga pemeriksaan dilanjutkan tanpa menaikkan hak database; kapasitas disk hanya dilaporkan untuk filesystem repo/backup.

Skrip tes memperoleh opsi --pg-bin agar versi cluster dapat disamakan dengan server aktif. Pengujian pada PostgreSQL 14.22 lulus lima model/27 tes dan cluster dihentikan; bukti audit/M0_LABEL_PG14_REPORT.json. Backup ingestion historis belum mencakup kondisi terbaru. Disiapkan M0_LABEL_ROLLOUT.md untuk backup baru dan persyaratan restore/simulasi sebelum persetujuan perubahan aktif. Backup baru atau rebuild aktif belum dijalankan pada tahap ini.

## 2026-09-11 — backup label, simulasi penerapan dan rollback

Backup lima relasi terbaru berhasil dibuat dan checksum diverifikasi: 060527b72cd4eea7aeb416ec0840284b8c7986051cca4618c25031801bd18fb3, ukuran 416.630.843 byte. Arsip berada pada direktori lokal yang diabaikan Git. Ditambahkan scripts/verify_m0_label_restore.py untuk memulihkan arsip pada PostgreSQL 14.22 privat, memeriksa baseline, membangun hanya tiga model pinjaman, membandingkan record dan menguji pemulihan kondisi lama.

Simulasi lulus tiga model dan 12 tes. Setiap layer mempertahankan 2.260.668 record dan ID unik; jumlah label 1 berubah dari 290.066 menjadi 268.599 dan NULL dari 893.851 menjadi 915.318. Perbandingan per ID menunjukkan nol perubahan kolom selain label. Raw/macro mempertahankan jumlah serta sidik agregat. Rollback memulihkan seluruh nilai record termasuk label dan definisi view tanpa perbedaan; cluster dihentikan. Bukti agregat dan hash source: audit/M0_LABEL_RESTORE_REPORT.json.

Black/isort/Ruff/mypy untuk skrip baru lulus. Restore tidak mencakup owner/ACL; pemeriksaan metadata target dan batas bukti dicatat di M0_LABEL_ROLLOUT.md. Rencana penerapan aktif diperinci dengan validasi baseline, seleksi tiga model, timeout, verifikasi dan pemulihan. Database aktif belum diubah, penerapan label masih menunggu persetujuan; tidak dilakukan commit/push, perubahan CI, training atau deployment.

## 2026-09-12 — persetujuan penerapan dan pemeriksaan kapasitas

Penerapan label terbatas serta pemulihan bila gagal disetujui. Branch, HEAD dan remote tetap sama; checksum backup, hash source dan salinan laporan cocok. Pemeriksaan filesystem menunjukkan ruang bebas sekitar 185–217 MiB, sehingga query berat dan rebuild aktif tidak dijalankan. Cluster simulasi sudah berhenti dan pgdata-nya memakai 4,3 GiB. Disiapkan arahan pembersihan hanya salinan yang dapat dibuat ulang; backup asli dan log dipertahankan. Pembersihan belum dieksekusi. Persetujuan dicatat dalam AGENTS.md dan rencana penerapan; kapasitas minimal 8 GiB perlu tersedia sebelum preflight berikutnya. Tidak ada perubahan label aktif, commit/push, training atau deployment.

## 2026-09-22 — penerapan label pada database aktif

Setelah ruang disk mencapai di atas 8 GiB, preflight baca-saja mencocokkan backup teruji, hash source, revisi, baseline tiga layer, input raw/macro, view dan metadata. Operator memastikan tidak ada workload CreditLens lain. Build terbatas lulus tiga model/12 tes; label positif turun 21.467 pada masing-masing layer menjadi 268.599, sementara NULL naik menjadi 915.318. Jumlah dan ID unik 2.260.668 tetap. SHA-256 baris berurutan tanpa label cocok sebelum/sesudah; raw/macro tidak berubah menurut sidik agregat. Autovacuum muncul sebagai proses perawatan setelah build. Laporan: audit/M0_LABEL_ACTIVE_ROLLOUT_REPORT.json. Rollback aktif tidak diperlukan; training, CI, merge dan deployment tidak dijalankan.

## 2026-09-22 — penelitian identitas artefak dataset

SHA-256, ukuran byte, jumlah kolom dan baris file gzip lokal cocok persis dengan artefak pada diagram provenance di repositori riset King's College London. Nama, ukuran dan format kolom bunga/utilisasi mendukung dataset Kaggle oleh Nathan George sebagai kandidat sumber distribusi. Catatan unduh lokal tidak ditemukan. Label CC0 pada halaman Kaggle dan kekhawatiran syarat penyedia asal yang dicatat pengunggah dipisahkan dari keputusan hak penggunaan untuk demo publik. Waktu metadata gzip tidak dipakai sebagai waktu snapshot outcome. Bukti terstruktur: audit/M0_DATA_SOURCE_RESEARCH_2026-09-22.json. Tidak ada data mentah yang dipublikasikan.

## 2026-09-23 — implementasi dan evaluasi M1 lokal berbatas sumber daya

Persetujuan eksplisit diberikan untuk M1 lokal sesuai `M1_LOCAL_IMPLEMENTATION_SCOPE.md`, tanpa
training penuh, deployment, merge atau push. Dibuat pipeline baru yang membagi data sebelum fit,
menggunakan whitelist fitur, median/RobustScaler numerik dan one-hot kategori hanya dari train, serta
menyimpan alasan exclusion dan checksum membership. Enam tes kontrak lulus, termasuk batas split,
status unresolved, larangan fitur leakage, kategori baru, train-only preprocessing dan reload artefak.

Cohort eligible berisi 157.993 train 2011–2013, 162.570 validation 2014 dan 283.024 frozen test
2015. Sebanyak 147 outcome unresolved dan dua annual income tidak valid dikeluarkan dengan alasan
tercatat. Constant baseline, Logistic Regression dan satu XGBoost kecil dijalankan dengan maksimum
dua thread. XGBoost dipilih dari validation dengan AP 0,2046, dibanding Logistic Regression 0,2016.
Frozen test dibuka sekali: AP 0,2197, ROC-AUC 0,6343 dan Brier 0,1241. AP gagal gate historis 0,25.
Ambang validation precision minimal 80% hanya didukung satu prediksi dan menghasilkan nol prediksi
positif pada test; operating point ditolak. Frozen test 2015 kini consumed.

Sesudah kegagalan dicatat, fungsi threshold diperkeras agar precision constraint memerlukan minimal
100 predicted-positive dan 0,5% baris validation. Ditambahkan tes negatif untuk titik precision tinggi
yang hanya didukung satu kasus. Perbaikan tidak dievaluasi ulang pada test 2015.

Eksekusi memerlukan 17,4 detik dan peak RSS sekitar 1.640,7 MiB pada macOS. Laporan mesin, model,
membership, SQL pembelajaran, notebook dan visual disimpan privat pada jalur yang diabaikan Git.
Bukti agregat yang aman direview: `audit/M1_LOCAL_EVALUATION_2026-09-23.md`. `mypy` dan `isort`
tidak tersedia pada environment Conda ini; Ruff, Black check dan enam tes M1 lulus. Collection seluruh
tes ML lama tertahan karena `email-validator` belum terpasang. Tidak ada commit, push, merge,
perubahan API, Docker release atau deployment.

Warning `fork()` pada macOS yang muncul dalam tes M1 berasal dari `n_jobs=2` pada Logistic
Regression. Parameter tersebut dihapus karena solver baseline ini tidak memerlukan proses anak;
XGBoost tetap dibatasi dua thread. Tes M1 kemudian dijalankan ulang untuk memastikan warning hilang.

Smoke Docker API dijalankan ulang dengan Docker 29.0.1. Allowlist `.dockerignore` membatasi context
ke 245,91 kB. Image 966.769.397 byte berhasil dibangun; `/health` mengembalikan HTTP 200 dengan
`model_loaded=false`, sedangkan `/predict` mengembalikan HTTP 503. Build sekitar sembilan menit dan
memasang dependency proyek lengkap, termasuk dependency transitive besar; ini menjadi alasan untuk
dependency set API yang dipin sebelum release. Container, image smoke dan 3,705 GB build cache yang
dapat dibuat ulang kemudian dihapus. Volume Docker tidak dihapus. Ruang host kembali sekitar 7,7 GiB.
Lihat `audit/M1_DOCKER_SMOKE_2026-09-23.md` dan `LOCAL_DOCKER_GUIDE.md`.

## 2026-09-23 — keputusan holdout M1 berikutnya

Pemilik proyek menyetujui arah eksperimen berikutnya: penggunaan demo pendidikan/portfolio,
prediction time saat aplikasi sebelum grade/pricing, target outcome buruk 36 bulan untuk tenor 36
bulan, dan satu holdout independen dari dataset/snapshot baru yang provenance, hak penggunaan,
as-of dan timing outcome-nya dapat diaudit. Tahun split belum ditetapkan karena harus diturunkan dari
maturity sumber baru tanpa membuka test.

Karena belum ada biaya false positive/false negative untuk keputusan kredit nyata, demo hanya
melaporkan probabilitas dan kurva operating point validation dengan minimum support. Threshold
approve/reject ditunda. Disusun `M1_NEXT_EXPERIMENT_SCOPE.md` sebagai gerbang intake, outcome/fitur,
split, evaluasi dan bukti. Tidak ada training baru, pembukaan ulang frozen test 2015, perubahan API,
deployment atau data mentah yang dipublikasikan pada tahap ini.

## 2026-09-29 — kelanjutan scope dan intake sumber M1

Scope eksperimen berikutnya disetujui untuk persiapan dan eksekusi lokal berbatas sumber daya setelah
gerbang sumber/kontrak/split lulus dan protokol terkunci. Status sumber saat ini MISSING_SOURCE;
persetujuan tidak menghilangkan persyaratan data. Tahun split belum ditetapkan.

Seleksi dokumentasi sumber membedakan turunan Zenodo 2007–2018, dataset Mendeley 2008–2019
dengan target BADLOAN yang berbeda, dan data mortgage Freddie Mac. Tidak ada sumber yang sudah
lolos kontrak personal-loan saat aplikasi/horizon 36 bulan dalam pencarian terbatas ini. Endpoint
historis LendingClub belum dapat diverifikasi melalui alat riset. Rujukan dan batas audit dicatat
dalam M1_SOURCE_INTAKE_GUIDE.md.

Ditambahkan scripts/inspect_m1_source.py untuk inventory folder privat dan inspeksi checksum/ukuran/
header CSV atau gzip. File hilang dan header ambigu menghasilkan status eksplisit; snapshot lama
ditandai dan semua hasil tetap ready_for_training=false. Script tidak mengakses database, memuat
record ke model atau membaca skor test. Tes memakai fixture sintetis kecil; laporan lokal tetap
privat. Persyaratan gap label availability dan independensi terhadap membership historis diperjelas.


## 2026-09-29 — push verification, local readiness and aggregate dashboard

Verified GitHub PR #14 head f1f430a and CI run 36519072615: lint/typecheck and application tests
passed, evaluation and Docker skipped. Added process liveness and fail-closed readiness; predictor
access now rejects missing/unverified/incomplete bundles. The legacy loader leaves verification
false. Existing API tests explicitly inject verified synthetic fixtures. API Docker HEALTHCHECK
now checks /ready. This is preparatory software protection; full manifest validation, runtime
compatibility, quality evidence and raw-to-HTTP parity remain unfinished.

Added a read-only Streamlit research dashboard with dated public aggregates, cohort distributions,
validation comparisons, recorded failed frozen-test results and limitations. No new training,
raw data access or test-set selection was performed. Added a separate non-root dashboard Dockerfile
and directly pinned UI dependencies; transitive lock and base-image digest remain open.

In an isolated temporary Python environment, 20 API/dashboard tests passed; one existing Feast
wiring test was deselected because Feast was not installed. Three Starlette deprecation warnings
were reported. Black, Ruff and isort checks passed for changed Python files. Targeted mypy with
follow-imports=silent passed; unrestricted local import checking encountered seven pre-existing
NumPy generic annotation errors in ML/explanation modules with local NumPy 1.26.4. New remote CI
is still required. Streamlit preview rendered and was inspected in the browser.

About 4.8 GiB free was observed before preparation, so Docker images were not rebuilt. No active
database mutation, model admission, full training, deployment, merge, commit or push was performed
in this preparation. Release prerequisites are recorded in PRODUCTION_READINESS_ROADMAP.md.


## 2026-09-29 — dashboard packaging CI and pilot preparation

Verified pushed head 61c960c and run 36535113262: lint/types pass, 146 passed / 4 skipped / 7
warnings; reported coverage 89% includes src test files. Added a separate Dashboard Docker Smoke
job after lint/tests, with read-only repository permissions and an image/revision-bound artifact.
The job checks healthy/non-root runtime, HTTP and absence of data/model/secret/backup paths.
A failed-health command fixture test verifies that smoke cannot report success and cleans only
its own container. Bash syntax and workflow parsing/dependencies passed. Actual image build
awaits new CI execution; laptop disk about 7.2 GiB does not meet the local 8 GiB smoke rule.

Added an entrypoint-level dependency file for the aggregate-only Streamlit pilot, reusing the UI
requirements and avoiding full project ML dependencies. Dependency include resolution dry-run
passed. Replaced deprecated dataframe width option; two rendered dashboard tests passed locally.
Added a technical pilot runbook with actual-URL verification and explicit rollback limits.
Community Cloud is a proposed free dashboard host, not an operated scoring service. No deployment,
new model fit/evaluation, database mutation, commit or push was performed in this preparation.
Personal storytelling/CV/publication notes remain in ignored private storage.


## 2026-09-29 — dashboard story and traceable aggregate distributions

Redesigned the aggregate-only UI into seven narrative sections with warehouse year/term filters,
label distribution, annual volume, vintage completeness heatmap, eligible-cohort purpose counts,
lineage/recovery evidence, model selection, API/security boundaries, deployment proof and conclusions.
Counts from the read-only 23 September profile reconcile with the public M0 label rollout;
603,587 eligible M1 loans remain distinct from 2,260,668 warehouse loans. Added repeatable-read
aggregate SQL; it was not executed against the active database during this change.

Preserved the failed historical gate and consumed test. The packaging snapshot records the
operator's 29 September smoke for code revision 928acc6, plus its CI link. It does not claim to
verify this new UI, a public cloud URL or an approved scoring model. No inference, new training,
active database mutation, cloud deployment, model admission or publication was performed.

Focused UI/aggregate/empty-state/error-state and negative packaging tests: 11 passed locally.
The isolated UI environment lacks pytest-asyncio, producing one unknown asyncio_mode config warning;
this is a test-runner configuration limitation, not an application exception. Black, Ruff and
isort passed for changed Python files; targeted mypy with follow-imports=silent passed for the
standalone dashboard module. Browser verification covered the overview and vintage visualization;
responsive layout was inspected separately. CI/build for this redesign remain pending after push.

Verification in the main checkout also reported a sandbox restriction on writing pytest cache.
All 11 tests still passed; no cache data is required by the application.


## 2026-09-30 — use case, dataset sheet and explicit model release decision

Added a prospective application-time manual-review *use case* to the research dashboard, while
retaining accepted-loan selection bias and unverified 36-month outcome timing. Curated only
historical aggregate feature percentiles/vintage/home ownership from the private read-only
23 September profile; extended the public repeatable-read SQL to reproduce those aggregates.
The new queries were not executed in this change. The model page now explains constant,
Logistic Regression and bounded XGBoost separately with validation metrics, relative tradeoffs,
and the selected candidate's failed frozen-test confusion matrix. No new fit or test use occurred.
The 30 September decision report records REJECT for the historical model and BLOCKED for scoring.
Public pilot publication and fresh CI are follow-on verification steps; they do not waive model gates.


## 2026-09-30 — verified aggregate dashboard pilot

Committed and pushed `084e524` on `codex/m0-mentoring`. PR #14 remained draft. CI run
36685936180 passed lint/typecheck, application tests and Dashboard Docker Smoke; the API-image
and model-gate jobs were skipped. The aggregate-only app was deployed on Streamlit Community
Cloud at https://creditlens-risk-evidence.streamlit.app/ with Python 3.12 and no secrets.
Cloud Sharing showed public and searchable. Nine live pages rendered without application errors;
the business, dataset and model pages displayed the intended caveats and historical numbers.
An anonymous HTTP request with a temporary in-memory cookie session returned 200. The release
snapshot records revision `084e524` and verification time `2026-09-30T08:03:29Z`.

This is a public research dashboard pilot. No scoring bundle was admitted, no fresh holdout was
opened, and the failed M1 candidate was not promoted. The branch may auto-update the Cloud app;
later revisions require a new public smoke before their URL evidence is considered current.

## 2026-09-30 — portfolio monitoring direction and dashboard narrative

The requested next use case is monitoring funded loans after disbursement. This updates the
direction for future data intake and experiment design; the application-time M1 results remain
historical and cannot be reused as an active-loan alert model. The dashboard copy now tells that
sequence plainly across nine pages, with a separate explanation of the three old model
candidates, their failed release gate, API refusal, and the public research pilot. The
downloadable summary uses the dated public-deployment evidence from the snapshot. A new
portfolio-monitoring scope states the periodic panel, prospective outcome, independent
evaluation and operating controls required before scoring can be reconsidered. No new
dataset was supplied, no model was trained, and no live alert was claimed.


## 2026-10-07 — private monthly-panel research and public BI status

Implemented a streaming ZIP-to-SQLite mortgage research builder with explicit three-calendar-month
labels, nullable censoring, a minimal as-of feature whitelist, strict keys/layout and owner-only
outputs outside Git. Development intake rejects frozen-test vintage 2020. The source is corrected
historical data; no claim of verified point-in-time availability or admission for training.
Actual local execution completed on sample 2018; private report/derived database remain outside Git.
No source records, outcome tables or model artifacts were published. No training, test evaluation,
scoring promotion or database recovery mutation was performed.

Updated Tableau runbook with the verified dashboard URL and filter reconciliation. Added a
Streamlit research-status page and Tableau link; public deployment of these UI changes must be
verified separately. Package metadata no longer claims production-grade scoring and points to the
actual repository. Existing API fail-closed contracts remain in place; no fake model pass replaces
the LendingClub historical failure.

Validation before publication: 27 focused tests passed (panel, dashboard and API readiness),
with four dependency deprecation warnings; new panel module coverage was 86%. Remaining uncovered
branches include malformed-file failures and CLI entry. Black/isort/ruff and strict mypy were run
on the changed Python files. The bounded local build completed in 17.09 seconds with about
80.3 MiB maximum RSS and a 248.3 MiB private SQLite output on this Mac; this is a panel-build
measurement, not training, serving capacity or an API latency benchmark.

Full application suite before commit: 169 passed, 4 skipped, 8 warnings in 22.42 seconds.
Skipped external/optional integration checks are not production evidence. All repository Python
files passed black/isort/ruff and mypy (80 source files). The private notebook code cells
executed successfully and reconciled eligible = labeled + censored; notebook remains ignored.


A follow-up service control fixes the tag API-image smoke: it now checks `/ready` and the
verified-model response contract instead of accepting `/health` 200. The probe binds only
loopback, has a bounded timeout and removes only its temporary container. Synthetic positive
and negative command fixtures check that liveness-only HTTP 200 fails; these are software
contracts, not a real model/image release. The API image job still requires a tag and remains
skipped on the PR. Actual serving/load/rollback and bundle admission remain open.

## 9 Oktober 2026 — persiapan admission dan batas request

Ditemukan metadata resmi Release 47 (29 Juli 2026, performance cutoff 31 Maret 2026).
Kesesuaian layout/periode lokal belum mengonfirmasi hubungan byte dengan release atau
review ketentuan pemilik. Proposal bounded research, kapasitas alert dan gate numerik
tersimpan dalam config/research/freddie_experiment_v1.json; belum ada persetujuan/fit.

CLI admission JSON memeriksa hash sumber/protokol, recorded owner review, scope retrospektif
dan deklarasi test tertutup. CLI hanya hash ZIP; tidak membaca member test, membuat label
validation, mengaktifkan API atau menyatakan kualitas model. Manifest dan laporan aktual
disimpan privat. Actual preflight keluar 2/BLOCKED karena review pemilik belum lengkap.

API menolak raw input/ctx pada error response, nilai non-finite/bool/string numerik,
extra features, envelope tidak dikenal dan jumlah fitur/ID berlebihan. CORS default
tertutup dengan origin eksplisit tervalidasi. Batas field ini bukan batas byte payload,
autentikasi atau rate limit; kontrol layanan lengkap dan adapter hipotek tetap terbuka.

Validasi lokal: seluruh suite src/ tests/ 202 passed, 4 skipped, 9 warnings, 23.62 detik;
black/isort/ruff lulus pada seluruh source/tests/scripts, strict mypy lulus 82 source files.
17 admission dan 14 input-control checks baru menggunakan fixture sintetis, termasuk
arsip opaque yang tidak bisa dibuka sebagai ZIP, JSON ambigu, hash berubah, unsupported
scope, CORS tak diizinkan dan numeric overflow response 422. Warning dependency/loky
dan integration skips tidak membuktikan produksi. Tidak ada evaluasi model real,
training Freddie, pembukaan test, deployment, merge atau penghapusan data.

The owner subsequently approved the exact experiment protocol hash and retrospective scope
on 9 October. Private review records reflect that approval, while source release binding and
terms remain unconfirmed. A fresh advisory preflight reports exactly those two blockers.
Configuration bytes and frozen-test contents remain unchanged; no fit/evaluation was started.
