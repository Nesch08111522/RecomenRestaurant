import importlib
from io import BytesIO
from copy import deepcopy
import pytest
from PIL import Image
from app import create_app
from models.user import UserModel
from models.restaurant import RestaurantModel


def module():
    assert importlib.util.find_spec('models.business_site') is not None, 'Falta portal empresarial Fase 4'
    return importlib.import_module('models.business_site')


def test_default_site_uses_real_business_not_fake_claims():
    site=module().default_site({'id':7,'name':'Café Norte','description':'Cocina propia'})
    assert site['name']=='Café Norte'
    assert site['slug']=='cafe-norte-7'
    assert site['gallery']==[] and site['videos']==[]
    assert 'rating' not in site


@pytest.mark.parametrize('patch',[{'primary_color':'red; background:url(javascript:bad)'},
    {'slug':'../../admin'},{'template':'<script>'},{'social':{'instagram':'javascript:alert(1)'}},
    {'gallery':['http://127.0.0.1/image.jpg']},{'videos':['https://example.com/script.html']}])
def test_unsafe_brand_settings_rejected(patch):
    with pytest.raises(ValueError):
        module().normalize_site(patch,module().default_site({'id':7,'name':'Café'}))


def test_brand_settings_never_change_owner_or_publish_from_client():
    row=module().normalize_site({'name':'Café Nuevo','owner_id':999,'published':True},module().default_site({'id':7,'name':'Café'}))
    assert row['name']=='Café Nuevo'
    assert 'owner_id' not in row and 'published' not in row


def test_logo_is_reencoded_and_extracts_palette():
    buffer=BytesIO();Image.new('RGB',(80,80),'#125c40').save(buffer,format='PNG')
    result=module().process_logo(buffer.getvalue())
    assert result['mime']=='image/png'
    assert result['palette'][0]=='#125c40'
    with pytest.raises(ValueError):
        module().process_logo(b'<svg onload="alert(1)"></svg>')


def test_sites_api_rejects_other_owner(monkeypatch):
    module()
    user={'id':10,'role':'business_owner','username':'owner','profile':{}}
    monkeypatch.setattr(UserModel,'get_by_id',lambda uid:deepcopy(user))
    monkeypatch.setattr(RestaurantModel,'get_by_id',lambda rid:{'id':rid,'owner_id':11,'name':'Otro negocio'})
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32,'WTF_CSRF_ENABLED':False}).test_client()
    with client.session_transaction() as s:s['user_id']=10
    assert client.put('/owner/api/sites/7',json={'name':'Intrusión'}).status_code==404


def test_draft_page_is_not_public(monkeypatch):
    model=module()
    monkeypatch.setattr(model.SiteModel,'all',lambda:[{'id':1,'restaurant_id':7,'draft':{'slug':'cafe'},'published':None}])
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32}).test_client()
    assert client.get('/negocio/cafe').status_code==404
