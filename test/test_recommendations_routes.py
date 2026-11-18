"""Phase 7 request and privacy boundaries with isolated commerce records."""
from contextlib import nullcontext
from datetime import datetime

import pytest
from flask_wtf.csrf import generate_csrf

from app import create_app
from logic.market import LIMA
from models import recommendation_history
from models.notification import NotificationModel
from models.user import UserModel
from views import market_kitchen, recommendations


@pytest.fixture
def recommendations_fixture(monkeypatch):
    at = datetime(2026, 11, 18, 13, tzinfo=LIMA)
    monkeypatch.setattr(recommendations, "now", lambda: at)
    accounts = {
        uid: {"id": uid, "username": f"user{uid}", "profile": {"name": "Cliente Uno", "preferences": ["mariscos"]}}
        for uid in (101, 102)
    }
    accounts[103] = {"id": 103, "username": "user103", "profile": {"preferences": ["japonesa"], "daily_budget": 10}}
    restaurants = [
        {"id": 1, "name": "Casa del Mar", "description": "Ceviche y pescados",
         "verified": True, "market_channels": ["Local", "Delivery"], "lat": -8.10, "lng": -79.02},
        {"id": 2, "name": "Cocina sin punto público", "verified": True, "lat": -8.11, "lng": -79.03},
        {"id": 3, "name": "Puerto Azul", "category": "Cevichería", "verified": True},
        {"id": 4, "name": "Forno", "category": "Italiana", "verified": True},
    ]
    dishes = [
        {"id": 3, "restaurant_id": 1, "name": "Ceviche de pescado",
         "price": 24, "ingredients": ["pescado"], "is_available": True},
        {"id": 4, "restaurant_id": 1, "name": "Ají de gallina", "price": 20, "is_available": True},
        {"id": 5, "restaurant_id": 2, "name": "Ramen de verduras", "price": 22, "category": "Japonesa"},
        {"id": 6, "restaurant_id": 2, "name": "Tempura de verduras", "price": 23, "category": "Japonesa"},
        {"id": 7, "restaurant_id": 3, "name": "Arroz con mariscos", "price": 23},
        {"id": 8, "restaurant_id": 3, "name": "Jalea mixta", "price": 25},
        {"id": 9, "restaurant_id": 4, "name": "Pizza hawaiana", "price": 25},
        {"id": 10, "restaurant_id": 4, "name": "Calzone", "price": 24},
        {"id": 11, "restaurant_id": 2, "name": "Pastel de manzana", "price": 13, "category": "Postres"},
    ]
    delivered = {
        "uid": 101, "rid": 1, "business": "Casa del Mar", "state": "Entregado", "paid": True,
        "day": "2026-11-12", "channel": "Local", "lines": [{"dish_id": 3, "name": "Ceviche de pescado", "qty": 1}],
    }
    datasets = {
        "market_orders": [delivered, {**delivered, "paid": False}, {**delivered, "refunded": True},
                          {**delivered, "state": "Cancelado"}, {**delivered, "uid": 102},
                          {**delivered, "state": "Confirmado", "day": "2026-11-18",
                           "lines": [{"dish_id": 4, "name": "Ají de gallina", "qty": 1}]}],
        "reservations": [
            {"user_id": 101, "restaurant_id": 1, "status": "confirmada", "date": "2026-11-11"},
            {"user_id": 101, "restaurant_id": 1, "status": "asistida", "date": "2026-11-13"},
            {"user_id": 103, "restaurant_id": 2, "status": "asistida", "date": "2026-11-13"},
        ],
        "favorites": [{"user_id": 103, "restaurant_id": 2}],
    }
    signals, searches, record_calls, weather_calls = {}, {}, [], []
    documents = {recommendations.COLLECTION: signals, recommendation_history.COLLECTION: searches}

    def records(collection, **fields):
        record_calls.append((collection, fields))
        return [row for row in datasets.get(collection, [])
                if all(row.get(field) == value for field, value in fields.items())]

    def save_document(collection, uid, values):
        documents[collection][uid] = values
        return values

    def conditions(*point):
        weather_calls.append(point)
        return {"apparent_temperature": 26, "precipitation": 0}

    class ConnectionStub:
        def execute(self, _query, _args):
            pass

    monkeypatch.setattr(UserModel, "get_by_id", staticmethod(accounts.get))
    monkeypatch.setattr(recommendations.RestaurantModel, "get_approved", staticmethod(lambda: restaurants))
    monkeypatch.setattr(recommendations.DishModel, "all", staticmethod(lambda: dishes))
    monkeypatch.setattr(recommendations.CategoryModel, "all", staticmethod(list))
    monkeypatch.setattr(recommendations.Repo, "all", staticmethod(lambda _collection: [{"id": 2, "kind": "Cocina desde casa"}]))
    monkeypatch.setattr(recommendations.Repo, "get_by_id", staticmethod(lambda collection, uid, **_: documents.get(collection, {}).get(uid)))
    monkeypatch.setattr(recommendations.Repo, "update", staticmethod(save_document))
    monkeypatch.setattr(recommendations.Repo, "create", staticmethod(lambda collection, values: save_document(collection, values["id"], values)))
    monkeypatch.setattr(recommendations, "catalog", list)
    monkeypatch.setattr(recommendations, "records", records)
    monkeypatch.setattr(recommendations, "document_transaction", lambda: nullcontext(ConnectionStub()))
    monkeypatch.setattr(recommendation_history, "document_transaction", lambda: nullcontext(ConnectionStub()))
    monkeypatch.setattr(recommendation_history, "now", lambda: at)
    monkeypatch.setattr(recommendations.weather, "conditions", conditions)

    app = create_app({"TESTING": True, "SECRET_KEY": "phase7-isolated-route-tests", "WTF_CSRF_ENABLED": True})
    app.get("/test-csrf")(lambda: {"token": generate_csrf()})
    return app.test_client(), record_calls, weather_calls, signals


