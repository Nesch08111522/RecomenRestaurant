"""Run browser QA only against a disposable database supplied by the operator."""
import os
from pathlib import Path
import secrets
import subprocess
import threading
from uuid import uuid4

from werkzeug.serving import make_server
from app import create_app
from models.user import UserModel
from models.restaurant import RestaurantModel

if __name__ == "__main__":
    if not os.environ.get("SMARTRESTO_TEST_DATABASE_URL") or os.environ["DATABASE_URL"] != os.environ["SMARTRESTO_TEST_DATABASE_URL"]:
        raise SystemExit("Configura una base temporal exclusiva para las pruebas.")
    prefix = "vista" + uuid4().hex[:7]
    password = secrets.token_urlsafe(24)
    for role in ("user", "business_owner", "admin"):
        user = UserModel.register(prefix + role, password, "", "Control visual", role)
        if role == "business_owner":
            RestaurantModel.create({"name":"Cocina de prueba visual","district":"Moche","owner_id":user["id"],"verified":True,
                                    "rating":0,"avg_price":0,"tags":[]})
    server = make_server("127.0.0.1", 0, create_app({"TESTING":True}), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = dict(os.environ, VISUAL_ORIGIN=f"http://127.0.0.1:{server.server_port}", VISUAL_PREFIX=prefix,
                   VISUAL_PASSWORD=password)
        command = ["node", str(Path(__file__).with_name("visual_browser.cjs"))]
        if os.environ.get("VISUAL_BASELINE"):
            subprocess.run(command, env=dict(env, VISUAL_COMPARE="1"), check=True)
        else:
            subprocess.run(command, env=env, check=True)
            subprocess.run(command, env=dict(env, VISUAL_COMPARE="1"), check=True)
    finally:
        server.shutdown()
