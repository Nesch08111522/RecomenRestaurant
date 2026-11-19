import os,sys,json,time
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0,str(Path.cwd()))
pw=Path(r'C:/Users/Nancy Sandoval/.codex/visualizations/2026/11/17/01a1e7c2-906d-78e2-bc7d-0d4f3be2d440/ecosystem-qa/pw').read_text().strip()
name=Path('.work/connectivity/test-env-name.txt').read_text().strip()
assert name.startswith('connectivity_') and name.replace('_','').isalnum()
os.environ.update(DATABASE_URL='postgresql://qa:'+quote(pw,safe='')+'@127.0.0.1:56487/'+name+'?sslmode=require',SECRET_KEY='local-smoke-'+'x'*32,FLASK_DEBUG='0')
for key in ['AI_API_KEY','OPENROUTER_API_KEY','ADMIN_AI_API_KEY']:os.environ[key]=''
from app import create_app
from database.connection import connection
from database.pool import close_pool,pool_stats
from concurrent.futures import ThreadPoolExecutor
start=time.perf_counter();app=create_app();result={'normal_startup_ms':round((time.perf_counter()-start)*1000,2),'pages':[]}
client=app.test_client()
for url in ['/','/auth/login','/auth/register','/ofertas','/para-negocios','/api/platform/health']:
 started=time.perf_counter();res=client.get(url);result['pages'].append({'path':url,'status':res.status_code,'ms':round((time.perf_counter()-started)*1000,2)});assert res.status_code==200,(url,res.status_code)
assert client.post('/auth/login',data={}).status_code==400
result['csrf_without_token']=400
from threading import Barrier
barrier=Barrier(8)
def query(_):
 barrier.wait()
 with connection() as conn:return conn.execute('SELECT 1 AS ok').fetchone()['ok']
with ThreadPoolExecutor(max_workers=8) as workers:assert list(workers.map(query,range(8)))==[1]*8
result['simultaneous_reads']=8;result['pool']=pool_stats();assert result['pool']['total']<=4 and result['pool']['in_use']==0
close_pool();Path('.work/connectivity/smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
