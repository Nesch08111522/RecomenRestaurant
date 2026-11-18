import json
import struct
from datetime import timedelta
from uuid import uuid4

import pytest

from app import create_app
from database.repository import PostgresDocumentRepository as Repo
from logic.market import MarketError, now
from models.market import kitchen, save_kitchen
from models.reservation import ReservationModel
from models.restaurant import RestaurantModel
from models.user import UserModel
from utils.dish_model import validate_glb


def test_ecosystem_roles_and_private_groups(test_database):
    app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex, "WTF_CSRF_ENABLED": False})
    clients = []
    users = []
    for role in ("user", "user", "business_owner", "admin"):
        user = UserModel.create({"username": uuid4().hex, "role": role})
        client = app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = user["id"]
        clients.append(client)
        users.append(user)
    buyer, other, owner, admin = clients
    shop = RestaurantModel.create({"name": "Test", "owner_id": users[2]["id"], "verified": True})
    assert app.test_client().get("/experiencias/").status_code == 200
    for path in ("/experiencias/", "/experiencias/grupos", "/experiencias/scan", "/experiencias/recompensas"):
        assert buyer.get(path).status_code == 200, path
    for path in ("/experiencias/ciudad", "/experiencias/publicaciones"):
        assert buyer.get(path).status_code == 403
        assert admin.get(path).status_code == 200
    business_path = f"/experiencias/negocio/{shop['id']}"
    assert owner.get(business_path).status_code == 200
    assert buyer.get(business_path).status_code == 403
    import base64
    raw = glb({"asset": {"version": "2.0"}})
    model = Repo.create("dish_models", {"rid": shop["id"], "data": base64.b64encode(raw).decode()})
    offer = Repo.create("market_offers", {"rid": shop["id"], "model_id": model["id"], "review_state": "pending"})
    model_path = f"/experiencias/modelos/{offer['id']}"
    assert buyer.get(model_path).status_code == 404
    assert admin.get(model_path).data == raw
    Repo.delete("market_offers", offer["id"])
    result = buyer.post("/experiencias/grupos", data={"title": "Almuerzo"})
    assert result.status_code == 302
    path = result.location
    assert buyer.get(path).status_code == 200
    assert other.get(path).status_code == 404
    group_id = int(path.rsplit("/", 1)[1])
    group = Repo.get_by_id("food_groups", group_id)
    Repo.update("food_groups", group_id, {"votes": {str(users[0]["id"]): 1}})
    assert other.post("/experiencias/grupos/unirse", data={"invite": group["invite"]}).status_code == 302
    assert Repo.get_by_id("food_groups", group_id)["votes"] == {}
    assert other.get(path).status_code == 200
    assert buyer.post(path, data={"action": "preferences", "budget": 20, "avoid": "leche"}).status_code == 200
    assert other.post(path, data={"action": "preferences", "budget": 15}).status_code == 200


def test_reservation_capacity_across_midnight_and_retry(test_database):
    shop = RestaurantModel.create({"name": "Test", "verified": True})
    store = kitchen(shop["id"])
    save_kitchen({**store, "seats": 2, "table_minutes": 90})
    today = (now().date() + timedelta(days=1)).isoformat()
    tomorrow = (now().date() + timedelta(days=2)).isoformat()
    first = ReservationModel.create(10001, shop["id"], today, "23:30", 2)
    assert ReservationModel.create(10001, shop["id"], today, "23:30", 2)["id"] == first["id"]
    with pytest.raises(MarketError):
        ReservationModel.create(10002, shop["id"], tomorrow, "00:15", 1)
    assert ReservationModel.create(10002, shop["id"], tomorrow, "01:00", 2)


def glb(document):
    raw = json.dumps(document).encode()
    raw += b" " * (-len(raw) % 4)
    return struct.pack("<4sII", b"glTF", 2, len(raw) + 20) + struct.pack("<I4s", len(raw), b"JSON") + raw


def test_model_rejects_external_assets():
    raw = glb({"asset": {"version": "2.0"}})
    assert validate_glb(raw) == raw
    with pytest.raises(MarketError):
        validate_glb(glb({"asset": {"version": "2.0"}, "images": [{"uri": "https://example.com/image"}]}))
