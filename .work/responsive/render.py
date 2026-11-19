from pathlib import Path
from unittest.mock import patch
import runpy,json,sys
sys.path.insert(0,str(Path.cwd()))
q=Path(r'C:/Users/Nancy Sandoval/.codex/visualizations/2026/11/17/01a1e7c2-906d-78e2-bc7d-0d4f3be2d440/filter-theme-qa')
x=runpy.run_path(str(q/'render.py'));app=x['app'];args=dict(x['common']);r=x['restaurant'];out=Path(__file__).parent
from flask import render_template,session
from analytics.intelligence import report
args.update(users=[dict(id=1,username='empresario_nombre_de_prueba',role='business_owner',profile={'name':'María de los Ángeles Sandoval','email':'contacto.restaurante.extenso@example.com'},favorites=[],preferences={})],business=r,selected_id=1,selected_name=r['name'],user={'id':1,'username':'Maria','profile':{'name':'Maria','email':'maria@example.com'},'preferences':{},'favorites':[]},restaurants=[r],pending=lambda *a:False,settings={'threshold':3,'diets':['Vegetariano']},result={},site={},sources=[],candidates=[],runs=[],claims=[],threads=[],notifications=[],cases=[],reviews=[],coupons=[],messages=[],thread={'id':1,'subject':'Consulta sobre mi pedido','business':'Cocina de prueba','last_id':1},uid=1,orders=[],lines=[],cart={'day':'2026-11-18','coupon':''},store={'channels':['Local','Recojo','Delivery'],'reward':0,'zones':['Trujillo'],'radius':3},diners=2,extra=0,share=2500,discount=0,points=5,digital=True,addresses=[],metrics={'income':123000,'sales':42,'rescued':12,'repeat':7,'customers':20},kinds=['Restaurante'],inventory=[],offers=[],recipes=[],movements=[],team=[],business_types=[],restaurant_id=1,offer={'id':1,'name':'Ceviche','price':2500,'description':'Pescado fresco','rid':1,'qty':4,'recipe':{},'status':'published'}, data=report([],[],args['start'],args['end']))
args['data'].update(website_views=15,published_offers=4,waste=[],recommendation_funnel={'views':15,'clicks':7,'orders':3},critical_ingredients=[],missing_metrics=[])
args.update(page=1,page_args={},districts=['Trujillo','Moche'],offer_diets=[],sort='')
views=[]
for p in Path('templates').rglob('*.html'):
 name=p.as_posix().removeprefix('templates/')
 if '{% extends' not in p.read_text(encoding='utf-8-sig'):continue
 role='admin' if name.startswith(('admin/','discovery/')) else 'business_owner' if name.startswith(('owner/','catalog/dashboard','sites/editor','ecosystem/business')) or name=='intelligence.html' else 'user'
 url='/admin/dashboard' if role=='admin' else '/owner/dashboard' if role=='business_owner' else '/auth/profile'
 if name in ['index.html','offers.html','business_plans.html','login.html','register.html','auth/recovery.html','detail.html']:continue
 try:
  with app.test_request_context(url):
   session['user']={'id':1,'role':role,'username':'Maria','profile':{'name':'María Sandoval','email':'maria@example.com'}};session['role']=role
   with patch('database.repository.PostgresDocumentRepository.all',return_value=[]),patch('database.repository.PostgresDocumentRepository.get_by_id',return_value=None):
    html=render_template(name,**args)
  slug=name.replace('/','-').removesuffix('.html');(out/(slug+'.html')).write_text(html,encoding='utf-8');views.append(slug)
 except Exception as e:print(name,type(e).__name__,str(e)[:160])
(out/'views.json').write_text(json.dumps(views));print('Rendered',len(views))
