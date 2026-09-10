# Commit metadata candidates — v0.1

> Status pemasangan 2026-09-08: arah v0.2 dan M0 disetujui. Dokumen ini adalah snapshot audit/rencana atribusi historis, bukan persetujuan rewrite.

Draft; no rewrite executed. Full metadata and all local refs: [GIT_EVIDENCE.json](GIT_EVIDENCE.json).

| Commit | Author/committer AI | Trailer AI | Reachable from main | Subject |
|---|---|---|---|---|
| ef479139d3abc4b7e5ab14ec7935d90f19874d6f | True | True | True | fix(types): use Any in fake __import__ wrapper signature |
| 94e77a4726f8bd2af50992b89997bfcf4acf400b | True | True | True | feat(survival): add Cox PH + DeepSurv survival analysis with survival curve API |
| 8654fd68f9a3b25ce4df2077e23213d4ebde1cac | True | True | True | test(feast): gate live integration tests behind CREDITLENS_RUN_INTEGRATION |
| b0757d5d806f33d32c50f6d6bfbbb2f3ec26b37b | True | True | True | fix(types): drop unused type-ignore in test_store via patch |
| a6dff9ac8c030a7b73e8563d58c5cbf103b5f187 | True | True | True | feat(mlops): MLflow eval logging, Grafana monitoring panels, incremental Feast materialize |
| 4d4c89000a1f46ec1e799d6dc49b8fbd2a54ba5f | True | True | True | fix(types): resolve mypy strict errors in monitoring modules |
| e8d168830fb5792897f1bddc16b09b37b037a550 | True | True | True | feat(monitoring): add Evidently drift, MLflow tracking, and Grafana dashboards |
| 060370371af83e47517b8e1ef06d9fe3d9c02db0 | True | True | True | feat(airflow): add Airflow DAGs for ETL, dbt, feast materialize, retraining, and monitoring |
| 6cf85e45d7b5287289f61dfc9db96d45e68de661 | True | True | True | fix(types): resolve mypy errors from feast extras dependency bump |
| 8fa29dc02b484c83b1eb1d85e77ca04b58d12565 | True | True | True | feat(feast): add Feast feature store with Redis online and PostgreSQL offline |
| 31c2f7c7c6a560d9006832e47772e90e8ae42093 | True | True | True | feat(api): FastAPI endpoints for predict and explain |
| fb2b713656013390abb161498f584b198c95a540 | True | True | True | feat(explainability): add SHAP, counterfactual (DiCE), and fairness audit (AIF360) |
| 67d073df5c2d9f38d48d87ae1bfb4c29700c727d | False | True | True | fix(ingestion): fix SEC EDGAR frames API column mapping and negative dti handling |
| 76d09e6d68129161ff88eea363b14fe4dca218e7 | False | True | True | feat(ingestion): add SEC EDGAR loader and batch insert optimisation |
| 91e96b6e6a4e17248b1e3d39991d278753d89af3 | False | True | True | feat(migration): create raw schema ORM models and initial migration |
| 21a8227456c47d0b68862a401396aef179054b24 | True | False | False | [test] Add unit tests for src.common.config and src.common.database |
| 1eb2c8accabde1eef8708563de7a7fa328338d55 | True | False | False | [fix] Fix pip editable install: drop dangling readme ref, add wheel packages config |
| bb92ac8dcb38c81721eea495336994c64e5affbe | True | False | False | [fix] Install project dependencies before mypy in CI lint job |
| 6afa17deec7e4e437f3f894c7a3b669c5d5fdbe3 | True | False | False | [chore] Add missing scripts/ directory referenced by CI lint job |
| 716be1fd8c3f5952c1bedf011b4abc38e1c6ac4b | True | False | False | [fix] Prevent Alembic env.py from importing a sibling project's src package |
