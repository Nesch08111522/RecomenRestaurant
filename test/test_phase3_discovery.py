import importlib
from copy import deepcopy
import pytest
from app import create_app
from models.user import UserModel


def engine():
    spec=importlib.util.find_spec('logic.business_radar')
    assert spec is not None, 'Falta el motor de radar gastronómico de Fase 3'
    return importlib.import_module('logic.business_radar')


def test_osm_candidate_preserves_unknowns_and_source():
    module=engine()
    row=module.from_osm({'type':'node','id':123,'lat':-8.11,'lon':-79.02,
        'tags':{'name':'Café Norte','amenity':'cafe','cuisine':'coffee_shop;peruvian',
                'website':'https://cafenorte.example','opening_hours':'Mo-Sa 08:00-20:00'}})
    assert row['data']['business_type']=='cafeteria'
    assert row['source_key']=='osm:node:123'
    assert row['status']=='pending_review'
    assert 'avg_price' not in row['data'] and 'rating' not in row['data']
    assert row['evidence']['name']['license']=='ODbL-1.0'
    assert row['evidence']['name']['source_url']=='https://www.openstreetmap.org/node/123'
    assert row['channels']['website']['verified'] is False
    assert 'address' in row['missing_fields']


@pytest.mark.parametrize('tags,kind', [({'shop':'bakery'},'panaderia'),
    ({'shop':'pastry'},'pasteleria'),({'amenity':'restaurant'},'restaurante'),
    ({'amenity':'fast_food','delivery':'only'},'cocina_oculta'),
    ({'shop':'convenience'},'tienda_comida')])
def test_food_business_types(tags,kind):
    assert engine().from_osm({'type':'node','id':1,'tags':{'name':'Local',**tags}})['data']['business_type']==kind


def test_duplicate_does_not_merge_separate_branches():
    mod=engine()
    first={'name':'Café Norte','lat':-8.11,'lng':-79.02,'address':'Calle 1'}
    assert mod.duplicate_reason(first,dict(first)) is not None
    assert mod.duplicate_reason(first,{**first,'lat':-8.15,'address':'Calle 100'}) is None


@pytest.mark.parametrize('url',['http://example.com','https://127.0.0.1/','https://[::1]/',
    'https://user:password@example.com','https://example.com:8000','javascript:alert(1)'])
def test_unsafe_source_url_rejected(url):
    with pytest.raises(ValueError):
        engine().validate_source_url(url)


def test_evidence_rejects_invented_ai_prices():
    mod=engine()
    extracted=mod.grounded_fields('Nombre: Café Norte. Dirección: Calle 1.',[
        {'field':'name','value':'Café Norte','quote':'Nombre: Café Norte'},
        {'field':'avg_price','value':25,'quote':'Nombre: Café Norte'},
        {'field':'phone','value':'999999999','quote':'Un teléfono inventado'}])
    assert extracted=={'name':'Café Norte'}


def test_official_page_detects_menu_and_media_without_copying_assets():
    mod=engine()
    html='''<html><a href="/carta.pdf">Carta</a><img src="/foto.jpg"><video src="/presentacion.mp4"></video>
    <script type="application/ld+json">{"@type":"Restaurant","name":"Café Norte","address":"Calle 1"}</script></html>'''
    row=mod.from_official_html(html,'https://cafenorte.example','owner_permission')
    assert row['data']['name']=='Café Norte'
    assert row['menu_links']==['https://cafenorte.example/carta.pdf']
    assert len(row['media'])==2
    assert all(asset['status']=='reference_only' for asset in row['media'])


def test_radar_routes_exist_and_deny_guest_and_diner(monkeypatch):
    app=create_app({'TESTING':True,'SECRET_KEY':'x'*32,'WTF_CSRF_ENABLED':False})
    guest=app.test_client()
    assert guest.get('/admin/api/discovery/candidates').status_code==401
    account={'id':5,'username':'diner','role':'user','profile':{}}
    monkeypatch.setattr(UserModel,'get_by_id',lambda uid:deepcopy(account))
    with guest.session_transaction() as session:
        session['user_id']=5
    assert guest.get('/admin/api/discovery/candidates').status_code==403
    assert guest.post('/admin/api/discovery/runs',json={'source':'osm'}).status_code==403


def test_claim_invitation_is_not_business_ownership():
    module=engine()
    assert module.claim_transition('invited','request')=='claim_pending'
    with pytest.raises(ValueError):
        module.claim_transition('pending_review','request')
    assert module.claim_transition('claim_pending','reject')=='approved'
