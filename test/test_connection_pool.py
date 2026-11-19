import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from database.pool import ConnectionPool, PoolBusy, PoolCoolingDown


class FakeConnection:
    closed = False
    broken = False
    autocommit = False
    rollbacks = 0
    def close(self): self.closed = True
    def rollback(self): self.rollbacks += 1


def test_reuses_connection_and_rolls_back_unfinished_work():
    pool = ConnectionPool(FakeConnection)
    conn, born = pool.acquire()
    pool.release(conn, born)
    other, second_born = pool.acquire()
    assert other is conn
    assert second_born == born
    assert conn.rollbacks == 1
    pool.release(other, second_born)
    assert pool.stats()['created'] == 1
    pool.close()
    assert conn.closed


def test_busy_pool_has_bounded_wait_and_recovers():
    pool = ConnectionPool(FakeConnection, maximum=1, timeout=.02)
    conn, born = pool.acquire()
    with pytest.raises(PoolBusy): pool.acquire()
    assert pool.stats()['total'] == 1
    pool.release(conn, born)
    assert pool.acquire()[0] is conn
    pool.release(conn, born)
    pool.close()


def test_discards_broken_connection_without_replaying_queries():
    pool = ConnectionPool(FakeConnection)
    conn, born = pool.acquire()
    conn.broken = True
    pool.release(conn, born)
    other, born = pool.acquire()
    assert other is not conn
    assert conn.closed
    pool.release(other, born)
    pool.close()


def test_auth_failure_cools_down_without_background_retries():
    calls = []
    def fail():
        calls.append(True)
        raise RuntimeError('authentication rejected')
    pool = ConnectionPool(fail, cooldown=30)
    with pytest.raises(RuntimeError): pool.acquire()
    for _ in range(4):
        with pytest.raises(PoolCoolingDown): pool.acquire()
    assert len(calls) == 1
    assert pool.stats()['total'] == 0
    pool.close()


def test_concurrency_respects_connection_budget():
    pool = ConnectionPool(FakeConnection, maximum=2, timeout=2)
    barrier = Barrier(8)
    def work(_):
        barrier.wait()
        conn, born = pool.acquire()
        try:
            time.sleep(.01)
            assert pool.stats()['total'] <= 2
        finally: pool.release(conn, born)
    with ThreadPoolExecutor(max_workers=8) as workers:
        list(workers.map(work, range(8)))
    assert pool.stats()['in_use'] == 0
    assert pool.stats()['created'] <= 2
    pool.close()


def test_idle_connection_expires():
    pool = ConnectionPool(FakeConnection, idle=0)
    conn, born = pool.acquire()
    pool.release(conn, born)
    other, born = pool.acquire()
    assert conn.closed and other is not conn
    pool.release(other, born)
    pool.close()


def test_performance_api_is_admin_only(monkeypatch):
    from app import create_app
    from models.user import UserModel
    import views.companies as companies
    app = create_app({'TESTING':True, 'SECRET_KEY':'x'*32})
    app.before_request_funcs[None].remove(companies.presence)
    client = app.test_client()
    assert client.get('/admin/api/performance').status_code in (302,401,403)
    monkeypatch.setattr(UserModel, 'get_by_id', lambda _: {'id':1,'role':'user','username':'test','profile':{}})
    with client.session_transaction() as session: session['user_id'] = 1
    assert client.get('/admin/api/performance').status_code in (302,401,403)
    monkeypatch.setattr(UserModel, 'get_by_id', lambda _: {'id':1,'role':'admin','username':'test','profile':{}})
    response = client.get('/admin/api/performance')
    assert response.status_code == 200
    assert 'pool' in response.json
    assert b'postgresql://' not in response.data

def test_driver_timeout_returns_safe_503():
    import psycopg
    from app import create_app
    app=create_app({'TESTING':True,'SECRET_KEY':'x'*32})
    @app.get('/api/test-db-outage')
    def outage(): raise psycopg.OperationalError('private-driver-detail')
    response=app.test_client().get('/api/test-db-outage')
    assert response.status_code==503
    assert b'private-driver-detail' not in response.data

def test_public_auth_does_not_query_private_sidebar(monkeypatch):
    from app import create_app
    from database.connection import DatabaseConnectionError
    from models.restaurant import RestaurantModel
    from models.category import CategoryModel
    import context_processors
    from models.site_settings import DEFAULTS
    monkeypatch.setattr(CategoryModel,'all',lambda:[])
    monkeypatch.setattr(context_processors,'site_settings',lambda:dict(DEFAULTS))
    def unavailable(): raise DatabaseConnectionError('private diagnostic')
    monkeypatch.setattr(RestaurantModel,'all',unavailable)
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32}).test_client()
    with client.session_transaction() as session:
        session['user']={'id':1,'role':'admin','username':'test','profile':{}}
    assert client.get('/auth/login').status_code==200


def test_database_error_page_does_not_requery_private_sidebar(monkeypatch):
    from app import create_app
    from database.connection import DatabaseConnectionError
    from models.restaurant import RestaurantModel
    from models.user import UserModel
    from models.category import CategoryModel
    import context_processors
    from models.site_settings import DEFAULTS
    monkeypatch.setattr(CategoryModel,'all',lambda:[])
    monkeypatch.setattr(context_processors,'site_settings',lambda:dict(DEFAULTS))
    def unavailable(): raise DatabaseConnectionError('private diagnostic')
    monkeypatch.setattr(RestaurantModel,'all',unavailable)
    monkeypatch.setattr(UserModel,'get_by_id',lambda _:{'id':1,'role':'admin','username':'test','profile':{}})
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32}).test_client()
    with client.session_transaction() as session:session['user_id']=1
    response=client.get('/admin/dashboard')
    assert response.status_code==503
    assert b'private diagnostic' not in response.data
