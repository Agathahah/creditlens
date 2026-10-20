# CreditLens project status

Updated 2026-10-20. M0 recovery and bounded LendingClub M1 are complete; the historical
LendingClub model remains rejected. Separate Freddie v4 past-history research has passed
both development validation and its one-shot independent vintage2022 test. Vintage2020/2022
are consumed. A private loopback feature-scoring API and real offline/reload/HTTP parity
smoke are implemented and verified. Fintech production scoring remains HOLD: source
availability, operating usage and full service acceptance are not established.

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


## Current — v4 research accepted, private HTTP path verified

The v4 protocol was locked before new 2021 outcomes or fit. It retains train2018, adds
nine exact past-history candidates and uses disjoint loan partitions of vintage2021
for 2023 calibration and 2024 validation. The same fixed calibrated HGB candidate then
passed all unchanged research criteria on the new vintage2022 2025 window, tested once.
Metadata, layout/keys/cutoff/source hashes reconcile; publisher attestation and operational
point-in-time validity remain absent. Vintage2021 is development and vintage2022 is now
consumed, including unused windows. Neither is a fresh holdout for model revision.

A private research bundle binds candidate, protocol, validation/test evidence, schema and
runtime. The separate API binds only loopback with owner-file bearer credentials, byte/rate
limits, invalid-input handling and explicit research versus production status. A real local
HTTP smoke with synthetic domain features matched the offline/reloaded score, exercised
401/422/413 failures and stopped its temporary server. Feature-only parity is not a verified
raw monthly-record/online-history adapter. No public model/data/API deployment occurred.

[The v4 contract and evidence](docs/FREDDIE_V4_HISTORY_PROTOCOL.md) records the exact scope,
limitations and remaining operational gates. Numerical mortgage outputs, weights, tokens,
notebooks and owner learning instructions stay private.

## 2026-10-20 — private HTTPS and pilot admission boundary

Source access remains private Freddie retrospective samples; an authorized operational
servicing source and authentic availability/correction feed are absent. The operational
pilot is NOT_ADMITTED. The [pilot contract](docs/PRIVATE_MORTGAGE_PILOT_CONTRACT.md) records
the business workflow, required provider/operator evidence and fixed admission sequence.
No source acceptance, fitting or independent-test decision is repeated.

The loopback API now optionally accepts a complete bounded owner-only TLS certificate/key
pair, validated before model loading. The monthly client enables HTTPS only with an explicit
private trust anchor, normal chain/IP checks and no redirect following or insecure fallback.
Actual accepted-model native and isolated Docker HTTPS agree with the existing candidate;
TLS1.3was negotiated. Wrong CA/hostname and plaintext were rejected. Restarting with fresh
test-only credentials rejects the retired token401and permits a new persisted score while
preserving earlier journal rows. Original credentials and model artifacts are unchanged.

The self-signed local certificate and restart-based rotation are bounded engineering
acceptance, not public TLS, enterprise identity, zero-downtime rotation or production admission.
Private keys/tokens/receipts stay outside Git. See
[the transport contract](docs/PRIVATE_RESEARCH_TRANSPORT_ACCEPTANCE.md).

## 2026-10-20 — persistent Docker journal and backup recovery

A separate local drill preserved the original synthetic monitoring journal and HMAC key,
then verified accepted-model scoring against a writable owner-only journal bind mount.
Removing and recreating the test container preserved all earlier rows. A temporarily missing
test-copy journal produced503without a successful score; returning it restored committed
writes. A chmod-only preliminary fault did not block writes on this Docker Desktop bind
mount and is retained as failed evidence, not a passed storage-security test.

SQLite online backup, integrity/schema/foreign-key checks, key identity and logical table
fingerprints admit only verified snapshots. Restore requires a fresh private directory;
corrupt copies and existing targets are rejected. Same-image scoring after restoration
matched the unchanged candidate and persisted new request IDs. The post-backup request was
explicitly excluded from recovery, accounting for the backup point rather than claiming
zero data loss. Temporary owned containers were removed; original artifacts are unchanged.

This same-host, network-none synthetic drill does not establish off-host recovery, retention,
public ingress, authentic operational outcomes or production acceptance. See
[the journal recovery contract](docs/FREDDIE_JOURNAL_RECOVERY.md).

## 2026-10-20 — private inference journal and synthetic delayed outcomes

Feature and monthly client execution succeeded. The research API now
returns server-generated request IDs and optionally commits a bounded private SQLite audit
before returning a successful score. The journal records sanitized request metadata, model
identity and successful probability; credentials, raw features and loan identifiers are excluded.
Audit failure returns503. Separate HMAC context linking deduplicates exact model/loan/month
retries while retaining every traffic event.

Synthetic-only follow-up intake reuses the locked three-month label, explicit availability
cutoffs and censoring rules. Resolved evidence must become available after actual scoring;
conflicts fail closed, replay is idempotent and censored revisions are retained. Reports
separate pending/censored/resolved observations by model. Actual accepted-model HTTP requests
and toy future-outcome integration passed locally; these diagnostics establish monitoring
plumbing, not prospective credit quality, source rights or production release.

No source archive, fit, independent retest or threshold change occurred. The main LendingClub
model remains rejected; the private mortgage candidate remains unchanged and accepted only
for retrospective research. See [the monitoring contract](docs/FREDDIE_INFERENCE_MONITORING.md).

## 2026-10-19 — isolated research API packaging and recovery

A separate pinned research image now loads no model/credential at build time. A private
runtime package relocates only manifest paths and retains accepted artifact hashes.
The image was exercised locally with non-root, read-only root/mounts, network-none, no
published ports and bounded CPU/RAM/PIDs. Synthetic monthly-feature/native/container HTTP
scores agree exactly;401/422/413negative cases pass. A deliberately corrupt candidate
checksum prevents startup, followed by successful restart on the known image+good bundle.
Only test-owned containers were removed; original evidence and the local image remain.

