from pathlib import Path
import os,json,tempfile,subprocess,shutil,hashlib
import psycopg2
ROOT=Path('/Users/agathasilalahi/Documents/creditlens');PG=Path('/opt/homebrew/opt/postgresql@16/bin')
backup_report=json.loads((ROOT/'docs/audit/M0_INGESTION_BACKUP.json').read_text());backup=Path(backup_report['backup_path'])
with backup.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==backup_report['sha256']
assert shutil.disk_usage(ROOT).free/1024**3>3.5
work=Path(tempfile.mkdtemp(prefix='m0-restore-',dir='/private/tmp'));socket=work/'socket';socket.mkdir(mode=0o700)
report={'workspace':str(work),'status':'started','source_backup_sha256':backup_report['sha256'],'scope':backup_report['scope'],'ownership_acl_restored':False}
def run(name,args):
 result=subprocess.run(args,capture_output=True,text=True,timeout=600)
 (work/(name+'.log')).write_text(result.stdout+result.stderr)
 if result.returncode:raise RuntimeError(name)
 print(name,'passed',flush=True)
try:
 run('init',[str(PG/'initdb'),'-D',str(work/'pgdata'),'-U','creditlens_m0','--auth=trust','--locale=C','--encoding=UTF8'])
 run('start',[str(PG/'pg_ctl'),'-D',str(work/'pgdata'),'-l',str(work/'pg.log'),'-o',f"-k {socket} -p 55439 -c listen_addresses='' -c shared_buffers=32MB -c max_wal_size=256MB",'-w','start'])
 base=['-h',str(socket),'-p','55439','-U','creditlens_m0']
 run('createdb',[str(PG/'createdb'),*base,'creditlens_restore'])
 with psycopg2.connect(host=str(socket),port=55439,user='creditlens_m0',dbname='creditlens_restore') as conn:
  with conn.cursor() as c:
   c.execute('SHOW data_directory');assert Path(c.fetchone()[0])==work/'pgdata'
   c.execute('CREATE SCHEMA raw; CREATE SCHEMA staging; CREATE SCHEMA mart')
 run('restore',[str(PG/'pg_restore'),*base,'-d','creditlens_restore','--exit-on-error','--no-owner','--no-privileges',str(backup)])
 with psycopg2.connect(host=str(socket),port=55439,user='creditlens_m0',dbname='creditlens_restore') as conn:
  with conn.cursor() as c:
   report['restored_counts']={}
   for table in backup_report['scope']:
    c.execute('SELECT COUNT(*) FROM '+table);report['restored_counts'][table]=c.fetchone()[0]
   assert report['restored_counts']==backup_report['before_counts']
   c.execute("SELECT character_maximum_length FROM information_schema.columns WHERE table_schema='raw' AND table_name='lc_loans' AND column_name='loan_status'");assert c.fetchone()[0]==50
   c.execute("SELECT count(*) FROM pg_indexes WHERE schemaname='raw' AND tablename='lc_loans'");report['raw_indexes_restored']=c.fetchone()[0];assert report['raw_indexes_restored']>=5
 report['status']='passed'
except Exception as exc:report.update(status='failed',error_type=type(exc).__name__)
finally:
 if (work/'pgdata/postmaster.pid').exists():
  run('stop',[str(PG/'pg_ctl'),'-D',str(work/'pgdata'),'-m','fast','-w','stop'])
 report['cluster_stopped']=not (work/'pgdata/postmaster.pid').exists()
 if report['status']=='passed' and report['cluster_stopped']:
  shutil.rmtree(work/'pgdata');report['temporary_restored_database_removed']=True
 report['disk_free_gib']=round(shutil.disk_usage(ROOT).free/1024**3,3)
 text=json.dumps(report,indent=2)+'\n';(work/'report.json').write_text(text);(ROOT/'docs/audit/M0_INGESTION_RESTORE_REPORT.json').write_text(text)
 if report['status']=='passed':
  backup_report['restore_tested']=True;backup_report['restore_report']='docs/audit/M0_INGESTION_RESTORE_REPORT.json';(ROOT/'docs/audit/M0_INGESTION_BACKUP.json').write_text(json.dumps(backup_report,indent=2)+'\n')
 print(text)
raise SystemExit(0 if report['status']=='passed' else 1)
