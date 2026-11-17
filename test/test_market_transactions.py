from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4
import hashlib
import hmac

import pytest

from app import create_app
from database.repository import PostgresDocumentRepository as Repo
from logic.market import MarketError, now
from models.dish import DishModel
from models.market import kitchen, place_order, save_kitchen, transition
from models.restaurant import RestaurantModel
from utils import market_payments as payments


@pytest.fixture
def sale(test_database):
    shop = RestaurantModel.create({"owner_id": 750001, "name": "Prueba de turnos", "verified": True})
    rid = shop["id"]
    slot = (now() + timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)
    store = kitchen(rid)
    store.update(channels=["Recojo"], capacity=1, pantry={})
    save_kitchen(store)
    dish = DishModel.create({"restaurant_id":rid, "name":"Menú", "is_available":True})
    listing = Repo.create("market_offers", {"rid":rid, "dish_id":dish["id"], "stock":2, "recipe":{}, "price":1500,
        "ends":slot.replace(hour=18).isoformat(), "day":slot.date().isoformat()})
    return rid, listing["id"], slot


def test_last_pickup_slot_and_retries(sale):
    rid, offer, slot = sale
    barrier = Barrier(2)
    def submit(uid):
        barrier.wait(timeout=5)
        try:
            return place_order(uid, rid, {offer:1}, "Recojo", [], slot, str(uuid4()), "Contraentrega")
        except MarketError:
            return None
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(submit, [750002,750003]))
    assert sum(r is not None for r in results) == 1
    order = next(r for r in results if r)
    repeat = place_order(order["uid"],rid,{offer:1},"Recojo",[],slot,order["request_key"],"Contraentrega")
    assert repeat["id"] == order["id"]
    assert Repo.get_by_id("market_offers", offer)["stock"] == 1
    transition(order, "Cancelado", buyer=True)
    assert Repo.get_by_id("market_offers", offer)["stock"] == 2


def test_webhook_uses_provider_amount_and_ignores_duplicates(sale, monkeypatch):
    rid, offer, slot = sale
    order = place_order(750002, rid, {offer:1}, "Recojo", [], slot, str(uuid4()), "Digital")
    monkeypatch.setenv("MARKET_PUBLIC_URL", "https://smartresto.example")
    monkeypatch.setenv(f"MP_ACCESS_TOKEN_{rid}", "solo-prueba")
    monkeypatch.setenv("MP_WEBHOOK_SECRET", "clave-local-prueba")
    pid = "123"
    canonical = {"id":123,"metadata":{"order_id":order["id"]},"currency_id":"PEN","transaction_amount":14,
                 "status":"approved","external_reference":payments.reference(order)}
    monkeypatch.setattr(payments,"call",lambda *args,**kwargs: canonical)
    app = create_app({"TESTING":True,"SECRET_KEY":uuid4().hex})
    client = app.test_client()
    signature = hmac.new(b"clave-local-prueba", b"id:123;request-id:abc;ts:1;", hashlib.sha256).hexdigest()
    headers = {"X-Signature":"ts=1,v1="+signature,"X-Request-Id":"abc"}
    path = f"/mercado/pagos/{rid}/notificar?data.id={pid}"
    assert client.post(path).status_code == 403
    assert client.post(path,headers=headers).status_code == 400
    assert not Repo.get_by_id("market_orders",order["id"])["paid"]
    canonical["transaction_amount"] = 15
    for _ in range(2):
        assert client.post(path,headers=headers).status_code == 204
    assert Repo.get_by_id("market_orders",order["id"])["payment_id"] == pid
    assert Repo.get_by_id("market_offers",offer)["stock"] == 1

