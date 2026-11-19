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
    assert data["earned"] == 0


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


def test_concurrent_birthday_claim_is_unique(service_db):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    diner = make_user("concurrent12", profile={"birthday": now().date().isoformat()})
    barrier = Barrier(2)

    def claim(index):
        barrier.wait(timeout=10)
        try:
            return birthday_claim(diner["id"])["points"]
        except ValueError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, range(2)))
    assert results.count(50) == 1
    assert results.count("duplicate") == 1
    assert len(events(diner["id"])) == 1


def test_refunded_visit_no_longer_counts_for_badges_or_history(service_db):
    owner = make_user("refundvisit12", "business_owner")
    business = make_business(owner["id"], "Visita revertida")
    diner = make_user("refunddiner12")
    session = closed_session(diner["id"], business["id"])
    paid_order = next(o for o in Repo.all("market_orders") if o.get("table_session") == session["id"])
    Repo.update("market_orders", paid_order["id"], {"refunded": True})
    data = wallet(diner["id"])
    assert data["balance"] == 0
    assert data["visits"] == [] and data["badges"] == []
    assert visits(diner["id"]) == []


def test_hidden_visits_are_not_exposed_in_business_segments(service_db):
    owner = make_user("privacyowner12", "business_owner")
    business = make_business(owner["id"], "Privacidad")
    diner = make_user("privacydiner12")
    order(diner["id"], business["id"])
    save_preferences(diner["id"], marketing=False, visits_visible=False, birthday_visible=False)
    assert owner_customers(business["id"])["customers"] == []
    assert wallet(diner["id"])["balance"] == 2
    save_preferences(diner["id"], marketing=False, visits_visible=True, birthday_visible=False)
    assert owner_customers(business["id"])["customers"][0]["marketing_allowed"] is False


def test_birthday_claim_respects_explicit_opt_out(service_db):
    diner = make_user("optoutbirthday12", profile={"birthday": now().date().isoformat(),
                                                "loyalty": {"birthday_visible": False}})
    with pytest.raises(ValueError, match="consentimiento"):
        birthday_claim(diner["id"])
    assert events(diner["id"]) == []


def test_customer_reservations_cancel_only_own_future_booking(service_db):
    from models.reservation import ReservationModel
    from logic.market import MarketError
    from app import create_app

    owner = make_user("reservationowner12", "business_owner")
    business = make_business(owner["id"], "Reservas")
    make_store(business["id"])
    diner = make_user("reservationdiner12")
    other = make_user("reservationother12")
    future = now() + timedelta(days=1)
    booking = ReservationModel.create(diner["id"], business["id"], future.date().isoformat(), "12:00", 2)
    with pytest.raises(MarketError):
        ReservationModel.cancel_for_user(booking["id"], other["id"])
    assert ReservationModel.get_by_id(booking["id"])["status"] == "pendiente"
    client = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex, "WTF_CSRF_ENABLED": False}).test_client()
    with client.session_transaction() as session:
        session["user_id"] = diner["id"]
    response = client.post(f"/restaurant/{business['id']}/reserve",
                           data={"date": future.date().isoformat(), "time": "13:00", "guests": 2})
    assert response.status_code == 302
    assert len(ReservationModel.get_by_user(diner["id"])) == 2
    page = client.get("/mis-reservas")
    assert page.status_code == 200 and str(booking["id"]).encode() in page.data
    result = client.post(f"/mis-reservas/{booking['id']}/cancelar")
    assert result.status_code == 302
    assert ReservationModel.get_by_id(booking["id"])["status"] == "cancelada"
    assert ReservationModel.cancel_for_user(booking["id"], diner["id"])["status"] == "cancelada"


def test_reservation_validation_and_audit_rollback(service_db, monkeypatch):
    from models.reservation import ReservationModel
    from logic.market import MarketError
    from utils import audit

    owner = make_user("validationowner12", "business_owner")
    business = make_business(owner["id"], "Validacion reservas")
    make_store(business["id"])
    diner = make_user("validationdiner12")
    future = now() + timedelta(days=1)
    for guests in (0, 21, True, "2"):
        with pytest.raises(MarketError):
            ReservationModel.create(diner["id"], business["id"], future.date().isoformat(), "12:00", guests)
    with pytest.raises(MarketError):
        ReservationModel.create(diner["id"], business["id"], "invalid", "12:00", 2)
    with pytest.raises(MarketError):
        ReservationModel.create(diner["id"], business["id"], (now() - timedelta(days=1)).date().isoformat(), "12:00", 2)
    booking = ReservationModel.create(diner["id"], business["id"], future.date().isoformat(), "12:00", 2)
    monkeypatch.setattr(audit, "record_event", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("audit unavailable")))
    with pytest.raises(RuntimeError, match="audit unavailable"):
        ReservationModel.cancel_for_user(booking["id"], diner["id"])
    assert ReservationModel.get_by_id(booking["id"])["status"] == "pendiente"
    Repo.update("restaurants", business["id"], {"status": "suspended"})
    with pytest.raises(MarketError):
        ReservationModel.create(diner["id"], business["id"], future.date().isoformat(), "13:00", 2)


def test_visits_history_contains_dishes_and_total(service_db):
    owner = make_user("owner12e", "business_owner")
    business = make_business(owner["id"], "Visitas")
    make_store(business["id"])
    diner = make_user("diner12e")
    closed_session(diner["id"], business["id"], total=2500)
    rows = visits(diner["id"])
    assert rows[0]["total"] == 2500
    assert ("Arroz con pollo", 1) in rows[0]["dishes"]