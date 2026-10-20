from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import psycopg2
from dotenv import dotenv_values
import yaml

ROOT = Path('/Users/agathasilalahi/Documents/creditlens')
PG = Path('/opt/homebrew/opt/postgresql@16/bin')
url = dotenv_values(ROOT / '.env').get('POSTGRES_URL')
parts = urlsplit(url or '')
assert parts.hostname in ('localhost', '127.0.0.1', '::1')
assert parts.path == '/creditlens' and (parts.port or 5432) == 5432
work = Path(tempfile.mkdtemp(prefix='creditlens-m0-recovery-', dir='/private/tmp'))
report = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'workspace': str(work), 'steps': [], 'status': 'started'}

def snapshot():
    with psycopg2.connect(url, connect_timeout=5, options='-c default_transaction_read_only=on -c statement_timeout=60000') as conn:
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor() as cur:
            result = {}
            for name in ['staging.lc_loans_clean', 'mart.loan_features', 'mart.final_features']:
                cur.execute('SELECT COUNT(*) FROM ' + name)
                result[name] = cur.fetchone()[0]
            return result

def run(name, args, env, timeout=180):
    result = subprocess.run(args, cwd=work, env=env, capture_output=True, text=True, timeout=timeout)
    (work / (name + '.log')).write_text(result.stdout + result.stderr)
    report['steps'].append({'step': name, 'exit_code': result.returncode})
    print(name, 'exit=', result.returncode, flush=True)
    if result.returncode != 0:
        raise RuntimeError(name + ' failed; inspect private log before further mutation')
    return result

try:
    report['before'] = snapshot()
    assert report['before']['staging.lc_loans_clean'] == 2260668
    assert report['before']['mart.loan_features'] == report['before']['mart.final_features'] == 1599982
    report['free_disk_gib_before'] = round(shutil.disk_usage(ROOT).free / 1024**3, 3)
    assert report['free_disk_gib_before'] > 2, 'Insufficient free disk space'
    env = {k:v for k,v in os.environ.items() if not k.startswith(('PG','POSTGRES','DBT_'))}
    from psycopg2.extensions import parse_dsn
    params = parse_dsn(url)
    backup_report = json.loads((ROOT / 'docs/audit/M0_INGESTION_BACKUP.json').read_text())
    assert backup_report['restore_tested']
    with Path(backup_report['backup_path']).open('rb') as f:
        assert hashlib.file_digest(f, 'sha256').hexdigest() == backup_report['sha256']
    report['backup'] = backup_report
    project = work / 'project'
    project.mkdir()
    for name in ['models', 'macros', 'tests/dbt']:
        shutil.copytree(ROOT / name, project / name)
    shutil.copy2(ROOT / 'dbt_project.yml', project / 'dbt_project.yml')
    report['source_sha256'] = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['models','macros','tests/dbt'] for p in (ROOT / folder).rglob('*') if p.is_file()}
    profile = {'creditlens': {'target':'m0_recovery','outputs':{'m0_recovery':{
        'type':'postgres','host':parts.hostname,'port':5432,'user':params['user'],
        'password':"{{ env_var('CREDITLENS_M0_DB_PASSWORD') }}",'dbname':'creditlens',
        'schema':'public','threads':1,'connect_timeout':5,
        'session_role':params['user'], 'retries':0,
    }}}}
    (project / 'profiles.yml').write_text(yaml.safe_dump(profile))
    env.pop('PGPASSWORD', None)
    env.update(CREDITLENS_M0_DB_PASSWORD=params.get('password',''), DBT_SEND_ANONYMOUS_USAGE_STATS='false', DBT_USE_COLORS='false', PGOPTIONS='-c statement_timeout=120000 -c lock_timeout=5000')
    report['mutation_started'] = True
    run('dbt_build', [str(ROOT / '.venv/bin/dbt'), 'build', '--project-dir', str(project), '--profiles-dir', str(project), '--select', 'loan_features', 'final_features'], env)
    results = json.loads((project / 'target/run_results.json').read_text())
    report['dbt_results'] = [{k:r.get(k) for k in ['unique_id','status','failures','adapter_response']} for r in results['results']]
    assert report['dbt_results'] and all(r['status'] in ('pass','success') for r in report['dbt_results'])
    built = {r['unique_id'] for r in report['dbt_results'] if r['unique_id'].startswith('model.')}
    assert built == {'model.creditlens.loan_features','model.creditlens.final_features'}
    report['after'] = snapshot()
    report['free_disk_gib_after'] = round(shutil.disk_usage(ROOT).free / 1024**3, 3)
    assert len(set(report['after'].values())) == 1 and report['after']['mart.loan_features'] == 2260668
    report['status'] = 'passed'
except (AssertionError, OSError, RuntimeError, ValueError, subprocess.SubprocessError, psycopg2.Error) as exc:
    report['status'] = 'failed'
    report['error_type'] = type(exc).__name__
    print('Recovery stopped:', type(exc).__name__, 'Inspect private logs; no automatic retry/restore.', flush=True)
finally:
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    text = json.dumps(report,indent=2,default=str)+'\n'
    (work / 'report.json').write_text(text)
    (ROOT / 'docs/audit/M0_POST_INGESTION_DBT_REPORT.json').write_text(text)
    print('Report:', work / 'report.json', flush=True)
    if 'after' in report: print('After:', report['after'], flush=True)
raise SystemExit(0 if report['status']=='passed' else 1)
