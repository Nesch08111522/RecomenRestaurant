from datetime import datetime, timedelta

import pytest

from database.repository import PostgresDocumentRepository as Repo
from logic.market import now
from logic.salon import ServiceError
from models.flow import (cancel, call_next, demand_pattern, estimate, join, no_show, queue,
                         save_settings, seat, settings, status)
from models.salon import active_session, save_table, snapshot, table_by_token
from service_fixtures import make_business, make_store, make_user


def setup(service_db):
    owner = make_user("owner11", "business_owner", "Dueño Flow")
    business = make_business(owner["id"], "Flow Norteño")
    make_store(business["id"], table_minutes=60)
    small = save_table(business["id"], owner["id"], {"label": "01", "capacity": 2})
    big = save_table(business["id"], owner["id"], {"label": "02", "capacity": 4})
    return owner, business, small, big


def test_queue_registration_position_and_no_identity_leak(service_db):
    owner, business, small, big = setup(service_db)
    first = join(business["id"], "Ana", 2)
    second = join(business["id"], "Luis", 4)
    assert first["code"] == "T-001" and second["code"] == "T-002"
    view = status(business["id"], [first["id"]])
    assert view["waiting"] == 2
    assert view["mine"][0]["position"] == 1
    assert all("name" not in row for row in view["ahead"])


def test_queue_can_be_closed_and_reopened(service_db):
    owner, business, small, big = setup(service_db)
    save_settings(business["id"], accepting=False, max_capacity=10)
    with pytest.raises(ServiceError):
        join(business["id"], "Ana", 2)
    save_settings(business["id"], accepting=True, max_capacity=10)
    assert join(business["id"], "Ana", 2)["status"] == "Esperando"


def test_calling_and_seating_a_turn_creates_a_real_session(service_db):
    owner, business, small, big = setup(service_db)
    row = join(business["id"], "Ana", 4, uid=owner["id"])
    call_next(business["id"], row["id"])
    session = seat(business["id"], row["id"], big["id"])
    assert session["uid"] == owner["id"]
    assert active_session(big["id"])["id"] == session["id"]
    assert queue(business["id"]) == []
    with pytest.raises(ServiceError):
        seat(business["id"], row["id"], small["id"])
    assert snapshot(business["id"])["occupied"] == 4


def test_seating_rejects_a_table_that_is_too_small(service_db):
    owner, business, small, big = setup(service_db)
    row = join(business["id"], "Ana", 4)
    with pytest.raises(ServiceError):
        seat(business["id"], row["id"], small["id"])


def test_maximum_capacity_blocks_extra_seating(service_db):
    owner, business, small, big = setup(service_db)
    save_settings(business["id"], accepting=True, max_capacity=4)
    first = join(business["id"], "Ana", 4)
    seat(business["id"], first["id"], big["id"])
    second = join(business["id"], "Luis", 2)
    with pytest.raises(ServiceError):
        seat(business["id"], second["id"], small["id"])


def test_cancel_and_no_show_release_the_turn(service_db):
    owner, business, small, big = setup(service_db)
    first = join(business["id"], "Ana", 2)
    second = join(business["id"], "Luis", 2)
    cancel(business["id"], first["id"])
    no_show(business["id"], second["id"])
    assert queue(business["id"]) == []
    assert len([row for row in Repo.all("flow_queue") if row["rid"] == business["id"]]) == 2


def test_estimate_uses_declared_duration_then_history(service_db):
    owner, business, small, big = setup(service_db)
    # Both tables are busy, so the next group cannot sit immediately.
    for table, minutes in ((small, 40), (big, 80)):
        opened = now() - timedelta(minutes=minutes)
        Repo.create("table_sessions", {
            "rid": business["id"], "table_id": table["id"], "token": "a" * 32,
            "uid": owner["id"], "party_size": table["capacity"], "status": "Abierta",
            "opened_at": opened.isoformat(), "cleaned_at": None, "order_ids": [],
        })
    initial = estimate(business["id"], 2)
    assert initial["minutes"] == 60 and "declarada" in initial["basis"]
    # Close three sessions with known durations to enable the historical basis.
    for table in (small, big):
        session = active_session(table["id"])
        Repo.update("table_sessions", session["id"], {
            "status": "Finalizada", "closed_at": now().isoformat(), "paid": True,
        })
    Repo.create("table_sessions", {
        "rid": business["id"], "table_id": small["id"], "token": "b" * 32,
        "uid": owner["id"], "party_size": 2, "status": "Finalizada",
        "opened_at": (now() - timedelta(minutes=50)).isoformat(),
        "closed_at": now().isoformat(), "cleaned_at": now().isoformat(), "paid": True,
        "order_ids": [],
    })
    historical = estimate(business["id"], 2)
    assert historical["samples"] >= 1
    assert historical["minutes"] is not None


def test_demand_pattern_counts_real_turns(service_db):
    owner, business, small, big = setup(service_db)
    join(business["id"], "Ana", 2)
    join(business["id"], "Luis", 4)
    pattern = demand_pattern(business["id"])
    assert pattern and pattern[0]["parties"] == 2 and pattern[0]["people"] == 6