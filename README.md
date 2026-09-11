# CreditLens

CreditLens is a public-data credit-risk project covering PostgreSQL/dbt transformations, model evaluation, explainability, and a scoring API.

## Current status

M0 data recovery is implemented locally: raw, staging, and both loan marts each contain 2,260,668 records. Ingestion preserves full source statuses and can resume missing records without overwriting existing rows. Scoped backup/restore and targeted dbt checks passed.

Production readiness has not been demonstrated. Label/feature-availability contracts, leakage-free evaluation, a versioned preprocessing/model bundle, API readiness, release gates, and operational monitoring remain open. Outputs are not intended for real lending decisions.

- [Project status](PROJECT_STATUS.md)
- [Technical documentation](docs/README.md)
- [Data design](docs/DATA_DESIGN.md)
- [Evaluation and release plan](docs/EVALUATION_RELEASE_PLAN.md)
- [Engineering rules](AGENTS.md)

Development has used AI assistance, including Claude and Codex. Technical claims are tied to source, tests, and recorded validation.
