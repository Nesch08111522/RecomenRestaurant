import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=False)
from database.connection import connection
from database.pool import close_pool
import json
result={}
try:
 with connection() as conn:
  conn.execute('SET TRANSACTION READ ONLY');conn.execute("SET LOCAL statement_timeout='4000ms'")
  result['indexes']=conn.execute("SELECT c.relname AS index_name,i.indisvalid,i.indisready,i.indisunique,pg_get_indexdef(i.indexrelid) AS definition FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid WHERE i.indrelid='public.app_records'::regclass").fetchall()
  result['api_permissions']=conn.execute("SELECT has_table_privilege('anon','public.app_records','SELECT') AS anon_read,has_table_privilege('authenticated','public.app_records','SELECT') AS authenticated_read,has_table_privilege('anon','public.app_records','INSERT,UPDATE,DELETE') AS anon_write,has_table_privilege('authenticated','public.app_records','INSERT,UPDATE,DELETE') AS authenticated_write").fetchone()
except Exception as e:result['error_type']=type(e).__name__
finally:close_pool()
Path('.work/connectivity/schema-review.json').write_text(json.dumps(result,indent=2,default=str));print(json.dumps(result,indent=2,default=str))

