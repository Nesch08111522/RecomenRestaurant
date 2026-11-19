"""Sitios de marca dentro de SmartResto: datos declarativos, nunca código generado."""
from __future__ import annotations
import base64
import re
import unicodedata
from copy import deepcopy
from io import BytesIO
from urllib.parse import urlsplit
from PIL import Image,ImageOps,UnidentifiedImageError
from models.base import DataModel
from models.restaurant import RestaurantModel
from database.repository import document_transaction
from logic.business_radar import now,validate_source_url
from utils.audit import record_event

TEMPLATES=('atelier','bistro','studio','commercial','minimal','promotional','fit','immersive')
TEXT_LIMITS={'name':160,'slug':70,'tagline':180,'description':2000,'history':5000,
             'seo_title':70,'seo_description':180,'delivery_info':700,'pickup_info':700}
NETWORKS={'instagram':'instagram.com','facebook':'facebook.com','youtube':'youtube.com',
          'tiktok':'tiktok.com','website':None}

class SiteModel(DataModel):
    collection='business_sites'

class BrandMediaModel(DataModel):
    collection='business_site_media'


def slugify(text):
    text=''.join(c for c in unicodedata.normalize('NFKD',str(text).lower()) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+','-',text).strip('-')[:60] or 'negocio'


def default_site(restaurant):
    return {'name':restaurant.get('name',''),'slug':f"{slugify(restaurant.get('name',''))}-{restaurant['id']}",
        'tagline':'','description':restaurant.get('description',''),'history':'',
        'primary_color':'#155c48','secondary_color':'#d9b985','template':'atelier',
        'on_primary':'#ffffff','logo':'','cover':'','gallery':[],'videos':[],
        'social':{},'specialties':[],'featured_dish_ids':[],'seo_title':restaurant.get('name',''),
        'seo_description':str(restaurant.get('description',''))[:160],
        'delivery_info':'','pickup_info':'','rights_confirmed':False}


def safe_media_url(value,video=False):
    value=str(value or '').strip()
    if not value:return ''
    if not video and re.fullmatch(r'/(?:static/[a-zA-Z0-9_./-]+|portal-media/[0-9]+)',value) and '..' not in value:
        return value
    p=validate_source_url(value)
    if video and not p.path.lower().endswith(('.mp4','.webm')):
        raise ValueError('Videos: usa una URL HTTPS directa MP4 o WebM autorizada')
    return value[:1200]


def normalize_site(patch,previous):
    if not isinstance(patch,dict):raise ValueError('Se requiere un objeto de configuración')
    result=deepcopy(previous)
    for key,limit in TEXT_LIMITS.items():
        if key in patch:
            if not isinstance(patch[key],str):raise ValueError(f'{key} debe ser texto')
            result[key]=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',patch[key]).strip()[:limit]
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',result['slug']) or not 3<=len(result['slug'])<=70:
        raise ValueError('La dirección debe tener 3–70 letras minúsculas, números o guiones')
    if not result['name']:raise ValueError('El negocio requiere nombre')
    for key in ('primary_color','secondary_color'):
        value=patch.get(key,result[key])
        if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):
            raise ValueError('Los colores deben tener formato hexadecimal #RRGGBB')
        result[key]=value.lower()
    rgb=[int(result['primary_color'][i:i+2],16)/255 for i in (1,3,5)]
    lum=sum(weight*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for weight,v in zip((.2126,.7152,.0722),rgb))
    result['on_primary']='#000000' if lum>.179 else '#ffffff'
    template=patch.get('template',result['template'])
    if template not in TEMPLATES:raise ValueError('Plantilla no disponible')
    result['template']=template
    for key in ('logo','cover'):
        if key in patch:result[key]=safe_media_url(patch[key])
    for key,limit in [('gallery',20),('videos',8),('specialties',12),('featured_dish_ids',12)]:
        if key not in patch:continue
        items=patch[key]
        if not isinstance(items,list) or len(items)>limit:raise ValueError(f'{key}: lista con máximo {limit} elementos')
        if key in ('gallery','videos'):
            result[key]=[safe_media_url(v,key=='videos') for v in items if v]
        elif key=='specialties':
            if any(not isinstance(v,str) for v in items):raise ValueError('Las especialidades deben ser texto')
            result[key]=[v.strip()[:160] for v in items if v.strip()]
        else:
            if any(not isinstance(v,int) or isinstance(v,bool) or v<1 for v in items):raise ValueError('Identificadores de platos inválidos')
            result[key]=list(dict.fromkeys(items))
    if 'social' in patch:
        if not isinstance(patch['social'],dict):raise ValueError('Redes sociales inválidas')
        social={}
        for network,url in patch['social'].items():
            if network not in NETWORKS or not url:continue
            p=validate_source_url(url);domain=NETWORKS[network]
            if domain and p.hostname!=domain and not p.hostname.endswith('.'+domain):
                raise ValueError(f'El enlace {network} debe pertenecer a su plataforma')
            social[network]=str(url)[:1200]
        result['social']=social
    if 'rights_confirmed' in patch:
        if not isinstance(patch['rights_confirmed'],bool):raise ValueError('Confirma derechos con un booleano')
        result['rights_confirmed']=patch['rights_confirmed']
    # Whitelist: ignore owner IDs, published state, arbitrary CSS/HTML and secrets.
    return {key:result[key] for key in default_site({'id':1,'name':'Base'})}


