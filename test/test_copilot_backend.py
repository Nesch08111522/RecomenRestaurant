"""Copilot contract tests: standalone Flask, mocked storage and provider."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
import hashlib
import time

import pytest
from flask import Flask
from views import copilot as c


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-only'
    app.register_blueprint(c.bp)
    app.add_url_rule('/recomendaciones', 'recommendations', lambda: '')
    monkeypatch.setattr(c, 'actor', lambda: {'id': 7, 'role': 'user'})
    monkeypatch.setattr(c, 'allow_attempt', lambda *args: True)
    monkeypatch.setattr(c, 'shops_for', lambda user: [{'id': 2, 'name': 'Test'}])
    monkeypatch.setattr(c, 'records', lambda *args, **kwargs: [])
    monkeypatch.setattr(c.NotificationModel, 'get_by_user', Mock(return_value=[]))
    monkeypatch.setattr(c.SiteModel, 'all', Mock(return_value=[]))
    app.add_url_rule('/', 'home', lambda: '')
    from models.dish import DishModel
    monkeypatch.setattr(DishModel, 'all', lambda: [])
    monkeypatch.setattr(c.Repo, 'get_by_id', Mock(side_effect=AssertionError('DB forbidden')))
    monkeypatch.setattr(c.Repo, 'create', Mock(side_effect=AssertionError('DB forbidden')))
    monkeypatch.setattr(c.Repo, 'update', Mock(side_effect=AssertionError('DB forbidden')))
    monkeypatch.setattr(c, 'document_transaction', nullcontext)
    monkeypatch.setattr(c, 'record_event', Mock())
    monkeypatch.setattr(c, 'log_provider_error', Mock())
    create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"reply":"Hola","links":[{"url":"/recomendaciones","label":"fake"},{"url":"https://evil.test"}]}'))]))
    config = SimpleNamespace(model='mock', client=lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(c, 'settings', Mock(return_value=config))
    app.provider_mock = create
    return app.test_client()


def test_multiturn_links_and_no_writes(client):
    messages = [{'role': 'user', 'content': 'Hola'}, {'role': 'assistant', 'content': 'Hola'}, {'role': 'user', 'content': 'Opciones'}]
    response = client.post('/api/copilot/chat', json={'messages': messages})
    assert response.status_code == 200
    assert response.json['links'] == [{'label': 'recommendations', 'url': '/recomendaciones'}]
    assert client.application.provider_mock.call_args.kwargs['messages'][2:] == messages
    assert 'action' not in response.json
    c.Repo.create.assert_not_called()


@pytest.mark.parametrize('messages', [[], [{'role': 'system', 'content': 'hack'}], [{'role': 'user', 'content': 3}], [{'role': 'user', 'content': 'a', 'extra': True}], [{'role': 'assistant', 'content': 'a'}], [{'role': 'user', 'content': 'a' * 2001}]])
def test_invalid_history(client, messages):
    assert client.post('/api/copilot/chat', json={'messages': messages}).status_code == 400
    client.application.provider_mock.assert_not_called()


@pytest.mark.parametrize('mode', ['root', None, {}, []])
def test_invalid_mode(client, mode):
    assert client.post('/api/copilot/chat', json={'mode': mode, 'messages': [{'role': 'user', 'content': 'a'}]}).status_code == 400


@pytest.mark.parametrize('url', ['/api/copilot/actions', '/api/copilot/actions/1/confirm'])
def test_full_required(client, url):
    assert client.post(url, json={'confirm': True, 'token': 'x', 'action': 'restaurant_promo', 'rid': 2, 'text': 'Hi'}).status_code == 400


def test_full_does_not_elevate(client):
    assert client.post('/api/copilot/actions', json={'mode': 'full', 'action': 'restaurant_promo', 'rid': 2, 'text': 'Hi'}).status_code == 403


@pytest.mark.parametrize('change', [{'action': 'http'}, {'rid': True}, {'url': '/admin'}, {'text': ''}])
def test_action_schema(client, change):
    payload = {'mode': 'full', 'action': 'restaurant_promo', 'rid': 2, 'text': 'Hi', **change}
    assert client.post('/api/copilot/actions', json=payload).status_code == 400


def test_prepare_confirm_replay_and_stale(client, monkeypatch):
    monkeypatch.setattr(c, 'actor', lambda: {'id': 7, 'role': 'business_owner'})
    shop = {'id': 2, 'owner_id': 7, 'name': 'Test', 'promo': 'Old'}
    monkeypatch.setattr(c.RestaurantModel, 'get_by_id', lambda rid: shop if rid == 2 else None)
    from utils import restaurant_review
    monkeypatch.setattr(restaurant_review, 'check_restaurant', lambda value: None)
    saved = {}
    def save(collection, value):
        saved.update(value, id=1)
        return saved
    monkeypatch.setattr(c.Repo, 'create', save)
    monkeypatch.setattr(c.Repo, 'get_by_id', lambda collection, ident, **kwargs: saved if collection == 'copilot_actions' else shop)
    monkeypatch.setattr(c.Repo, 'update', lambda collection, ident, value: saved.update(value))
    update = Mock(return_value=shop)
    monkeypatch.setattr(c.RestaurantModel, 'update', update)
    prepared = client.post('/api/copilot/actions', json={'mode': 'full', 'action': 'restaurant_promo', 'rid': 2, 'text': 'New'})
    assert prepared.status_code == 200
    assert saved['token_hash'] != prepared.json['token']
    update.assert_not_called()
    confirm = {'mode': 'full', 'confirm': True, 'token': prepared.json['token']}
    assert client.post('/api/copilot/actions/1/confirm', json={**confirm, 'token': 'wrong'}).status_code == 403
    shop['promo'] = 'Concurrent'
    assert client.post('/api/copilot/actions/1/confirm', json=confirm).status_code == 409
    shop['promo'] = 'Old'
    assert client.post('/api/copilot/actions/1/confirm', json=confirm).status_code == 200
    update.assert_called_once_with(2, {'promo': 'New'})
    assert client.post('/api/copilot/actions/1/confirm', json=confirm).status_code == 409
    saved['used'] = False
    saved['until'] = time.time() - 1
    assert client.post('/api/copilot/actions/1/confirm', json=confirm).status_code == 409


@pytest.mark.parametrize('mode,role,action,expected', [
    ('basic', 'user', {'action': 'restaurant_promo', 'rid': 2, 'text': 'Hi'}, 200),
    ('full', 'user', {'action': 'restaurant_promo', 'rid': 2, 'text': 'Hi'}, 503),
    ('full', 'business_owner', {'action': 'restaurant_promo', 'rid': 2, 'text': 'Hi'}, 200),
    ('full', 'business_owner', {'action': 'restaurant_promo', 'rid': 99, 'text': 'Hi'}, 503),
    ('full', 'business_owner', {'action': 'restaurant_name', 'rid': 2, 'text': 'Hi'}, 503),
])
def test_chat_proposals(client, monkeypatch, mode, role, action, expected):
    import json
    monkeypatch.setattr(c, 'actor', lambda: {'id': 7, 'role': role})
    from analytics import management
    monkeypatch.setattr(management, 'scoped_records', lambda *args: [])
    monkeypatch.setattr(c, 'report', lambda *args: {'orders': 0, 'income': 0, 'known_costs': 0, 'cost_coverage': 0, 'top_products': []})
    client.application.provider_mock.return_value.choices[0].message.content = json.dumps({'reply': 'Propuesta', 'action': action})
    response = client.post('/api/copilot/chat', json={'mode': mode, 'messages': [{'role': 'user', 'content': 'Hola'}]})
    assert response.status_code == expected
    if expected == 200:
        assert response.json.get('action') == (action if mode == 'full' else None)
    c.Repo.create.assert_not_called()


@pytest.mark.parametrize('mode', ['basic', 'full'])
@pytest.mark.parametrize('question,destination,allowed', [
    ('Abre inicio', '/', True),
    ('Abre recomendaciones', '/recomendaciones', True),
    ('Hola', '/', False),
    ('No abre inicio', '/', False),
    ('Abre recomendaciones', '/', False),
    ('Abre inicio', '//evil.test', False),
    ('Abre inicio', '/admin/restaurants', False),
    ('Abre inicio', {'url': '/'}, False),
])
def test_navigation(client, mode, question, destination, allowed):
    import json
    client.application.provider_mock.return_value.choices[0].message.content = json.dumps({'reply': 'Hola', 'navigate': destination})
    response=client.post('/api/copilot/chat', json={'mode': mode, 'messages': [{'role': 'user', 'content': question}]})
    assert response.status_code == 200
    assert ('navigate' in response.json) == allowed
    if allowed:
        assert response.json['navigate'] == {'url': destination, 'verified': True}
        assert any(link['url'] == destination for link in response.json['links'])


def test_notifications_scoped_minimal(client, monkeypatch):
    import json
    reader=Mock(return_value=[{'user_id': 7, 'title': 'Propia', 'message': 'Aviso', 'read': True, 'link': '/recomendaciones', 'private': 'omit'}, {'user_id': 8, 'title': 'Ajena'}, {'user_id': 7, 'title': 'Otra', 'link': '/admin'}])
    monkeypatch.setattr(c.NotificationModel, 'get_by_user', reader)
    assert client.post('/api/copilot/chat', json={'messages': [{'role': 'user', 'content': 'Mis avisos'}]}).status_code == 200
    reader.assert_called_once_with(7, limit=5)
    context=json.loads(client.application.provider_mock.call_args.kwargs['messages'][1]['content'].split(': ',1)[1])
    assert len(context['notifications']) == 2
    assert context['notifications'][0] == {'title': 'Propia', 'message': 'Aviso', 'read': True, 'link': '/recomendaciones'}
    assert context['notifications'][1]['link'] is None
    c.Repo.update.assert_not_called()


@pytest.mark.parametrize('answer', ['[]', '{"reply": 3}', '{"reply":"ok","links":{}}', 'bad json'])
def test_malformed_provider(client, answer):
    client.application.provider_mock.return_value.choices[0].message.content=answer
    assert client.post('/api/copilot/chat', json={'messages': [{'role': 'user', 'content': 'Hola'}]}).status_code == 503


def test_public_sites_visibility(client, monkeypatch):
    import json
    client.application.add_url_rule('/negocio/<slug>', 'site', lambda slug: '')
    monkeypatch.setattr(c, 'shops_for', lambda user: [{'id': 2, 'name': 'Visible', 'verified': True, 'owner_id': 7}, {'id': 3, 'name': 'Oculto', 'verified': True, 'owner_id': 7, 'status': 'suspended'}])
    monkeypatch.setattr(c.SiteModel, 'all', lambda: [
        {'restaurant_id': 2, 'owner_id': 7, 'published': {'slug': 'visible'}},
        {'restaurant_id': 3, 'owner_id': 7, 'published': {'slug': 'oculto'}},
        {'restaurant_id': 2, 'owner_id': 8, 'published': {'slug': 'ajeno'}},
        {'restaurant_id': 2, 'owner_id': 7, 'published': {'slug': '../evil'}},
    ])
    client.application.provider_mock.return_value.choices[0].message.content=json.dumps({'reply': 'Sitio', 'navigate': '/negocio/visible'})
    response=client.post('/api/copilot/chat', json={'messages': [{'role': 'user', 'content': 'Visita Visible'}]})
    assert response.status_code == 200
    assert response.json['navigate']['url'] == '/negocio/visible'
    context=json.loads(client.application.provider_mock.call_args.kwargs['messages'][1]['content'].split(': ',1)[1])
    assert [link['url'] for link in context['links'] if link['url'].startswith('/negocio/')] == ['/negocio/visible']


@pytest.mark.parametrize('images', [None, {}, ['https://evil.test/a.png'], ['data:image/png;base64,bad'], ['x'] * 4])
def test_invalid_images(client, images):
    response = client.post('/api/copilot/chat', json={'messages': [{'role': 'user', 'content': 'Imagen'}], 'images': images})
    assert response.status_code == 400
    client.application.provider_mock.assert_not_called()


def test_multimodal_existing_provider(client):
    import base64
    from io import BytesIO
    from PIL import Image
    buffer = BytesIO()
    Image.new('RGB', (2, 2)).save(buffer, format='PNG')
    image = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
    response = client.post('/api/copilot/chat', json={'messages': [{'role': 'user', 'content': 'Describe'}], 'images': [image]})
    assert response.status_code == 200
    content = client.application.provider_mock.call_args.kwargs['messages'][-1]['content']
    assert content == [{'type': 'text', 'text': 'Describe'}, {'type': 'image_url', 'image_url': {'url': image}}]
    c.Repo.create.assert_not_called()


def test_images_require_session(client, monkeypatch):
    from flask import abort
    monkeypatch.setattr(c, 'actor', lambda: abort(401))
    assert client.post('/api/copilot/chat', json={'images': []}).status_code == 401
    client.application.provider_mock.assert_not_called()


def test_provider_failure(client):
    client.application.provider_mock.side_effect = RuntimeError('mock failure')
    assert client.post('/api/copilot/chat', json={'messages': [{'role': 'user', 'content': 'Hola'}]}).status_code == 503
