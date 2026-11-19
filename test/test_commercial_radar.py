"""Isolated tests: no application factory, database, network or dotenv loading."""
import json
from contextlib import nullcontext
from unittest.mock import MagicMock
import pytest
from flask import Flask
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from models import commercial_radar as service
from views import commercial_radar as routes
from utils.discovery_sources import SourceUnavailable
from logic.business_radar import from_osm


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__, template_folder='../templates')
    app.config.update(TESTING=True, SECRET_KEY='isolated-test-only')
    CSRFProtect(app)
    app.register_blueprint(routes.bp)
    app.add_url_rule('/token', view_func=lambda: generate_csrf())
    monkeypatch.setattr(routes, 'fresh_session_user', lambda: {'id': 1, 'role': 'admin'})
    monkeypatch.setattr(routes, 'allow_attempt', lambda *a: True)
    return app.test_client()


def post(client, path, data):
    token = client.get('/token').text
    return client.post('/admin/api/radar-comercial/' + path, json=data, headers={'X-CSRFToken': token})


@pytest.mark.parametrize('role', ['consumer', 'owner', 'business_owner', 'waiter', None])
def test_roles(client, monkeypatch, role):
    monkeypatch.setattr(routes, 'fresh_session_user', lambda: {'id': 1, 'role': role} if role else None)
    monkeypatch.setattr(service.ProspectModel, 'all', lambda: pytest.fail('unauthorized DB access'))
    assert client.get('/admin/api/radar-comercial').status_code == (403 if role else 401)
    for path in ('discover', '1/state', '1/analyze', '1/convert'):
        assert post(client, path, {}).status_code == (403 if role else 401)


def test_csrf_and_limit(client, monkeypatch):
    assert client.post('/admin/api/radar-comercial/discover', json={}).status_code == 400
    monkeypatch.setattr(routes, 'allow_attempt', lambda *a: False)
    assert post(client, 'discover', {}).status_code == 429


def test_failure_endpoint_no_fabrication(client, monkeypatch):
    def fail(*args):
        raise SourceUnavailable('Overpass unavailable')
    monkeypatch.setattr(service, 'discover', fail)
    response = post(client, 'discover', {'lat': -8.1, 'lng': -79.03})
    assert response.status_code == 502
    assert 'prospects' not in response.json


def test_source_failure_does_not_ingest(monkeypatch):
    monkeypatch.setattr(service, 'document_transaction', lambda: nullcontext(MagicMock()))
    monkeypatch.setattr(service.discovery, 'lock', lambda c: None)
    monkeypatch.setattr(service.QueryModel, 'all', lambda: [])
    monkeypatch.setattr(service.QueryModel, 'create', lambda d: {'id': 1, **d})
    changes = []
    monkeypatch.setattr(service.QueryModel, 'update', lambda i, d: changes.append(d))
    monkeypatch.setattr(service.discovery, 'ingest', lambda *a: pytest.fail('ingest on failure'))
    def fail(*a, **kw):
        raise SourceUnavailable('Unavailable')
    monkeypatch.setattr(service, 'osm_search', fail)
    with pytest.raises(SourceUnavailable):
        service.discover(1, {'lat': -8.1, 'lng': -79.03})
    assert changes == [{'status': 'failed'}]


def test_success_discovery_deduplicates_and_notifies(monkeypatch):
    row = from_osm({'id': 123, 'type': 'node', 'lat': -8.1, 'lon': -79.03, 'tags': {'name': 'Fixture only', 'amenity': 'restaurant'}})
    monkeypatch.setattr(service, 'document_transaction', lambda: nullcontext(MagicMock()))
    monkeypatch.setattr(service.discovery, 'lock', lambda c: None)
    monkeypatch.setattr(service.QueryModel, 'all', lambda: [])
    monkeypatch.setattr(service.QueryModel, 'create', lambda d: {'id': 1, **d})
    monkeypatch.setattr(service.QueryModel, 'update', lambda *a: None)
    monkeypatch.setattr(service, 'osm_search', lambda *a, **kw: [row])
    monkeypatch.setattr(service, 'nominatim_reference', lambda *a: {'label': 'Mock Trujillo reference'})
    monkeypatch.setattr(service.discovery, 'ingest', lambda *a: None)
    monkeypatch.setattr(service.discovery.CandidateModel, 'all', lambda: [{'id': 5, **row}])
    saved = []
    monkeypatch.setattr(service.ProspectModel, 'all', lambda: saved.copy())
    monkeypatch.setattr(service.ProspectModel, 'create', lambda d: saved.append({'id': 7, **d}) or saved[-1])
    monkeypatch.setattr(service.ProspectModel, 'update', lambda i, d: saved[0].update(d))
    notification = MagicMock()
    monkeypatch.setattr(service.NotificationModel, 'create_notification', notification)
    assert service.discover(1, {'lat': -8.1, 'lng': -79.03})['created'] == 1
    saved[0]['state'] = 'contactado'
    assert service.discover(1, {'lat': -8.1, 'lng': -79.03})['created'] == 0
    assert saved[0]['state'] == 'contactado'
    assert saved[0]['distance_km'] == 0
    assert 'rating' not in saved[0]['data']
    notification.assert_called_once()


