import sys,json,time,importlib.util
from pathlib import Path
from statistics import mean
sys.path.insert(0,str(Path.cwd()))
from dotenv import load_dotenv
load_dotenv(override=False)
from database.connection import connection
from database.pool import close_pool,pool_stats
from database.repository import PostgresDocumentRepository as Repo
old_path=Path(r'C:/Users/Nancy Sandoval/.codex/visualizations/2026/11/17/01a1e7c2-906d-78e2-bc7d-0d4f3be2d440/connectivity-backup-20261118/database/connection.py')
spec=importlib.util.spec_from_file_location('before_connection',old_path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
result={}
try:
 for name,fn in [('before',old.connection),('after',connection)]:
  rows=[]
  for i in range(3):
   start=time.perf_counter()
   with fn() as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    n=conn.execute('SELECT count(*) AS n FROM public.app_records WHERE collection=%s',('restaurants',)).fetchone()['n']
   rows.append(round((time.perf_counter()-start)*1000,2))
  result[name]={'samples_ms':rows,'mean_ms':round(mean(rows),2),'restaurant_count':n}
 with connection() as conn:
  conn.execute('SET TRANSACTION READ ONLY')
  result['schema']=conn.execute("SELECT c.relkind,c.relrowsecurity,(SELECT count(*) FROM pg_constraint k WHERE k.conrelid=c.oid AND k.contype='p') AS primary_keys,(SELECT count(*) FROM pg_index i WHERE i.indrelid=c.oid) AS indexes FROM pg_class c JOIN pg_namespace ns ON ns.oid=c.relnamespace WHERE ns.nspname='public' AND c.relname='app_records'").fetchone()
  result['duplicate_id_groups']=conn.execute('SELECT count(*) AS n FROM (SELECT collection,id FROM public.app_records GROUP BY collection,id HAVING count(*)>1) d').fetchone()['n']
 result['pool']=pool_stats()
 result['improvement_pct']=round((1-result['after']['mean_ms']/result['before']['mean_ms'])*100,1)
except Exception as e:result['error_type']=type(e).__name__;result['stopped_without_retry']=True
finally:close_pool()
Path('.work/connectivity/comparison.json').write_text(json.dumps(result,indent=2,default=str));print(json.dumps(result,indent=2,default=str))
