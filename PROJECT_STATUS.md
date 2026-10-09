# CreditLens project status

Updated 2026-10-09. M0 data recovery is implemented and the approved bounded M1 local
experiment has completed. The candidate failed release gates. The next holdout direction is approved,
but a new auditable dataset/snapshot has not been admitted; the project is not production ready.

**Current product direction (30 September):** portfolio monitoring after disbursement.
The old application-time M1 experiment and its gate are historical evidence, not an
active-loan alert model. A dated [scope and data contract](docs/PORTFOLIO_MONITORING_SCOPE_2026-09-30.md)
records required periodic snapshots, prospective outcomes, and independent evaluation.
No new source has been admitted for fintech scoring; scoring release remains on hold. The public Streamlit dashboard
is a historical research exhibit, not a live monitoring service.

**5 October follow-up:** The owner reported that, after rebooting Streamlit Cloud, the public
overview shows “CreditLens: dari data pinjaman ke pemantauan portofolio”. This confirms the new
headline was visible to the owner; a fresh independent check of all nine pages and the deployed
revision was not completed. PR #14 remains draft. A separate Freddie Mac mortgage-performance
research track was chosen; [source intake](docs/FREDDIE_MAC_RESEARCH_INTAKE_2026-10-05.md)
documents its monthly panel, terms and boundaries. The Freddie file has passed preliminary structural intake, but has not been admitted for training
or published. The LendingClub M1 model remains rejected and scoring remains blocked.

