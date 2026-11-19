"""Auth presentation/API contracts; no operational database, accounts or provider calls."""
from contextlib import nullcontext
from pathlib import Path
from threading import Thread
import re
import pytest
from flask import g
from werkzeug.serving import make_server
from app import create_app
from models.category import CategoryModel

@pytest.fixture
def authapp(monkeypatch):
    monkeypatch.setattr(CategoryModel,'all',staticmethod(lambda:[]))
    return create_app({'TESTING':True,'SECRET_KEY':'auth-visual-test-only','TEMPLATES_AUTO_RELOAD':True})

@pytest.mark.parametrize('path',['/auth/login','/auth/register','/auth/recuperar'])
def test_auth_views_share_real_scene_and_preserve_csrf(authapp,path):
    response=authapp.test_client().get(path)
    assert response.status_code==200
    html=response.data.decode()
    assert 'data-food-experience-api=' in html
    assert '/static/js/auth/food-scene.js' in html
    assert 'name="csrf_token"' in html
    assert 'name="password"' in html
    assert 'ax-form' in html
    if 'recuperar' in path: assert 'name="code"' in html

def test_login_remember_is_explicit_not_forced(authapp,monkeypatch):
    import views.auth as module
    monkeypatch.setattr(module.protection,'allow_attempt',lambda *args:True)
    monkeypatch.setattr(module.protection,'authenticate',lambda *args:{'id':99,'username':'visual','role':'user','profile':{}})
    for remembered in (False,True):
        c=authapp.test_client();html=c.get('/auth/login').data.decode()
        token=re.search(r'name="csrf_token" value="([^"]+)"',html)[1]
        r=c.post('/auth/login',data={'username':'visual','password':'Password123','csrf_token':token,**({'remember':'on'} if remembered else {})})
        assert r.status_code==302
        with c.session_transaction() as s: assert s.permanent is remembered

def test_scene_api_guests_use_editorial_no_private_profile(authapp):
    c=authapp.test_client();r=c.get('/api/food-experience?view=login&user_id=99')
    assert r.status_code==200
    data=r.get_json()
    assert not data['personalized']
    assert data['items'][0]['scene']=='lomo'
    assert 'profile' not in data and 'preferences' not in data
    assert 'no-store' in r.headers['Cache-Control']

def test_registration_confirmation_rejected_before_storage(authapp):
    c=authapp.test_client();html=c.get('/auth/register').data.decode();token=re.search(r'name="csrf_token" value="([^"]+)"',html)[1]
    r=c.post('/auth/register',data={'username':'visual','name':'Visual','email':'v@example.test','password':'Password123','password_confirm':'different123','csrf_token':token})
    assert r.status_code==200
    assert 'no coinciden' in r.data.decode()

@pytest.fixture(scope='module')
def auth_origin():
    original=CategoryModel.all
    CategoryModel.all=staticmethod(lambda:[])
    app=create_app({'TESTING':True,'SECRET_KEY':'visual-auth','TEMPLATES_AUTO_RELOAD':True})
    server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();thread.join(5);CategoryModel.all=original

@pytest.fixture(scope='module')
def auth_browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b=p.chromium.launch(channel='msedge',headless=True)
        yield b
        b.close()

@pytest.fixture
def auth_page(auth_browser,auth_origin):
    context=auth_browser.new_context(reduced_motion='reduce')
    page=context.new_page()
    def route(r):
        if '/api/food-experience' in r.request.url:
            r.fulfill(json={'personalized':False,'selection':'editorial','items':[]})
        elif r.request.url.startswith(auth_origin):r.continue_()
        else:r.abort()
    page.route('**/*',route)
    yield page
    context.close()

@pytest.mark.parametrize('width',[320,375,480,640,768,1024,1280,1440,1920])
@pytest.mark.parametrize('path',['/auth/login','/auth/register','/auth/recuperar'])
def test_auth_adaptive_grid_and_panel_do_not_overflow(auth_page,auth_origin,width,path):
    page=auth_page;page.set_viewport_size({'width':width,'height':1000});page.goto(auth_origin+path)
    page.wait_for_timeout(250)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    visual=page.locator('.ax-visual').bounding_box();forms=page.locator('.ax-forms').bounding_box()
    if width>=1024:
        assert visual['x']<forms['x']
        assert .38<=visual['width']/(visual['width']+forms['width'])<=.46
    if width<=900:assert visual is None  # Compact auth intentionally prioritizes the form.
    for control in page.locator('.ax-pane:not([inert]) .ax-control').all():
        box=control.bounding_box();assert box['width']>=100 and box['x']+box['width']<=width+1

def test_business_role_fields_preserve_values(auth_page,auth_origin):
    p=auth_page;p.set_viewport_size({'width':375,'height':950});p.goto(auth_origin+'/auth/register?role=business_owner')
    p.locator('#ax-reg-name').fill('María Test')
    p.locator('#ax-business-name').fill('Mesa de María')
    p.locator('#ax-reg-role').select_option('user')
    assert not p.locator('#ax-business-fields').is_visible()
    p.locator('#ax-reg-role').select_option('business_owner')
    assert p.locator('#ax-business-name').input_value()=='Mesa de María'
    assert p.locator('#ax-reg-name').input_value()=='María Test'


def test_password_visibility_and_two_factor_are_accessible(auth_page,auth_origin):
    p=auth_page;p.goto(auth_origin+'/auth/login')
    p.locator('#ax-login-password').fill('Password123');p.get_by_role('button',name='Mostrar contraseña',exact=True).first.click()
    assert p.locator('#ax-login-password').get_attribute('type')=='text'
    p.locator('.ax-totp summary').click();assert p.locator('#ax-login-otp').is_visible()

def test_switch_keeps_next_and_never_stores_credentials(auth_page,auth_origin):
    p=auth_page;p.goto(auth_origin+'/auth/login?next=/market/carrito')
    p.locator('#ax-login-username').fill('visual')
    p.locator('[data-ax-switch="register"]').click();p.wait_for_url('**/auth/register?**')
    p.locator('[data-ax-switch="login"]').click();p.wait_for_url('**/auth/login?**')
    assert 'next=' in p.url
    assert p.locator('#ax-login-username').input_value()==''
    assert p.evaluate("!Object.entries(localStorage).some(([k,v]) => /password|credential/i.test(k) || v.includes('Password123'))")
