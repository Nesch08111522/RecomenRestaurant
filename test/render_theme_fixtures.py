from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import re
from jinja2 import Environment,FileSystemLoader,ChainableUndefined

root=Path(__file__).resolve().parents[1]
env=Environment(loader=FileSystemLoader(root/'templates'),undefined=ChainableUndefined,autoescape=True)
env.filters['soles']=lambda v:f'S/ {v or 0:.2f}'
env.globals.update(url_for=lambda endpoint,**kw:'/static/'+kw['filename'] if endpoint=='static' else '/'+endpoint.replace('.','/'),csrf_token=lambda:'fixture',get_flashed_messages=lambda **kw:[],APP_NAME='SmartResto',MONEDA='S/',now=datetime.now)
session={'user':{'id':1,'role':'admin','name':'Control de tema','username':'control'},'user_id':1}
common=dict(session=session,request=SimpleNamespace(endpoint='admin.dashboard',blueprint='admin',path='/admin',args={}),start=datetime(2026,11,1),end=datetime(2026,11,18),report=dict(income=3250,count=24,completed=20,active_clients=12),categories=[dict(id=1,name='Restaurantes')],cid='',total_users=40,owners=10,published=8,pending=[],claims=[],signals=[],unsettled=[],charts=[('Ventas',[('Lunes',4),('Martes',8)])],events=[],site=dict(name='Mesa del bosque',slug='mesa',template='atelier',tagline='Sabores para compartir',description='Cocina con identidad y productos locales.',specialties=['Cocina peruana','Productos locales'],featured_dish_ids=[1],primary_color='#ffffff',secondary_color='#ffff00'),restaurant=dict(id=1,name='Mesa del bosque',description='Una mesa para todos',district='Trujillo',address='Calle principal 123',open_time='12:00',close_time='22:00',promo='Especial de temporada'),dishes=[dict(id=1,name='Arroz de la casa',description='Preparado al momento',price=25)],reviews=[dict(rating=5,comment='Excelente experiencia')],branches=[],canonical='',schema={},share_image='',preview=False)
out=root/'outputs/theme-qa';out.mkdir(parents=True,exist_ok=True)
common.update(total_restaurants=8,total_favorites=20,total_reviews=12,avg_rating=4.5,users=[dict(id=1,username='control',role='admin',profile=dict(name='Control',email='control@example.test',preferences=[]))],restaurants=[common['restaurant']])
common['request'].form={}
common.update(profile={},stats={},filters={},catalog={},pages=1,number=1,selected_date_iso='2026-11-18')
common.update(today_date_iso='2026-11-18',selected_date_label='18 de noviembre',meal_times=[])
for name,template in [('admin','admin/dashboard.html'),('public','sites/public.html'),('editor','sites/editor.html'),('analytics','admin/analytics.html'),('categories','admin/categories.html'),('users','admin/users.html'),('restaurant-form','admin/restaurant_form.html'),('catalog','catalog/dashboard.html'),('login','login.html'),('register','register.html'),('market','market/browse.html'),('menu','owner/menu_management.html')]:
 html=env.get_template(template).render(**common)
 # Isolate presentation from application API calls and third-party requests.
 html=re.sub(r'<script\b[^>]*src="([^"]+)"[^>]*></script>',lambda m:m[0] if '/js/theme.js' in m[1] else '',html)
 html=re.sub(r'<link\b[^>]*href="https:[^"]+"[^>]*>','',html)
 (out/f'{name}.html').write_text(html,encoding='utf-8')
print('Rendered real admin, public and editor templates with in-memory fixtures.')
