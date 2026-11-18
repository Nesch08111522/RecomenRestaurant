"""Radar gastronómico: normalización y evidencia; nunca publica ni ejecuta IA."""
from __future__ import annotations
import hashlib
import ipaddress
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin

KINDS = ('restaurante','cafeteria','panaderia','jugueria','pasteleria',
         'emprendimiento','cocina_oculta','tienda_comida','puesto_comida')
ALLOWED_FIELDS = {'name','business_type','address','district','phone','opening_hours',
                  'description','lat','lng','categories'}
SCHEMA_KINDS = {'Restaurant':'restaurante','CafeOrCoffeeShop':'cafeteria','Bakery':'panaderia',
                'FoodEstablishment':'emprendimiento','FastFoodRestaurant':'restaurante'}


def now():
    return datetime.now(timezone.utc).isoformat()


def clean(value, limit=240):
    return ' '.join(str(value or '').split())[:limit]


def normalized(value):
    text=unicodedata.normalize('NFKD',clean(value).lower())
    return re.sub(r'[^a-z0-9]+',' ',''.join(c for c in text if not unicodedata.combining(c))).strip()


def validate_source_url(value):
    try:
        p=urlsplit(str(value))
        host=p.hostname
        port=p.port
    except ValueError:
        raise ValueError('La URL no es válida') from None
    if p.scheme!='https' or not host or p.username or p.password or port not in (None,443):
        raise ValueError('Solo se permiten fuentes HTTPS sin credenciales ni puertos alternativos')
    if host.lower() in {'localhost','localhost.localdomain'} or host.lower().endswith(('.local','.internal')):
        raise ValueError('No se permiten servidores internos')
    try:
        address=ipaddress.ip_address(host)
        if not address.is_global or address.is_multicast or address.is_reserved:
            raise ValueError('No se permiten direcciones privadas o locales')
    except ValueError as error:
        if 'No se permiten' in str(error):
            raise
    return p


def reference(value,base=None):
    value=urljoin(base,str(value or '')) if base else str(value or '')
    try:
        validate_source_url(value)
        return value[:1200]
    except ValueError:
        return None


def kind_from_tags(tags):
    if tags.get('delivery')=='only':
        return 'cocina_oculta'
    if tags.get('drink:juice')=='yes' or tags.get('cuisine')=='juice':
        return 'jugueria'
    return {'cafe':'cafeteria','restaurant':'restaurante','fast_food':'restaurante',
            'food_court':'puesto_comida','bakery':'panaderia','pastry':'pasteleria',
            'convenience':'tienda_comida','deli':'tienda_comida','food':'tienda_comida'}.get(
                tags.get('amenity') or tags.get('shop'),'emprendimiento')


def candidate(data,source_key,source_url,license_name,quote_map=None):
    fetched=now()
    data={k:v for k,v in data.items() if k in ALLOWED_FIELDS and v not in (None,'',[])}
    missing=[key for key in ('name','business_type','address','phone','opening_hours') if key not in data]
    if 'lat' not in data or 'lng' not in data:
        missing.append('coordinates')
    # Coverage is a transparent heuristic, not a probability of truth or verification.
    score=round((6-len(missing))/6,2)
    return {'source_key':source_key,'source_url':source_url,'data':data,
            'status':'pending_review','missing_fields':missing,'confidence':score,
            'confidence_level':'high' if score>=0.8 else 'medium' if score>=0.5 else 'low',
            'confidence_method':'field-coverage-v1','owner_verified':False,
            'evidence':{k:{'source_url':source_url,'license':license_name,'retrieved_at':fetched,
                           'quote':clean((quote_map or {}).get(k,v),500),'verified':False} for k,v in data.items()},
            'channels':{},'menu_links':[],'media':[],'created_at':fetched,'last_seen_at':fetched}


def from_osm(element):
    tags=element.get('tags') or {}
    eid=int(element['id'])
    typ=element.get('type','node')
    if typ not in {'node','way','relation'}:
        raise ValueError('Tipo OSM inválido')
    coords=element.get('center') or element
    data={'name':clean(tags.get('name')),'business_type':kind_from_tags(tags),
          'address':clean(tags.get('addr:full') or ' '.join(filter(None,[tags.get('addr:street'),tags.get('addr:housenumber')]))),
          'district':clean(tags.get('addr:suburb') or tags.get('addr:city')),
          'phone':clean(tags.get('contact:phone') or tags.get('phone')),
          'opening_hours':clean(tags.get('opening_hours')),
          'categories':[clean(v,80) for v in tags.get('cuisine','').split(';') if v]}
    for key,source,minimum,maximum in [('lat','lat',-90,90),('lng','lon',-180,180)]:
        val=coords.get(source)
        if isinstance(val,(int,float)) and not isinstance(val,bool) and math.isfinite(val) and minimum<=val<=maximum:
            data[key]=val
    row=candidate(data,f'osm:{typ}:{eid}',f'https://www.openstreetmap.org/{typ}/{eid}','ODbL-1.0')
    for key,tags_keys in {'website':('contact:website','website'),'facebook':('contact:facebook',),
                          'instagram':('contact:instagram',)}.items():
        url=next((reference(tags.get(k)) for k in tags_keys if reference(tags.get(k))),None)
        if url:
            row['channels'][key]={'url':url,'verified':False,'source':'OpenStreetMap'}
    menu=reference(tags.get('website:menu') or tags.get('contact:menu'))
    if menu:
        row['menu_links']=[menu]
    image=reference(tags.get('image'))
    if image:
        row['media']=[{'url':image,'kind':'photo','status':'reference_only','license':'unknown'}]
    return row


