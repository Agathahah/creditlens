from pathlib import Path
import sys, json, hashlib, time
import pandas as pd
ROOT=Path('/Users/agathasilalahi/Documents/creditlens')
sys.path.insert(0,str(ROOT))
from src.ingestion.lending_club import SOURCE_TO_RAW,normalize_chunk
source=ROOT/'data/raw/accepted_2007_to_2018Q4.csv.gz'
report={'mode':'CSV normalization only; no database writes','read_rows':0,'valid_rows':0,'excluded_required_fields':0,'long_status_rows':0}
indices={k:i for i,k in enumerate(SOURCE_TO_RAW)}
start=time.monotonic()
for chunk in pd.read_csv(source,usecols=list(SOURCE_TO_RAW),dtype='string',chunksize=50000):
 rows,excluded=normalize_chunk(chunk)
 for row in rows:
  assert row[indices['loan_amnt']]>0
  for k,p in [('loan_amnt',12),('funded_amnt',12),('int_rate',5),('installment',10),('annual_inc',15),('dti',8),('revol_bal',15),('revol_util',5),('total_pymnt',15),('total_rec_prncp',15),('total_rec_int',15),('recoveries',15),('collection_recovery_fee',15),('last_pymnt_amnt',15)]:
   value=row[indices[k]]
   assert value is None or abs(round(value,2))<10**(p-2),k
  assert row[indices['annual_inc']]>=0
  rate=row[indices['int_rate']]
  assert rate is None or 0<=rate<=100
 report['read_rows']+=len(chunk);report['valid_rows']+=len(rows);report['excluded_required_fields']+=excluded
 report['long_status_rows']+=sum(r[indices['loan_status']] is not None and len(r[indices['loan_status']])>50 for r in rows)
 if report['read_rows']%500000==0: print('Validated CSV rows:',report['read_rows'],flush=True)
with source.open('rb') as f: report['source_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
assert report['source_sha256']=='55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d'
report.update(status='passed',elapsed_seconds=round(time.monotonic()-start,2))
(ROOT/'docs/audit/M0_INGESTION_DRYRUN.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
