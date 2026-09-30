# CreditLens technical documentation

Updated 2026-09-30. Documentation records implemented behavior, decisions, validation evidence and remaining work. The current product direction is portfolio monitoring after disbursement; older application-time plans remain dated historical context.

| Document | Purpose |
|---|---|
| [Project status](../PROJECT_STATUS.md) | Current implementation and unresolved risks |
| [PRD](PRD.md) | Product scope, intended use and acceptance criteria |
| [Data design](DATA_DESIGN.md) | Lineage, grain, features and temporal constraints |
| [Technical design](TECHNICAL_DESIGN.md) | Pipeline, bundle, serving and integration boundaries |
| [Evaluation/release plan](EVALUATION_RELEASE_PLAN.md) | Validation, quality gates and release evidence |
| [Portfolio monitoring scope](PORTFOLIO_MONITORING_SCOPE_2026-09-30.md) | Current use case, required periodic data, evaluation and release blockers |
| [Next holdout decision](M1_NEXT_HOLDOUT_DECISION.md) | Approved prediction horizon, timing, source and holdout direction |
| [Next experiment scope](M1_NEXT_EXPERIMENT_SCOPE.md) | Source intake, temporal split and evaluation gates before new training |
| [M1 source intake](M1_SOURCE_INTAKE_GUIDE.md) | Source screening evidence and bounded file inspection commands |
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

## Local demo and release preparation

- [Production readiness roadmap](PRODUCTION_READINESS_ROADMAP.md): dated research dashboard, fail-closed API probes, and remaining model/release gates.

- [Dashboard packaging and pilot runbook](DASHBOARD_RELEASE_RUNBOOK.md): dedicated Docker smoke, isolated cloud dependencies, public checks and rollback boundaries.

- [Dashboard data story and provenance](audit/DASHBOARD_DATA_STORY_2026-09-29.md): purpose,
  denominator definitions, vintage completeness, historical findings and operational limits.
- [Aggregate SQL](../scripts/sql/dashboard_aggregates.sql): repeatable-read queries for warehouse
  lineage, vintage/term labels and the separate M1 purpose distribution.

- [Tableau Public dashboard guide](TABLEAU_PUBLIC_DASHBOARD_GUIDE.md): public aggregate export,
  dashboard layout, denominators and publication checks.

- [Model release decision](audit/MODEL_RELEASE_DECISION_2026-09-30.md): fintech use case,
  three-candidate validation comparison, rejected historical candidate and required gates.
