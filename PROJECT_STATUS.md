# CreditLens project status

Updated 2026-09-23. M0 data recovery is implemented and the approved bounded M1 local
experiment has completed. The candidate failed release gates. The next holdout direction is approved,
but a new auditable dataset/snapshot has not been admitted; the project is not production ready.

## Verified implementation

| Area | Evidence / status |
|---|---|
| Ingestion source | 2,260,701 CSV records; 2,260,668 ingestion candidates and 33 missing required fields |
| Root mechanism | Existing raw IDs matched the first 16 CSV chunks; 761 source statuses exceeded VARCHAR(50). The historical failure log supports the mechanism but does not uniquely identify the last database load |
| Schema | Revision 4b7d2a91c608 changes loan_status to TEXT and transactionally recreates the known staging view; unexpected metadata/dependencies fail safely |
| Resume | 660,686 inserted, 1,599,982 skipped, 33 excluded; 14 committed batches |
| Existing data | Count and aggregate row fingerprint unchanged, including loaded_at |
| ID reconciliation | Zero source IDs missing from raw and zero raw IDs outside source candidates |
| Raw / staging / loan / final | Each contains 2,260,668 rows; raw issue dates June 2007–December 2018 |
| Retrospective label rollout | Active staging and two loan marts rebuilt on 22 September 2026; 3 models/12 tests passed, row and ID counts preserved, non-label SHA-256 streams matched baseline |
| Dataset artifact identity | Local gzip SHA-256, byte size, 151 columns and 2,260,701 rows match an independently published research artifact; the local download path, upstream rights and outcome snapshot date remain open |
| M0 feature profile | 1,345,350 labeled candidates inspected read-only; 376 missing source DTI values and 361 nonpositive annual incomes are hidden by current zero-valued derivations; eligibility and availability remain open |
| M1 local cohort/split | Approved and implemented for accepted 36-month loans issued 2011–2015. Eligible rows: train 2011–2013 = 157,993; validation 2014 = 162,570; frozen test 2015 = 283,024. Exclusions: 147 unresolved outcomes and 2 invalid incomes. The 2015 test is now consumed |
| M1 local evaluation | Constant, Logistic Regression and one bounded XGBoost candidate used train-only preprocessing. XGBoost validation AP was 0.2046 and frozen-test AP was 0.2197 (row-bootstrap 95% interval 0.2164–0.2221), below the historical 0.25 gate. The locked threshold predicted no test positives, so the operating point also failed |
| Next holdout decision | Approved for an educational/portfolio demo: application-time prediction before pricing, 36-month outcome for 36-month loans, and one new auditable dataset/snapshot. Concrete years remain unset until maturity and outcome timing pass intake; no new training has started |
| Docker packaging smoke | Allowlist `.dockerignore` reduced context to 221.13 kB; arm64 image built, `/health` reported no model, `/predict` returned 503; temporary image/container/cache cleaned |
| Recovery validation | 7 parsing tests; 8 private PostgreSQL checks; two dbt models built and 9 selected tests passed |
| Backup | Scoped raw/view/mart archive restored on a private server; owner/ACL recovery outside the drill |
| Local resources | About 14 GiB free after temporary Docker build cleanup on 22 September; not a full-training capacity benchmark |

## Pull request and CI

