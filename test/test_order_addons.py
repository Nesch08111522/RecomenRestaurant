from uuid import uuid4

import pytest
from app import create_app
from database.repository import PostgresDocumentRepository as Repo
from logic.market import MarketError
from logic.order_addons import resolve
from models.market import kitchen, place_order, save_kitchen, transition
from models.salon import save_table, open_session
from test_market_transactions import sale
from service_fixtures import make_user


def setup_addon(offer):
    listing = Repo.get_by_id('market_offers', offer)
    Repo.update('dishes', listing['dish_id'], {'addons':[dict(name='Ensalada', price_cents=250, stock=2)]})
    return listing['dish_id']


def test_addons_price_stock_retry_cancel_and_stale_total(sale):
    rid, offer, slot = sale
    did = setup_addon(offer)
    args = (750002, rid, {offer:1}, 'Recojo', [], slot, str(uuid4()), 'Contraentrega')
    with pytest.raises(MarketError):
        place_order(*args, expected=1500, addons={offer:['Ensalada']})
    assert Repo.get_by_id('dishes', did)['addons'][0]['stock'] == 2
    order = place_order(*args, expected=1750, addons={offer:['Ensalada']})
    assert order['total'] == 1750 and order['lines'][0]['addons'][0]['price_cents'] == 250
    assert order['lines'][0]['cost'] is None
    assert Repo.get_by_id('dishes', did)['addons'][0]['stock'] == 1
    assert place_order(*args, expected=1750, addons={offer:['Ensalada']})['id'] == order['id']
    transition(order, 'Cancelado', buyer=True)
    assert Repo.get_by_id('dishes', did)['addons'][0]['stock'] == 2


@pytest.mark.parametrize('selected', [['Inventado'], ['Ensalada','Ensalada'], [{'name':'Ensalada','price':0}]])
def test_invalid_addon_selections_rejected(selected):
    with pytest.raises(MarketError):
        resolve({'addons':[dict(name='Ensalada', price_cents=250, stock=1)]}, selected, 1)


def test_addon_insufficient_stock_and_restrictions():
    dish = {'addons':[dict(name='Ensalada', price_cents=250, stock=1)]}
    with pytest.raises(MarketError):
        resolve(dish, ['Ensalada'], 2)
    with pytest.raises(MarketError):
        resolve(dish, ['Ensalada'], 1, restricted=True)


def test_addon_configuration_owner_and_business_scope(sale):
    rid, offer, slot = sale
    did = setup_addon(offer)
    owner = make_user(uuid4().hex, 'business_owner')
    other = make_user(uuid4().hex, 'business_owner')
    Repo.update('restaurants', rid, {'owner_id':owner['id']})
    client = create_app(dict(TESTING=True, SECRET_KEY=uuid4().hex, WTF_CSRF_ENABLED=False)).test_client()
    data = dict(dish=did, name='Ensalada', price='3', stock=4)
    with client.session_transaction() as s:
        s['user_id'] = other['id']
    assert client.post(f'/mercado/cocina/{rid}/adicional', data=data).status_code == 403
    with client.session_transaction() as s:
        s['user_id'] = owner['id']
    assert client.post(f'/mercado/cocina/{rid}/adicional', data={**data,'dish':did+999999}).status_code == 404
    assert client.post(f'/mercado/cocina/{rid}/adicional', data=data).status_code == 302
    assert Repo.get_by_id('dishes', did)['addons'][0]['price_cents'] == 300
    assert Repo.get_by_id('dishes', did)['addons'][0]['stock'] == 4


def test_salon_addons_are_priced_in_cart_and_persisted(sale):
    rid, offer, slot = sale
    setup_addon(offer)
    owner = make_user(uuid4().hex, 'business_owner')
    diner = make_user(uuid4().hex)
    Repo.update('restaurants', rid, {'owner_id':owner['id']})
    store = kitchen(rid)
    store.update(channels=['Local'])
    save_kitchen(store)
    from logic.market import now
    Repo.update('market_offers', offer, {'day':now().date().isoformat(), 'ends':now().replace(hour=23,minute=59).isoformat()})
    table = save_table(rid, owner['id'], dict(label='Addon', capacity=2))
    visit = open_session(table, uid=diner['id'], party_size=1, name='Cliente', actor=owner['id'])
    app = create_app(dict(TESTING=True, SECRET_KEY=uuid4().hex, WTF_CSRF_ENABLED=False))
    client = app.test_client()
    with client.session_transaction() as s:
        s['user_id'] = diner['id']
    token = table['qr_token']
    stranger = app.test_client()
    with stranger.session_transaction() as s:
        s['user_id'] = owner['id']
    assert stranger.post(f'/mesa/{token}/pedido', data={'total':1750}).status_code == 403
    assert client.post(f'/mesa/{token}/carrito', data={'offer':offer,'qty':1,'addon':'Ensalada'}).status_code == 302
    page = client.get(f'/mesa/{token}/carrito')
    assert page.status_code == 200 and b'Ensalada' in page.data
    assert client.post(f'/mesa/{token}/pedido', data={'total':1750}).status_code == 302
    orders = [r for r in Repo.all('market_orders') if r.get('table_session') == visit['id']]
    assert orders[0]['total'] == 1750 and orders[0]['lines'][0]['addons'][0]['name'] == 'Ensalada'
