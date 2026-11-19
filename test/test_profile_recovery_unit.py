import copy
import io
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest
from flask import Flask
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.security import check_password_hash

from core.profile import normalize_profile_patch, save_profile_image
from utils import password_codes as codes
from utils import security_delivery as delivery


@pytest.fixture
def store(monkeypatch):
    rows = {('users', 1): {'id': 1, 'username': 'alice', 'auth_epoch': 0,
                          'profile': {'email': 'alice@example.test', 'phone': '+51900000000'}}}
    @contextmanager
    def transaction():
        yield Mock()
    def get(collection, uid, **kwargs):
        return copy.deepcopy(rows.get((collection, uid)))
    def update(collection, uid, fields):
        rows[(collection, uid)].update(fields)
    def create(collection, fields):
        rows[(collection, fields['id'])] = copy.deepcopy(fields)
        return fields
    monkeypatch.setattr(codes, 'document_transaction', transaction)
    monkeypatch.setattr(codes.Repo, 'get_by_id', get)
    monkeypatch.setattr(codes.Repo, 'update', update)
    monkeypatch.setattr(codes.Repo, 'create', create)
    monkeypatch.setattr(codes.UserModel, 'get_by_username', lambda name: get('users', 1) if name == 'alice' else None)
    monkeypatch.setattr(codes, 'configured', lambda channel: True)
    monkeypatch.setattr(codes, 'record_event', Mock())
    sender = Mock()
    monkeypatch.setattr(codes, 'send_code', sender)
    app = Flask(__name__)
    app.secret_key = 'synthetic-unit-test-session-key-only'
    with app.app_context():
        yield rows, sender


def test_verified_reset_is_bound_single_use_and_invalidates_sessions(store):
    rows, sender = store
    challenge = codes.issue('alice', 'email')
    code = sender.call_args.args[2]
    row = rows[(codes.COLLECTION, 1)]
    assert code not in row.values()
    assert not codes.complete('alice', challenge, 'forged', 'Password123')
    assert codes.verify('alice', 'other-session', code) is None
    token = codes.verify('alice', challenge, code)
    assert token and token not in row.values()
    assert codes.verify('alice', challenge, code) is None
    assert codes.complete('alice', challenge, token, 'Password123')
    assert rows[('users', 1)]['auth_epoch'] == 1
    assert check_password_hash(rows[('users', 1)]['password'], 'Password123')
    assert not codes.complete('alice', challenge, token, 'Another123')


def test_max_attempts_expiry_resend_and_contact_change(store):
    rows, sender = store
    challenge = codes.issue('alice', 'sms')
    code = sender.call_args.args[2]
    wrong = '000000' if code != '000000' else '111111'
    assert codes.issue('alice', 'sms', challenge) == challenge
    assert sender.call_count == 1
    for _ in range(5):
        assert codes.verify('alice', challenge, wrong) is None
    assert codes.verify('alice', challenge, code) is None
    row = rows[(codes.COLLECTION, 1)]
    row['attempts'] = 0
    row['until'] = 0
    assert codes.verify('alice', challenge, code) is None
    row['until'] = 10**12
    rows[('users', 1)]['profile']['phone'] = '+51911111111'
    assert codes.verify('alice', challenge, code) is None


def test_unknown_and_failed_delivery_never_authorize(store):
    rows, sender = store
    assert codes.issue('unknown', 'email')
    sender.assert_not_called()
    sender.side_effect = delivery.DeliveryUnavailable('email_rejected')
    challenge = codes.issue('alice', 'email')
    assert not rows[(codes.COLLECTION, 1)]['delivered']
    assert codes.verify('alice', challenge, sender.call_args.args[2]) is None


@pytest.mark.parametrize('data', [
    {'email': 'a'*255+'@example.test'}, {'email': 'a\n@example.test'},
    {'phone': '900000000'}, {'phone': '+0123456789'},
    {'restrictions': ['inventada']}, {'restrictions': 'vegano'},
])
def test_profile_rejects_invalid_contact_and_restrictions(data):
    with pytest.raises(ValueError):
        normalize_profile_patch(data)


def test_private_upload_reencoding_and_limits(tmp_path):
    app = Flask(__name__, instance_path=str(tmp_path))
    raw = io.BytesIO()
    Image.new('RGB', (20, 20)).save(raw, 'PNG')
    with app.app_context():
        name = save_profile_image(FileStorage(stream=io.BytesIO(raw.getvalue()), filename='../../bad.svg'), 1, 'avatar')
        assert len(name) == 52 and name.endswith('.jpg')
        assert (tmp_path / 'profile_images' / '1' / name).is_file()
        assert not (tmp_path / 'profile_images' / '2').exists()
        for data in (b'<svg>active</svg>', b'x'*(2*1024*1024+1)):
            with pytest.raises(ValueError):
                save_profile_image(FileStorage(stream=io.BytesIO(data)), 1, 'avatar')


