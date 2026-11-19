from datetime import timedelta
from uuid import uuid4

import pytest

from database.repository import PostgresDocumentRepository as Repo
from logic.market import now
from models.loyalty import (birthday_claim, events, level_for, owner_customers,
                            review_session, save_preferences, visits, wallet)
from models.salon import save_table
from models.user import UserModel
from service_fixtures import make_business, make_store, make_user


def order(uid, rid, total=2500, state="Entregado", paid=True, refunded=False,
          table_session=None, days_ago=0, name="Ana"):
    at = now() - timedelta(days=days_ago)
    payload = {
        "uid": uid, "rid": rid, "business": name, "total": total, "state": state,
        "paid": paid, "refunded": refunded, "created": at.isoformat(),
        "slot": at.isoformat(), "day": at.date().isoformat(), "channel": "Local",
        "lines": [{"name": "Arroz con pollo", "qty": 1, "unit": total, "cost": 50,
                   "saving": 0, "usage": {}, "offer": None, "dish_id": 1}],
        "history": [{"state": state, "at": at.isoformat()}], "method": "Cuenta",
    }
    if table_session:
        payload["table_session"] = table_session
    return Repo.create("market_orders", payload)


def closed_session(uid, rid, total=2500, days_ago=0, paid=True):
    owner = make_user(f"staff{uuid4().hex[:6]}", "business_owner")
    table = save_table(rid, owner["id"], {"label": uuid4().hex[:6], "capacity": 4})
    at = now() - timedelta(days=days_ago)
    session = Repo.create("table_sessions", {
        "rid": rid, "table_id": table["id"], "token": uuid4().hex, "uid": uid,
        "party_size": 2, "status": "Finalizada", "opened_at": (at - timedelta(minutes=50)).isoformat(),
        "closed_at": at.isoformat(), "cleaned_at": at.isoformat(), "paid": paid,
        "total": total, "order_ids": [],
    })
    order(uid, rid, total=total, table_session=session["id"], days_ago=days_ago)
    return session


def test_points_come_only_from_paid_orders_and_real_visits(service_db):
    owner = make_user("owner12", "business_owner")
    business = make_business(owner["id"], "Puntos Norteño")
    make_store(business["id"])
    diner = make_user("diner12")
    order(diner["id"], business["id"], total=2500)
    order(diner["id"], business["id"], total=9000, state="Cancelado", paid=False)
    order(diner["id"], business["id"], total=1200, state="Entregado", paid=False)
    closed_session(diner["id"], business["id"], total=2500)
    data = wallet(diner["id"])
    assert data["balance"] == 14  # 2 por cada compra pagada (dos) + 10 por la visita
    assert len(data["visits"]) == 1
    assert data["badges"] == ["Primera visita"]


def test_refund_reverses_purchase_points(service_db):
    owner = make_user("owner12b", "business_owner")
    business = make_business(owner["id"], "Reembolso")
    make_store(business["id"])
    diner = make_user("diner12b")
    order(diner["id"], business["id"], total=3000, refunded=True)
    data = wallet(diner["id"])
    kinds = [row["kind"] for row in data["events"]]
    assert "Compra" in kinds and "Reversión por reembolso" in kinds
    assert data["balance"] == 0


def test_levels_are_derived_from_lifetime_points():
    assert level_for(0)["name"] == "Bronce"
    assert level_for(200)["name"] == "Plata"
    assert level_for(500)["name"] == "Oro"
    assert level_for(1200)["name"] == "Diamante"
    assert level_for(1200)["next"] is None


def test_birthday_benefit_once_per_year(service_db):
    diner = make_user("birthday12", profile={"birthday": now().date().isoformat()})
    row = birthday_claim(diner["id"])
    assert row["points"] == 50
    with pytest.raises(ValueError):
        birthday_claim(diner["id"])


def test_birthday_requires_the_actual_day_and_registered_date(service_db):
    diner = make_user("birthday12b")
    with pytest.raises(ValueError):
        birthday_claim(diner["id"])


def test_visit_review_is_verified_and_updates_reputation(service_db):
    owner = make_user("owner12c", "business_owner")
    business = make_business(owner["id"], "Reseña Norteño")
    make_store(business["id"])
    diner = make_user("diner12c")
    session = closed_session(diner["id"], business["id"])
    review = review_session(session, 5, "Excelente atención")
    assert review["session_id"] == session["id"]
    saved = Repo.get_by_id("table_sessions", session["id"])
    assert saved["review"] == review["id"]
    with pytest.raises(ValueError):
        review_session(saved, 4, "Otra vez")


def test_owner_customer_segments_use_real_orders(service_db):
    owner = make_user("owner12d", "business_owner")
    business = make_business(owner["id"], "Clientes")
    make_store(business["id"])
    one = make_user("one12")
    two = make_user("two12")
    for _ in range(3):
        order(one["id"], business["id"], total=1000, days_ago=5)
    order(two["id"], business["id"], total=1000, days_ago=120)
    data = owner_customers(business["id"])
    assert data["frequent"] == 1
    assert data["inactive"] == 1
    assert data["new"] == 1


def test_loyalty_preferences_are_independent(service_db):
    diner = make_user("prefs12")
    save_preferences(diner["id"], marketing=True, visits_visible=False, birthday_visible=True)
    profile = UserModel.get_by_id(diner["id"])["profile"]
    assert profile["loyalty"] == {"marketing": True, "visits_visible": False, "birthday_visible": True}


def test_visits_history_contains_dishes_and_total(service_db):
    owner = make_user("owner12e", "business_owner")
    business = make_business(owner["id"], "Visitas")
    make_store(business["id"])
    diner = make_user("diner12e")
    closed_session(diner["id"], business["id"], total=2500)
    rows = visits(diner["id"])
    assert rows[0]["total"] == 2500
    assert ("Arroz con pollo", 1) in rows[0]["dishes"]