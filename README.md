# CreditLens

CreditLens is a public-data credit-risk project covering PostgreSQL/dbt transformations, model evaluation, explainability, and a scoring API.

## Business problem and intended workflow

An origination risk team must prioritize a limited amount of human application review. CreditLens
asks whether features known **before pricing or a credit decision** can support a reliable risk
ranking, and whether the data/evaluation/serving evidence is strong enough to release that ranking.
The intended output is decision support for analysts, not automatic loan approval or pricing.

The current accepted-loan dataset cannot establish performance for rejected applicants, a verified
36-month default horizon, or measured profit/loss improvements. This is an auditable research and
engineering case with an explicit release refusal when gates fail. See the
[dated model release decision](docs/audit/MODEL_RELEASE_DECISION_2026-09-30.md).

## Current status

M0 data recovery is implemented locally: raw, staging, and both loan marts each contain 2,260,668 records. Ingestion preserves full source statuses and can resume missing records without overwriting existing rows. Scoped backup/restore and targeted dbt checks passed.

A bounded local M1 experiment implemented a train-only temporal pipeline for accepted 36-month loans. Its frozen-test average precision was 0.2197, below the historical 0.25 gate, and its initial operating threshold failed. The candidate is retained as local research evidence only; the 2015 test is consumed and the model is not served by the API.

The next M1 direction is approved for an educational/portfolio demo: prediction at application time,
a 36-month outcome for 36-month loans, and one new independent holdout from an auditable
dataset/snapshot. Source intake must pass before new training begins.

Production readiness has not been demonstrated. Label/feature-availability contracts, leakage-free evaluation, a versioned preprocessing/model bundle, API readiness, release gates, and operational monitoring remain open. Outputs are not intended for real lending decisions.

- [Project status](PROJECT_STATUS.md)
- [Technical documentation](docs/README.md)
- [Data design](docs/DATA_DESIGN.md)
- [Evaluation and release plan](docs/EVALUATION_RELEASE_PLAN.md)
- [Next holdout decision](docs/M1_NEXT_HOLDOUT_DECISION.md)
- [Next experiment scope](docs/M1_NEXT_EXPERIMENT_SCOPE.md)
- [Local Docker guide](docs/LOCAL_DOCKER_GUIDE.md)
- [Engineering rules](AGENTS.md)

Development has used AI assistance, including Claude and Codex. Technical claims are tied to source, tests, and recorded validation.

## CreditLens research dashboard

The dashboard asks whether the available loan data and model evidence support a scoring release.
It presents 2,260,668 warehouse loans, explicit unresolved outcomes, vintage/term filters,
data lineage, historical model evaluation, API rejection contracts and dated Docker evidence.
Nine sections connect the business problem, descriptive dataset and models to the release decision. It reads only published aggregates;
there is no borrower upload, database connection or credit decision.

```bash
python -m streamlit run src/dashboard/app.py --server.address=127.0.0.1
```

Open http://localhost:8501 on the machine running the server. See the
[dashboard evidence and population definitions](docs/audit/DASHBOARD_DATA_STORY_2026-09-29.md),
[read-only aggregate queries](scripts/sql/dashboard_aggregates.sql), and
[packaging/public pilot runbook](docs/DASHBOARD_RELEASE_RUNBOOK.md).
The model remains below its release gate; a verified public deployment URL is not yet recorded.
