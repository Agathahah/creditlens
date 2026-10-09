# End-to-end project flow

Updated 2026-09-11. Counts describe the validated local recovery, not a deployed service.

| Stage | Implemented behavior | Remaining work |
|---|---|---|
| Source → raw | CSV mapping into PostgreSQL; resumable batch loading; 2,260,668 rows | Source license/as-of; explicit training cohort |
| Raw → staging | dbt view filters/deduplicates and derives the legacy label; 2,260,668 rows | Label/availability/null contract |
| Staging → mart | SQL ratios and macro join; both loan marts 2,260,668 rows | Point-in-time feature validity |
| Data checks | Nonempty, uniqueness and count reconciliation; negative fixtures demonstrated | Automate database boundary tests in CI |
| Preprocessing | Existing numeric/category transforms | Fit only on train and persist mapping/order/missingness rules |
| Split/evaluation | Existing temporal train/test intent and metric code | Validation split, maturity/as-of, frozen test, calibration and threshold protocol |
| Model | Logistic Regression, XGBoost, LightGBM implementations | Valid baseline comparison and saved versioned bundle; no measured winner yet |
| API | FastAPI score/explain routes and fixture tests | Bundle integration, raw→HTTP parity and honest readiness |
| Release | GitHub lint/typecheck/application tests | Model/data gate inputs, evaluated image/bundle, smoke/load/rollback |
| Monitoring | Tables and dashboard code | Versioned real inference events and delayed-label performance |

## Record lineage

Public record 68407277 was traced CSV → raw → staging → mart.final_features. Installment 123.03 and annual income 55,000 produce installment_to_income_ratio 0.02684290909 using the current SQL formula. The final mart contains revol_util_clean 0.297 and legacy label 0 for this record. This is a data-lineage check; no real model/API score has been validated for it.

## Validation boundaries

Equal counts alone do not establish correct feature values or labels. A two-record fixture demonstrates software behavior, not predictive quality. Software CI success does not demonstrate point-in-time data, calibrated probabilities or an operational deployment.

See MODEL_DECISIONS.md for candidate selection, DATA_DESIGN.md for feature availability and EVALUATION_RELEASE_PLAN.md for release evidence.
