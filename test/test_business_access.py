from uuid import uuid4
import pytest
from app import create_app
from models.user import UserModel
from models.restaurant import RestaurantModel
from database.repository import PostgresDocumentRepository as Repo
from models.membership import authorized


def test_branch_permissions_revocation_and_verification(test_database):
    app = create_app({'TESTING': True, 'SECRET_KEY': uuid4().hex, 'WTF_CSRF_ENABLED': False})
    accounts = {}
    clients = {}
    for role in ('business_owner', 'user', 'admin'):
        accounts[role] = UserModel.create({'username': role + uuid4().hex, 'password': 'Password123', 'role': role, 'status': 'ACTIVE'})
        clients[role] = app.test_client()
        with clients[role].session_transaction() as session:
            session['user_id'] = accounts[role]['id']
    shop = RestaurantModel.create({'name': 'Local de prueba', 'owner_id': accounts['business_owner']['id'], 'verified': True})
    other = RestaurantModel.create({'name': 'Otra sucursal', 'owner_id': accounts['business_owner']['id'], 'verified': True})
    url = '/owner/acceso/' + str(shop['id'])
    assert clients['user'].get(url).status_code == 403
    assert clients['business_owner'].get(url).status_code == 200
    form = {'username': accounts['user']['username'], 'role': 'waiter', 'status': 'active'}
    response = clients['business_owner'].post(url, data=form, follow_redirects=True)
    assert Repo.all('branch_memberships'), response.get_data(as_text=True)
    assert authorized(accounts['user'], shop['id'], 'tables.service'), Repo.all('branch_memberships')
    assert not authorized(accounts['user'], other['id'], 'tables.service')
    assert not authorized(accounts['user'], shop['id'], 'staff.manage')
    assert clients['user'].get('/salon/' + str(shop['id'])).status_code == 200
    assert clients['user'].get('/salon/' + str(other['id'])).status_code == 403
    assert clients['business_owner'].post(url, data={**form, 'status': 'revoked'}).status_code == 302
    assert clients['user'].get('/salon/' + str(shop['id'])).status_code == 403
    verify = url + '/verificacion'
    document = {'tax_id': '20123456789', 'legal_name': 'Empresa de prueba', 'evidence': 'https://example.test/private-reference'}
    assert clients['user'].post(verify, data=document).status_code == 403
    assert clients['business_owner'].post(verify, data=document).status_code == 302
    assert clients['business_owner'].post(verify, data=document).status_code == 409
    item = next(v for v in Repo.all('business_verifications') if v['rid'] == shop['id'])
    review = '/admin/verificacion-empresarial'
    decision = {'id': item['id'], 'status': 'approved', 'note': 'Documentación revisada manualmente'}
    assert clients['business_owner'].post(review, data=decision).status_code == 403
    assert clients['admin'].get(review).status_code == 200
    assert clients['admin'].post(review, data=decision).status_code == 302
    assert RestaurantModel.get_by_id(shop['id'])['identity_verified'] is True
    assert clients['admin'].post(review, data=decision).status_code == 409


def test_direct_connection_and_autocommit_blocked(test_database):
    import psycopg
    from database.connection import connection, DatabaseConfigurationError
    with pytest.raises(DatabaseConfigurationError):
        psycopg.connect('postgresql://not-used')
    with pytest.raises(DatabaseConfigurationError):
        with connection(autocommit=True):
            pass
