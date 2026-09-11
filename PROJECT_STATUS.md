# CreditLens project status

Updated 2026-09-11. M0 data recovery is implemented; the data/evaluation contract is not yet closed.

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
| Recovery validation | 7 parsing tests; 8 private PostgreSQL checks; two dbt models built and 9 selected tests passed |
| Backup | Scoped raw/view/mart archive restored on a private server; owner/ACL recovery outside the drill |
| Local resources | 3.747 GiB free after the recorded rebuild; not a full-training capacity benchmark |

## Pull request and CI

[PR #14](https://github.com/Agathahah/creditlens/pull/14) is open and draft. At verification its head was 745dd28c2bd5cfe6e5b13d288bbc0d3b76d6de9d. [Run 34506955747](https://github.com/Agathahah/creditlens/actions/runs/34506955747) passed lint/typecheck and application tests; model evaluation and Docker build were skipped under the workflow conditions.

The earlier detailed run on 7a859fe reported 124 passed, 4 skipped, 8 warnings. Reported total coverage was 91% including test files under src; the ingestion module was 54%. Private PostgreSQL migration/transaction checks are local evidence and are not yet CI jobs. See [CI evidence](docs/audit/M0_PR14_CI_REPORT.json).

## Outstanding work

| Priority | Required work |
|---|---|
| P0 | Establish source/license/as-of, target definition, cohort eligibility and feature availability |
| P0 | Split before fitting preprocessing; persist transforms and freeze validation/test protocol |
| P0 | Align training, evaluation and serving through one versioned bundle/schema |
| P1 | Fail readiness when the model bundle is missing, corrupt or incompatible |
| P1 | Supply explicit model/data inputs to evaluation gates and bind them to release artifacts |
| P1 | Verify parity, load limits, deployment smoke tests and rollback |
| P1 | Monitor actual inference events and delayed labels rather than historical issue-date volume |

The legacy label still maps Late (31–120 days) to one. The proposed outcome contract remains a draft. All member_id values are missing; label availability and borrower overlap cannot be established from that column.

M1–M5, full training, deployment and history rewriting are not authorized by this status document. PR success does not establish model validity or production readiness. See [milestones](docs/MILESTONES_ADR.md), [target draft](docs/M0_LABEL_DECISION_DRAFT.md) and [technical worklog](docs/WORKLOG.md).
