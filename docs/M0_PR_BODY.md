Lending Club ingestion stopped because a 51-character loan status exceeded the raw VARCHAR(50) column. Separately, existing warehouse tests could pass on empty or stale marts. This change preserves complete status strings, adds resumable missing-ID ingestion, and detects nonempty/count-reconciliation failures.

Changes:
- Synchronize loan_status TEXT across migration, ORM and initial schema. Recreate the known staging view transactionally; refuse unsafe downgrade and unsupported dependencies/metadata.
- Parse columns and insert in batches. The insert-missing mode preserves existing records; default upsert updates only changed outcome fields.
- Add dbt nonempty/reconciliation checks and private PostgreSQL reproduction scripts.
- Document product scope, data/technical design, evaluation requirements, recovery results and remaining risks.

Validation:
- Local application suite: 124 passed, 4 skipped. GitHub lint/typecheck and application tests passed on 745dd28 (run 34506955747).
- Eight private PostgreSQL ingestion checks passed, including rollback, view preservation, resume/no-op and downgrade guards.
- Scoped backup restored on a private server before local recovery; owner/ACL recovery was outside the drill.
- Recovery inserted 660,686 missing records. Raw, staging and both loan marts each contain 2,260,668 rows; source/raw ID differences are zero and existing-row aggregate fingerprints are unchanged.
- Two dbt models built and nine selected tests passed after recovery.

Limitations: PostgreSQL recovery checks are local evidence and are not yet CI jobs. Model evaluation and Docker build were skipped on PR runs; model/data inputs to the main-branch evaluation gate remain unresolved. Source licensing/as-of, label availability, preprocessing/evaluation, model bundles and API readiness remain open. This PR does not establish production readiness or deploy a service.

Source, tests and documentation were developed with AI assistance. Raw data, credentials and backup archives are not included.