def process_logo(raw):
    if not raw or len(raw)>2*1024*1024:raise ValueError('El logo debe pesar hasta 2 MB')
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format not in {'PNG','JPEG','WEBP'} or image.width*image.height>8000000:
                raise ValueError('Usa un logo PNG, JPG o WebP de hasta 8 megapíxeles')
            clean=ImageOps.exif_transpose(image).convert('RGBA');clean.thumbnail((768,768))
            palette_image=clean.copy();palette_image.thumbnail((96,96))
            pixels=palette_image.tobytes()
            visible=[tuple(pixels[i:i+3]) for i in range(0,len(pixels),4) if pixels[i+3]>128]
            if not visible:raise ValueError('El logotipo no tiene píxeles visibles')
            sample=Image.new('RGB',(len(visible),1));sample.putdata(visible)
            quantized=sample.quantize(colors=5)
            colors=sorted(quantized.getcolors(),reverse=True);pal=quantized.getpalette()
            palette=['#%02x%02x%02x'%tuple(pal[index*3:index*3+3]) for _,index in colors]
            out=BytesIO();clean.save(out,format='PNG',optimize=True)
    except (OSError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValueError('No se pudo validar el logotipo raster') from None
    return {'content':base64.b64encode(out.getvalue()).decode(),'mime':'image/png','palette':palette}


def find_site(restaurant_id):
    return next((site for site in SiteModel.all() if site['restaurant_id']==restaurant_id),None)


def save_draft(restaurant,patch,actor):
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731041)')
        existing=find_site(restaurant['id'])
        draft=normalize_site(patch,(existing or {}).get('draft') or default_site(restaurant))
        for other in SiteModel.all():
            if other['restaurant_id']==restaurant['id']:continue
            if other['draft']['slug']==draft['slug'] or (other.get('published') or {}).get('slug')==draft['slug']:
                raise ValueError('Esta dirección ya pertenece a otro negocio')
        changes={'restaurant_id':restaurant['id'],'owner_id':actor,'draft':draft,'updated_at':now()}
        row=SiteModel.update(existing['id'],changes) if existing else SiteModel.create({**changes,'published':None})
        record_event('ADMIN_RESTAURANT_UPDATE',resource_type='business_site',resource_id=row['id'],metadata={'operation':'draft_save'})
        return row


def publish(restaurant,actor,enabled=True):
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731041)')
        row=find_site(restaurant['id'])
        if not row:raise ValueError('Guarda el borrador antes de publicar')
        if enabled and row.get('content_review_state')=='rejected':raise ValueError('El sitio fue retirado; solicita revisión administrativa antes de volver a publicar')
        if enabled:
            if not restaurant.get('verified') or restaurant.get('status') in {'suspended','archived','rejected'}:
                raise ValueError('El negocio requiere aprobación para publicar su sitio')
            if not row['draft'].get('rights_confirmed'):
                raise ValueError('Confirma derechos sobre textos, imágenes y videos antes de publicar')
            # Recheck slug under the same lock used for draft changes.
            for other in SiteModel.all():
                if other['id']!=row['id'] and ((other.get('published') or {}).get('slug')==row['draft']['slug'] or other['draft']['slug']==row['draft']['slug']):
                    raise ValueError('Dirección ocupada')
        previous=row.get('published')
        row=SiteModel.update(row['id'],{'published':deepcopy(row['draft']) if enabled else None,
            'published_at':now() if enabled else None,'revisions':(row.get('revisions',[])+([{'site':previous,'changed_at':now()}] if previous else []))[-20:]})
        record_event('ADMIN_RESTAURANT_UPDATE',resource_type='business_site',resource_id=row['id'],metadata={'operation':'publish' if enabled else 'unpublish'})
        return row


class SiteAIQuotaModel(DataModel):
    collection='business_site_ai_quota'


def consume_ai_quota(actor,clock=None):
    import time
    moment=time.time() if clock is None else clock
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731042)')
        row=next((r for r in SiteAIQuotaModel.all() if r['user_id']==actor),None)
        window=row['window_start'] if row and moment-row['window_start']<3600 else moment
        count=row['count'] if row and window==row['window_start'] else 0
        if row and moment-row['last_call']<20:
            raise ValueError('Espera veinte segundos entre solicitudes IA')
        if count>=20:raise ValueError('Alcanzaste veinte solicitudes IA en esta hora; intenta después')
        values={'user_id':actor,'window_start':window,'last_call':moment,'count':count+1}
        if row:SiteAIQuotaModel.update(row['id'],values)
        else:SiteAIQuotaModel.create(values)
