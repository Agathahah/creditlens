# Read-only warehouse verification

Validated local recovery: raw, staging and both loan marts contain 2,260,668 rows.

Connect using the database role's local credential:

```bash
PGOPTIONS='-c default_transaction_read_only=on' psql -X -h localhost -p 5432 -U creditlens -d creditlens
```

For the verified macOS installation, psql is also available at /opt/homebrew/opt/postgresql@16/bin/psql.

```sql
SHOW transaction_read_only;
SELECT 'raw' AS layer, COUNT(*) FROM raw.lc_loans
UNION ALL SELECT 'staging', COUNT(*) FROM staging.lc_loans_clean
UNION ALL SELECT 'loan', COUNT(*) FROM mart.loan_features
UNION ALL SELECT 'final', COUNT(*) FROM mart.final_features;
```

Expected: transaction_read_only on and four counts of 2260668 for the recorded snapshot. Count differences require diagnosis of the source, filters and last build; do not blindly rerun ingestion or rebuild. These queries do not validate all row values, label maturity or model quality. Source-ID reconciliation and detailed results are recorded in audit/M0_ID_RECONCILIATION.json.
