"""QA interno: solo lectura, sesiones inyectadas para verificar renderizado por rol."""
from pathlib import Path
import sys
import json
import re

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import create_app
from database.repository import document_transaction
from utils.security import session_identity

app = create_app()
results = {'templates': [], 'routes': [], 'assets': [], 'schema': []}
with document_transaction() as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    expected = ['app_records','ai_decisions','sr_audit_events','sr_branches','sr_businesses','sr_memberships','sr_settings']
    for name in expected:
        row = conn.execute('SELECT to_regclass(%s) AS name', ('public.' + name,)).fetchone()
        results['schema'].append({'table':name, 'exists':bool(row['name'])})
    for name in app.jinja_env.list_templates():
        try:
            app.jinja_env.get_template(name)
            results['templates'].append({'name':name,'ok':True})
        except Exception as error:
            results['templates'].append({'name':name,'ok':False,'error_type':type(error).__name__})
    public = ['/', '/auth/login','/auth/register','/auth/recuperar','/api/categories',
              '/api/restaurants/top-rated','/api/restaurants/nearby?lat=-8.1&lng=-79.0',
              '/api/dishes/search?q=arroz','/api/platform/manifest','/api/platform/health',
              '/mercado/', '/ecosistema/', '/api/platform/me', '/auth/api/favorites']
    # Use route map for blueprint prefixes rather than guessing.
    public = [p for p in public if not p.startswith(('/mercado','/ecosistema'))]
    for endpoint in ['market.browse','ecosystem.home','ecosystem.index']:
        rules = list(app.url_map.iter_rules(endpoint)) if endpoint in app.view_functions else []
        if rules:
            public.append(rules[0].rule)
    rid_row = conn.execute("SELECT id FROM public.app_records WHERE collection='restaurants' AND payload->>'verified'='true' ORDER BY id LIMIT 1").fetchone()
    if rid_row:
        public.append(f"/restaurant/{rid_row['id']}")
    pages = []
    def check(client, path, role, expected=(200,)):
        response = client.get(path)
        results['routes'].append({'role':role,'path':path,'status':response.status_code,'ok':response.status_code in expected})
        if response.mimetype == 'text/html' and response.status_code == 200:
            pages.append(response.get_data(as_text=True))
    guest = app.test_client()
    for path in public:
        check(guest,path,'guest', (401,) if path in {'/api/platform/me','/auth/api/favorites'} else (200,))
    for role, paths in {
        'user':['/auth/profile','/auth/favorites','/auth/seguridad','/api/platform/me','/auth/api/favorites'],
        'business_owner':['/owner/dashboard','/admin/restaurants','/auth/profile','/api/platform/me'],
        'admin':['/admin/dashboard','/admin/users','/admin/restaurants','/admin/categories',
                 '/admin/moderation','/admin/analytics','/admin/controles','/admin/operaciones',
                 '/admin/api/analytics','/admin/api/bi/overview','/api/platform/me'],
    }.items():
        row = conn.execute("SELECT payload FROM public.app_records WHERE collection='users' AND payload->>'role'=%s AND upper(coalesce(payload->>'status','ACTIVE'))='ACTIVE' ORDER BY id LIMIT 1", (role,)).fetchone()
        if not row:
            results['routes'].append({'role':role,'skipped':'No hay cuenta activa para renderizar'})
            continue
        account = row['payload']
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = account['id']
            sess['user'] = session_identity(account)
            sess['auth_epoch'] = account.get('auth_epoch',0)
        for path in paths:
            check(client,path,role)
    assets = {u for page in pages for u in re.findall(r'(?:src|href)=[\"\']([^\"\']+)',page) if u.startswith('/static/')}
    for url in sorted(assets):
        response=guest.get(url)
        results['assets'].append({'url':url,'status':response.status_code,'ok':response.status_code==200})

out = ROOT / '.work' / 'debug' / 'read-only-smoke.json'
out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
failures = [item for group in results.values() for item in group if item.get('ok') is False or item.get('exists') is False]
print(json.dumps({'templates':len(results['templates']),'routes':len(results['routes']),
                  'assets':len(results['assets']),'schema':results['schema'], 'failures':failures},ensure_ascii=True,indent=2))
raise SystemExit(1 if failures else 0)