def _login(client, uid):
    with client.session_transaction() as session:
        session["user_id"] = uid


def _post(client, path, data):
    csrf = client.get("/test-csrf").get_json()["token"]
    return client.post(path, json=data, headers={"X-CSRFToken": csrf})


def test_guest_uses_only_public_catalog_and_query(recommendations_fixture):
    client, record_calls, _, _ = recommendations_fixture
    response = client.get("/api/recomendaciones?q=ceviche")
    data = response.get_json()
    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    assert not record_calls and not data["authenticated"]
    assert data["history"] == {"dishes": [], "restaurants": [], "searches": []}
    assert [card["name"] for card in data["dishes"]] == ["Ceviche de pescado"]
    assert data["search_active"] and data["search_results"]
    assert data["for_you_cards"] == []
    assert data["dishes"][0]["href"].endswith("/restaurant/1#plato-3")
    assert data["dishes"][0]["token"] is None
    restaurant_only = client.get("/api/recomendaciones?kind=restaurant").get_json()
    assert restaurant_only["recommendations"] and all(row["kind"] == "restaurant" for row in restaurant_only["recommendations"])
    page = client.get("/recomendaciones?q=ceviche")
    assert page.status_code == 200 and "Ceviche de pescado" in page.get_data(as_text=True)


def test_clean_page_puts_the_three_sections_in_order_without_filling_search_or_history(recommendations_fixture):
    client, _, _, _ = recommendations_fixture
    data = client.get("/api/recomendaciones").get_json()
    assert not data["search_active"]
    assert data["search_results"] == data["for_you_cards"] == []
    assert data["discovery_cards"]
    page = client.get("/recomendaciones").get_data(as_text=True)
    assert page.index('id="busqueda"') < page.index('id="para-ti"') < page.index('id="por-descubrir"')
    search_section = page[page.index('id="busqueda"'):page.index('id="para-ti"')]
    assert "Resultados de búsqueda" in search_section and "data-rec-card" not in search_section
    assert "Inicia sesión para usar tu historial" in page


def test_personalized_selection_is_independent_of_the_search_term(recommendations_fixture):
    client, _, _, _ = recommendations_fixture
    _login(client, 101)
    baseline = client.get("/api/recomendaciones?kind=dish").get_json()
    assert baseline["for_you_cards"]
    expected = [card["key"] for card in baseline["for_you_cards"]]
    expected_feeds = [[card["key"] for card in baseline[section]] for section in ("for_you_cards", "discovery_cards")]

    for query in ("ceviche", "antojodelque no hay ninguno"):
        result = client.get("/api/recomendaciones", query_string={"kind": "dish", "q": query}).get_json()
        assert [card["key"] for card in result["personalized_recommendations"]] == expected
        assert all(card["token"] and card["href"] for card in result["personalized_recommendations"])
        assert [[card["key"] for card in result[section]] for section in ("for_you_cards", "discovery_cards")] == expected_feeds
    assert not result["search_results"]

    response = client.get("/recomendaciones?kind=dish&q=inexistente&budget=25")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Algo que te podría interesar" in page and "Sin coincidencias" in page
    assert 'data-rec-key="dish-3"' in page
    assert "kind=dish&amp;budget=25.0#busqueda" in page


