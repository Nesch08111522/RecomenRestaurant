from uuid import uuid4

import pytest
from app import create_app
from database.repository import PostgresDocumentRepository as Repo
from logic.market import MarketError
from models.market import kitchen, place_order, save_kitchen, transition
from models.user import UserModel
from test_market_transactions import sale


def test_coupon_diet_and_delivery_workflow(sale):
    rid, offer, slot = sale
    store = kitchen(rid)
    store.update(channels=["Delivery"], zones=["Moche"], coupon={"code":"BARRIO","percent":20,"until":slot.date().isoformat()})
    save_kitchen(store)
    buyer = UserModel.create({"username":uuid4().hex,"role":"user","profile":{"restrictions":["vegano"]}})
    args = [buyer["id"],rid,{offer:1},"Delivery",["Moche","Calle de prueba"],slot,str(uuid4()),"Contraentrega"]
    with pytest.raises(MarketError):
        place_order(*args, coupon_code="BARRIO")
    assert Repo.get_by_id("market_offers",offer)["stock"] == 2
    Repo.update("market_offers",offer,{"diets":["Vegano"]})
    with pytest.raises(MarketError):
        place_order(*args, coupon_code="VENCIDO")
    order = place_order(*args, expected=1200, coupon_code="BARRIO")
    assert place_order(*args, expected=1200, coupon_code="BARRIO")["id"] == order["id"]
    assert (order["discount"],order["total"]) == (300,1200)
    for state in ("Confirmado","Preparando","Listo"):
        order = transition(order,state)
    with pytest.raises(MarketError):
        transition(order,"Entregado")
    order = transition(order,"En reparto")
    assert transition(order,"Entregado")["paid"]
    assert Repo.get_by_id("market_offers",offer)["stock"] == 1


def test_merchant_reports_and_shared_page(sale):
    rid, offer, slot = sale
    owner = UserModel.create({"username":uuid4().hex,"role":"business_owner"})
    Repo.update("restaurants",rid,{"owner_id":owner["id"],"district":"Moche"})
    client = create_app({"TESTING":True,"SECRET_KEY":uuid4().hex}).test_client()
    with client.session_transaction() as s:
        s["user_id"] = owner["id"]
    report = client.get(f"/owner/dashboard?rid={rid}")
    assert report.status_code == 200 and f'data-public="/restaurant/{rid}"'.encode() in report.data
    assert client.get(f"/owner/dashboard?rid={rid+999999}").status_code == 404
    detail = client.get(f"/restaurant/{rid}")
    assert detail.status_code == 200 and b'property="og:title"' in detail.data
    assert client.get(f"/mercado/oferta/{offer}").status_code == 200
