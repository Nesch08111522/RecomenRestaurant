import sys,json,time,socket,ssl,struct,os
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from dotenv import load_dotenv
load_dotenv(override=False)
from urllib.parse import urlsplit
from config import Config
from database.connection import connection
parts=urlsplit(Config.DATABASE_URL);host=parts.hostname;port=parts.port or 5432
result={'configured':bool(host),'port':port,'mode_hint':'transaction_pooler' if 'pooler.supabase.com' in host and port==6543 else 'session_pooler' if 'pooler.supabase.com' in host else 'direct_or_custom','sslmode':Config.DATABASE_SSLMODE}
def timed(name,fn):
 start=time.perf_counter()
 try:
  value=fn();result[name]={'ms':round((time.perf_counter()-start)*1000,2),'ok':True,'value':value};return value
 except Exception as e:result[name]={'ms':round((time.perf_counter()-start)*1000,2),'ok':False,'type':type(e).__name__,'sqlstate':getattr(e,'sqlstate',None)}
addresses=timed('dns',lambda:socket.getaddrinfo(host,port,type=socket.SOCK_STREAM))
if addresses:
 result['dns']['value']={'ipv4':sum(a[0]==socket.AF_INET for a in addresses),'ipv6':sum(a[0]==socket.AF_INET6 for a in addresses)}
 def tcp():
  with socket.create_connection((host,port),timeout=5):return 'reachable'
 timed('tcp',tcp)
 def tls():
  with socket.create_connection((host,port),timeout=5) as sock:
   sock.sendall(struct.pack('!II',8,80877103))
   if sock.recv(1)!=b'S':return 'TLS refused'
   with ssl.create_default_context().wrap_socket(sock,server_hostname=host) as secured:return secured.version()
 timed('tcp_plus_tls',tls)
start=time.perf_counter()
try:
 with connection() as conn:
  result['connect_auth']={'ms':round((time.perf_counter()-start)*1000,2),'ok':True}
  conn.execute('SET TRANSACTION READ ONLY')
  conn.execute("SET LOCAL statement_timeout='4000ms'")
  for n in range(3):timed('select1_'+str(n),lambda:conn.execute('SELECT 1 AS ok').fetchone()['ok'])
  timed('read20',lambda:len(conn.execute("SELECT payload FROM public.app_records WHERE collection=%s ORDER BY id LIMIT 20",('restaurants',)).fetchall()))
  timed('explain',lambda:conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT payload FROM public.app_records WHERE collection=%s ORDER BY id LIMIT 20",('restaurants',)).fetchone()['QUERY PLAN'])
  timed('indexes',lambda:conn.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='app_records'").fetchall())
  timed('activity',lambda:conn.execute("SELECT state,count(*) AS count FROM pg_stat_activity WHERE datname=current_database() GROUP BY state").fetchall())
except Exception as e:result['connect_auth']={'ms':round((time.perf_counter()-start)*1000,2),'ok':False,'type':type(e).__name__,'classification':str(e) if type(e).__name__=='DatabaseConnectionError' else 'redacted','sqlstate':getattr(e,'sqlstate',None)}
Path('.work/connectivity/baseline.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('explain','indexes')},indent=2))
