# Delivery milestones and architecture decisions

v0.2 · Updated 2026-09-23. M0 recovery and one bounded M1 experiment are complete; the next M1 holdout direction is approved and awaits source intake.

| Milestone | Deliverables | Exit criteria |
|---|---|---|
| M0 — data integrity and reproducibility | Source manifest, ingestion/mart recovery, nonempty/reconciliation tests, private reproduction and backup/restore evidence | Data coverage accounted for; source/label/availability contract ready for M1 |
| M1 — preprocessing and evaluation | Explicit cohort/splits, feature whitelist, train-only transforms, baselines, validation/calibration protocol | Leakage/maturity tests pass; reproducible comparison; frozen test untouched by tuning |
| M2 — bundle and API | Versioned bundle, schema validation, score/explain integration, readiness and parity | Raw→bundle→reload→HTTP agreement; missing/corrupt bundle fails readiness |
| M3 — CI and release | Artifact-aware gates, reproducible image, environment/load limits, smoke and rollback | Failing gates prevent release; evaluated artifacts match deployed artifacts; rollback demonstrated |
| M4 — monitoring and pilot | Inference events, drift/reference data, delayed-label metrics, SLO/runbook | Metrics reflect real requests; versioned joins and response procedures verified |
| M5 — release acceptance | End-to-end acceptance, recovery verification and operating constraints | PRD criteria met for a named version, environment, load and usage scope |

M0 evidence: 2,260,668 rows per required loan layer; source/raw ID differences zero; scoped restore passed. Target mapping is approved and verified in isolation; provenance/as-of and cohort eligibility remain open. The active warehouse has not been rebuilt. Full training and deployment require explicit authorization; finishing a checklist does not itself authorize them.

## Decision register

| ADR | State | Decision / tradeoff |
|---|---|---|
| ADR-008 | Accepted product scope | Public-data educational/portfolio demonstration, local then isolated staging; no real lending decisions |
| ADR-009 | Mapping disetujui; SQL/tes terisolasi selesai | Charged Off/Default vs Fully Paid; status lain NULL. Kelayakan cohort/waktu belum final; database aktif belum direbuild |
| ADR-010 | Train-only pipeline implemented locally; bundle pending M2 | Fit preprocessing on train only and use an immutable versioned bundle for serving parity |
| ADR-011 | Next direction approved; source intake pending | Application-time 36-month target for 36-month loans; validation-only selection and a new frozen temporal test from an auditable snapshot |
| ADR-012 | Proposed | Inline raw-feature serving first; Feast only after key/type/parity validation |
| ADR-013 | Proposed | Separate liveness/readiness; release fails closed on model/schema incompatibility |
| ADR-014 | Proposed | Versioned inference monitoring and delayed-label evaluation; human review of drift |
| ADR-016 | Proposed | Release-owner acceptance supported by automated negative tests and restore/rollback evidence |

Historical ADR-001–007 are summarized in CLAUDE.md; their presence does not establish runtime integration.

## Deferred Ops Copilot

After the core stabilizes, design retrieval over runbooks, release metadata and sanitized operational evidence. Begin with a single bounded read-only tool loop, citations, prompt-injection controls, timeouts and explicit stop conditions. Compare with non-agent retrieval. Measure evidence correctness, task success, unsupported claims, latency and cost before adding complexity.
