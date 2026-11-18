from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from app import create_app
from database.repository import document_transaction
from models.restaurant import RestaurantModel
from utils.security import session_identity
app=create_app();checks=[]
with document_transaction() as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    rows=conn.execute("SELECT payload FROM public.app_records WHERE collection='users' AND payload->>'role'='business_owner' ORDER BY EXISTS(SELECT 1 FROM public.app_records r WHERE r.collection='restaurants' AND r.payload->>'owner_id'=public.app_records.payload->>'id') DESC LIMIT 1").fetchall()
    if rows:
        user=rows[0]['payload'];client=app.test_client()
        with client.session_transaction() as s:s['user_id']=user['id'];s['user']=session_identity(user)
        own=RestaurantModel.get_by_owner(user['id'])
        paths=['/owner/catalog']
        if own:paths += [f"/owner/api/catalog/{own[0]['id']}",f"/owner/catalog/{own[0]['id']}/template.xlsx"]
        for path in paths:
            result=client.get(path);checks.append({'path':path,'status':result.status_code,'ok':result.status_code==200})
        not_owned=next((r for r in RestaurantModel.all() if r.get('owner_id')!=user['id']),None)
        if not_owned:
            path=f"/owner/api/catalog/{not_owned['id']}";result=client.get(path);checks.append({'path':'foreign catalog','status':result.status_code,'ok':result.status_code in (403,404)})
    for path in ['/owner/catalog','/owner/api/catalog/1']:
        result=app.test_client().get(path);checks.append({'path':'anonymous '+path,'status':result.status_code,'ok':result.status_code==401})
    for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    for asset in ['css/catalog.css','js/catalog.js']:
        result=app.test_client().get('/static/'+asset);checks.append({'path':asset,'status':result.status_code,'ok':result.status_code==200})
    for statement,params in [
        ('INSERT INTO public.sr_businesses(slug,name,status,metadata) VALUES(%s,%s,%s,%s)',('qa-plan-only','Prueba','draft','{}')),
        ('INSERT INTO public.sr_branches(business_id,name,address,district,latitude,longitude,status) VALUES(%s,%s,%s,%s,%s,%s,%s)',(1,'Prueba','','',None,None,'draft')),
        ('INSERT INTO public.sr_memberships(user_id,business_id,role,status) VALUES(%s,%s,%s,%s)',(1,1,'business_owner','active'))]:
        conn.execute('EXPLAIN '+statement,params);checks.append({'path':'SQL EXPLAIN canonical','ok':True})
output=ROOT/'.work/debug/phase5-smoke.json';output.write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(checks),'templates':len(app.jinja_env.list_templates()),'failures':[r for r in checks if not r['ok']]},indent=2))
raise SystemExit(1 if any(not r['ok'] for r in checks) else 0)
