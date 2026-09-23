from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime,timezone
from dataclasses import asdict
import os,sys,json,hashlib,logging,shutil,time
from dotenv import dotenv_values
import psycopg2
from alembic.config import Config
from alembic import command
ROOT=Path('/Users/agathasilalahi/Documents/creditlens');sys.path.insert(0,str(ROOT))
from src.ingestion.lending_club import load_csv
report={'started_at_utc':datetime.now(timezone.utc).isoformat(),'status':'started','steps':[]}
url=dotenv_values(ROOT/'.env')['POSTGRES_URL'];parts=urlsplit(url)
assert parts.hostname in ('localhost','127.0.0.1','::1') and parts.path=='/creditlens' and (parts.port or 5432)==5432
source=ROOT/'data/raw/accepted_2007_to_2018Q4.csv.gz'
logging.basicConfig(level=logging.INFO,format='%(message)s')
def snapshot(cutoff):
 with psycopg2.connect(url,options='-c default_transaction_read_only=on -c statement_timeout=180000') as conn:
  with conn.cursor() as c:
   c.execute('SELECT count(*), min(issue_date), max(issue_date), count(*) FILTER (WHERE length(loan_status)>50) FROM raw.lc_loans')
   row=c.fetchone();result={'raw_count':row[0],'issue_min':str(row[1]),'issue_max':str(row[2]),'long_status_count':row[3]}
   c.execute("SELECT count(*), sum(('x'||substr(h,1,16))::bit(64)::bigint::numeric)::text, sum(('x'||substr(h,17,16))::bit(64)::bigint::numeric)::text FROM (SELECT md5(row_to_json(t)::text) h FROM raw.lc_loans t WHERE loaded_at < %s OR loaded_at IS NULL) x",(cutoff,))
   result['original_rows_fingerprint']=list(c.fetchone())
   c.execute('SELECT version_num FROM alembic_version');result['revision']=[r[0] for r in c.fetchall()]
   c.execute("SELECT data_type FROM information_schema.columns WHERE table_schema='raw' AND table_name='lc_loans' AND column_name='loan_status'");result['loan_status_type']=c.fetchone()[0]
   return result
try:
 for name in ['M0_INGESTION_ISOLATED_REPORT.json','M0_INGESTION_DRYRUN.json','M0_INGESTION_RESTORE_REPORT.json']:
  assert json.loads((ROOT/'docs/audit'/name).read_text())['status']=='passed',name
 backup=json.loads((ROOT/'docs/audit/M0_INGESTION_BACKUP.json').read_text());assert backup['restore_tested']
 with Path(backup['backup_path']).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==backup['sha256']
 with source.open('rb') as f:report['source_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
 assert report['source_sha256']=='55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d'
 report['disk_free_gib_before']=round(shutil.disk_usage(ROOT).free/1024**3,3);assert report['disk_free_gib_before']>2.5
 with psycopg2.connect(url,options='-c default_transaction_read_only=on') as conn:
  with conn.cursor() as c:c.execute('SELECT localtimestamp');cutoff=c.fetchone()[0]
 report['fingerprint_cutoff_local_timestamp']=str(cutoff)
 report['before']=snapshot(cutoff)
 assert report['before']['raw_count']==1599982
 assert report['before']['original_rows_fingerprint'][0]==1599982
 assert report['before']['revision']==['e9827ae898f0'] and report['before']['loan_status_type']=='character varying'
 # Short locks prevent waiting indefinitely behind another local session.
 os.environ['PGOPTIONS']='-c lock_timeout=5000 -c statement_timeout=180000'
 cfg=Config(str(ROOT/'alembic.ini'));cfg.set_main_option('script_location',str(ROOT/'migrations'));cfg.set_main_option('sqlalchemy.url',url.replace('%','%%'))
 command.upgrade(cfg,'4b7d2a91c608');report['steps'].append('migration_applied');print('Migration applied',flush=True)
 connection=psycopg2.connect(url,connect_timeout=5,options='-c lock_timeout=5000 -c statement_timeout=120000')
 try:report['ingestion']=asdict(load_csv(source,connection,insert_missing=True,chunksize=50000))
 finally:connection.close()
 report['steps'].append('insert_missing_completed');print('Insert missing completed',report['ingestion'],flush=True)
 report['after']=snapshot(cutoff)
 assert report['after']['raw_count']==2260668 and report['after']['long_status_count']==761
 assert report['after']['revision']==['4b7d2a91c608'] and report['after']['loan_status_type']=='text'
 assert report['after']['original_rows_fingerprint']==report['before']['original_rows_fingerprint']
 assert report['ingestion']['written_rows']==660686 and report['ingestion']['skipped_existing']==1599982 and report['ingestion']['excluded_required_fields']==33
 report['steps'].append('original_rows_count_and_aggregate_fingerprint_unchanged');report['status']='passed'
except Exception as exc:
 report.update(status='failed',error_type=type(exc).__name__)
 print('Stopped:',type(exc).__name__,'No automatic rollback of committed batches or retry.',flush=True)
finally:
 report['disk_free_gib_after']=round(shutil.disk_usage(ROOT).free/1024**3,3);report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
 (ROOT/'docs/audit/M0_INGESTION_RECOVERY_REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
raise SystemExit(0 if report['status']=='passed' else 1)
