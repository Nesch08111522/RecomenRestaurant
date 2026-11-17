import re
import time
from uuid import uuid4

from app import create_app
from models.user import UserModel
from test_business_flow import token
from utils.account_security import totp


def test_account_recovery_and_second_factor(test_database, monkeypatch):
    app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex})
    first, second = app.test_client(), app.test_client()
    username, password = uuid4().hex, uuid4().hex + "1A"
    UserModel.register(username, password, "", username)
    def post(client, path, **data):
        return client.post("/auth/" + path, data={**data, "csrf_token": token(client)})
    for client in (first, second):
        assert post(client, "login", username=username, password=password).status_code == 302
    enrollment = post(first, "seguridad", password=password, action="start")
    secret = re.search(rb"<code>([A-Z2-7]+)</code>", enrollment.data)[1].decode()
    step = int(time.time() // 30)
    enabled = post(first, "seguridad", password=password, action="enable", otp=totp(secret,step))
    recovery = re.search(rb"<code>([A-Za-z0-9_-]+)</code>", enabled.data)[1].decode()
    assert second.get("/auth/profile").status_code == 302
    assert post(second, "login", username=username, password=password).status_code == 200
    assert post(second, "login", username=username, password=password, otp=totp(secret,step)).status_code == 200
    assert post(second, "login", username=username, password=password, otp=totp(secret,step+1)).status_code == 302
    new = uuid4().hex + "A2"
    assert post(second, "recuperar", username=username, code=recovery, password=new).status_code == 302
    assert first.get("/auth/profile").status_code == 302
    assert post(second, "recuperar", username=username, code=recovery, password=password).status_code == 200
    assert post(second, "login", username=username, password=new).status_code == 302


def test_bounded_account_attempts(test_database):
    app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex})
    client, name = app.test_client(), uuid4().hex
    headers = {"X-CSRFToken": token(client)}
    for _ in range(12):
        assert client.post("/auth/login", data={"username":name,"password":"incorrecta"}, headers=headers).status_code == 200
    assert client.post("/auth/login", data={"username":name,"password":"incorrecta"}, headers=headers).status_code == 429
