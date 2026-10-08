import re

from app import create_app


def _client():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app, app.test_client()


def test_public_contracts_and_security_headers():
    app, client = _client()
    home = client.get('/')
    assert home.status_code == 200
    assert b"main-content" in home.data
    assert client.get('/auth/login').status_code == 200
    search = client.post('/api/search', json={'district': 'Huanchaco'})
    assert search.status_code == 200
    assert isinstance(search.get_json(), list)
    assert home.headers.get('X-Content-Type-Options') == 'nosniff'
    assert home.headers.get('X-Frame-Options') == 'SAMEORIGIN'


def test_admin_endpoint_is_not_public_and_has_stable_api_shape():
    _, client = _client()
    response = client.get('/admin/api/bi/overview')
    assert response.status_code in (302, 401, 403)
    assert client.get('/admin/api/analytics').status_code in (302, 401, 403)


def test_invalid_mutations_are_rejected_without_internal_traceback():
    _, client = _client()
    response = client.post('/api/search', data='not-json', content_type='application/json')
    assert response.status_code in (200, 400)
    if response.is_json:
        assert 'Traceback' not in str(response.get_json())
    favorite = client.post('/auth/api/favorites/toggle', json={'restaurant_id': 'not-an-id'})
    assert favorite.status_code in (400, 401)


def test_routes_are_unique_and_have_no_debug_server_requirement():
    app, _ = _client()
    rules = list(app.url_map.iter_rules())
    endpoints = [rule.endpoint for rule in rules]
    assert len(endpoints) == len(set(endpoints))
    assert not app.debug
    assert re.search(r"/admin/api/bi/overview", " ".join(str(rule) for rule in rules))
