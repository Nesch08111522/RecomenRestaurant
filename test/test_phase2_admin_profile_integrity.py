from copy import deepcopy

from app import create_app
from models.user import UserModel
import views.admin as admin_routes


def _admin_client(monkeypatch):
    admin = {"id": 1, "username": "admin", "role": "admin", "status": "ACTIVE", "auth_epoch": 0, "profile": {}}
    target = {
        "id": 2,
        "username": "diner",
        "role": "user",
        "status": "ACTIVE",
        "profile": {
            "name": "Nombre anterior",
            "email": "anterior@example.test",
            "preferences": ["criolla"],
            "restrictions": ["sin gluten"],
            "daily_budget": 55.0,
            "location_consent": True,
        },
    }
    calls = []

    def get_by_id(user_id):
        return deepcopy(admin if int(user_id) == 1 else target)

    def update(user_id, payload):
        calls.append((user_id, deepcopy(payload)))
        return {**deepcopy(target), **deepcopy(payload)}

    monkeypatch.setattr(UserModel, "get_by_id", get_by_id)
    monkeypatch.setattr(UserModel, "update", update)
    monkeypatch.setattr(admin_routes, "record_event", lambda *args, **kwargs: None)
    client = create_app({
        "TESTING": True,
        "SECRET_KEY": "x" * 32,
        "WTF_CSRF_ENABLED": False,
    }).test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
    return client, calls, target


def test_admin_partial_profile_edit_preserves_preferences_and_privacy(monkeypatch):
    client, calls, target = _admin_client(monkeypatch)

    response = client.put("/admin/user/2", json={
        "profile": {"name": "Nombre nuevo", "email": "nuevo@example.test"},
    })

    assert response.status_code == 200, response.get_json()
    saved_profile = calls[0][1]["profile"]
    assert saved_profile["name"] == "Nombre nuevo"
    assert saved_profile["email"] == "nuevo@example.test"
    assert saved_profile["preferences"] == target["profile"]["preferences"]
    assert saved_profile["restrictions"] == target["profile"]["restrictions"]
    assert saved_profile["daily_budget"] == target["profile"]["daily_budget"]
    assert saved_profile["location_consent"] is True


def test_admin_profile_edit_rejects_invalid_email_without_writing(monkeypatch):
    client, calls, _ = _admin_client(monkeypatch)

    response = client.put("/admin/user/2", json={
        "profile": {"name": "Nombre nuevo", "email": "correo-invalido"},
    })

    assert response.status_code == 400
    assert calls == []
