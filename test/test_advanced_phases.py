from datetime import date,timedelta
from uuid import uuid4
from unittest.mock import patch
import pytest
from app import create_app
from models.user import UserModel
from models.restaurant import RestaurantModel
from database.repository import PostgresDocumentRepository as Repo
from analytics.intelligence import report
from logic.immersive import model_metadata
from logic.market import MarketError
from werkzeug.security import generate_password_hash,check_password_hash


def test_forecast_requires_evidence_and_ignores_refunds():
    end=date(2026,11,18);start=end-timedelta(days=29)
    assert report([],[],start,end)['forecast']==[]
    orders=[{'uid':1,'total':2500,'state':'Entregado','paid':True,'created':(end-timedelta(days=i)).isoformat()+'T12:00:00-05:00','lines':[{'name':'Plato','qty':1,'cost':1000}]} for i in range(56)]
    result=report(orders+[dict(orders[0],refunded=True)],[],start,end)
    assert result['orders']==30 and result['income']==75000 and result['margin']==45000
    assert len(result['forecast'])==7 and all(f['orders']==1 for f in result['forecast'])
    orders[0]['lines'][0]['cost']=None
    assert report(orders,[],start,end)['margin'] is None

@pytest.mark.parametrize('payload',[{'width_cm':'NaN','height_cm':10,'depth_cm':10},{'width_cm':10},{'width_cm':-1,'height_cm':2,'depth_cm':3}])
def test_dimensions_validate_finite_complete_values(payload):
    with pytest.raises(MarketError):model_metadata(payload)

def test_owner_cannot_self_verify_scale():
    value=model_metadata({'width_cm':20,'height_cm':5,'depth_cm':20,'portion_g':250,'scale_verified':True})
    assert not value['scale_verified'] and value['width_cm']==20

@pytest.fixture
def setup(test_database):
    app=create_app({'TESTING':True,'SECRET_KEY':uuid4().hex,'WTF_CSRF_ENABLED':False})
    accounts={};clients={}
    for role in ('user','business_owner','admin'):
        account=UserModel.create({'username':uuid4().hex,'role':role,'password':generate_password_hash('Password123'),'profile':{'email':'test@example.test','phone':'+51976399537'}})
        accounts[role]=account;clients[role]=app.test_client()
        with clients[role].session_transaction() as state:state['user_id']=account['id']
    shop=RestaurantModel.create({'name':'Cocina de prueba','owner_id':accounts['business_owner']['id'],'verified':True})
    other=RestaurantModel.create({'name':'Otra cocina','owner_id':99999999,'verified':True})
    return app,accounts,clients,shop,other


def test_otp_single_use_and_session_revocation(setup,monkeypatch):
    from utils import password_codes as codes
    app,accounts,_,_,_=setup;user=accounts['user'];sent=[]
    monkeypatch.setattr(codes,'configured',lambda c:True)
    monkeypatch.setattr(codes,'send_code',lambda channel,to,code,identifier:sent.append((to,code)))
    with app.test_request_context():
        challenge=codes.issue(user['username'],'email')
        assert codes.issue(user['username'],'email',challenge)==challenge
        assert len(sent)==1
        state=Repo.get_by_id(codes.COLLECTION,user['id'])
        assert sent[0][0]=='test@example.test' and sent[0][1] not in str(state)
        assert not codes.consume(user['username'],challenge,'111111' if sent[0][1]!='111111' else '222222','NewPassword456')
        assert codes.consume(user['username'],challenge,sent[0][1],'NewPassword456')
        assert not codes.consume(user['username'],challenge,sent[0][1],'AnotherPassword789')
        assert UserModel.get_by_id(user['id'])['auth_epoch']==1
        assert check_password_hash(UserModel.get_by_id(user['id'])['password'],'NewPassword456')


def test_otp_attempt_limit_expiry_and_destination_binding(setup,monkeypatch):
    from utils import password_codes as codes
    app,accounts,_,_,_=setup;user=accounts['user'];sent=[]
    monkeypatch.setattr(codes,'configured',lambda c:True)
    monkeypatch.setattr(codes,'send_code',lambda ch,to,code,i:sent.append(code))
    with app.test_request_context():
        challenge=codes.issue(user['username'],'sms')
        wrong='000000' if sent[0]!='000000' else '999999'
        for i in range(5):assert not codes.consume(user['username'],challenge,wrong,'NewPassword456')
        assert not codes.consume(user['username'],challenge,sent[0],'NewPassword456')
        Repo.update(codes.COLLECTION,user['id'],{'attempts':0,'until':0})
        assert not codes.consume(user['username'],challenge,sent[0],'NewPassword456')
        Repo.update(codes.COLLECTION,user['id'],{'until':99999999999})
        UserModel.update(user['id'],{'profile':{'phone':'+51999999999'}})
        assert not codes.consume(user['username'],challenge,sent[0],'NewPassword456')


