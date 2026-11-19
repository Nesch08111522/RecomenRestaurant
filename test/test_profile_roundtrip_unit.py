import copy
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from flask import Flask, jsonify
from flask_wtf.csrf import CSRFProtect

import views.auth as auth
from database.repository import PostgresDocumentRepository as Repo
from utils import security


@pytest.fixture
def profile_client(monkeypatch):
    row = {'id': 1, 'username': 'alice', 'role': 'user', 'auth_epoch': 0,
           'profile': {'name': 'Alice', 'email': 'alice@example.test',
                       'phone': '', 'preferences': [], 'restrictions': [],
                       'business_details': {'legal_name': 'Existing'}}}
    @contextmanager
    def transaction():
        before = copy.deepcopy(row)
        try:
            yield Mock()
        except Exception:
            row.clear()
            row.update(before)
            raise
    def update(uid, fields):
        assert uid == 1
        row.update(copy.deepcopy(fields))
        return copy.deepcopy(row)
    monkeypatch.setattr('database.repository.document_transaction', transaction)
    monkeypatch.setattr(Repo, 'get_by_id', lambda collection, uid, **kw: copy.deepcopy(row) if uid == 1 else None)
    monkeypatch.setattr(auth.UserModel, 'get_by_id', lambda uid: copy.deepcopy(row) if uid == 1 else None)
    monkeypatch.setattr(auth.UserModel, 'update', update)
    monkeypatch.setattr(auth.protection, 'allow_attempt', lambda *args: True)
    monkeypatch.setattr(auth.FavoriteModel, 'get_by_user', lambda uid: [])
    monkeypatch.setattr('models.review.ReviewModel.get_by_user', lambda uid: [])
    monkeypatch.setattr(auth, 'render_template', lambda template, **kw: jsonify(template=template, **kw))
    app = Flask(__name__)
    app.secret_key = 'synthetic-profile-tests'
    app.register_blueprint(auth.auth_bp, url_prefix='/auth')
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['auth_epoch'] = 0
        session['user'] = security.session_identity(row)
    return app, client, row


@pytest.mark.parametrize('role', ['user', 'business_owner', 'admin'])
def test_persisted_get_roundtrip_supported_fields(profile_client, role):
    app, client, row = profile_client
    row['role'] = role
    data = {'name': 'Alice Updated', 'email': 'alice@example.test', 'phone': '',
            'preferences': ['criolla', 'japonesa'], 'restrictions': ['celiaco', 'alergia mariscos'],
            'addresses': 'Street One\nStreet Two', 'daily_budget': '12.50', 'weekly_budget': '90',
            'birthday': '2000-01-02', 'transactional_notifications': 'on',
            'promotions_opt_in': 'on', 'location_consent': 'on'}
    response = client.post('/auth/profile/update', data=data, headers={'Accept': 'application/json'})
    assert response.status_code == 200 and response.json['success']
    persisted = client.get('/auth/profile').json['user']['profile']
    assert persisted == row['profile']
    assert persisted['name'] == 'Alice Updated'
    assert persisted['email'] == data['email'] and persisted['phone'] == ''
    assert persisted['preferences'] == data['preferences']
    assert persisted['restrictions'] == data['restrictions']
    assert persisted['addresses'] == ['Street One', 'Street Two']
    assert persisted['daily_budget'] == 12.5 and persisted['weekly_budget'] == 90
    assert persisted['birthday'] == data['birthday']
    assert persisted['notification_preferences'] == {'transactional': True, 'marketing': True, 'reviews': False, 'waitlist': False}
    assert persisted['location_consent'] is True and persisted['cookies_consent'] is False
    assert persisted['business_details'] == {'legal_name': 'Existing'}
    assert client.get('/auth/profile').json['template'] == ('auth/profile_owner.html' if role == 'business_owner' else 'auth/profile.html')


@pytest.mark.parametrize('fields', [{'phone': '90000'}, {'email': 'bad'}, {'restrictions': ['unknown']}])
def test_validation_no_write_and_retains_input(profile_client, fields):
    app, client, row = profile_client
    before = copy.deepcopy(row)
    response = client.post('/auth/profile/update', data={'name': 'Retained', **fields})
    assert response.status_code == 400
    assert response.json['user']['profile']['name'] == 'Retained'
    assert response.json['profile_error']
    assert row == before


def test_contacts_require_password_and_do_not_fake_success(profile_client, monkeypatch):
    app, client, row = profile_client
    configure = Mock(side_effect=ValueError('Verifica la contraseña actual.'))
    monkeypatch.setattr(auth.protection, 'configure', configure)
    before = copy.deepcopy(row)
    response = client.post('/auth/profile/update', data={'email': 'new@example.test', 'phone': '+51911111111'}, headers={'Accept': 'application/json'})
    assert response.status_code == 400 and not response.json['success']
    assert configure.call_args.args[1] == ''
    assert row == before


