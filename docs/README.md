# CreditLens technical documentation

Updated 2026-09-11. Documentation records implemented behavior, decisions, validation evidence and remaining work.

| Document | Purpose |
|---|---|
| [Project status](../PROJECT_STATUS.md) | Current implementation and unresolved risks |
| [PRD](PRD.md) | Product scope, intended use and acceptance criteria |
| [Data design](DATA_DESIGN.md) | Lineage, grain, features and temporal constraints |
| [Technical design](TECHNICAL_DESIGN.md) | Pipeline, bundle, serving and integration boundaries |
| [Evaluation/release plan](EVALUATION_RELEASE_PLAN.md) | Validation, quality gates and release evidence |
| [Milestones/ADRs](MILESTONES_ADR.md) | Delivery sequence and decision status |
| [Decisions](DECISIONS.md) | Adopted and proposed technical choices |
| [Project walkthrough](PROJECT_WALKTHROUGH.md) | End-to-end record flow and implemented gaps |
| [Model decisions](MODEL_DECISIONS.md) | Baselines, candidate rationale and selection protocol |
| [Data provenance](DATA_PROVENANCE.md) | Source checksum, coverage and unresolved source metadata |
| [Target draft](M0_LABEL_DECISION_DRAFT.md) | Outcome mapping, exclusions and limitations |
| [Worklog](WORKLOG.md) | Technical changes and validation results |

## Recovery runbooks and evidence

- [Private reproduction](M0_ISOLATION_PLAN.md), [initial mart recovery](M0_MART_RECOVERY.md), [ingestion recovery](M0_INGESTION_RECOVERY.md).
- [Read-only verification](M0_TERMINAL_CHECK.md).
- [Initial audit findings](audit/AUDIT_FINDINGS.md): historical snapshot; later recovery results supersede the empty-mart state.
- [Ingestion results](audit/M0_INGESTION_RECOVERY_REPORT.json), [post-ingestion dbt results](audit/M0_POST_INGESTION_DBT_REPORT.json), [ID reconciliation](audit/M0_ID_RECONCILIATION.json), [CI results](audit/M0_PR14_CI_REPORT.json).

Raw data, credentials and backup archives are not repository deliverables. Historical reports retain their recorded counts and dates; current status is maintained in PROJECT_STATUS.md.
