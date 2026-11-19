import os,sys,subprocess,uuid
from pathlib import Path
from urllib.parse import quote
import psycopg
pw=Path(r'C:/Users/Nancy Sandoval/.codex/visualizations/2026/11/17/01a1e7c2-906d-78e2-bc7d-0d4f3be2d440/ecosystem-qa/pw').read_text().strip()
name='connectivity_'+uuid.uuid4().hex[:8]
base='postgresql://qa:'+quote(pw,safe='')+'@127.0.0.1:56487/'
with psycopg.connect(base+'postgres?sslmode=require',autocommit=True) as conn:conn.execute('CREATE DATABASE '+name)
dsn=base+name+'?sslmode=require'
with psycopg.connect(dsn) as conn:
 for file in ['database/app_records.sql','database/ai_decisions.sql','database/platform_foundation.sql']:conn.execute(Path(file).read_text(encoding='utf-8-sig'))
env=os.environ.copy();env.update(DATABASE_URL=dsn,SMARTRESTO_TEST_DATABASE_URL=dsn,PYTHONDONTWRITEBYTECODE='1',SECRET_KEY='local-qa-only-'+'x'*32)
Path('.work/connectivity/test-env-name.txt').write_text(name)
cmd=[sys.executable,'-m','pytest']+(sys.argv[1:] or ['test'])+['-q','--disable-warnings','--junitxml=.work/connectivity/tests.xml']
sys.exit(subprocess.call(cmd,env=env))