@pytest.mark.parametrize('state', ['expired', 'inactive', 'anonymous'])
def test_get_and_update_reject_invalid_session(profile_client, state):
    app, client, row = profile_client
    if state == 'expired':
        row['auth_epoch'] = 1
    elif state == 'inactive':
        row['status'] = 'DISABLED'
    else:
        with client.session_transaction() as session:
            session.clear()
    before = copy.deepcopy(row)
    assert client.get('/auth/profile').status_code == 302
    assert client.post('/auth/profile/update', data={'name': 'Forbidden'}).status_code == 302
    assert row == before


def test_csrf_missing_token_blocks_write(profile_client):
    app, client, row = profile_client
    CSRFProtect(app)
    before = copy.deepcopy(row)
    assert client.post('/auth/profile/update', data={'name': 'Forbidden'}).status_code == 400
    assert row == before


def test_protected_contact_roundtrip_and_upload_rollback(profile_client, monkeypatch):
    from werkzeug.security import generate_password_hash
    from werkzeug.datastructures import FileStorage
    import io
    app, client, row = profile_client
    row['password'] = generate_password_hash('Password123')
    states = {}
    def get(collection, uid, **kw):
        return copy.deepcopy(row if collection == 'users' else states.get(uid))
    def update(collection, uid, fields):
        target = row if collection == 'users' else states[uid]
        target.update(copy.deepcopy(fields))
        return copy.deepcopy(target)
    monkeypatch.setattr(Repo, 'get_by_id', get)
    monkeypatch.setattr(Repo, 'update', update)
    monkeypatch.setattr(Repo, 'create', lambda collection, fields: states.setdefault(fields['id'], fields))
    monkeypatch.setattr(auth.protection, 'document_transaction', __import__('database.repository', fromlist=['document_transaction']).document_transaction)
    monkeypatch.setattr('utils.audit.record_event', Mock())
    data = {'name': 'New Name', 'email': 'new@example.test', 'phone': '+51911111111',
            'current_password': 'Password123'}
    response = client.post('/auth/profile/update', data=data, headers={'Accept': 'application/json'})
    assert response.status_code == 200 and response.json['success']
    persisted = client.get('/auth/profile').json['user']['profile']
    assert persisted['email'] == data['email'] and persisted['phone'] == data['phone']
    assert persisted['email_verified'] is False and persisted['phone_verified'] is False
    assert row['auth_epoch'] == 1 and states[1]['recovery'] is None
    with client.session_transaction() as session:
        assert session['auth_epoch'] == 1
    before = copy.deepcopy(row)
    monkeypatch.setattr('core.profile.save_profile_image', Mock(side_effect=ValueError('Imagen invalida')))
    response = client.post('/auth/profile/update', data={**data, 'email': 'other@example.test',
                           'avatar': FileStorage(stream=io.BytesIO(b'invalid'), filename='bad.png')},
                           headers={'Accept': 'application/json'})
    assert response.status_code == 400 and not response.json['success']
    assert row == before
    with client.session_transaction() as session:
        assert session['auth_epoch'] == 1


def test_existing_private_images_survive_and_new_images_roundtrip(profile_client, monkeypatch):
    import io
    from werkzeug.datastructures import FileStorage
    app, client, row = profile_client
    row['profile'].update(avatar='a' * 48 + '.jpg', background='b' * 48 + '.jpg')
    response = client.post('/auth/profile/update', data={'name': 'Alice'})
    assert response.status_code == 302
    assert client.get('/auth/profile').json['user']['profile']['avatar'] == 'a' * 48 + '.jpg'
    save = Mock(side_effect=['c' * 48 + '.jpg', 'd' * 48 + '.jpg'])
    monkeypatch.setattr('core.profile.save_profile_image', save)
    response = client.post('/auth/profile/update', data={
        'avatar': FileStorage(stream=io.BytesIO(b'image'), filename='avatar.png'),
        'background': FileStorage(stream=io.BytesIO(b'image'), filename='background.png')})
    assert response.status_code == 302
    persisted = client.get('/auth/profile').json['user']['profile']
    assert persisted['avatar'] == 'c' * 48 + '.jpg' and persisted['background'] == 'd' * 48 + '.jpg'
    assert [call.args[1:] for call in save.call_args_list] == [(1, 'avatar'), (1, 'background')]


def test_profile_template_compiles_and_has_no_reload():
    from pathlib import Path
    from jinja2 import Environment
    root = Path(__file__).resolve().parents[1]
    text = (root / 'templates/auth/profile_content.html').read_text(encoding='utf-8')
    Environment().parse(text)
    assert 'location.reload' not in text and 'setInterval' not in text
    assert 'new FormData(form)' in text and 'csrf_token' in text
    assert 'profile_photo' in text and 'profile-feedback' in text


def test_missing_persisted_result_is_error(profile_client, monkeypatch):
    app, client, row = profile_client
    monkeypatch.setattr(auth.UserModel, 'update', lambda *args: None)
    response = client.post('/auth/profile/update', data={'name': 'Changed'}, headers={'Accept': 'application/json'})
    assert response.status_code == 400 and not response.json['success']