@pytest.mark.parametrize('channel,status', [('email', 202), ('sms', 201)])
def test_provider_requests_are_mocked(monkeypatch, channel, status):
    for key, value in {'RESEND_API_KEY': 'synthetic', 'SECURITY_FROM_EMAIL': 'onboarding@resend.dev',
                       'SECURITY_EMAIL_PROVIDER': 'resend', 'TWILIO_ACCOUNT_SID': 'AC'+'0'*32,
                       'TWILIO_AUTH_TOKEN': 'synthetic', 'TWILIO_FROM_NUMBER': '+15005550006'}.items():
        monkeypatch.setenv(key, value)
    post = Mock(return_value=Mock(status_code=status))
    monkeypatch.setattr(delivery.requests, 'post', post)
    assert delivery.configured(channel)
    delivery.send_code(channel, '+51900000000' if channel == 'sms' else 'alice@example.test', '123456', 'test-delivery')
    assert post.call_args.kwargs['allow_redirects'] is False
    post.return_value.status_code = 403
    with pytest.raises(delivery.DeliveryUnavailable):
        delivery.send_code(channel, '+51900000000' if channel == 'sms' else 'alice@example.test', '123456', 'test-delivery')


def test_routes_keep_code_state_and_ignore_client_verification(store, monkeypatch):
    from views.auth import auth_bp
    import views.auth as auth
    rows, sender = store
    monkeypatch.setattr(auth.protection, 'allow_attempt', lambda *args: True)
    monkeypatch.setattr(auth, 'render_template', lambda template, **kwargs: kwargs.get('state', {}).get('step', 'request'))
    app = Flask(__name__)
    app.secret_key = 'synthetic-unit-test-session-key-only'
    app.register_blueprint(auth_bp, url_prefix='/auth')
    client = app.test_client()
    response = client.post('/auth/recuperar', data={'action': 'send_code', 'username': 'alice', 'channel': 'email'})
    assert response.status_code == 302
    assert client.get('/auth/recuperar').data == b'code'
    assert client.get('/auth/recuperar').data == b'code'
    client.post('/auth/recuperar', data={'action': 'reset_password', 'verified': 'true', 'password': 'Password123'})
    assert 'password' not in rows[('users', 1)]
    client.post('/auth/recuperar', data={'action': 'verify_code', 'code': sender.call_args.args[2]})
    assert client.get('/auth/recuperar').data == b'password'
    assert client.get('/auth/recuperar').headers['Cache-Control'] == 'no-store, private'


def test_profile_photo_only_own_account(monkeypatch, tmp_path):
    from views.auth import auth_bp
    from utils import security
    import views.auth as auth
    monkeypatch.setattr(security, 'fresh_session_user', lambda: {'id': 1})
    other_name = 'a'*48 + '.jpg'
    own_name = 'b'*48 + '.jpg'
    for uid, name in ((1, own_name), (2, other_name)):
        folder = tmp_path / 'profile_images' / str(uid)
        folder.mkdir(parents=True)
        (folder / name).write_bytes(b'own' if uid == 1 else b'other')
    monkeypatch.setattr(auth.UserModel, 'get_by_id', lambda uid: {'profile': {'avatar': own_name}})
    app = Flask(__name__, instance_path=str(tmp_path))
    app.register_blueprint(auth_bp, url_prefix='/auth')
    client = app.test_client()
    assert client.get('/auth/profile/photo/avatar?user_id=2').data == b'own'
    assert client.get('/auth/profile/photo/invalid').status_code == 404
    monkeypatch.setattr(security, 'fresh_session_user', lambda: None)
    assert client.get('/auth/profile/photo/avatar').status_code == 401


def test_validated_restrictions_feed_existing_recommendation_evidence():
    from logic.hybrid_recommender import explain_detail
    profile = normalize_profile_patch({'restrictions': ['celiaco', 'alergia mariscos']})
    result = explain_detail({'dietary_restrictions': ['sin gluten']}, profile, [])
    assert not result['compatible']
    assert any('alergia mariscos' in value for value in result['exclusions'])
    assert result['dietary_options']['gluten_free']


def test_recovery_rate_limit_keeps_state(store, monkeypatch):
    from views.auth import auth_bp
    import views.auth as auth
    monkeypatch.setattr(auth.protection, 'allow_attempt', lambda *args: False)
    monkeypatch.setattr(auth, 'render_template', lambda template, **kwargs: kwargs['state']['step'])
    app = Flask(__name__)
    app.secret_key = 'synthetic-unit-test-session-key-only'
    app.register_blueprint(auth_bp, url_prefix='/auth')
    client = app.test_client()
    with client.session_transaction() as session:
        session['password_recovery'] = {'username': 'alice', 'challenge': 'local', 'step': 'code'}
    response = client.post('/auth/recuperar', data={'action': 'verify_code', 'code': '123456'})
    assert response.status_code == 429 and response.data == b'code'
    store[1].assert_not_called()


def test_recovery_template_stable_and_explicit_states():
    text = (Path(__file__).resolve().parents[1] / 'templates/auth/recovery.html').read_text(encoding='utf-8')
    assert 'data-recovery-step="code"' in text
    assert 'data-recovery-step="password"' in text
    assert 'verify_code' in text and 'reset_password' in text
    assert 'setInterval' not in text and 'location.reload' not in text