def test_explicit_search_uses_only_submitted_filters_and_does_not_write_history(recommendations_fixture):
    client, _, _, _ = recommendations_fixture
    _login(client, 103)
    result = client.get("/api/recomendaciones?q=ramen").get_json()
    assert [card["name"] for card in result["search_results"]] == ["Ramen de verduras"]
    assert result["for_you_cards"] == result["history"]["searches"] == []
    assert not result["context"]["has_recommendation_history"]
    assert result["history"]["restaurants"]
    card = result["search_results"][0]
    assert _post(client, "/api/recomendaciones/interaccion", {"token": card["token"], "action": "dismiss"}).status_code == 200

    dismissed = client.get("/api/recomendaciones?q=ramen&kind=dish").get_json()
    assert [card["id"] for card in dismissed["search_results"]] == [5]
    assert dismissed["for_you_cards"] == []
    budget_only = client.get("/api/recomendaciones?budget=21").get_json()
    assert budget_only["search_active"] and budget_only["search_results"]
    assert all(card["price"] <= 21 for card in budget_only["search_results"])
    zero = client.get("/api/recomendaciones?budget=0").get_json()
    assert zero["search_active"] and zero["search_results"] == []


def test_search_filters_an_explicit_occasion_but_does_not_assume_a_saved_one(recommendations_fixture, monkeypatch):
    client, _, _, _ = recommendations_fixture
    offer = {"rid": 1, "price": 1900, "available": 3, "day": "2026-11-18", "channels": ["Local"]}
    monkeypatch.setattr(recommendations, "catalog", lambda: [
        {**offer, "id": 15, "dish_id": 3, "name": "Ceviche para compartir", "context_tags": ["Para compartir"]},
        {**offer, "id": 16, "dish_id": 4, "name": "Ají para llevar", "context_tags": ["Rápido"]},
    ])
    with client.session_transaction() as session:
        session["food_context"] = {"moment": "familia", "until": "2026-11-18T14:00:00-05:00"}
    ordinary = client.get("/api/recomendaciones?kind=experience").get_json()
    assert {card["id"] for card in ordinary["search_results"]} == {15, 16}
    requested = client.get("/api/recomendaciones?kind=experience&moment=familia").get_json()
    assert [card["id"] for card in requested["search_results"]] == [15]


def test_saved_searches_personalize_both_feeds_without_mixing_accounts(recommendations_fixture):
    client, _, _, _ = recommendations_fixture
    _login(client, 101)
    for _ in range(2):
        assert _post(client, "/api/recomendaciones/historial", {"query": "Ramen"}).status_code == 200

    data = client.get("/api/recomendaciones?kind=dish").get_json()
    assert data["history"]["searches"] == [
        {"query": "Ramen", "count": 2, "last_searched_at": "2026-11-18T13:00:00-05:00"}
    ]
    familiar, discovery = data["for_you_cards"], data["discovery_cards"]
    assert familiar and discovery
    assert any(card["name"] == "Ramen de verduras" for card in familiar)
    assert any(card["name"] == "Tempura de verduras" for card in familiar)
    assert any(card["name"] == "Pastel de manzana" for card in discovery)
    assert {card["key"] for card in familiar}.isdisjoint(card["key"] for card in discovery)
    assert all(card["is_new"] and card["id"] != 3 for card in discovery)
    assert any("Coincide con lo que has buscado antes" in card["reasons"] for card in (*familiar, *discovery))
    page = client.get("/recomendaciones").get_data(as_text=True)
    assert 'id="rec-for-you-title">Para ti' in page
    assert 'id="rec-discovery-title">Algo que te podría interesar' in page
    assert 'Búsquedas recientes (1)' in page and '2 búsquedas' in page

    _login(client, 102)
    other = client.get("/api/recomendaciones?kind=dish").get_json()
    assert other["history"]["searches"] == []
    assert not any("Coincide con lo que has buscado antes" in card["reasons"]
                   for card in (*other["for_you_cards"], *other["discovery_cards"]))