@pytest.mark.parametrize('lat,lng', [('nan', -79), (-8, 'inf'), (True, -79), (0, 0), (None, -79)])
def test_coordinate_validation(lat, lng):
    with pytest.raises(ValueError):
        service.coordinates(lat, lng)


def test_ai_rejects_invented_evidence(monkeypatch):
    row = {'id': 1, 'data': {'name': 'Fixture'}, 'evidence': {'name': {}}, 'last_seen_at': 't'}
    monkeypatch.setattr(service.ProspectModel, 'get_by_id', lambda i: row)
    monkeypatch.setattr(service.ProspectModel, 'update', lambda *a: pytest.fail('invalid analysis saved'))
    provider = MagicMock()
    provider.client.return_value.__enter__.return_value.chat.completions.create.return_value.choices[0].message.content = json.dumps({'priority': 'alta', 'fields': ['popularity']})
    monkeypatch.setattr(service, 'settings', lambda **kw: provider)
    with pytest.raises(ValueError):
        service.analyze(1)


def test_affiliation_requires_actual_company(monkeypatch):
    monkeypatch.setattr(service, 'document_transaction', lambda: nullcontext(MagicMock()))
    monkeypatch.setattr(service.discovery, 'lock', lambda c: None)
    monkeypatch.setattr(service.ProspectModel, 'get_by_id', lambda i: {'id': i, 'state': 'interesado'})
    monkeypatch.setattr(service, 'companies', lambda: [])
    with pytest.raises(ValueError):
        service.update_state(1, 'afiliado', 1, 'verified identity', 999)


def test_convert_uses_existing_review_not_affiliation(monkeypatch):
    monkeypatch.setattr(service, 'document_transaction', lambda: nullcontext(MagicMock()))
    monkeypatch.setattr(service.discovery, 'lock', lambda c: None)
    monkeypatch.setattr(service.ProspectModel, 'get_by_id', lambda i: {'id': i, 'state': 'interesado', 'candidate_id': 3})
    monkeypatch.setattr(service.discovery.CandidateModel, 'get_by_id', lambda i: {'id': i, 'status': 'pending_review'})
    review = MagicMock(return_value={'business_id': 9})
    monkeypatch.setattr(service.discovery, 'review', review)
    monkeypatch.setattr(service.ProspectModel, 'update', lambda i, d: d)
    result = service.convert(1, 2, 'Reviewed source')
    assert result['company_id'] == 9 and 'state' not in result
    review.assert_called_once_with(3, 'approve', 2, 'Reviewed source')


def test_overpass_query_uses_bounded_reference(monkeypatch):
    from utils import discovery_sources as sources
    calls = []
    def request(url, method, body, headers, **kwargs):
        calls.append((url, body.decode()))
        return 200, 'application/json', b'{"elements": []}'
    monkeypatch.setattr(sources, 'request_bytes', request)
    assert sources.osm_search(2, 100, center=(-8.1, -79.03)) == []
    assert calls[0][0] == sources.OVERPASS
    assert 'around:2000,-8.1,-79.03' in calls[0][1]
    with pytest.raises(ValueError):
        sources.osm_search(float('nan'))


def test_nominatim_failure_no_inferred_address(monkeypatch):
    from utils import discovery_sources as sources
    monkeypatch.setattr(sources, 'request_bytes', lambda *a, **kw: (200, 'application/json', b'{"error":"missing"}'))
    with pytest.raises(SourceUnavailable):
        sources.nominatim_reference(-8.1, -79.03)


def test_no_unsafe_contact_links():
    row = {'data': {'phone': 'javascript:alert(1)'}, 'channels': {'website': {'url': 'http://localhost/'}}}
    result = service.presentation(row)
    assert not result['channels'] and result['phone_link'] is None
