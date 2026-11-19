import pytest


@pytest.fixture
def outage_app(monkeypatch):
    import dotenv
    import psycopg
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: None)
    def blocked(*a, **k):
        pytest.fail('Live database connection attempted')
    monkeypatch.setattr(psycopg, 'connect', blocked)
    from app import create_app
    import database.repository as repository
    from database.connection import DatabaseConnectionError
    calls = []
    def unavailable(*a, **k):
        calls.append(True)
        raise DatabaseConnectionError('private-secret-diagnostic')
    monkeypatch.setattr(repository, 'connection', unavailable)
    app = create_app({'TESTING': True, 'SECRET_KEY': 'unit-test-only-' * 4})
    @app.get('/outage-page')
    def page():
        from flask import render_template
        return render_template('404.html')
    return app, calls


def authenticate(client):
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['user'] = {'id': 1, 'role': 'admin'}
        session['role'] = 'admin'


def test_authenticated_static_and_missing_static_never_use_database(outage_app):
    app, calls = outage_app
    client = app.test_client()
    authenticate(client)
    response = client.get('/static/images/editorial/home.webp')
    assert response.status_code == 200
    assert response.mimetype == 'image/webp'
    assert client.get('/static/images/not-present.webp').status_code == 404
    assert calls == []


@pytest.mark.parametrize('authenticated', [False, True])
def test_page_failure_is_safe_503_without_context_recursion(outage_app, authenticated):
    app, calls = outage_app
    client = app.test_client()
    if authenticated:
        authenticate(client)
    response = client.get('/outage-page')
    assert response.status_code == 503
    assert b'<h1>503</h1>' in response.data
    assert b'private-secret' not in response.data
    assert response.headers['X-Request-ID']
    assert len(calls) == 1


@pytest.mark.parametrize('authenticated', [False, True])
def test_search_failure_is_json_503(outage_app, authenticated):
    app, calls = outage_app
    client = app.test_client()
    if authenticated:
        authenticate(client)
    response = client.post('/api/search', json={})
    assert response.status_code == 503
    assert response.json['code'] == 'database_unavailable'
    assert response.json['success'] is False
    assert b'private-secret' not in response.data
    assert len(calls) == 1


def test_failed_user_read_cached_only_within_request(outage_app):
    from utils.security import fresh_session_user
    from database.connection import DatabaseConnectionError
    from flask import session
    app, calls = outage_app
    for _ in range(2):
        with app.test_request_context('/'):
            session['user_id'] = 1
            for _ in range(3):
                with pytest.raises(DatabaseConnectionError):
                    fresh_session_user()
    assert len(calls) == 2


def test_permissions_revalidated_after_outage(outage_app, monkeypatch):
    from models.user import UserModel
    import core.company_access as access
    import views.companies as companies
    app, calls = outage_app
    client = app.test_client()
    authenticate(client)
    assert client.get('/owner/dashboard').status_code == 503
    reads, checks = [], []
    def user(uid):
        reads.append(uid)
        return {'id': uid, 'role': 'business_owner', 'username': 'test', 'profile': {}}
    monkeypatch.setattr(UserModel, 'get_by_id', user)
    monkeypatch.setattr(access.RestaurantModel, 'get_by_owner', lambda uid: [{'id': 7}])
    def denied(user, rid, permission):
        checks.append((user['role'], rid, permission))
        return False
    monkeypatch.setattr(access, 'permitted', denied)
    # Presence is unrelated to authorization; prohibit its transaction in this test.
    app.before_request_funcs[None].remove(companies.presence)
    response = client.get('/owner/dashboard')
    assert response.status_code == 403
    assert reads == [1]
    assert checks == [('business_owner', 7, 'business.manage')]
    assert len(calls) == 1


def test_successful_user_and_invalid_user_reads_cached(outage_app, monkeypatch):
    from models.user import UserModel
    from utils.security import fresh_session_user
    from flask import session
    app, _ = outage_app
    reads = []
    def user(uid):
        reads.append(uid)
        return {'id': uid, 'role': 'user', 'username': 'test', 'profile': {}}
    monkeypatch.setattr(UserModel, 'get_by_id', user)
    with app.test_request_context('/'):
        session['user_id'] = 1
        assert fresh_session_user() == fresh_session_user()
    assert reads == [1]
    monkeypatch.setattr(UserModel, 'get_by_id', lambda uid: None)
    with app.test_request_context('/'):
        session['user_id'] = 1
        assert fresh_session_user() is None
        assert fresh_session_user() is None
        assert 'user_id' not in session