def test_related_history_covers_multiple_searches_and_can_focus_without_changing_exact_results(recommendations_fixture):
    client, _, _, _ = recommendations_fixture
    _login(client, 101)
    path = "/api/recomendaciones/historial"
    for query in ["ceviche"] * 5 + ["ramen", "pizza hawaiana"]:
        assert _post(client, path, {"query": query}).status_code == 200

    base = client.get("/api/recomendaciones").get_json()
    recommendations = base["for_you"]
    names = {card["name"] for card in recommendations["dishes"]}
    assert {"Arroz con mariscos", "Jalea mixta", "Ramen de verduras", "Pizza hawaiana"} <= names
    assert any(card["name"] == "Puerto Azul" for card in recommendations["restaurants"])
    visible = {card["name"] for card in recommendations["items"][:6]}
    assert "Ramen de verduras" in visible and "Pizza hawaiana" in visible

    filtered = client.get("/api/recomendaciones?q=inexistente&budget=1&kind=dish").get_json()
    assert filtered["search_results"] == []
    assert [card["key"] for card in filtered["for_you"]["items"]] == [card["key"] for card in recommendations["items"]]

    topic = next(topic for topic in base["history_topics"] if topic["query"] == "ramen")
    focused = client.get("/api/recomendaciones", query_string={"interes": topic["id"], "q": "ceviche"}).get_json()
    assert focused["active_history_topic"]["query"] == "ramen"
    focused_names = {card["name"] for card in focused["for_you"]["dishes"]}
    assert {"Ramen de verduras", "Tempura de verduras"} <= focused_names
    assert "Ceviche de pescado" not in focused_names and "Pizza hawaiana" not in focused_names
    assert [card["name"] for card in focused["search_results"] if card["kind"] == "dish"] == ["Ceviche de pescado"]
    personal_products = {(card["restaurant_id"], card["dish_id"]) for card in focused["for_you"]["items"]}
    discovery_products = {(card["restaurant_id"], card["dish_id"]) for card in focused["discovery_items"]["items"]}
    assert personal_products.isdisjoint(discovery_products)

    html = client.get("/recomendaciones", query_string={"interes": topic["id"]}).get_data(as_text=True)
    assert "Opciones relacionadas con «ramen»" in html and "Todo mi historial" in html

    _login(client, 102)
    other = client.get("/api/recomendaciones", query_string={"interes": topic["id"]}).get_json()
    assert other["active_history_topic"] is None


def test_history_uses_only_own_purchases_and_attended_local_visits(recommendations_fixture):
    client, record_calls, _, _ = recommendations_fixture
    _login(client, 101)
    data = client.get("/api/recomendaciones").get_json()
    dishes, visits = data["history"]["dishes"], data["history"]["restaurants"]
    assert data["authenticated"] and data["profile"]["name"] == "Cliente"
    assert [(item["name"], item["count"]) for item in dishes] == [("Ceviche de pescado", 1)]
    assert [(item["name"], item["visits"]) for item in visits] == [("Casa del Mar", 2)]
    assert all(fields.get("uid", fields.get("user_id")) == 101 for _, fields in record_calls)


def test_orderable_experience_links_to_marketplace_and_public_media(recommendations_fixture, monkeypatch):
    client, _, _, signals = recommendations_fixture
    offer = {"id": 15, "rid": 1, "dish_id": 3, "name": "Ceviche de pescado", "price": 2200,
             "available": 3, "day": "2026-11-18", "ends": "2026-11-18T21:00:00-05:00",
             "channels": ["Delivery"], "occasion": "Almuerzo", "photo_id": 77, "model_id": 81}
    monkeypatch.setattr(recommendations, "catalog", lambda: [dict(offer)])
    data = client.get("/api/recomendaciones?channel=Delivery&kind=experience").get_json()
    assert len(data["recommendations"]) == 1
    card = data["recommendations"][0]
    assert card["kind"] == "experience" and card["price"] == 22
    assert card["href"] == "/mercado/oferta/15"
    assert card["image"] == "/mercado/oferta/15/foto"
    assert "/experiencias/" in card["model"]
    html = client.get("/recomendaciones?kind=experience").get_data(as_text=True)
    assert '/mercado/oferta/15#load-dish-model' in html

    _login(client, 101)
    card = client.get("/api/recomendaciones?kind=experience").get_json()["recommendations"][0]
    response = _post(client, "/api/recomendaciones/interaccion", {"token": card["token"], "action": "like"})
    assert response.get_json()["liked"] is True
    assert signals[101]["signals"][card["key"]]["dish_id"] == 3


