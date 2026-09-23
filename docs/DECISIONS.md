# Technical decisions

Updated 2026-09-23. Implemented decisions are distinguished from proposed contracts.

| Decision | Status | Rationale / consequence |
|---|---|---|
| PostgreSQL raw → staging → mart | Existing architecture | Preserve source lineage and explicit SQL transformations |
| Required nonempty + row reconciliation dbt tests | Implemented M0 | Existing column tests passed on empty data; new tests cover empty/stale relations |
| loan_status TEXT | Implemented M0 | 761 source values exceeded VARCHAR(50); keep source text intact |
| Transactional staging view recreation | Implemented M0 | PostgreSQL prevents type changes while the view depends on the column; RESTRICT and metadata guards prevent silent loss |
| Bulk insertion and insert-missing mode | Implemented M0 | Resume partial ingestion while preserving existing rows and reporting exclusions |
| Scoped backup and private restore rehearsal | Verified M0 | Demonstrate recoverability before active mutation; owner/ACL restoration remains outside the drill |
| Fully Paid vs Charged Off/Default | Disetujui; SQL lokal dan tes terisolasi selesai | Label 0=Fully Paid, 1=Charged Off/Default, lainnya NULL; klaim retrospektif. Database aktif belum direbuild; maturity/as-of tetap terbuka |
| No macro/SEC baseline enrichment initially | Proposed | FRED vintage timing and SEC borrower linkage are not established |
| Train-only preprocessing + versioned bundle | Proposed M1/M2 | Prevent distribution leakage and training-serving mismatch |
| Validation for selection/calibration/threshold, frozen test | Proposed M1 | Prevent test-set tuning; temporal availability must be explicit |
| Next independent M1 holdout | Direction approved; source intake pending | Educational/portfolio demo; prediction at application before pricing; 36-month outcome for 36-month loans; use one new auditable snapshot and keep its frozen test closed until the protocol is locked |
| Decision threshold | Deferred for credit decisions | Report probabilities and validation operating curves for the demo; require minimum support and an approved FP/FN cost objective before any approve/reject policy |
| Separate readiness from liveness | Proposed M2 | Process health must not imply scoring availability |
| Gate-bound artifacts and rollback | Proposed M3 | Deploy the evaluated bundle/image combination and retain recovery evidence |
| Inference events + delayed labels | Proposed M4 | Monitor real request behavior and delayed outcome quality |

Next decisions: admit a new dataset/snapshot, derive concrete mature split years, lock calibration and
model gates, then decide whether evidence supports an M2 bundle proposal. Feature availability,
resource envelope and deployment exposure remain open. Full training and deployment remain separate
authorizations.
