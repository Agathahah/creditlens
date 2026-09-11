# CreditLens — product requirements

v0.2 · Public-data demonstration · M0 active. Detailed model and release contracts remain draft.

## Purpose and intended use

Provide a reproducible pipeline that turns public loan records into historical risk estimates and explanations, with traceable data, evaluation and operational evidence. Initial use is retrospective analysis and a single-record scoring demonstration. There is no verified production lender, live credit decision or measured business impact.

Outputs must not be presented as real credit approval, rejection, pricing or limits. The existing API approved field requires a scoped simulation contract before release.

## Product scope

- Versioned source manifest and PostgreSQL/dbt lineage with explicit grain, exclusions, labels and feature availability.
- Constant baseline, Logistic Regression and a measured XGBoost candidate on the same eligible cohort.
- Train-only preprocessing and one versioned preprocessing/model/schema bundle shared by evaluation and API.
- Score/explain endpoints with model version and separate liveness/readiness.
- Temporal evaluation with validation-only model/threshold selection, calibration and error analysis.
- CI/release evidence binding source, data, bundle and image versions, plus smoke/rollback checks.
- Monitoring for request volume, errors, latency, feature/prediction distributions and delayed outcomes.

Start locally, then validate in an isolated staging environment before an approved deployment with explicit load, exposure and cost limits. Platform and numeric SLOs are not yet finalized.

## Data and target constraints

Use accepted Lending Club records after provenance and usage rights are established. Rejected applications are not observed negative/default labels. Accepted-only data produces selection bias.

The proposed target is observed Fully Paid versus Charged Off/Default; current, late/grace and out-of-policy statuses remain separate. This is not yet the implemented label contract. Without defensible event/as-of data, do not claim a fixed-horizon probability of default or a prospective backtest.

Grade, sub_grade, int_rate, installment and verification_status require explicit availability at the intended scoring stage. FRED is excluded from the proposed baseline until publication/vintage timing is supported. SEC has no valid implemented borrower join.

## Acceptance criteria

| ID | Requirement | Required evidence |
|---|---|---|
| AC01 | Traceable source and valid cohort | Provenance, checksum, label/availability decisions, exclusions and nonempty/reconciliation checks |
| AC02 | Evaluation isolation | Train-only fit tests, temporal split manifest, overlap/maturity checks and frozen test protocol |
| AC03 | Defensible model comparison | Same cohort, baseline, denominator/prevalence, uncertainty, calibration and error analysis |
| AC04 | Training-serving parity | Same raw record produces batch/reload/HTTP probabilities within a declared tolerance; unseen/null/invalid inputs tested |
| AC05 | Honest readiness | Missing/corrupt/incompatible bundle yields 503; valid loaded bundle yields ready |
| AC06 | Auditable release and rollback | Source/data/model/image versions tied to gates; smoke and rollback evidence |
| AC07 | Operational monitoring | Versioned inference events, traffic/error/latency metrics and delayed-label linkage |
| AC08 | Explicit resource envelope | Measured latency, throughput and peak memory on a named environment and workload |
| AC09 | Reproducibility | Documented setup, migrations, data/model manifests and verification commands |
| AC10 | Recoverability | Tested scoped restore and release rollback with documented limitations |

The historical PR-AUC 0.25 and latency <100ms settings are candidate requirements, not established quality results. Final gates require an approved protocol before candidate/test evaluation.

## Exclusions

Real lending decisions, claims of regulatory compliance or comprehensive demographic fairness, high availability, automatic retraining/promotion, production survival/counterfactual services, SEC borrower enrichment and Ops Copilot are outside the current release scope. Ops Copilot requires a separate design after the core is stable.

Full training, deployment and changes to published history require explicit authorization outside this document.