**7 October follow-up:** Tableau Public was published on 6 October and the owner confirms
it works. [Open the full dashboard](https://public.tableau.com/app/profile/agatha.silalahi/viz/creditlens/CreditLensPortofoliodanBuktiModel).
Year/term filters reconcile the warehouse KPI, trend and outcome heatmap; model validation
uses a separate source. Independent anonymous access and aggregate redistribution rights
are not recorded as complete. See [the updated guide](docs/TABLEAU_PUBLIC_DASHBOARD_GUIDE.md).

A private Freddie 2018 monthly panel and forward three-month label builder are now implemented
and exercised locally. Inputs remain a corrected historical mortgage snapshot, not point-in-time
operator data. Training/source admission and independent evaluation remain pending. The builder
rejects frozen-test vintage 2020; label NULL preserves censoring. Neither source records nor
private derived panels are GitHub deliverables. See [the protocol](docs/FREDDIE_MONTHLY_RESEARCH_PROTOCOL.md).
The Streamlit source adds a research-status page and Tableau link; deployment of this revision
still requires CI and a fresh public check. Scoring remains HOLD; the old test is not reopened.

The 5 October docs-only PR run passed lint and tests but failed while Codecov initialized
an optional coverage upload due to TLS handshake failure; a focused workflow fix was pushed
as `fe2a67f`. Subsequent PR run 37275600387 passed lint, tests, and dashboard Docker smoke;
the model evaluation and API image jobs remained skipped.

The separate Freddie Mac `sample_2018.zip` was downloaded privately and passed ZIP CRC plus
bounded structural inspection: 50,000 unique origination loans, 2,059,564 monthly performance
rows, period 2018-01 through 2026-03, and no basic key/period defects observed. This is a
preliminary source intake, not admission for training or a CreditLens fintech scoring release.
See the [sanitized intake report](docs/audit/FREDDIE_SAMPLE_INTAKE_2026-10-05.md).

## 2026-10-09 — admission and request boundary preparation

Private 2019/2020 sample archives are present; 2019 passed structural intake and loan IDs
do not overlap the development 2018 sample. No validation outcome profile or frozen-test
contents were opened in admission preparation. Official Release 47 metadata was found
(29 July 2026, performance cutoff 31 March 2026); local artifact binding and owner terms
review remain unconfirmed. Historical corrected data is not verified point-in-time.

A hash-bound proposed bounded research experiment and an advisory admission CLI are
implemented. The CLI never enables scoring; owner review, protocol approval, real evaluation,
bundle/parity and service acceptance remain separate. API request/CORS boundaries are
strengthened without admitting a real bundle. See
[release preparation](docs/FREDDIE_RELEASE_PREPARATION_2026-10-09.md).
Training remains blocked, independent evaluation NOT_RUN and scoring HOLD.

The preceding exact head d5bff5a passed lint/tests/dashboard smoke in
[run 37565762222](https://github.com/Agathahah/creditlens/actions/runs/37565762222);
model evaluation/API image were skipped. Validation of the current follow-up is recorded
separately in WORKLOG; no new dashboard public revision or scoring deployment is claimed.

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

[PR #14](https://github.com/Agathahah/creditlens/pull/14) is open and draft. Verification on
29 September 2026 found remote head `61c960c`, matching the main local checkout (ahead/behind 0/0).
[Run 36535113262](https://github.com/Agathahah/creditlens/actions/runs/36535113262) passed
lint/typecheck and application tests: 146 passed, 4 skipped, 7 warnings; reported aggregate coverage
was 89% including test files under src. Model Evaluation Gate and the API Docker job were skipped.
This run preceded dashboard packaging. Run 36538053231 at head 928acc6 subsequently passed
lint, application tests and the separate dashboard Docker smoke job. The new dashboard redesign
prepared below still requires its own commit/push and CI. Neither skipped jobs nor PR success establish model release acceptance.

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


## 2026-09-29 — bounded local release preparation

The request to continue toward production authorizes local readiness protection, a read-only
research dashboard and concrete release criteria. `/live` reports process availability; `/ready`,
`/predict` and `/explain` reject missing/unverified bundles. The legacy loader never marks a bundle
verified. Synthetic test fixtures can exercise the ready path; no real model has been admitted.

A Streamlit dashboard displays only the published, dated M1 research aggregates and failed gates.
It performs no source download, database query, training, prediction or test-set reselection.
Complete bundle validation/parity, independent model evaluation, release CI, deployment and actual
monitoring remain open. The old M1 authorization did not itself cover those steps; the new request
covers the local preparation described here. Hosting target/cost and release acceptance remain
unset. About 4.8 GiB free was observed, so no new Docker build was run.
See [the roadmap](docs/PRODUCTION_READINESS_ROADMAP.md).


## Dashboard packaging and pilot preparation

A dedicated PR job builds only the research dashboard and checks Docker health, HTTP, non-root
runtime, absence of five specified /app paths, and reconciled failure disclosures. Its report
binds the image ID to code revision. The unhealthy-container negative test passed locally; actual
Docker execution subsequently passed in CI run 36538053231 at head 928acc6. The operator also
ran a local smoke on 29 September: healthy container, HTTP 200, non-root runtime and five forbidden
/app paths absent. These results predate the redesign below; they do not cover every image file. Community Cloud dependency discovery is prepared in the UI entrypoint directory.
The aggregate dashboard pilot is publicly reachable at
[creditlens-risk-evidence.streamlit.app](https://creditlens-risk-evidence.streamlit.app/).
Revision `084e524` passed lint, application tests and Dashboard Docker Smoke in
[CI run 36685936180](https://github.com/Agathahah/creditlens/actions/runs/36685936180).
Streamlit Cloud reports the app public and searchable; all nine pages rendered in the live app,
and an anonymous HTTP request completed with 200. This verifies the dashboard pilot, not a
scoring-model/API release. Source admission for new M1 remains MISSING_SOURCE.
See [dashboard pilot runbook](docs/DASHBOARD_RELEASE_RUNBOOK.md).


## 2026-09-29 — dashboard data story redesign

Prepared seven sections covering purpose, warehouse/vintage distributions, engineering lineage,
model selection, API/security contracts, historical packaging and conclusions. Year/term filters
apply only to warehouse charts; M1 metrics/purpose counts retain their separate denominators.
Published aggregates reconcile to 2,260,668 warehouse loans and 603,587 eligible M1 loans.
The aggregate SQL is read-only; it has not been rerun against the active database in this change.

The UI and filter/empty-state contracts pass locally. Historical model failure and consumed test
remain explicit. The dashboard does not probe a live API, load borrower records/models or train.
Public URL verification and CI/build for this redesign were completed on 30 September; see
[data story and evidence](docs/audit/DASHBOARD_DATA_STORY_2026-09-29.md).


## 2026-09-30 — business framing, profile and candidate explanations

The dashboard now states the intended application-time manual-review prioritization use case and
its measurement limits. A descriptive sheet adds prior read-only eligible-cohort percentiles,
vintage aggregates and home-ownership counts; it does not query the active database during render.
The three candidate methods and their validation results are explained separately, with no implied
test result for unselected baselines. A dated release decision keeps the historical candidate
REJECT and scoring API BLOCKED. The source/holdout, bundle/parity and operations gates remain open.
The public demo update was committed as `084e524`, passed the new dashboard CI job and was
URL-verified on 30 September. The historical model remains REJECT for scoring; no source
holdout, model bundle or scoring API deployment was promoted.