def test_feedback_requires_csrf_and_a_card_token_for_the_current_user(recommendations_fixture):
    client, _, _, signals = recommendations_fixture
    path = "/api/recomendaciones/interaccion"
    _login(client, 101)
    data = client.get("/api/recomendaciones").get_json()
    card = next(row for row in data["dishes"] if row["id"] == 3)
    action = {"token": card["token"], "action": "like"}
    assert client.post(path, json=action).status_code == 400
    assert _post(client, path, action).get_json()["liked"] is True
    assert _post(client, path, {**action, "action": "view"}).get_json()["state"] == "liked"
    assert _post(client, path, {**action, "action": "view"}).get_json()["state"] == "liked"
    assert signals[101]["items"] == {card["key"]: "liked"}
    assert signals[101]["signals"][card["key"]]["views"] == 2
    assert signals[101]["signals"][card["key"]]["last_seen"] == "2026-11-18T13:00:00-05:00"
    _login(client, 102)
    assert _post(client, path, action).status_code == 400
    _login(client, 101)
    assert _post(client, path, {**action, "action": "dismiss"}).get_json()["state"] == "dismissed"
    assert all(row["key"] != card["key"] for row in client.get("/api/recomendaciones").get_json()["dishes"])
    assert _post(client, path, {**action, "action": "undo"}).get_json()["state"] is None
    assert any(row["key"] == card["key"] for row in client.get("/api/recomendaciones").get_json()["dishes"])


def test_location_and_weather_require_active_consent_and_hide_private_pins(recommendations_fixture):
    client, _, weather_calls, _ = recommendations_fixture
    path = "/api/recomendaciones/contexto"
    with client.session_transaction() as session:
        session["user_lat"], session["user_lng"] = -8.1, -79.0
    result = client.get("/api/recomendaciones").get_json()
    assert not result["location_enabled"] and not weather_calls
    assert _post(client, path, {"lat": True, "lng": -79}).status_code == 400
    assert _post(client, path, {"lat": -8.1, "lng": -79.0}).get_json()["location_enabled"]
    result = client.get("/api/recomendaciones").get_json()
    distances = {row["id"]: row["distance_km"] for row in result["restaurants"]}
    assert distances[1] is not None and distances[2] is None
    assert not weather_calls
    assert _post(client, path, {"weather": True}).get_json()["weather_enabled"]
    assert client.get("/api/recomendaciones").get_json()["context"]["weather"]
    assert weather_calls == [(-8.1, -79.0)]
    assert _post(client, path, {"clear": True}).status_code == 200
    result = client.get("/api/recomendaciones").get_json()
    assert not result["location_enabled"] and not result["context"]["weather"]
    assert len(weather_calls) == 1


def test_merchant_can_record_attendance_only_after_a_confirmed_visit_starts(recommendations_fixture, monkeypatch):
    client, _, _, _ = recommendations_fixture
    booking = {"id": 5, "restaurant_id": 1, "user_id": 102, "date": "2026-11-18", "time": "15:00", "status": "confirmada"}
    clock = [datetime(2026, 11, 18, 14, tzinfo=LIMA)]
    monkeypatch.setattr(market_kitchen, "now", lambda: clock[0])
    monkeypatch.setattr(market_kitchen, "document_transaction", nullcontext)
    monkeypatch.setattr(market_kitchen, "lock_business", lambda _rid: None)
    monkeypatch.setattr(market_kitchen, "authorize", lambda _rid: None)
    monkeypatch.setattr(market_kitchen.Repo, "get_by_id",
                        staticmethod(lambda collection, _rid, **_: booking if collection == "reservations" else None))
    monkeypatch.setattr(market_kitchen.ReservationModel, "update", staticmethod(lambda _rid, values: booking.update(values)))
    monkeypatch.setattr(NotificationModel, "create_notification", staticmethod(lambda *args, **kwargs: None))
    _login(client, 101)
    csrf = client.get("/test-csrf").get_json()["token"]
    url = "/mercado/cocina/1/reserva/5"
    payload = {"csrf_token": csrf, "status": "asistida"}
    assert client.post(url, data=payload).status_code == 400
    assert booking["status"] == "confirmada"
    clock[0] = datetime(2026, 11, 18, 15, tzinfo=LIMA)
    assert client.post(url, data=payload).status_code == 302
    assert booking["status"] == "asistida" and booking["attended_at"] == clock[0].isoformat()