def duplicate_reason(first,second):
    same_name=SequenceMatcher(None,normalized(first.get('name')),normalized(second.get('name'))).ratio()>=0.92
    if not first.get('name') or not second.get('name') or not same_name:
        return None
    if all(row.get(k) is not None for row in (first,second) for k in ('lat','lng')):
        lat1,lat2=map(math.radians,(float(first['lat']),float(second['lat'])))
        dlat=lat2-lat1
        dlon=math.radians(float(second['lng'])-float(first['lng']))
        distance=6371000*2*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))
        return 'Nombre coincidente y distancia menor a 75 m' if distance<=75 else None
    if first.get('address') and normalized(first['address'])==normalized(second.get('address')):
        return 'Nombre y dirección coincidentes'
    return None


def grounded_fields(text,fields):
    """Aceptar solo valores con cita literal; no inferir precios, ratings o alérgenos."""
    result={}
    if not isinstance(fields,list):
        return result
    for item in fields[:20]:
        if not isinstance(item,dict):
            continue
        field,quote,value=item.get('field'),item.get('quote'),item.get('value')
        if field not in ALLOWED_FIELDS or field in {'lat','lng','business_type','categories'}:
            continue
        if isinstance(value,str) and isinstance(quote,str) and len(quote)>=3 and quote in text and value in quote:
            result[field]=clean(value,1200 if field=='description' else 240)
    return result


class OfficialParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.images=[]; self.videos=[]; self.text=[]; self.jsonld=[]
        self.capture=False; self.buffer=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='script':
            self.capture=attrs.get('type','').lower()=='application/ld+json'; self.buffer=[]; self.skip+=1
        elif tag in {'style','noscript'}:
            self.skip+=1
        elif tag=='a' and attrs.get('href'):
            self.links.append(attrs['href'])
        elif tag=='img' and attrs.get('src'):
            self.images.append(attrs['src'])
        elif tag in {'video','source'} and attrs.get('src'):
            self.videos.append(attrs['src'])
    def handle_data(self,text):
        if self.capture:
            self.buffer.append(text)
        elif not self.skip:
            self.text.append(text)
    def handle_endtag(self,tag):
        if tag=='script':
            if self.capture:
                self.jsonld.append(''.join(self.buffer))
            self.capture=False
        if tag in {'script','style','noscript'}:
            self.skip=max(0,self.skip-1)


def from_official_html(html,url,rights,ai_fields=None):
    validate_source_url(url)
    if rights not in {'owner_permission','open_license'}:
        raise ValueError('La fuente requiere permiso de uso documentado')
    parser=OfficialParser(); parser.feed(html)
    text=clean(' '.join(parser.text),30000)
    data={}; quotes={}
    for raw in parser.jsonld[:10]:
        try:
            nodes=json.loads(raw)
        except (ValueError,TypeError):
            continue
        nodes=nodes if isinstance(nodes,list) else nodes.get('@graph',[nodes]) if isinstance(nodes,dict) else []
        for node in nodes[:30]:
            if not isinstance(node,dict):
                continue
            types=node.get('@type',[]); types=[types] if isinstance(types,str) else types
            kind=next((SCHEMA_KINDS[t] for t in types if t in SCHEMA_KINDS),None)
            if not kind:
                continue
            for key,schema in [('name','name'),('phone','telephone'),('description','description'),('opening_hours','openingHours')]:
                if isinstance(node.get(schema),str):
                    data[key]=clean(node[schema],1200 if key=='description' else 240); quotes[key]=data[key]
            data['business_type']=kind
            address=node.get('address')
            if isinstance(address,str):
                data['address']=clean(address)
            elif isinstance(address,dict):
                data['address']=clean(address.get('streetAddress')); data['district']=clean(address.get('addressLocality'))
            for key,value in grounded_fields(text,ai_fields or []).items():
                data.setdefault(key,value)
            break
    for key,value in grounded_fields(text,ai_fields or []).items():
        data.setdefault(key,value)
    row=candidate(data,'official:'+hashlib.sha256(url.encode()).hexdigest()[:24],url,rights,quotes)
    row['channels']['website']={'url':url,'verified':False,'source':'Página declarada por administrador'}
    row['menu_links']=list(dict.fromkeys(u for href in parser.links if re.search(r'menu|menú|carta|\.pdf(?:$|\?)',href,re.I) and (u:=reference(href,url))))[:10]
    row['media']=[{'url':u,'kind':kind,'status':'reference_only','license':'unknown'} for kind,links in [('photo',parser.images),('video',parser.videos)] for link in links[:8] if (u:=reference(link,url))]
    for link in parser.links:
        u=reference(link,url)
        if u:
            host=urlsplit(u).hostname or ''
            for network,domain in [('facebook','facebook.com'),('instagram','instagram.com'),('youtube','youtube.com'),('tiktok','tiktok.com')]:
                if host==domain or host.endswith('.'+domain):
                    row['channels'].setdefault(network,{'url':u,'verified':False,'source':url})
    row['content_hash']=hashlib.sha256(html.encode()).hexdigest()
    return row


def claim_transition(state,action):
    transitions={('invited','request'):'claim_pending',('claim_pending','reject'):'approved',
                 ('claim_pending','approve'):'claimed'}
    if (state,action) not in transitions:
        raise ValueError('Transición de reclamación no autorizada')
    return transitions[state,action]
