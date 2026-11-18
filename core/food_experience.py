"""Pure food presentation selection. No LLM, sessions, database, or external requests."""
from __future__ import annotations
from urllib.parse import urlsplit
import re, unicodedata

SCENES = {
 'lomo':('Lomo saltado','Cocina peruana · sabores con carácter'),
 'ceviche':('Ceviche premium','Frescura del norte · inspiración marina'),
 'dessert':('Café y un momento dulce','Una pausa para volver a empezar'),
 'signature':('Causa de autor','Una nueva forma de presentar tu cocina'),
}
VIEW_SCENE={'login':'lomo','register':'ceviche','recover':'dessert','business':'signature','home':'lomo'}

def text(value,limit=160):
    return ' '.join(str(value or '').split())[:limit]

def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',text(value,2000).lower()) if not unicodedata.combining(c))

def safe_media_url(value):
    value=text(value,1400)
    if not value or '\\' in value or any(ord(c)<32 for c in value):return ''
    if value.startswith('/') and not value.startswith('//'):return value
    parsed=urlsplit(value)
    if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password:return value
    return ''

def scene_for(value):
    value=folded(value)
    if any(s in value for s in ['ceviche','marino','pescado','marisco']):return 'ceviche'
    if any(s in value for s in ['cafe','postre','dulce','flan','chocolate']):return 'dessert'
    if any(s in value for s in ['causa','vegetal','ensalada','vegano','vegetariano']):return 'signature'
    return 'lomo'

def editorial(scene):
    name,subtitle=SCENES[scene]
    return {'id':f'editorial-{scene}','name':name,'subtitle':subtitle,'image':f'/static/images/auth/{scene}.webp',
            'model':f'/static/models/auth/{scene}.glb','model_kind':'reference','scene':scene,'source':'editorial',
            'caption':'Inspiración gastronómica · representación 3D de referencia','href':'/mercado'}

def _list(value):return value if isinstance(value,list) else []

def _eligible(dish,restrictions):
    description=folded(' '.join([text(dish.get('name')),text(dish.get('description')),*map(str,_list(dish.get('ingredients'))),*map(str,_list(dish.get('allergens')))]))
    diets={folded(x) for x in _list(dish.get('dietary_info'))+_list(dish.get('diets'))}
    for restriction in restrictions:
        r=folded(restriction)
        if r.startswith('alergia '):
            allergen=r.removeprefix('alergia ')
            # Unknown ingredients/allergens are not silently considered safe.
            if not dish.get('ingredients') and not isinstance(dish.get('allergens'),list):return False
            if allergen in description:return False
        elif r in ('vegano','vegetariano','sin gluten','celiaco'):
            required='sin gluten' if r=='celiaco' else r
            if required not in diets and not(required=='vegetariano' and 'vegano' in diets):return False
    return True

def select_food_scene(view,profile,dishes,favorite_restaurants=(),favorite_dishes=()):
    profile=profile if isinstance(profile,dict) else {}
    restrictions=_list(profile.get('restrictions'))[:30]
    preferences=[folded(p) for p in _list(profile.get('preferences'))[:30] if isinstance(p,str) and p.strip()]
    rest_ids=set(favorite_restaurants);dish_ids=set(favorite_dishes)
    candidates=[]
    for dish in dishes[:1000]:
        if not isinstance(dish,dict) or dish.get('id') is None or dish.get('is_available') is False or dish.get('availability') in ('out_of_stock','unavailable','draft'):
            continue
        if not _eligible(dish,restrictions):continue
        haystack=folded(' '.join([text(dish.get('name')),text(dish.get('category')),*map(str,_list(dish.get('tags'))),*map(str,_list(dish.get('ingredients')))]))
        score=(50 if dish.get('id') in dish_ids else 0)+(20 if dish.get('restaurant_id') in rest_ids else 0)+sum(10 for p in preferences if p in haystack)
        scene=scene_for(haystack)
        if scene==VIEW_SCENE.get(view,'lomo'):score+=1
        images=_list(dish.get('images'))
        image=next((safe_media_url(x) for x in images if safe_media_url(x)),safe_media_url(dish.get('image')))
        model=safe_media_url(dish.get('model_url'))
        item={'id':f'dish-{dish["id"]}','name':text(dish.get('name')) or 'Plato del catálogo','subtitle':text(dish.get('business')) or 'Del catálogo gastronómico',
              'image':image or f'/static/images/auth/{scene}.webp','model':model or f'/static/models/auth/{scene}.glb',
              'model_kind':'catalog' if model else 'reference','scene':scene,'source':'catalog',
              'caption':'Modelo publicado por el negocio' if model else 'Fotografía del catálogo · 3D de referencia' if image else 'Representación de referencia · consulta el plato real',
              'href':f'/mercado/plato/{dish["id"]}'}
        candidates.append((score,text(dish.get('name')),item))
    candidates.sort(key=lambda row:(-row[0],row[1]))
    if candidates:return [row[2] for row in candidates[:3]]
    if restrictions:return []
    primary=VIEW_SCENE.get(view,'lomo')
    if preferences:primary=scene_for(' '.join(preferences))
    order=[primary]+[s for s in SCENES if s!=primary]
    return [editorial(s) for s in order[:3]]

def normalize_business_details(source):
    result={key:text(source.get(key),120 if key=='business_name' else 80 if key=='district' else 30) for key in ['business_name','ruc','phone','district']}
    if result['ruc'] and not re.fullmatch(r'\d{11}',result['ruc']):raise ValueError('El RUC debe tener 11 dígitos, cuando corresponda.')
    if result['phone'] and not re.fullmatch(r'\+?[\d ()-]{7,22}',result['phone']):raise ValueError('Revisa el número de teléfono del negocio.')
    return {k:v for k,v in result.items() if v}