def test_otp_failed_delivery_never_activates(setup,monkeypatch):
    from utils import password_codes as codes
    from utils.security_delivery import DeliveryUnavailable
    app,accounts,_,_,_=setup;user=accounts['user']
    monkeypatch.setattr(codes,'configured',lambda c:True)
    monkeypatch.setattr(codes,'send_code',lambda *a:(_ for _ in ()).throw(DeliveryUnavailable()))
    with app.test_request_context():
        codes.issue(user['username'],'email')
        assert not Repo.get_by_id(codes.COLLECTION,user['id'])['delivered']


def test_scoped_intelligence_and_privileged_pages(setup):
    app,accounts,clients,shop,other=setup
    for rid,total in [(shop['id'],1200),(other['id'],999999)]:
        Repo.create('market_orders',{'rid':rid,'uid':accounts['user']['id'],'total':total,'state':'Entregado','paid':True,'created':date.today().isoformat()+'T01:00:00-05:00','slot':date.today().isoformat()+'T12:00:00-05:00','lines':[]})
    owner=clients['business_owner'];response=owner.get('/api/inteligencia?rid='+str(shop['id']))
    assert response.status_code==200 and response.json['report']['income']==1200
    assert owner.get('/api/inteligencia?rid='+str(other['id'])).status_code==404
    assert clients['user'].get('/inteligencia').status_code==403
    assert clients['user'].get('/admin/confianza').status_code==403
    assert owner.get('/admin/confianza').status_code==403
    assert clients['admin'].get('/admin/confianza').status_code==200
    assert owner.get('/inteligencia').status_code==200
    assert clients['user'].get('/copilot').status_code==200


def test_copilot_confirmation_actor_scope_and_replay(setup):
    _,_,clients,shop,other=setup;owner=clients['business_owner']
    assert clients['user'].post('/api/copilot/actions',json={'action':'restaurant_promo','rid':shop['id'],'text':'Cena especial'}).status_code==403
    assert owner.post('/api/copilot/actions',json={'action':'restaurant_promo','rid':other['id'],'text':'Cena especial'}).status_code==404
    response=owner.post('/api/copilot/actions',json={'action':'restaurant_promo','rid':shop['id'],'text':'Cena especial'})
    assert response.status_code==200
    proposal=response.json;url='/api/copilot/actions/'+str(proposal['id'])+'/confirm'
    assert RestaurantModel.get_by_id(shop['id']).get('promo') is None
    assert owner.post(url,json={'token':proposal['token'],'confirm':False}).status_code==400
    assert clients['admin'].post(url,json={'token':proposal['token'],'confirm':True}).status_code==404
    assert owner.post(url,json={'token':proposal['token'],'confirm':True}).status_code==200
    assert RestaurantModel.get_by_id(shop['id'])['promo']=='Cena especial'
    assert owner.post(url,json={'token':proposal['token'],'confirm':True}).status_code==409


def test_new_routes_keep_csrf():
    client=create_app({'TESTING':True,'SECRET_KEY':uuid4().hex}).test_client()
    for path in ['/api/copilot/chat','/api/copilot/actions','/api/copilot/actions/1/confirm','/auth/recuperar']:
        assert client.post(path,json={}).status_code==400


def test_model_visibility_review_and_metadata(setup):
    import base64
    app,accounts,clients,shop,_=setup
    model=Repo.create('dish_models',{'rid':shop['id'],'data':base64.b64encode(b'test-glb').decode(),'width_cm':20,'height_cm':4,'depth_cm':20,'scale_verified':False})
    offer=Repo.create('market_offers',{'rid':shop['id'],'model_id':model['id'],'review_state':'pending'})
    path='/experiencias/modelos/'+str(offer['id'])
    assert app.test_client().get(path).status_code==404
    assert clients['admin'].get(path+'/metadata').status_code==200
    review={'offer':offer['id'],'state':'approved','note':'Escala contrastada con referencia','scale_verified':'on'}
    assert clients['business_owner'].post('/experiencias/publicaciones',data=review).status_code==403
    assert clients['admin'].post('/experiencias/publicaciones',data=review).status_code==302
    meta=app.test_client().get(path+'/metadata')
    assert meta.status_code==200 and meta.json['scale_verified']
    RestaurantModel.update(shop['id'],{'status':'suspended'})
    assert app.test_client().get(path).status_code==404


