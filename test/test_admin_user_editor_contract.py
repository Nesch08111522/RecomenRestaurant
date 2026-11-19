from copy import deepcopy
from pathlib import Path

from app import create_app
from models.user import UserModel
import views.admin as admin_routes


def test_admin_user_editor_sends_only_supported_profile_role_and_status_fields():
    template = (Path(__file__).resolve().parents[1] / "templates/admin/users.html").read_text(encoding="utf-8")
    assert 'data-status="{{ user.status or \'ACTIVE\' }}"' in template
    assert '<select id="edit-status">' in template
    assert 'const payload = { profile: { name: fName.value.trim(), email: fEmail.value.trim() }, role: fRole.value, status: fStatus.value };' in template
    assert 'id="edit-password"' not in template
    assert 'payload.password' not in template


def test_admin_user_update_accepts_profile_and_status_contract(monkeypatch):
    admin = {"id": 1, "username": "admin", "role": "admin", "status": "ACTIVE", "profile": {}}
    target = {"id": 2, "username": "diner", "role": "user", "status": "ACTIVE",
              "profile": {"name": "Antes", "email": "antes@example.test"}}
    calls = []

    def get_by_id(user_id):
        return deepcopy(admin if int(user_id) == 1 else target)

    def update(user_id, payload):
        calls.append((user_id, deepcopy(payload)))
        return {**deepcopy(target), **deepcopy(payload)}

    monkeypatch.setattr(UserModel, "get_by_id", get_by_id)
    monkeypatch.setattr(UserModel, "update", update)
    monkeypatch.setattr(admin_routes, "record_event", lambda *args, **kwargs: None)
    client = create_app({"TESTING": True, "SECRET_KEY": "x" * 32, "WTF_CSRF_ENABLED": False}).test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1

    response = client.put("/admin/user/2", json={
        "profile": {"name": "Nuevo", "email": "nuevo@example.test"},
        "role": "business_owner",
        "status": "SUSPENDED",
    })

    assert response.status_code == 200, response.get_json()
    assert calls == [(2, {"profile": {"name": "Nuevo", "email": "nuevo@example.test"},
                         "role": "business_owner", "status": "SUSPENDED"})]
    assert response.get_json()["user"]["status"] == "SUSPENDED"
    assert "password" not in response.get_json()["user"]
