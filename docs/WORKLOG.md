# Technical worklog

## 2026-09-08 — baseline audit

Raw and staging contained 1,599,982 loans while both loan marts were empty. Source review identified preprocessing before split, estimator-only persistence, incomplete model readiness, evaluation gates without artifacts, and monitoring queries not based on inference events. Findings remain in audit/AUDIT_FINDINGS.md; unchanged findings remain open.

## 2026-09-09 — mart reproduction and recovery

- Reproduced the empty-data failure on a private PostgreSQL cluster. The 24 existing dbt tests passed with empty input.
- Added nonempty_required_models and reconcile_loan_counts. Negative cases detected empty relations and stale staging→loan/loan→final counts.
- Built a two-loan fixture: five models and 26 tests passed. Deleting one final row was detected; rebuilding restored the expected counts.
- Initial active recovery stopped before mutation at the disk preflight. After capacity increased, backed up two empty marts and rebuilt only loan_features/final_features.
- Both marts recovered to 1,599,982 records and nine selected dbt tests passed.
- Source profiling found 660,686 candidate CSV IDs still missing from raw.

Evidence: audit/M0_ISOLATED_TEST_REPORT.json, audit/M0_MART_RECOVERY_PREFLIGHT_REPORT.json, audit/M0_MART_RECOVERY_REPORT.json.

## 2026-09-10 — ingestion recovery

| Change / check | Reason and result |
|---|---|
| Source/log diagnosis | Raw IDs matched the first 16 CSV chunks; 761 statuses of length 51 exceeded VARCHAR(50), beginning in chunk 17 |
| TEXT migration + ORM/init SQL | Preserve complete source strings; recreate the known dependent view transactionally; refuse unsupported metadata/dependencies and unsafe downgrade |
| Batch loader + insert-missing | Resume missing IDs without updating existing rows; rollback failed batches; report exclusions/commits |
| Fixture verification | Seven unit tests and eight private PostgreSQL checks passed, including no-op repeats and downgrade protection |
| Full CSV dryrun | 2,260,668 valid candidates; 33 missing required fields; date/numeric validation passed |
| Scoped backup/restore | Restored raw, staging view and both marts on a private server; counts and five raw indexes verified |
| Restore environment correction | Initial socket path exceeded the macOS limit; a shorter private path allowed the drill to complete |
| Active recovery | 660,686 rows inserted; 1,599,982 skipped; 33 excluded; 14 committed batches |
| Preservation/reconciliation | Existing rows retained count and aggregate fingerprint; source/raw ID differences were zero |
| dbt rebuild | Two models and nine tests passed; raw/staging/loan/final each 2,260,668 |
| Label feasibility | Proposed resolved-outcome mapping gives 1,345,350 candidates before temporal eligibility; no label or model change applied |

Evidence: audit/M0_INGESTION_DIAGNOSIS.json, audit/M0_INGESTION_DRYRUN.json, audit/M0_INGESTION_RESTORE_REPORT.json, audit/M0_INGESTION_RECOVERY_REPORT.json, audit/M0_POST_INGESTION_DBT_REPORT.json, audit/M0_LABEL_FEASIBILITY.json.

## 2026-09-10–11 — pull request validation

PR #14 contains the dbt tests, ingestion fix and supporting documentation. Local application checks passed (124 tests, four skipped); the detailed GitHub run on 7a859fe also passed with 124 tests, four skipped and eight warnings. The subsequent run 34506955747 on 745dd28 passed lint/typecheck and tests; evaluation/build jobs were skipped.

The ingestion module's reported CI coverage on the detailed run is 54%. Private PostgreSQL checks have not been integrated into CI. Model/data inputs to the main-branch evaluation gate remain unresolved.

## 2026-09-11 — documentation scope correction

Consolidated documentation around product scope, implementation, architecture, decisions, runbooks and technical evidence. Removed unrelated documents, corrected outdated status summaries and aligned the proposed PR description with the implementation. Source code, SQL, test behavior and factual validation results are unchanged. Documentation checks cover patch formatting, JSON parsing and internal links.