A small sequential/concurrency2diagnostic completed without request failures. It measures
in-namespace HTTP and process RSS, not public ingress, lender SLOs or live credit quality.
The new CI image job contains only public software/config and checks pinned versions,
non-root/no-private-artifact content and refusal of missing bundles. Real accepted-model
verification remains private and separate from that CI job. No test archive was reopened.
See [the acceptance contract](docs/FREDDIE_CONTAINER_ACCEPTANCE.md).

## 2026-10-16 — monthly adapter and authenticated client integration

A bounded single-loan monthly adapter now reconstructs locked v4 features from normalized
records, selecting the latest supplied correction available by prediction time. Future
records and late corrections cannot affect features; missing calendar/status remains
explicit. The authenticated client sends only features to literal loopback and rejects
redirects, failed readiness and inconsistent model/scope/output. Private owner-only inputs
and tokens remain outside Git.

Synthetic float32 features match the existing batch training collector. The accepted-model
reload score and actual HTTP score from a synthetic monthly snapshot match exactly on the
owner's local server. Supplied timestamp checks do not attest real source availability;
authentic history/correction evidence, history storage and operating acceptance remain open.
There was no training, test-source access, production promotion or public model publication.
See [the adapter contract](docs/FREDDIE_MONTHLY_ADAPTER_CONTRACT.md).

## Earlier 2026-10-13 — v3 calibration and independent test completed

The v3 protocol was locked before new development-window statistics or fit. Train vintage2018
was expanded across pre-crisis/crisis periods; calibration and validation vintage2019 are
separate in calendar and loan identity. HGB plus frozen-base sigmoid passed all validation
criteria. A separate checksum-bound test contract was then locked and executed once on
vintage2020 at a later calendar window, with no fitting or threshold/model changes.

Independent test passed ranking, uncertainty, support and both Brier-baseline criteria but
failed fixed top1% capacity recall: **REJECT_TEST**. The consumption ledger was created before
first ZIP-member access; all vintage2020 is now consumed, including unused calendar windows.
Current private manifests record consumption and preserve their previous bytes as evidence.
This supersedes the earlier sealed-test statements below. No retraining/retesting on this
source, bundle promotion, API scoring activation or production acceptance occurred.

The public research page reports completed validation/test and the specific failure without
loading private numerical outputs. [V3 design and results](docs/FREDDIE_V3_CALIBRATION_PROTOCOL.md)
and [next research/service sequence](docs/FREDDIE_NEXT_RESEARCH_AND_SERVICE.md) describe the
implemented evidence, private-source boundaries and next independent-data requirement.
Local software suite: 237 passed, 4 skipped; black/isort/ruff and mypy pass. CI/public dashboard
revision checks remain separate. Numeric results, models, manifests and notebook11 stay private.

## Earlier 2026-10-13 — development history audit

A bounded past-history candidate audit is implemented and exercised on admitted development
2018/2019 only. Its eligible observation counts reconcile with the v3 development cohorts;
no future labels, fitting, test archive access or candidate promotion occurs. Calendar gaps
and unknown statuses remain explicit. Quantiles are approximate bounded-reservoir summaries;
counts and moments use the full eligible development observations. Numeric profiles remain
private. See [the audit contract](docs/FREDDIE_DEVELOPMENT_HISTORY_AUDIT.md).

The remaining owner action is private metadata intake for new samples 2021/2022 and public UI
verification. They are not available locally at this checkpoint. A fresh experiment must lock
availability, features, cohort, calibration, alert policy and independent test before fitting.
The local disk has less than the documented 8-GiB dashboard-build guard; Docker packaging is
verified separately by CI. Source admission already accepted is not requested again.

## Earlier 2026-10-13 — v1/v2 bounded mortgage training

Private/internal mortgage research terms have been accepted. Freddie source admission is
complete for corrected retrospective research with inferred Release 47 binding; publisher
checksums and operational point-in-time validity are not established. This supersedes the
source-pending entries below, which retain their dated historical context.

Real bounded training and development validation completed for v1 and a locked, domain-motivated
v2 adding four origination features. Both validation decisions are **REJECT_VALIDATION**.
V2 improves ranking but still fails probability-quality and fixed alert-capacity recall gates.
Frozen-test vintage 2020 remains unopened; there is no accepted mortgage serving bundle.
The LendingClub historical model remains rejected. Scoring release remains HOLD.

Software includes supervised training, train-only preprocessing, private artifact checksums,
loan-cluster uncertainty and a candidate eligibility checker that recomputes validation gates.
The dashboard research page now reports completed training and failed validation without
loading private data. Numeric mortgage results/models/notebooks stay outside publication.
[Training evidence and limits](docs/FREDDIE_TRAINING_VALIDATION_2026-10-13.md) record methods,
resource measurements, validation and the actual release blockers. Local suite: 219 passed,
4 skipped; CI/public deployment for the new revision require separate evidence.

## 2026-10-09 — admission and request boundary preparation

Private 2019/2020 sample archives are present; 2019 passed structural intake and loan IDs
do not overlap the development 2018 sample. No validation outcome profile or frozen-test
contents were opened in admission preparation. Official Release 47 metadata was found
(29 July 2026, performance cutoff 31 March 2026); local artifact binding and owner terms
review remain unconfirmed. Historical corrected data is not verified point-in-time.

A hash-bound bounded research experiment and an advisory admission CLI are
implemented. The owner approved the exact protocol hash on 9 October; source release/terms
review remains incomplete. The CLI never enables scoring; owner review, protocol approval, real evaluation,
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
