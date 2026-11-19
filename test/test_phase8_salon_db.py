from datetime import timedelta
from uuid import uuid4

import pytest

from logic.market import MarketError, now
from logic.salon import ServiceError, split_equal
from models.market import kitchen, place_order, records, transition
from models.salon import (active_session, close_session, delete_table, mark_cleaned,
                          open_session, pay_share, request, resolve, save_table,
                          session_by_token, session_orders, set_split, table_by_token,
                          table_detail, tables)
from service_fixtures import make_business, make_dish, make_offer, make_store, make_user


def setup_business(role="business_owner"):
    owner = make_user("owner8", role, "Dueño Salón")
    business = make_business(owner["id"])
    make_store(business["id"])
    return owner, business


def test_table_structure_and_qr_token(service_db):
    owner, business = setup_business()
    table = save_table(business["id"], owner["id"], {"label": "08", "floor": "Segundo piso",
                                                     "zone": "Terraza", "capacity": 4})
    assert table["floor"] == "Segundo piso" and table["zone"] == "Terraza"
    assert len(table["qr_token"]) == 32
    assert table_by_token(table["qr_token"])["id"] == table["id"]
    with pytest.raises(ServiceError):
        save_table(business["id"], owner["id"], {"label": "08", "floor": "Segundo piso",
                                                 "zone": "Terraza", "capacity": 4})
    with pytest.raises(ServiceError):
        save_table(business["id"], owner["id"], {"label": "09", "capacity": 0})


def test_session_opens_only_by_confirmation_and_releases_after_cleaning(service_db):
    owner, business = setup_business()
    table = save_table(business["id"], owner["id"], {"label": "08", "capacity": 4})
    assert table_detail(business["id"])[0]["state"] == "Disponible"
    session = open_session(table, uid=owner["id"], party_size=2, name="Ana")
    assert active_session(table["id"])["id"] == session["id"]
    with pytest.raises(ServiceError):
        open_session(table, uid=owner["id"], party_size=2)
    with pytest.raises(ServiceError):
        open_session(table, uid=owner["id"], party_size=9)
    assert table_detail(business["id"])[0]["state"] == "Ocupada"
    closed = close_session(session, paid=True, actor=owner["id"])
    assert closed["status"] == "Finalizada"
    assert table_detail(business["id"])[0]["state"] == "Limpieza"
    with pytest.raises(ServiceError):
        open_session(table, uid=owner["id"], party_size=2)
    mark_cleaned(closed, owner["id"])
    assert table_detail(business["id"])[0]["state"] == "Disponible"
    assert open_session(table, uid=owner["id"], party_size=2)["status"] == "Abierta"


def test_attendance_requests_change_table_state_and_resolve(service_db):
    owner, business = setup_business()
    table = save_table(business["id"], owner["id"], {"label": "01", "capacity": 2})
    session = open_session(table, uid=owner["id"], party_size=2)
    row = request(session, "Mozo")
    assert request(session, "Mozo")["id"] == row["id"]
    assert table_detail(business["id"])[0]["state"] == "Solicita atención"
    resolve(row["id"], business["id"], owner["id"])
    assert table_detail(business["id"])[0]["state"] == "Ocupada"
    request(session, "Cuenta")
    assert table_detail(business["id"])[0]["state"] == "Solicita cuenta"
    with pytest.raises(ServiceError):
        request(session, "Otra cosa")


def test_table_order_uses_offer_stock_and_requires_settlement(service_db):
    owner, business = setup_business()
    dish = make_dish(business["id"])
    offer = make_offer(business["id"], dish, stock=10)
    table = save_table(business["id"], owner["id"], {"label": "08", "capacity": 4})
    session = open_session(table, uid=owner["id"], party_size=2)
    order = place_order(owner["id"], business["id"], {str(offer["id"]): 2}, "Local", [], now(),
                        uuid4().hex, "Cuenta", 3600, table_session=session)
    assert order["table_session"] == session["id"]
    assert order["destination"][0] == "Mesa 08"
    assert session_orders(session)[0]["id"] == order["id"]
    assert kitchen(business["id"])["pantry"]["arroz"]["quantity"] == 4800

    shares = set_split(session, people=2)["split"]["shares"]
    assert [row["amount"] for row in shares] == split_equal(3600, 2)
    pay_share(session, 1)
    from database.repository import PostgresDocumentRepository as Repo
    saved = Repo.get_by_id("table_sessions", session["id"])
    assert saved["split"]["shares"][0]["paid"] is True

    with pytest.raises(ServiceError):
        close_session(session, paid=False, actor=owner["id"])
    for action in ("Confirmado", "Preparando", "Listo", "Entregado"):
        order = transition(order, action)
    with pytest.raises(ServiceError):
        close_session(session, paid=False, actor=owner["id"])
    closed = close_session(session, paid=True, actor=owner["id"])
    assert closed["total"] == 3600 and closed["paid"] is True
    assert session_orders(closed)[0]["paid"] is True


def test_tables_cannot_be_deleted_with_open_session(service_db):
    owner, business = setup_business()
    table = save_table(business["id"], owner["id"], {"label": "02", "capacity": 2})
    open_session(table, uid=owner["id"], party_size=2)
    with pytest.raises(ServiceError):
        delete_table(business["id"], table["id"])
    assert tables(business["id"])


def test_session_lookup_by_token_includes_closed_for_review(service_db):
    owner, business = setup_business()
    table = save_table(business["id"], owner["id"], {"label": "03", "capacity": 2})
    session = open_session(table, uid=owner["id"], party_size=2)
    closed = close_session(session, paid=True, actor=owner["id"])
    assert session_by_token(closed["token"]) is None
    assert session_by_token(closed["token"], active_only=False)["id"] == closed["id"]