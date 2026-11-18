from copy import deepcopy
import pytest
from app import create_app
from core.profile import normalize_profile_patch
from models.user import UserModel


@pytest.mark.parametrize('patch', [
    {'location_consent': 'false'},
    {'cookies_consent': 1},
    {'notification_preferences': {'marketing': 'false'}},
])
def test_consent_requires_real_json_boolean(patch):
    with pytest.raises(ValueError):
        normalize_profile_patch(patch)


def test_patch_preserves_existing_private_profile(monkeypatch):
    account = {'id': 71, 'username': 'test-diner', 'role': 'user', 'status': 'ACTIVE',
               'profile': {'name': 'Ana', 'email': 'ana@example.com',
                           'restrictions': ['sin gluten'], 'addresses': ['Av. Perú 120'],
                           'weekly_budget': 210,
                           'notification_preferences': {'marketing': True, 'reviews': True}}}
    monkeypatch.setattr(UserModel, 'get_by_id', lambda uid: deepcopy(account) if uid == 71 else None)
    def save(uid, changes):
        assert uid == 71
        account.update(deepcopy(changes))
        return deepcopy(account)
    monkeypatch.setattr(UserModel, 'update', save)
    client = create_app({'TESTING': True, 'SECRET_KEY': 'x' * 32,
                         'WTF_CSRF_ENABLED': False}).test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 71
    response = client.patch('/api/platform/me/profile', json={
        'daily_budget': 35, 'notification_preferences': {'marketing': False}})
    assert response.status_code == 200
    profile = response.json['profile']
    assert profile['restrictions'] == ['sin gluten']
    assert profile['addresses'] == ['Av. Perú 120']
    assert profile['weekly_budget'] == 210
    assert profile['daily_budget'] == 35
    assert profile['notification_preferences'] == {'marketing': False, 'reviews': True}
    assert account['profile']['promotions_opt_in'] is False
