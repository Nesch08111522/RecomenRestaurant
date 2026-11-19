"""Real profile route and templates, offline DB and browser resources."""
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def profile_app(monkeypatch):
    import dotenv
    import psycopg
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: None)

    def blocked(*a, **k):
        pytest.fail('Live database access attempted')

    monkeypatch.setattr(psycopg, 'connect', blocked)
    import database.repository as repository
    monkeypatch.setattr(repository, 'connection', blocked)
    from app import create_app
    from models.user import UserModel
    from models.restaurant import RestaurantModel
    from models.favorite import FavoriteModel
    from models.review import ReviewModel
    from models.category import CategoryModel
    import context_processors
    import models.company as company
    from models.site_settings import DEFAULTS

    record = {'id': 7, 'username': 'offline', 'role': 'business_owner',
              'auth_epoch': 0, 'profile': {'name': 'Fresh Name',
              'email': 'offline@example.test', 'preferences': ['criolla'],
              'restrictions': ['vegano'], 'addresses': ['Test street'],
              'daily_budget': 25}}
    reads = Mock(side_effect=lambda uid: dict(record))
    shops = Mock(return_value=[{'id': 9, 'name': 'Offline business'}])
    monkeypatch.setattr(UserModel, 'get_by_id', reads)
    monkeypatch.setattr(RestaurantModel, 'get_by_owner', shops)
    monkeypatch.setattr(FavoriteModel, 'get_by_user', Mock(return_value=[]))
    monkeypatch.setattr(ReviewModel, 'get_by_user', Mock(return_value=[]))
    monkeypatch.setattr(CategoryModel, 'all', Mock(return_value=[]))
    monkeypatch.setattr(context_processors, 'site_settings', Mock(return_value=dict(DEFAULTS)))
    monkeypatch.setattr(company, 'permitted', Mock(return_value=True))
    import views.companies as companies_view
    from contextlib import contextmanager
    from datetime import datetime, timezone
    @contextmanager
    def transaction():
        yield Mock()
    monkeypatch.setattr(companies_view, 'document_transaction', transaction)
    monkeypatch.setattr(company.Repo, 'get_by_id', lambda *a: {'at': datetime.now(timezone.utc).isoformat(), 'epoch': '0'})
    app = create_app({'TESTING': True, 'SECRET_KEY': 'offline-profile-only-' * 4})
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 7
        session['auth_epoch'] = 0
        session['user'] = {'id': 7, 'username': 'stale', 'role': 'business_owner',
                           'profile': {'name': 'Stale Name'}}
    return app, client, record, reads, shops


@pytest.mark.parametrize('role', ['business_owner', 'user'])
def test_profile_fresh_record_once_per_request(profile_app, role):
    app, client, record, reads, shops = profile_app
    record['role'] = role
    response = client.get('/auth/profile')
    assert response.status_code == 200
    assert b'Fresh Name' in response.data and b'Stale Name' not in response.data
    assert b'value="25"' in response.data
    assert b'name="csrf_token"' in response.data
    assert reads.call_count == 1
    if role == 'business_owner':
        assert shops.call_count == 1
    record['profile']['name'] = 'Next Request'
    assert b'Next Request' in client.get('/auth/profile').data
    assert reads.call_count == 2
    record['auth_epoch'] = 1
    assert client.get('/auth/profile').status_code == 302


@pytest.mark.parametrize('role', ['business_owner', 'user'])
@pytest.mark.parametrize('width', [390, 1280])
@pytest.mark.parametrize('cdn', ['pending', 'blocked'])
def test_profile_visible_without_external_load(profile_app, role, width, cdn):
    app, client, record, reads, shops = profile_app
    record['role'] = role
    record['profile']['avatar'] = 'a' * 48 + '.jpg'
    pending = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': width, 'height': 900})
        page.add_init_script('window.profileLoaded=false; window.addEventListener("load",()=>window.profileLoaded=true);')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def serve(route):
            url = urlsplit(route.request.url)
            if url.hostname != 'offline.test':
                if cdn == 'pending':
                    pending.append(route)
                else:
                    route.abort()
            elif url.path == '/auth/profile/photo/avatar' and cdn == 'pending':
                pending.append(route)
            elif url.path.startswith('/static/'):
                file = ROOT / url.path.lstrip('/')
                if file.is_file():
                    route.fulfill(body=file.read_bytes(), content_type={'.css': 'text/css', '.js': 'application/javascript', '.svg': 'image/svg+xml'}.get(file.suffix, 'application/octet-stream'))
                else:
                    route.fulfill(status=404, body='')
            elif url.path == '/auth/profile':
                response = client.get(url.path)
                assert response.status_code == 200
                route.fulfill(body=response.data, content_type='text/html')
            else:
                route.fulfill(json={'notifications': [], 'items': [], 'unread_count': 0, 'favorites': [], 'pending': []})

        page.route('**/*', serve)
        try:
            page.goto('http://offline.test/auth/profile', wait_until='commit')
            page.wait_for_function('!!document.querySelector(".profile-form")', timeout=5000)
            visible = page.locator('.profile-container').evaluate('el => { for(let n=el;n;n=n.parentElement){const s=getComputedStyle(n);if(s.display==="none"||s.visibility==="hidden"||Number(s.opacity)===0)return false;} return el.getBoundingClientRect().height>0; }')
            assert visible
            assert page.locator('input[name="name"]').input_value() == 'Fresh Name'
            assert page.locator('input[name="daily_budget"]').input_value() == '25'
            for selector in ['.profile-account-links', '.profile-sidebar', '.profile-form-container', 'input[name="email"]', 'input[name="preferences"]', 'input[name="restrictions"]', 'input[name="cookies_consent"]', '.profile-form button[type="submit"]']:
                assert page.locator(selector).first.is_visible(), selector
            assert page.locator('.profile-account-links a').first.get_attribute('href') == '/auth/seguridad'
            assert page.locator('.profile-form').get_attribute('action') == '/auth/profile/update'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            if cdn == 'pending':
                assert pending
                assert not page.evaluate('window.profileLoaded')
            assert not errors, errors
            print(f'profile role={role} width={width} CDN={cdn}: HTTP200, content visible, load={page.evaluate("window.profileLoaded")}, pending resources={len(pending)}')
        finally:
            page.unroute_all(behavior='ignoreErrors')
            browser.close()