def test_email_contact_changes_require_current_password(setup):
    _,accounts,clients,_,_=setup
    response=clients['user'].patch('/api/platform/me/profile',json={'email':'other@example.test'})
    assert response.status_code==403
    response=clients['user'].patch('/api/platform/me/profile',json={'email':'other@example.test','current_password':'Password123'})
    assert response.status_code==200
    assert UserModel.get_by_id(accounts['user']['id'])['auth_epoch']==1


def test_moderated_media_can_be_hidden_without_deleting_evidence(setup):
    import base64
    app,accounts,clients,shop,_=setup
    media=Repo.create('business_site_media',{'owner_id':accounts['business_owner']['id'],'restaurant_id':shop['id'],'content':base64.b64encode(b'example').decode()})
    path='/admin/confianza/revisar/media/'+str(media['id'])
    assert clients['business_owner'].post(path,data={'decision':'rejected','note':'Contenido incompatible'}).status_code==403
    assert clients['admin'].post(path,data={'decision':'rejected','note':'Contenido incompatible'}).status_code==302
    assert Repo.get_by_id('business_site_media',media['id'])['content']
    assert app.test_client().get('/portal-media/'+str(media['id'])).status_code==404
    assert clients['admin'].get('/portal-media/'+str(media['id'])).status_code==200


def test_security_delivery_uses_fixed_provider_and_no_redirects(monkeypatch):
    from utils.security_delivery import send_code
    class Response:status_code=200
    calls=[]
    monkeypatch.setenv('RESEND_API_KEY','test-key')
    monkeypatch.setenv('SECURITY_FROM_EMAIL','security@example.test')
    monkeypatch.setenv('SECURITY_EMAIL_PROVIDER','resend')
    monkeypatch.setattr('utils.security_delivery.requests.post',lambda *a,**kw:calls.append((a,kw)) or Response())
    send_code('email','account@example.test','123456','test-delivery-id')
    assert calls[0][0][0]=='https://api.resend.com/emails'
    assert calls[0][1]['json']['to']==['account@example.test']
    assert calls[0][1]['allow_redirects'] is False
    assert calls[0][1]['headers']['Idempotency-Key']=='test-delivery-id'


def test_copilot_rechecks_promotion_before_confirming(setup):
    _,_,clients,shop,_=setup;owner=clients['business_owner']
    response=owner.post('/api/copilot/actions',json={'action':'restaurant_promo','rid':shop['id'],'text':'Cena especial'})
    proposal=response.json
    RestaurantModel.update(shop['id'],{'promo':'Almuerzo familiar'})
    response=owner.post('/api/copilot/actions/'+str(proposal['id'])+'/confirm',json={'confirm':True,'token':proposal['token']})
    assert response.status_code==409
    assert RestaurantModel.get_by_id(shop['id'])['promo']=='Almuerzo familiar'


def test_copilot_uses_server_scope_and_does_not_trust_client_context(setup,monkeypatch):
    from unittest.mock import MagicMock
    _,_,clients,shop,other=setup
    seen=[];config=MagicMock();config.model='test-model'
    def complete(**kwargs):
        seen.append(str(kwargs['messages']))
        response=MagicMock();response.choices[0].message.content='{"reply":"Consulta preparada con los datos de tu negocio."}'
        return response
    config.client.return_value.chat.completions.create.side_effect=complete
    monkeypatch.setattr('views.copilot.settings',lambda **kwargs:config)
    response=clients['business_owner'].post('/api/copilot/chat',json={'messages':[{'role':'user','content':'Muéstrame mis ventas'}],'restaurants':[{'id':other['id'],'name':'forged-private-context'}]})
    assert response.status_code==200
    assert 'forged-private-context' not in seen[0]
    assert other['name'] not in seen[0]
    assert shop['name'] in seen[0]
