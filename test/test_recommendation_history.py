"""Only submitted searches reach the private account history."""

from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

import pytest
from flask_wtf.csrf import generate_csrf

from app import create_app
from logic.market import LIMA
from models import recommendation_history as history
from models.user import UserModel


PATH = "/api/recomendaciones/historial"


@pytest.fixture
def history_fixture(monkeypatch):
    records = {}
    accounts = {user_id: {"id": user_id, "username": f"comensal{user_id}"} for user_id in (11, 12)}
    clock = [datetime(2026, 11, 18, 12, tzinfo=LIMA)]

    class Transaction:
        def execute(self, statement, params):
            assert "pg_advisory_xact_lock" in statement and params[0].startswith("search-history:")

    def create(collection, fields):
        record = (collection, fields["id"])
        assert record not in records
        records[record] = deepcopy(fields)

    def update(collection, user_id, fields):
        records[collection, user_id].update(deepcopy(fields))

    monkeypatch.setattr(UserModel, "get_by_id", staticmethod(accounts.get))
    monkeypatch.setattr(history, "document_transaction", lambda: nullcontext(Transaction()))
    monkeypatch.setattr(history.Repo, "get_by_id", staticmethod(lambda collection, uid, **_: deepcopy(records.get((collection, uid)))))
    monkeypatch.setattr(history.Repo, "create", staticmethod(create))
    monkeypatch.setattr(history.Repo, "update", staticmethod(update))
    monkeypatch.setattr(history, "now", lambda: clock[0])

    app = create_app({"TESTING": True, "SECRET_KEY": "phase7-search-history-isolated-tests", "WTF_CSRF_ENABLED": True})
    app.get("/test-csrf")(lambda: {"token": generate_csrf()})

    def client(user_id=None):
        browser = app.test_client()
        if user_id is not None:
            with browser.session_transaction() as session:
                session["user_id"] = user_id
        return browser

    return client, records, clock


def _post(client, data):
    csrf_token = client.get("/test-csrf").get_json()["token"]
    return client.post(PATH, json=data, headers={"X-CSRFToken": csrf_token})


def test_searches_aggregate_and_survive_new_sessions(history_fixture):
    client, records, clock = history_fixture
    browser = client(11)
    first = {"query": " ¿Té   matcha? ", "submission_id": str(uuid4()), "user_id": 12}
    assert _post(browser, first).status_code == 200
    assert _post(browser, first).status_code == 200
    clock[0] = clock[0].replace(hour=13)
    assert _post(browser, {"query": "TE MATCHA"}).status_code == 200

    result = client(11).get(PATH + "?user_id=12")
    assert result.status_code == 200
    assert "no-store" in result.headers["Cache-Control"] and "Cookie" in result.headers["Vary"]
    assert result.get_json()["history"] == [
        {"query": "TE MATCHA", "count": 2, "last_searched_at": clock[0].isoformat()},
    ]
    assert client(12).get(PATH).get_json()["history"] == []
    assert list(records) == [(history.COLLECTION, 11)]


def test_validation_and_csrf_do_not_create_a_history(history_fixture):
    client, records, _ = history_fixture
    assert client().get(PATH).status_code == 401
    assert _post(client(), {"query": "ramen"}).status_code == 401
    browser = client(11)
    assert browser.post(PATH, json={"query": "ramen"}).status_code == 400
    for data in ([], {"query": ["ramen"]}, {"query": "--"}, {"query": "a" * 141},
                 {"query": "A\x00BC"}, {"query": "ramen", "submission_id": "reused"}):
        assert _post(browser, data).status_code == 400
    assert not records


def test_order_and_retention_are_bounded(history_fixture, monkeypatch):
    client, records, _ = history_fixture
    monkeypatch.setattr(history, "HISTORY_LIMIT", 2)
    monkeypatch.setattr(history, "SUBMISSION_LIMIT", 2)
    browser = client(11)
    latest_ids = []
    for query in ("pan", "ramen", "pan", "wok"):
        submission_id = str(uuid4())
        latest_ids.append(submission_id)
        assert _post(browser, {"query": query, "submission_id": submission_id}).status_code == 200
    result = browser.get(PATH).get_json()["history"]
    assert [(entry["query"], entry["count"]) for entry in result] == [("wok", 1), ("pan", 2)]
    assert records[history.COLLECTION, 11]["submissions"] == latest_ids[-2:][::-1]
