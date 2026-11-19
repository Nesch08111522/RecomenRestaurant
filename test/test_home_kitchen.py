from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from app import create_app
from database.repository import PostgresDocumentRepository as Repo
from logic.market import MarketError, now
from models import home_kitchen as home
from service_fixtures import make_user


def recipe(uid, confirmed=True):
    return home.save_recipe(uid, dict(name='Arroz declarado', ingredients=[dict(name='arroz', quantity=100, unit='g')],
                                     steps=['Seguir la coccion declarada por el usuario.'], servings=1, confirmed=confirmed))


def pantry(uid, quantity=200, days=3):
    return home.save_pantry(uid, dict(name='arroz', unit='g', quantity=quantity,
                                    expires=(now().date() + timedelta(days=days)).isoformat()))


def test_pantry_crud_and_owner_scope(service_db):
    uid = make_user(uuid4().hex)['id']
    other = make_user(uuid4().hex)['id']
    row = pantry(uid)
    with pytest.raises(MarketError):
        home.save_pantry(other, row, row['id'])
    with pytest.raises(MarketError):
        home.remove(other, 'home_pantry', row['id'])
    changed = home.save_pantry(uid, {**row, 'quantity': 40}, row['id'])
    assert changed['quantity'] == 40
    home.remove(uid, 'home_pantry', row['id'])
    assert home.rows('home_pantry', uid) == []


@pytest.mark.parametrize('changes', [{'quantity': -1}, {'quantity': 'NaN'}, {'unit': 'kg'}, {'expires': 'bad'}])
def test_pantry_rejects_invalid_data(service_db, changes):
    with pytest.raises(MarketError):
        home.save_pantry(99, {**dict(name='arroz', quantity=10, unit='g', expires=now().date().isoformat()), **changes})


def test_draft_recipe_cannot_prepare_or_plan(service_db):
    uid = make_user(uuid4().hex)['id']
    r = recipe(uid, False)
    with pytest.raises(MarketError):
        home.prepare(uid, r['id'], 1, str(uuid4()))
    with pytest.raises(MarketError):
        home.plan(uid, r['id'], now().date().isoformat(), 'Almuerzo')


def test_preparation_fefo_retry_and_atomic_shortage(service_db):
    uid = make_user(uuid4().hex)['id']
    r = recipe(uid)
    expired = pantry(uid, 1000, -1)
    first = pantry(uid, 70, 1)
    second = pantry(uid, 150, 3)
    request_key = str(uuid4())
    result = home.prepare(uid, r['id'], 1, request_key)
    assert [u['quantity'] for u in result['usage']] == [70, 30]
    assert Repo.get_by_id('home_pantry', expired['id'])['quantity'] == 1000
    assert Repo.get_by_id('home_pantry', first['id'])['quantity'] == 0
    assert home.prepare(uid, r['id'], 1, request_key)['id'] == result['id']
    with pytest.raises(MarketError):
        home.prepare(uid, r['id'], 2, str(uuid4()))
    assert Repo.get_by_id('home_pantry', second['id'])['quantity'] == 120
    assert len(home.rows('home_preparations', uid)) == 1


def test_weekly_shopping_allocates_stock_once_and_preparation_updates_plan(service_db):
    uid = make_user(uuid4().hex)['id']
    r = recipe(uid)
    pantry(uid, 150)
    day = now().date()
    start = day - timedelta(days=day.weekday())
    first = home.plan(uid, r['id'], day.isoformat(), 'Almuerzo')
    home.plan(uid, r['id'], day.isoformat(), 'Cena')
    assert home.shopping(uid, start) == [dict(name='arroz', unit='g', quantity=50)]
    home.prepare(uid, r['id'], 1, str(uuid4()), first['id'])
    assert Repo.get_by_id('home_plan', first['id'])['prepared'] is True
    with pytest.raises(MarketError):
        home.prepare(uid, r['id'], 1, str(uuid4()), first['id'])
    assert home.shopping(uid, start)[0]['quantity'] == 50


def test_concurrent_preparation_cannot_oversell(service_db):
    uid = make_user(uuid4().hex)['id']
    r = recipe(uid)
    pantry(uid, 100)
    barrier = Barrier(2)
    def cook(_):
        barrier.wait(timeout=10)
        try:
            return home.prepare(uid, r['id'], 1, str(uuid4()))
        except MarketError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(cook, range(2)))
    assert sum(r is not None for r in results) == 1
    assert home.rows('home_pantry', uid)[0]['quantity'] == 0


def test_home_http_private_shell_and_cross_user(service_db):
    uid = make_user(uuid4().hex)['id']
    other = make_user(uuid4().hex)['id']
    row = pantry(uid)
    app = create_app(dict(TESTING=True, SECRET_KEY=uuid4().hex, WTF_CSRF_ENABLED=False))
    client = app.test_client()
    assert client.get('/home/').status_code == 401
    with client.session_transaction() as s:
        s['user_id'] = other
    response = client.get('/home/')
    assert response.status_code == 200 and b'sr-saas-private' in response.data
    assert b'aria-label="Cocina en casa"' in response.data
    assert client.post('/home/pantry', json={**row, 'quantity': 0}).status_code == 400
    assert Repo.get_by_id('home_pantry', row['id'])['quantity'] == 200
    with client.session_transaction() as s:
        s['user_id'] = uid
    assert client.get('/home/').status_code == 200


def test_audit_failure_rolls_back_stock(service_db, monkeypatch):
    uid = make_user(uuid4().hex)['id']
    r = recipe(uid)
    row = pantry(uid, 100)
    monkeypatch.setattr(home, 'record_event', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('audit unavailable')))
    with pytest.raises(RuntimeError):
        home.prepare(uid, r['id'], 1, str(uuid4()))
    assert Repo.get_by_id('home_pantry', row['id'])['quantity'] == 100
    assert home.rows('home_preparations', uid) == []
