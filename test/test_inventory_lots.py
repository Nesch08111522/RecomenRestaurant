from datetime import timedelta
from uuid import uuid4

import pytest
from app import create_app
from logic.market import MarketError, available, now
from logic.inventory_lots import consume, restore
from models.market import kitchen, place_order, save_kitchen, transition
from database.repository import PostgresDocumentRepository as Repo
from test_market_transactions import sale
from service_fixtures import make_user


def ingredient(rotation='FEFO'):
    return dict(unit='g', quantity=300, expires='2030-01-01', cost=100, basis=100, lot='early', rotation=rotation,
                lots=[dict(lot='later', quantity=200, expires='2030-01-03', cost=200, basis=100, received_at='2026-01-01'),
                      dict(lot='early', quantity=100, expires='2030-01-01', cost=100, basis=100, received_at='2026-01-02')])


@pytest.mark.parametrize('rotation,first', [('FEFO', 'early'), ('FIFO', 'later')])
def test_rotation_cost_and_restore(rotation, first):
    stock = ingredient(rotation)
    usage, cost = consume(stock, 150, '2029-01-01')
    assert usage[0]['lot'] == first
    assert stock['quantity'] == 150
    assert int(cost) == (200 if rotation == 'FEFO' else 300)
    restore(stock, usage)
    assert stock['quantity'] == 300


def test_expired_batches_are_not_available():
    stock = ingredient()
    assert available(dict(day='2030-01-02', stock=10, recipe={'arroz':100}), {'arroz':stock}, '2030-01-02') == 2
    with pytest.raises(MarketError):
        consume(stock, 250, '2030-01-02')
    assert stock['quantity'] == 300


def test_sale_consumes_multiple_batches_and_cancel_restores_originals(sale):
    rid, offer, slot = sale
    stock = ingredient()
    for batch in stock['lots']:
        batch['expires'] = (slot.date() + timedelta(days=1 if batch['lot'] == 'early' else 3)).isoformat()
    store = kitchen(rid)
    store['pantry'] = {'arroz': stock}
    save_kitchen(store)
    Repo.update('market_offers', offer, {'recipe': {'arroz':150}})
    order = place_order(750002, rid, {offer:1}, 'Recojo', [], slot, str(uuid4()), 'Contraentrega')
    assert [r['amount'] for r in order['lines'][0]['usage']['arroz']['lots']] == [100,50]
    assert order['lines'][0]['cost'] == 200
    assert kitchen(rid)['pantry']['arroz']['quantity'] == 150
    transition(order, 'Cancelado', buyer=True)
    assert kitchen(rid)['pantry']['arroz']['quantity'] == 300
    assert [r['quantity'] for r in kitchen(rid)['pantry']['arroz']['lots']] == [200,100]


def test_inventory_http_adds_batches_without_changing_name_and_denies_other_owner(sale):
    rid, offer, slot = sale
    owner = make_user(uuid4().hex, 'business_owner')
    other = make_user(uuid4().hex, 'business_owner')
    Repo.update('restaurants', rid, {'owner_id': owner['id']})
    app = create_app(dict(TESTING=True, SECRET_KEY=uuid4().hex, WTF_CSRF_ENABLED=False))
    client = app.test_client()
    data = dict(name='arroz', move='Entrada', quantity=100, unit='g', expires=slot.date().isoformat(), cost='1', basis=100, rotation='FEFO')
    with client.session_transaction() as s:
        s['user_id'] = other['id']
    assert client.post(f'/mercado/cocina/{rid}/inventario', data=data).status_code in (403,404)
    with client.session_transaction() as s:
        s['user_id'] = owner['id']
    assert client.post(f'/mercado/cocina/{rid}/inventario', data=data).status_code == 302
    assert client.post(f'/mercado/cocina/{rid}/inventario', data={**data, 'cost':'2'}).status_code == 302
    stock = kitchen(rid)['pantry']['arroz']
    assert len(stock['lots']) == 2 and stock['quantity'] == 200
    result = client.post(f'/mercado/cocina/{rid}/inventario', data={**data, 'move':'Merma', 'quantity':150, 'lot_id':stock['lots'][0]['lot']})
    assert result.status_code == 400
    assert kitchen(rid)['pantry']['arroz']['quantity'] == 200
