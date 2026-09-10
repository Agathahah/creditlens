from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
import json
import psycopg2
from dotenv import dotenv_values
root=Path('/Users/agathasilalahi/Documents/creditlens');url=dotenv_values(root/'.env')['POSTGRES_URL']
assert urlsplit(url).hostname in ('localhost','127.0.0.1','::1') and urlsplit(url).path=='/creditlens'
report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'mode':'read-only aggregate; no label or ML changes'}
queries={
 'loan_status_counts':"SELECT loan_status, COUNT(*) FROM raw.lc_loans GROUP BY 1 ORDER BY 2 DESC",
 'year_status_counts':"SELECT EXTRACT(YEAR FROM issue_date)::int, loan_status, COUNT(*) FROM raw.lc_loans GROUP BY 1,2 ORDER BY 1,2",
 'term_status_counts':"SELECT TRIM(term), loan_status, COUNT(*) FROM raw.lc_loans GROUP BY 1,2 ORDER BY 1,2",
 'availability':"SELECT COUNT(*) AS rows, COUNT(member_id) AS nonnull_member_id, COUNT(*) FILTER (WHERE last_pymnt_date IS NULL) AS missing_last_payment_date, min(last_pymnt_date)::text, max(last_pymnt_date)::text FROM raw.lc_loans",
 'legacy_staging_label_counts':"SELECT is_default, COUNT(*) FROM staging.lc_loans_clean GROUP BY 1 ORDER BY 1 NULLS LAST",
}
with psycopg2.connect(url,options='-c default_transaction_read_only=on -c statement_timeout=120000') as conn:
 conn.set_session(readonly=True,isolation_level='REPEATABLE READ')
 with conn.cursor() as c:
  for name,sql in queries.items():
   c.execute(sql);report[name]={'columns':[d.name for d in c.description],'rows':c.fetchall()}
(root/'docs/audit/M0_LABEL_FEASIBILITY.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('year_status_counts','term_status_counts')},indent=2))
