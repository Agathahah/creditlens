from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime,timezone
from dotenv import dotenv_values
from psycopg2.extensions import parse_dsn
import psycopg2,os,subprocess,tempfile,shutil,hashlib,json
ROOT=Path('/Users/agathasilalahi/Documents/creditlens');PG=Path('/opt/homebrew/opt/postgresql@16/bin')
url=dotenv_values(ROOT/'.env')['POSTGRES_URL'];parts=urlsplit(url);params=parse_dsn(url)
assert parts.hostname in ('localhost','127.0.0.1','::1') and parts.path=='/creditlens' and (parts.port or 5432)==5432
assert shutil.disk_usage(ROOT).free/1024**3>3.5
parent=ROOT/'.local-backups';parent.mkdir(exist_ok=True,mode=0o700)
work=Path(tempfile.mkdtemp(prefix='m0-ingestion-',dir=parent));os.chmod(work,0o700)
report={'started_at_utc':datetime.now(timezone.utc).isoformat(),'status':'started','backup_dir':str(work),'scope':['raw.lc_loans','staging.lc_loans_clean','mart.loan_features','mart.final_features'],'restore_tested':False}
env={k:v for k,v in os.environ.items() if not k.startswith(('PG','POSTGRES'))};env['PGPASSWORD']=params.get('password','')
try:
 with psycopg2.connect(url,options='-c default_transaction_read_only=on -c statement_timeout=60000') as conn:
  with conn.cursor() as c:
   report['before_counts']={}
   for table in report['scope']:
    c.execute('SELECT COUNT(*) FROM '+table);report['before_counts'][table]=c.fetchone()[0]
   assert set(report['before_counts'].values())=={1599982}
   c.execute("SELECT version_num FROM alembic_version");assert c.fetchall()==[('e9827ae898f0',)]
 backup=work/'before.dump'
 args=[str(PG/'pg_dump'),'-h',parts.hostname,'-p','5432','-U',params['user'],'-d','creditlens','-w','-Fc','-f',str(backup),'--lock-wait-timeout=5000']
 for table in report['scope']:args+=['-t',table]
 result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=600)
 (work/'dump.log').write_text(result.stderr);assert result.returncode==0
 os.chmod(backup,0o600)
 result=subprocess.run([str(PG/'pg_restore'),'--list',str(backup)],capture_output=True,text=True,timeout=30)
 assert result.returncode==0
 (work/'toc.txt').write_text(result.stdout)
 for entry in ['TABLE raw lc_loans','TABLE mart loan_features','TABLE mart final_features','VIEW staging lc_loans_clean']:assert entry in result.stdout
 with backup.open('rb') as f:report['sha256']=hashlib.file_digest(f,'sha256').hexdigest()
 report.update(status='backup_verified',backup_path=str(backup),bytes=backup.stat().st_size,disk_free_gib=round(shutil.disk_usage(ROOT).free/1024**3,3))
except Exception as e:report.update(status='failed',error_type=type(e).__name__)
finally:
 report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
 text=json.dumps(report,indent=2)+'\n';(work/'report.json').write_text(text);(ROOT/'docs/audit/M0_INGESTION_BACKUP.json').write_text(text);print(text)
raise SystemExit(0 if report['status']=='backup_verified' else 1)
