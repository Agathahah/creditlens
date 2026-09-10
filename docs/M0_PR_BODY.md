Lending Club ingestion stopped after the first 16 CSV chunks because a 51-character source status exceeded the raw column's VARCHAR(50) limit. Separately, the warehouse tests could pass with empty or stale loan marts. This change preserves full status strings, makes ingestion resumable, and adds checks for required nonempty relations and matching row counts.

The loader parses dates by column and writes batches. `--insert-missing` skips existing loan IDs and uses `ON CONFLICT DO NOTHING`; the default upsert updates only changed outcome fields. The migration changes loan_status to TEXT, recreates the known staging view transactionally, and refuses unsafe narrowing or unexpected view metadata/dependencies. ORM and initialization SQL use the same type.

Validation:

- Local application suite: 124 passed, 4 skipped, 7 warnings. Live Feast tests were disabled; optional dependency cases are reported separately. This is software testing with fixtures, not full real-data training.
- Black/isort/Ruff passed on src, tests and scripts; mypy passed on src.
- Private PostgreSQL ingestion fixture: 8 checks passed, covering rollback, migration/view preservation, dependency protection, resume/no-op and downgrade guards.
- dbt reproduction demonstrated that the 24 previous tests could pass on empty data; the added tests detect empty/stale relations.
- Scoped backup was restored in a private cluster before local recovery. Owner/ACL recovery is outside that drill.
- Local recovery inserted 660,686 missing records. Raw, staging and both loan marts now each contain 2,260,668 records; source/raw ID differences are zero. Two dbt models and 9 tests passed after rebuilding. Existing rows retained their count and aggregate fingerprint.
- Agatha independently ran `SELECT COUNT(*) FROM mart.final_features;` and confirmed 2260668.

The PostgreSQL/dbt recovery checks above are local evidence, not jobs newly added to GitHub Actions. Pushing this PR does not migrate or populate another database. Data files, credentials and backup archives are not included.

M0 remains open for data provenance/as-of and label/feature-availability decisions. This PR does not validate model quality or production readiness, change the ML label contract, deploy a service, or rewrite Git history. Local reproduction scripts currently target the verified macOS PostgreSQL installation; cross-platform automation is later work.

Implementation, tests and documentation were prepared with Codex assistance. Agatha defined the scope, resolved disk capacity, verified the database result, and is performing the Git publication steps; actual publication status is established by the commits and PR. Detailed decisions, evidence and contribution boundaries are in PROJECT_STATUS.md, LEARNING_LOG.md and docs/WORKLOG.md.
