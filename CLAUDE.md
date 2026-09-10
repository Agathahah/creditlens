# CreditLens — Project Memory

> Transisi mentoring, 2026-09-08: aturan aktif lintas-agent ada di
> [AGENTS.md](AGENTS.md), persetujuan dan checkpoint ada di
> [PROJECT_STATUS.md](PROJECT_STATUS.md). Arah v0.2 dan M0 telah disetujui;
> training penuh, deployment dan rewrite riwayat belum disetujui.
> Konteks di bawah dipertahankan sebagai catatan historis. Klaim production-grade
> dan daftar komponen tidak membuktikan runtime sudah siap. Aturan session/model
> routing khusus Claude di bawah digantikan workflow mentoring AGENTS.md.
> Commit baru memakai identitas manusia yang dikonfirmasi, tanpa author/co-author
> AI otomatis; bantuan AI tetap dicatat jujur di [LEARNING_LOG.md](LEARNING_LOG.md).

## Overview
Production-grade explainable credit scoring engine untuk fintech lending.
Membantu lender menilai risiko kredit dengan transparansi penuh — setiap
keputusan bisa dijelaskan kepada applicant dan regulator.

## Data Sources (SQL-First)
- Lending Club: 2.9M loan records, 150+ kolom (Kaggle)
- SEC EDGAR: Financial statements perusahaan publik AS (sec.gov)
- FRED: Macro indicators — fed funds rate, unemployment, CPI, GDP (API)

## Architecture
- Data Warehouse: PostgreSQL 16 (raw → staging → mart layers)
- SQL Transformations: dbt (data build tool)
- Feature Store: Feast (online: Redis, offline: PostgreSQL)
- ML Models: XGBoost (primary), LightGBM (comparison), Logistic Regression (baseline)
- Explainability: SHAP (global + local) + Counterfactual (DiCE)
- Fairness: AIF360 — disparate impact, equal opportunity, demographic parity
- Survival Analysis: DeepSurv/Cox — prediksi KAPAN default terjadi
- API: FastAPI + Pydantic validation
- Orchestration: Apache Airflow (ETL scheduling)
- Monitoring: Evidently AI (drift) + MLflow (experiments) + Grafana (dashboards)
- CI/CD: GitHub Actions (lint → test → eval gate → build → deploy)
- Containerization: Docker + Docker Compose

## Coding Rules
- Python 3.11+, type hints WAJIB di semua fungsi publik
- Google Style docstrings
- Setiap modul WAJIB punya unit test minimal 85% coverage
- Atomic commits: [type] description (feat, fix, refactor, test, docs, chore, infra)
- Satu fitur = satu branch = satu PR = satu session Claude Code baru
- Pre-commit hooks: black, isort, ruff, mypy
- SQL: semua query harus documented di dbt schema.yml
- No bare except — selalu specify exception type
- Max function length: 30 baris (single responsibility)

## Perintah Penting
- Setup: `make setup` (install deps + pre-commit + docker-compose up)
- Load data: `make load-data` (download + load ke PostgreSQL)
- dbt run: `make dbt-run` (run all dbt models + tests)
- Test semua: `make test` (pytest src/ tests/ -v --cov)
- Test satu modul: `pytest src/ml/tests/ -v`
- Run API: `make run-api` (uvicorn src.api.main:app --reload)
- Evaluation: `make eval` (python src/ml/evaluate.py)
- Lint: `make lint` (black + isort + ruff + mypy)
- Docker: `make docker-up` / `make docker-down`

## Database Schema Overview
- raw.lc_loans — Lending Club raw data (2.9M rows)
- raw.sec_financials — SEC EDGAR financial statements
- raw.fred_indicators — FRED macro indicators
- staging.lc_loans_clean — cleaned, deduplicated, type-casted
- staging.fred_* — cleaned macro data
- mart.loan_features — SQL-engineered features (window functions, CTEs)
- mart.macro_features — macro context features
- mart.final_features — joined feature table untuk ML

## Key Metrics
- Primary: PR-AUC (dataset imbalanced, ~15% default rate)
- Secondary: AUC-ROC, Recall@Precision80, KS Statistic
- Fairness: Disparate Impact Ratio (target: 0.8-1.25)
- Latency: <100ms per prediction (API)

## Model Routing (Claude Code)
- Sonnet 5: daily coding, tests, docs (80% tasks)
- Opus 4.8: architecture decisions, complex debugging (15%)
- Fable 5: database schema, SQL engineering, hardest problems (5%)

## ADR (Architecture Decision Records)
- ADR-001: PostgreSQL sebagai data warehouse (bukan BigQuery) — full control, free
- ADR-002: dbt untuk SQL transformations — testing, documentation, lineage
- ADR-003: Temporal split bukan random split — prevent data leakage
- ADR-004: PR-AUC sebagai primary metric — imbalanced dataset
- ADR-005: XGBoost sebagai primary model — proven, explainable, fast inference
- ADR-006: Feast untuk feature store — online/offline serving
- ADR-007: SHAP + Counterfactual untuk explainability — regulatory requirement
