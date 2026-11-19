from datetime import date, timedelta
import pytest
from models.company import subscription_allows, CAPABILITIES, permitted


def company(plan='basic', **values):
    return {'id': 1, 'status': 'active', 'metadata': {'subscription': {'plan': plan, 'status': 'active', **values}}}


@pytest.mark.parametrize('plan,level', [('basic', 0), ('decente', 1), ('premium', 2)])
def test_capability_matrix(plan, level):
    for permission, required in CAPABILITIES.items():
        assert subscription_allows(company(plan), permission) == (level >= required)


def test_expired_disabled_and_unknown_fail_closed():
    assert not subscription_allows(None, 'catalog.manage')
    assert not subscription_allows(company('unknown'), 'catalog.manage')
    assert not subscription_allows(company('premium'), 'invented.module')
    assert not subscription_allows(company(expires_on=(date.today()-timedelta(days=1)).isoformat()), 'catalog.manage')
    assert not subscription_allows(company(expires_on='bad'), 'catalog.manage')
    assert not subscription_allows(company(disabled=['catalog.manage']), 'catalog.manage')
    assert not subscription_allows(company(status='suspended'), 'catalog.manage')


def test_role_and_company_intersection(monkeypatch):
    from models.user import UserModel
    from models.restaurant import RestaurantModel
    import models.company as model
    monkeypatch.setattr(UserModel, 'get_by_id', lambda uid: {'id': uid, 'role': 'business_owner'})
    monkeypatch.setattr(RestaurantModel, 'get_by_id', lambda rid: {'id': rid, 'owner_id': 7})
    monkeypatch.setattr(model, 'company_for_restaurant', lambda rid: company())
    assert permitted({'id': 7}, 1, 'catalog.manage')
    assert not permitted({'id': 7}, 1, 'ai.business')
    monkeypatch.setattr(model, 'company_for_restaurant', lambda rid: company('premium'))
    assert permitted({'id': 7}, 1, 'ai.business')
    monkeypatch.setattr(UserModel, 'get_by_id', lambda uid: {'id': uid, 'role': 'admin', 'status': 'SUSPENDED'})
    assert not permitted({'id': 7}, 1, 'catalog.manage')


def test_bootstrap_disposable(isolated_database, monkeypatch):
    from config import Config
    from app import create_app
    from scripts.company_bootstrap import bootstrap
    from database.repository import PostgresDocumentRepository as Repo
    from models.company import companies
    monkeypatch.setattr(Config, 'DATABASE_URL', isolated_database)
    application = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'SECRET_KEY': 'disposable-company-test-key'})
    with application.app_context():
        result = bootstrap(True)
        assert len(result['created_users']) == 3
        assert len(result['created_restaurants']) == 3
        assert len(companies()) == 3
        again = bootstrap(True)
        assert not again['changed']
        users = Repo.all('users')
        assert all(u.get('activation_pending') and not u['profile']['email'] for u in users)
        uid = users[0]['id']
        admin = Repo.create('users', {'username': 'test-admin', 'role': 'admin'})
    client = application.test_client()
    with client.session_transaction() as session:
        session['user_id'] = admin['id']
    assert client.get('/admin/empresas').status_code == 200
    assert client.post('/admin/empresas', data={'id': companies()[0]['id'], 'plan': 'premium', 'status': 'active'}).status_code == 400
    response = client.post('/admin/empresas/activacion/'+str(uid), data={'confirm': 'yes'})
    assert response.status_code == 200
    assert 'no-store' in response.headers['Cache-Control']
    import re
    link = re.search(rb'/activar-empresa#([^" ]+)', response.data)[1].decode()
    token, challenge, username = link.split(':')
    client.post('/auth/logout')
    assert client.post('/activar-empresa', data={'token': token, 'challenge': challenge, 'username': username, 'password': 'Personal123!'}).status_code == 302
    assert client.post('/activar-empresa', data={'token': token, 'challenge': challenge, 'username': username, 'password': 'Personal123!'}).status_code == 400
