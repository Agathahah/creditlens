from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
import json
import numpy as np
import pandas as pd
import psycopg2
from dotenv import dotenv_values

root=Path('/Users/agathasilalahi/Documents/creditlens')
url=dotenv_values(root/'.env').get('POSTGRES_URL')
assert urlsplit(url).hostname in ('localhost','127.0.0.1','::1')
assert urlsplit(url).path=='/creditlens'
ids=[]
for chunk in pd.read_csv(root/'data/raw/accepted_2007_to_2018Q4.csv.gz',usecols=['id','issue_d','loan_amnt'],chunksize=100000,dtype='string'):
    numeric=pd.to_numeric(chunk['id'],errors='coerce')
    good=numeric.notna() & pd.to_numeric(chunk['loan_amnt'],errors='coerce').notna() & chunk['issue_d'].notna()
    ids.append(numeric[good].to_numpy(dtype=np.int64))
source_ids=np.concatenate(ids)
unique_ids=np.unique(source_ids)
conn=psycopg2.connect(url,connect_timeout=5,options='-c default_transaction_read_only=on -c statement_timeout=60000')
try:
    conn.set_session(readonly=True,isolation_level='REPEATABLE READ')
    with conn.cursor(name='m0_read_ids') as cur:
        cur.itersize=10000
        cur.execute('SELECT loan_id FROM raw.lc_loans')
        raw_ids=np.fromiter((row[0] for row in cur),dtype=np.int64)
    with conn.cursor() as cur:
        cur.execute('SELECT id, loan_amnt, issue_d, installment_to_income_ratio, revol_util_clean, is_default FROM mart.final_features WHERE id = %s',(68407277,))
        record=cur.fetchone()
    assert record is not None, 'Audited example missing after rebuild'
    out={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'mode':'read-only; no ingestion/training',
         'source_rows_with_numeric_id_amount_and_issue':int(len(source_ids)),
         'source_distinct_ids':int(len(unique_ids)),
         'source_duplicate_id_rows':int(len(source_ids)-len(unique_ids)),
         'raw_distinct_ids':int(len(np.unique(raw_ids))),
         'source_ids_missing_from_raw':int(len(np.setdiff1d(unique_ids,raw_ids))),
         'raw_ids_absent_from_source':int(len(np.setdiff1d(raw_ids,unique_ids))),
         'verified_final_example':dict(zip(['id','loan_amnt','issue_d','installment_to_income_ratio','revol_util_clean','is_default'],record)),
         'limits':'Exact loan-ID coverage against the currently available CSV for rows with basic fields present. This does not validate all cell values, labels, source license or prediction-time availability.'}
    (root/'docs/audit/M0_ID_RECONCILIATION.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    print(json.dumps(out,indent=2,default=str))
finally:
    conn.rollback();conn.close()
