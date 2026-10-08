import re

from app import create_app

SECRET = "test-secret-key-123456789012345678901234"
app = create_app({"TESTING": True, "SECRET_KEY": SECRET, "WTF_CSRF_ENABLED": True})
client = app.test_client()

search_read_only = client.post("/api/search", json={"district": "Huanchaco"})
assert search_read_only.status_code == 200, search_read_only.status_code

profile_without_csrf = client.post("/auth/profile/update", data={"name": "Attempt"})
assert profile_without_csrf.status_code == 400, profile_without_csrf.status_code
assert profile_without_csrf.get_json() is None

login_page = client.get("/auth/login")
assert login_page.status_code == 200
assert b'name="csrf_token"' in login_page.data
match = re.search(rb'name="csrf_token"[^>]+value="([^"]+)"', login_page.data)
assert match, "No se encontró token CSRF en login"
token = match.group(1).decode()
login_without_csrf = client.post("/auth/login", data={"username": "unknown", "password": "invalid"})
assert login_without_csrf.status_code == 400
login_with_csrf = client.post("/auth/login", data={"username": "unknown", "password": "invalid", "csrf_token": token})
assert login_with_csrf.status_code in (200, 302)

home = client.get("/")
for header, expected in (("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "SAMEORIGIN")):
    assert home.headers.get(header) == expected, (header, home.headers.get(header))

print("csrf_and_headers=ok")
print("read_only_search_exemption=ok")
print("profile_mutation_without_csrf=400")
print("login_without_csrf=400")
print("security_headers=ok")
