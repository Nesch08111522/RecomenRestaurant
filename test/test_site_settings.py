from unittest.mock import patch
import pytest
from models.site_settings import DEFAULTS, validate_settings

@pytest.mark.parametrize("url", ["javascript:alert(1)","https://instagram.com.evil.test/x","https://user@instagram.com/x","http://instagram.com/x","https://instagram.com:bad/x"])
def test_social_links_require_official_https(url):
    with pytest.raises(ValueError): validate_settings({**DEFAULTS,"instagram":url})

def test_settings_allowlist_and_phone():
    data=validate_settings({**DEFAULTS,"instagram":"https://www.instagram.com/example/","secret":"do-not-store"})
    assert "secret" not in data
    assert data["phone"]=="+51976399537"
    with pytest.raises(ValueError):validate_settings({**DEFAULTS,"phone":"tel:bad"})

@pytest.fixture
def app():
    from app import create_app
    return create_app({"TESTING":True,"SECRET_KEY":"site-test","WTF_CSRF_ENABLED":True})

def test_footer_roles_and_public_pages(app):
    from flask import session, render_template
    with patch('database.repository.PostgresDocumentRepository.all',return_value=[]), patch('database.repository.PostgresDocumentRepository.get_by_id',return_value=None):
        for role, path, visible in [("admin","/admin/configuracion-sitio",False),("business_owner","/owner/dashboard",False),("admin","/para-negocios",True),("guest","/auth/login",True),("guest","/informacion/privacidad",True)]:
            with app.test_request_context(path):
                if role!="guest":session['user']={"id":1,"role":role,"username":"Test","profile":{}}
                html=render_template('partials/footer.html')
                assert ('sr-unified-footer' in html)==visible, (role,path)
                if visible:assert '+51976399537' in html and '/ofertas' in html and '/para-negocios' in html

def test_settings_access_and_csrf(app):
    with patch('views.admin.fresh_session_user',return_value=None):
        assert app.test_client().get('/admin/configuracion-sitio').status_code==302
    with patch('views.admin.fresh_session_user',return_value={"id":1,"role":"user"}):
        assert app.test_client().get('/admin/configuracion-sitio').status_code==302
    assert app.test_client().post('/admin/configuracion-sitio',data=DEFAULTS).status_code==400

def test_legal_pages_render(app):
    with patch('database.repository.PostgresDocumentRepository.all',return_value=[]),patch('database.repository.PostgresDocumentRepository.get_by_id',return_value=None):
        for section in ['privacidad','condiciones','tecnologia']:
            response=app.test_client().get('/informacion/'+section)
            assert response.status_code==200
            assert b'sr-unified-footer' in response.data


def test_settings_persist_only_validated_fields():
    from unittest.mock import MagicMock
    from models.site_settings import save_site_settings
    transaction=MagicMock()
    with patch('models.site_settings.document_transaction',return_value=transaction), patch('models.site_settings.Repo.update',return_value=False) as update, patch('models.site_settings.Repo.create') as create:
        save_site_settings({**DEFAULTS,"brand":"Mi sitio","secret":"not-stored"})
        assert update.call_args.args[0:2]==("site_settings",1)
        assert create.call_args.args[1]["brand"]=="Mi sitio"
        assert "secret" not in create.call_args.args[1]
    with patch('models.site_settings.Repo.update') as update:
        with pytest.raises(ValueError):save_site_settings({**DEFAULTS,"instagram":"javascript:alert(1)"})
        update.assert_not_called()
