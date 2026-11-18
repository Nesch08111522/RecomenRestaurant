from pathlib import Path
import sys,json,re
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from app import create_app
from database.repository import document_transaction
from utils.security import session_identity
from models.discovery import CandidateModel,SourceModel,RunModel,ClaimModel
app=create_app()
results=[]
with document_transaction() as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    row=conn.execute("SELECT payload FROM public.app_records WHERE collection='users' AND payload->>'role'='admin' AND upper(coalesce(payload->>'status','ACTIVE'))='ACTIVE' LIMIT 1").fetchone()
    admin=app.test_client()
    if row:
        account=row['payload']
        with admin.session_transaction() as sess:
            sess['user_id']=account['id'];sess['user']=session_identity(account);sess['auth_epoch']=account.get('auth_epoch',0)
        for path in ['/admin/discovery','/admin/discovery/google-lookup','/admin/api/discovery/candidates','/admin/api/discovery/sources','/admin/api/discovery/export/osm']:
            response=admin.get(path)
            result={'path':path,'status':response.status_code,'ok':response.status_code==200}
            if response.mimetype=='text/html':
                for url in set(re.findall(r'(?:src|href)=[\"\']([^\"\']+)',response.get_data(as_text=True))):
                    if url.startswith('/static/'):
                        asset=admin.get(url); results.append({'asset':url,'status':asset.status_code,'ok':asset.status_code==200})
            results.append(result)
    guest=app.test_client()
    response=guest.get('/reclamar');results.append({'path':'/reclamar','status':response.status_code,'ok':response.status_code==200})
    response=guest.get('/admin/api/discovery/candidates');results.append({'path':'guest radar','status':response.status_code,'ok':response.status_code==401})
    for name in app.jinja_env.list_templates():
        app.jinja_env.get_template(name)
    # Plan SQL without INSERT execution and without advancing sequences.
    conn.execute("EXPLAIN INSERT INTO public.sr_businesses(slug,name,status,metadata) VALUES ('qa-not-inserted','QA','draft','{}'::jsonb) RETURNING id").fetchall()
    conn.execute("EXPLAIN INSERT INTO public.sr_branches(business_id,name,address,status) VALUES(1,'QA','No insertada','draft') RETURNING id").fetchall()
    conn.execute("EXPLAIN INSERT INTO public.sr_memberships(user_id,business_id,role,status) VALUES(1,1,'business_owner','active')").fetchall()
out=ROOT/'.work'/'debug'/'phase3-smoke.json';out.write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(results),'templates':len(app.jinja_env.list_templates()),'failures':[r for r in results if not r['ok']]},indent=2))
raise SystemExit(1 if any(not r['ok'] for r in results) else 0)
