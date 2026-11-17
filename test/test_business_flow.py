"""Integration with a disposable PostgreSQL database provisioned by the caller."""
import re
from datetime import datetime, timezone
from uuid import uuid4

from app import create_app
from models.category import CategoryModel
from models.moderation import ModerationModel
from models.reservation import ReservationModel
from models.restaurant import RestaurantModel
from models.user import UserModel
from utils.audit import AuditEventModel


def token(client):
    page = client.get("/auth/login")
    return re.search(rb'name="csrf-token" content="([^"]+)"', page.data)[1].decode()


def test_three_roles(test_database, monkeypatch):
    app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex})
    owner, admin, guest = (app.test_client() for _ in range(3))
    suffix = uuid4().hex[:10]
    password = uuid4().hex + "A1"
    for role, client in [("business_owner", owner), ("user", guest), ("admin", admin)]:
        username = role + suffix
        data = {"username": username, "password": password, "role": role}
        if role == "admin":
            UserModel.register(username, password, "", username, role)
        else:
            assert client.post("/auth/register", data={**data, "csrf_token": token(client)}).status_code == 302
        assert client.post("/auth/login", data={**data, "csrf_token": token(client)}).status_code == 302
        with client.session_transaction() as session:
            assert session["role"] == role

    category_name = "Categoria " + suffix
    headers = {"X-CSRFToken": token(admin)}
    assert admin.post("/admin/category", data={"name": category_name, "slug": suffix}, headers=headers).status_code == 302
    category_id = CategoryModel.get_by_name(category_name)["id"]
    owner_headers = {"X-CSRFToken": token(owner)}
    assert owner.post("/admin/restaurant/new", headers=owner_headers, data={
        "name": suffix, "district": "Trujillo", "category_id": category_id,
        "service_mode": "dine_in_only", "lat": 0, "lng": 0,
    }).status_code == 302
    restaurant = next(r for r in RestaurantModel.all() if r["name"] == suffix)
    rid = restaurant["id"]
    assert guest.get(f"/restaurant/{rid}").status_code == 404
    dish = owner.post("/owner/dish/add", headers=owner_headers, json={
        "restaurant_id": rid, "name": "Ceviche", "price": 24, "category": "Fondo", "meal_time": "almuerzo",
    })
    assert dish.get_json()["success"]
    dish_id = dish.get_json()["dish"]["id"]
    assert owner.post(f"/owner/menu/{rid}/audit", headers=owner_headers, json={"scope": "all", "use_ai": False}).get_json()["total"] == 1
    assert owner.post("/owner/save_daily_menu", headers=owner_headers, json={
        "restaurant_id": rid, "dish_ids": [dish_id], "price": 24,
    }).get_json()["success"]
    assert admin.post(f"/admin/moderation/restaurant/{rid}/review", headers=headers, json={"action": "approve"}).get_json()["success"]
    history_url = f"/admin/moderation/restaurant/{rid}/history"
    entry = admin.get(history_url).get_json()
    ModerationModel.update(entry["moderation_id"], {"content_id": str(rid)})
    assert admin.get(history_url).get_json()["history"] == entry["history"]
    guest_headers = {"X-CSRFToken": token(guest)}
    assert guest.post("/api/save-location", headers=guest_headers, json={"lat": 0, "lng": 0}).get_json()["success"]
    nearby = guest.get("/api/restaurants/nearby?lat=0&lng=0").get_json()
    assert any(row["id"] == rid and row["distance_km"] == 0 for row in nearby["results"])
    detail = guest.get(f"/restaurant/{rid}")
    assert detail.status_code == 200 and b"Ceviche" in detail.data
    assert b"0.0 km" in detail.data
    assert admin.post(f"/admin/moderation/restaurant/{rid}/notify-owner", headers=headers,
                      json={"message": "Actualiza los horarios del restaurante."}).get_json()["success"]
    assert owner.get("/api/notifications").get_json()["unread_count"] == 1
    assert guest.post("/auth/api/favorites/toggle", headers=guest_headers, json={"restaurant_id": rid}).get_json()["favorited"]
    for rating in ("incorrecta", True, 6):
        assert guest.post("/api/reviews", headers=guest_headers, json={"restaurant_id": rid, "rating": rating}).status_code == 400
    assert guest.post("/api/reviews", headers=guest_headers, json={"restaurant_id": rid, "rating": "4"}).get_json()["stats"]["average"] == 4
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            utc = datetime(2030, 6, 2, 2, 0, tzinfo=timezone.utc)
            return utc.astimezone(tz) if tz else utc.replace(tzinfo=None)

    monkeypatch.setattr("views.main.datetime", FixedClock)
    # At 02:00 UTC it is still 21:00 on June 1 in Lima.
    assert guest.post(f"/restaurant/{rid}/reserve", headers=guest_headers, data={
        "date": "2030-06-01", "time": "22:00", "guests": 2,
    }).status_code == 302
    assert ReservationModel.get_by_restaurant(rid)[0]["guests"] == 2
    with monkeypatch.context() as patch:
        patch.setattr("views.ai_routes._llm_json", lambda messages: {"reply": "Ceviche", "restaurant_ids": [rid, -1]})
        chat = guest.post("/api/ai/chat", headers=guest_headers, json={
            "restaurants": [{"id": rid, "name": suffix}], "messages": [{"role": "user", "content": "¿Dónde hay ceviche?"}],
        })
        assert chat.get_json()["restaurant_ids"] == [rid]
    assert admin.get("/admin/api/bi/overview").status_code == 200
    entry_url = f"/admin/moderation/restaurant/{rid}/review"
    assert admin.post(entry_url, headers=headers, json={"action": "suspend"}).get_json()["success"]
    assert guest.get(f"/restaurant/{rid}").status_code == 404
    assert admin.post(entry_url, headers=headers, json={"action": "approve"}).get_json()["success"]
    UserModel.update(restaurant["owner_id"], {"status": "SUSPENDED"})
    assert owner.get("/owner/dashboard").status_code == 302
    assert admin.delete(f"/admin/category/{category_id}", headers=headers).get_json()["success"]
    actions = {event["action"] for event in AuditEventModel.all()
               if event["resource_type"] == "category" and event["resource_id"] == category_id}
    assert actions == {"ADMIN_CATEGORY_CREATE", "ADMIN_CATEGORY_DELETE"}
    assert guest.post("/auth/logout").status_code == 400
    assert guest.post("/auth/logout", headers=guest_headers).status_code == 302


