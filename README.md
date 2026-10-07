# CreditLens

CreditLens is a public-data credit-risk project covering PostgreSQL/dbt transformations, model evaluation, explainability, and a scoring API.

## Business problem and intended workflow

As of 30 September 2026, the next product direction is **monitoring funded loans after
disbursement**: understand vintage quality and, when valid periodic data exists, help analysts
prioritize review of active loans. The current dashboard is a historical portfolio analysis;
it does not issue live alerts. See the [dated monitoring scope](docs/PORTFOLIO_MONITORING_SCOPE_2026-09-30.md).

The following application-time experiment remains historical evidence, not a validated model
for monitoring active loans.

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

The earlier next-M1 direction was an educational application-time demo. The updated
monitoring direction needs a periodic loan panel and an independently timed outcome before
new training begins. No new dataset has been admitted.

Production readiness has not been demonstrated. Label/feature-availability contracts, leakage-free evaluation, a versioned preprocessing/model bundle, API readiness, release gates, and operational monitoring remain open. Outputs are not intended for real lending decisions.

- [Project status](PROJECT_STATUS.md)
- [Technical documentation](docs/README.md)
- [Data design](docs/DATA_DESIGN.md)
- [Evaluation and release plan](docs/EVALUATION_RELEASE_PLAN.md)
- [Next holdout decision](docs/M1_NEXT_HOLDOUT_DECISION.md)
- [Next experiment scope](docs/M1_NEXT_EXPERIMENT_SCOPE.md)
- [Local Docker guide](docs/LOCAL_DOCKER_GUIDE.md)
- [Tableau Public aggregate dashboard guide](docs/TABLEAU_PUBLIC_DASHBOARD_GUIDE.md)
- [Engineering rules](AGENTS.md)

Development has used AI assistance, including Claude and Codex. Technical claims are tied to source, tests, and recorded validation.

## CreditLens research dashboard

The dashboard explains the funded-loan portfolio, its outcome gaps, and the historical
model evidence behind a decision to hold scoring.
It presents 2,260,668 warehouse loans, explicit unresolved outcomes, vintage/term filters,
data lineage, historical model evaluation, API rejection contracts and dated Docker evidence.
Ten sections connect the business problem, descriptive dataset and models to the release decision. It reads only published aggregates;
there is no borrower upload, database connection or credit decision.

```bash
python -m streamlit run src/dashboard/app.py --server.address=127.0.0.1
```

Open http://localhost:8501 on the machine running the server. See the
[dashboard evidence and population definitions](docs/audit/DASHBOARD_DATA_STORY_2026-09-29.md),
[read-only aggregate queries](scripts/sql/dashboard_aggregates.sql), and
[packaging/public pilot runbook](docs/DASHBOARD_RELEASE_RUNBOOK.md).
The [public dashboard pilot](https://creditlens-risk-evidence.streamlit.app/) shows the
aggregate research story. Revision `084e524` passed dashboard CI and was checked on the public
URL on 30 September 2026. The model remains below its release gate; the pilot provides no
scoring API or credit decision.

## Monthly mortgage research — separate from fintech scoring

A private streaming builder now creates a Freddie Mac loan-month SQLite panel and a
three-month prospective label, preserving missing follow-up and termination as censoring.
It does not train or publish borrower records. The research dashboard explains implementation
status; independent evaluation and scoring release remain on hold. The corrected source has
not established point-in-time availability. See [protocol and local commands](docs/FREDDIE_MONTHLY_RESEARCH_PROTOCOL.md).

[Tableau portfolio dashboard](https://public.tableau.com/app/profile/agatha.silalahi/viz/creditlens/CreditLensPortofoliodanBuktiModel)
was published on 6 October 2026; the owner confirmed it works on 7 October. This is a
historical aggregate exhibit, not a scoring-model release.
