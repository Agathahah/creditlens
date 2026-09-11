# Technical decisions

Updated 2026-09-11. Implemented decisions are distinguished from proposed contracts.

| Decision | Status | Rationale / consequence |
|---|---|---|
| PostgreSQL raw → staging → mart | Existing architecture | Preserve source lineage and explicit SQL transformations |
| Required nonempty + row reconciliation dbt tests | Implemented M0 | Existing column tests passed on empty data; new tests cover empty/stale relations |
| loan_status TEXT | Implemented M0 | 761 source values exceeded VARCHAR(50); keep source text intact |
| Transactional staging view recreation | Implemented M0 | PostgreSQL prevents type changes while the view depends on the column; RESTRICT and metadata guards prevent silent loss |
| Bulk insertion and insert-missing mode | Implemented M0 | Resume partial ingestion while preserving existing rows and reporting exclusions |
| Scoped backup and private restore rehearsal | Verified M0 | Demonstrate recoverability before active mutation; owner/ACL restoration remains outside the drill |
| Fully Paid vs Charged Off/Default | Proposed | Separate resolved adverse outcomes from current/late states; maturity/as-of still required |
| No macro/SEC baseline enrichment initially | Proposed | FRED vintage timing and SEC borrower linkage are not established |
| Train-only preprocessing + versioned bundle | Proposed M1/M2 | Prevent distribution leakage and training-serving mismatch |
| Validation for selection/calibration/threshold, frozen test | Proposed M1 | Prevent test-set tuning; temporal availability must be explicit |
| Separate readiness from liveness | Proposed M2 | Process health must not imply scoring availability |
| Gate-bound artifacts and rollback | Proposed M3 | Deploy the evaluated bundle/image combination and retain recovery evidence |
| Inference events + delayed labels | Proposed M4 | Monitor real request behavior and delayed outcome quality |

Next decisions: dataset provenance/as-of, target and eligibility, feature whitelist, split protocol, calibration/threshold rules, bundle/API contract, resource envelope and deployment exposure. Detailed target alternatives are in M0_LABEL_DECISION_DRAFT.md. Technical validation supports each milestone; full training and deployment remain separate authorizations.