def test_global_error_and_csrf_contract():
    client = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex}).test_client()
    assert client.get("/api/missing").get_json()["code"] == "not_found"
    for rule in client.application.url_map.iter_rules():
        for method in rule.methods & {"POST", "PUT", "PATCH", "DELETE"}:
            if rule.endpoint in {"main.search", "market.payment_notification"}:  # read-only search or provider signature
                continue
            path = re.sub(r"<(?:int:)?[^>]+>", "1", rule.rule)
            response = client.open(path, method=method, json={})
            assert response.status_code == 400, (method, path)
            assert response.get_json()["code"] == "csrf_invalid", (method, path)


def test_category_and_audit_roll_back_together(test_database, monkeypatch):
    app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex})
    client = app.test_client()
    name = "Categoria " + uuid4().hex[:10]
    admin = UserModel.register(uuid4().hex, uuid4().hex, "", "Admin", "admin")
    with client.session_transaction() as session:
        session["user_id"] = admin["id"]

    def unavailable(*args, **kwargs):
        raise RuntimeError("diagnostico_interno_de_prueba")

    monkeypatch.setattr("views.admin.record_event", unavailable)
    result = client.post("/admin/api/categories", json={"name": name}, headers={"X-CSRFToken": token(client)})
    assert result.status_code == 500
    assert b"diagnostico_interno_de_prueba" not in result.data
    assert CategoryModel.get_by_name(name) is None


def test_qwen_settings_are_shared(monkeypatch):
    from utils.admin_ai import provider_settings
    from utils.llm_provider import GROQ_URL, settings

    for variable in ("QWEN_API_KEY", "ADMIN_QWEN_BASE_URL", "ADMIN_QWEN_MODEL"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "solo-prueba")
    monkeypatch.setenv("QWEN_BASE_URL", GROQ_URL)
    monkeypatch.setenv("QWEN_MODEL", "modelo-de-prueba")
    assert provider_settings()[:3] == settings()[:3] == ("solo-prueba", GROQ_URL, "modelo-de-prueba")
    monkeypatch.setenv("ADMIN_QWEN_MODEL", "modelo-administrativo")
    assert provider_settings().model == "modelo-administrativo"