[PR #14](https://github.com/Agathahah/creditlens/pull/14) is open and draft. At verification its head was 0acd49a9aefc22c4facd73b78a00d5b329d36a33, matching the local checkout, and GitHub reported MERGEABLE. [Run 34556669746](https://github.com/Agathahah/creditlens/actions/runs/34556669746) passed lint/typecheck and application tests; model evaluation and Docker build were skipped under the workflow conditions. MERGEABLE indicates no merge conflict, not release acceptance. See [M0 review](docs/audit/M0_PR14_REVIEW.md) for the unresolved main-branch evaluation dependency and M0 exit criteria.

The earlier detailed run on 7a859fe reported 124 passed, 4 skipped, 8 warnings. Reported total coverage was 91% including test files under src; the ingestion module was 54%. Private PostgreSQL migration/transaction checks are local evidence and are not yet CI jobs. See [CI evidence](docs/audit/M0_PR14_CI_REPORT.json).

## Outstanding work

| Priority | Required work |
|---|---|
| P0 | Decide data usage rights and outcome as-of; then establish cohort eligibility and feature availability. Artifact identity is corroborated, but local acquisition path is not recorded |
| P0 | Obtain and admit a new dataset/snapshot with verifiable rights, outcome as-of and event timing; the approved 36-month protocol cannot assign concrete split years before this audit |
| P0 | Redesign threshold selection with minimum support and an approved false-positive/false-negative objective; the initial precision-80% rule was degenerate |
| P0 | Align training, evaluation and serving through one versioned bundle/schema |
| P1 | Fail readiness when the model bundle is missing, corrupt or incompatible |
| P1 | Supply explicit model/data inputs to evaluation gates and bind them to release artifacts |
| P1 | Verify parity, load limits, deployment smoke tests and rollback |
| P1 | Monitor actual inference events and delayed labels rather than historical issue-date volume |

Kontrak label retrospektif sudah diterapkan pada database aktif: Fully Paid=0, Charged Off/Default=1, status lain=NULL. Pada masing-masing staging dan dua mart pinjaman, label 0=1.076.751, label 1=268.599, NULL=915.318; 21.467 record Late (31–120 days) kini NULL. Bukti: [laporan penerapan aktif](docs/audit/M0_LABEL_ACTIVE_ROLLOUT_REPORT.json). Asal/as-of, kelayakan cohort dan fitur tetap terbuka. Seluruh member_id kosong sehingga pemisahan peminjam tidak dapat dijamin dari kolom tersebut.

Identitas byte dataset kini cocok dengan [artefak riset yang dipublikasikan](docs/audit/M0_DATA_SOURCE_RESEARCH_2026-09-22.json). Kaggle merupakan kandidat distribusi yang kuat, tetapi jalur unduh lokal, hak penggunaan data asal dan waktu snapshot outcome belum terverifikasi. File mentah tetap privat; keputusan penggunaan demo publik masih terbuka.

Bounded M1 local implementation and evaluation were explicitly authorized and executed on 23
September 2026. Full training, M2–M5, deployment, merge, push and history rewriting remain outside
that authorization. PR success and the local experiment do not establish model validity or production
readiness. See [M1 local evidence](docs/audit/M1_LOCAL_EVALUATION_2026-09-23.md),
[milestones](docs/MILESTONES_ADR.md) and [technical worklog](docs/WORKLOG.md).

The next M1 holdout direction was approved on 23 September 2026. It authorizes source intake and
scope preparation, not training on the consumed 2015 test. The active gate is a new private
dataset/snapshot with auditable provenance, rights, as-of and outcome timing. See the
[decision](docs/M1_NEXT_HOLDOUT_DECISION.md) and [next experiment scope](docs/M1_NEXT_EXPERIMENT_SCOPE.md).

Backup label berhasil dipulihkan dan rollback diuji pada PostgreSQL 14.22 terisolasi; lihat [laporan restore](docs/audit/M0_LABEL_RESTORE_REPORT.json). Setelah kapasitas pulih, preflight database aktif mencocokkan backup, source, migrasi, baseline baris/label, input dan metadata. Penerapan 22 September 2026 lulus tiga model/12 tes; jumlah dan ID tetap, SHA-256 atas baris berurutan tanpa label cocok pada ketiga layer, dan raw/macro tidak berubah menurut sidik agregat. Rollback aktif tidak diperlukan. Pemeriksaan awal yang tertahan kapasitas tetap dicatat sebagai [bukti historis](docs/audit/M0_LABEL_2026-09-22_BLOCKER.json); hasil akhir ada pada [laporan penerapan](docs/audit/M0_LABEL_ACTIVE_ROLLOUT_REPORT.json). Ini belum memvalidasi cohort/as-of, training, CI atau kesiapan produksi.
