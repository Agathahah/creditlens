# M0 — diagnosis historical empty marts

Recorded 2026-09-09. This snapshot predates ingestion completion; current counts are in PROJECT_STATUS.md and M0_POST_INGESTION_DBT_REPORT.json.

## Evidence

Read-only audit counts showed raw/staging at 1,599,982 and loan/final marts at zero. Historical dbt log excerpts showed an earlier successful populated build followed by a successful empty build. The target artifacts recorded 24 passing column tests. Source, log excerpts and checksums were preserved in M0_DBT_LOG_EVIDENCE.json before rebuilding.

A successful dbt execution does not guarantee nonempty input, and unique/not_null tests can pass on zero rows. The logs contain time-of-day without enough server/date identity to reconstruct the exact historical cause of empty staging input.

## Reproduction and remediation

A separate PostgreSQL server was required because generate_schema_name returns fixed custom staging/mart names. Schema-only isolation would not protect the active database.

The private fixture reproduced the empty build and passing legacy tests. New nonempty and row-reconciliation tests detected empty and stale relations. Populated fixture builds passed 26 tests; deleting one final row was detected. Active recovery rebuilt two loan marts after a scoped backup and passed nine selected tests.

Evidence: M0_ISOLATED_TEST_REPORT.json and M0_MART_RECOVERY_REPORT.json. Subsequent source profiling and ingestion recovery are documented separately; the original build chronology remains partially uncertain.
