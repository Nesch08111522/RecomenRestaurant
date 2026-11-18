from pathlib import Path
import sys,json
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from app import create_app
from database.repository import document_transaction
from models.restaurant import RestaurantModel
from models.business_site import default_site,SiteModel
from utils.security import session_identity
app=create_app();checks=[]
with document_transaction() as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    rows=conn.execute("SELECT payload FROM public.app_records WHERE collection='users' AND payload->>'role'='business_owner' ORDER BY EXISTS(SELECT 1 FROM public.app_records r WHERE r.collection='restaurants' AND r.payload->>'owner_id'=public.app_records.payload->>'id') DESC LIMIT 1").fetchall()
    if rows:
        user=rows[0]['payload'];client=app.test_client()
        with client.session_transaction() as s:
            s['user_id']=user['id'];s['user']=session_identity(user)
        own=RestaurantModel.get_by_owner(user['id'])
        response=client.get('/owner/sites');checks.append({'path':'/owner/sites','status':response.status_code,'ok':response.status_code==200})
        for r in own[:2]:
            for path in [f"/owner/sites/{r['id']}/preview",f"/owner/api/sites/{r['id']}"]:
                response=client.get(path);checks.append({'path':path,'status':response.status_code,'ok':response.status_code==200})
    approved=RestaurantModel.get_approved()
    if approved:
        restaurant=approved[0];draft=default_site(restaurant);draft['slug']='qa-render-only'
        # Synthetic snapshot only in process memory; no database writes, no real publication.
        with patch.object(SiteModel,'all',return_value=[{'id':0,'restaurant_id':restaurant['id'],'owner_id':restaurant['owner_id'],'published':draft,'draft':draft}]):
            response=app.test_client().get('/negocio/qa-render-only');html=response.get_data(as_text=True)
            checks.append({'path':'public SSR memory snapshot','status':response.status_code,'ok':response.status_code==200 and '<h1' in html and 'og:title' in html and 'application/ld+json' in html})
    for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    for asset in ['css/business-sites.css','js/business-sites.js']:
        response=app.test_client().get('/static/'+asset);checks.append({'path':asset,'ok':response.status_code==200,'status':response.status_code})
output=ROOT/'.work/debug/phase4-smoke.json';output.write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(checks),'templates':len(app.jinja_env.list_templates()),'failures':[r for r in checks if not r['ok']]},indent=2))
raise SystemExit(1 if any(not r['ok'] for r in checks) else 0)
