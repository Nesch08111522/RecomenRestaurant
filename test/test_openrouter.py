"""Provider selection without external requests or real credentials."""
import pytest

from utils.llm_provider import AIUnavailable, settings


@pytest.fixture
def router(monkeypatch):
    for name in ("ADMIN_AI_API_KEY", "ADMIN_AI_BASE_URL", "ADMIN_AI_MODEL",
                 "ADMIN_QWEN_BASE_URL", "ADMIN_QWEN_MODEL", "AI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("AI_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-router-key")
    return monkeypatch


def test_router_shared_by_admin_and_chat(router):
    assert settings()[:3] == settings(admin=True)[:3]
    assert settings().key == "test-router-key"
    assert settings().model == "openai/gpt-4o-mini"


def test_router_supports_paid_model_and_admin_override(router):
    router.setenv("AI_MODEL", "provider/paid-model")
    router.setenv("ADMIN_AI_API_KEY", "test-admin-key")
    assert settings().model == "provider/paid-model"
    assert settings(admin=True).key == "test-admin-key"


def test_router_never_sends_legacy_provider_key(router):
    router.setenv("OPENROUTER_API_KEY", "")
    router.setenv("QWEN_API_KEY", "test-legacy-key")
    router.setenv("GROQ_API_KEY", "test-other-key")
    with pytest.raises(AIUnavailable, match="provider_not_configured"):
        settings()


@pytest.mark.parametrize("endpoint", ["https:///api", "http://external.example/v1",
                                     "https://user:password@example.com/v1"])
def test_reject_invalid_endpoint(router, endpoint):
    router.setenv("AI_BASE_URL", endpoint)
    with pytest.raises(AIUnavailable, match="invalid_endpoint"):
        settings()


@pytest.mark.parametrize("base", ["https://openrouter.ai", "https://openrouter.ai/api/v1/",
                                 "https://openrouter.ai/api/v1/chat/completions"])
def test_sdk_request_url_headers_and_key_priority(router, monkeypatch, base):
    import httpx
    from openai import OpenAI
    import utils.llm_provider as provider

    router.setenv("AI_BASE_URL", base)
    router.setenv("AI_API_KEY", "  preferred-test-key  ")

    def respond(request):
        assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert request.method == "POST"
        assert request.headers["authorization"] == "Bearer preferred-test-key"
        assert request.headers["user-agent"] == "SmartResto-Backend/1.0"
        assert request.headers["http-referer"] == "http://127.0.0.1:5000"
        assert request.headers["content-type"] == "application/json"
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "OK"}}]})

    monkeypatch.setattr(provider, "OpenAI", lambda **kwargs: OpenAI(
        **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond))))
    with settings().client() as client:
        assert client.chat.completions.create(model=settings().model, messages=[]).choices[0].message.content == "OK"


def test_interpret_csrf_methods_and_upstream_diagnostics(router, monkeypatch, caplog):
    import httpx
    from openai import PermissionDeniedError
    from itsdangerous import URLSafeTimedSerializer
    from app import create_app

    app = create_app({"TESTING": True, "SECRET_KEY": "test-request-secret"})
    client = app.test_client()
    response = client.get("/api/ai/interpret")
    assert response.status_code == 405
    assert response.is_json
    assert "POST" in response.headers["Allow"]
    assert client.get("/auth/api/missing").is_json
    assert client.post("/api/ai/interpret", json={"text": "Un almuerzo"}).status_code == 400
    with client.session_transaction() as session:
        session["csrf_token"] = "test-csrf"
    token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("test-csrf")
    headers = {"X-CSRFToken": token}
    monkeypatch.setattr("views.ai_routes._rate_limited", lambda: False)
    monkeypatch.setattr("views.ai_routes._llm_json", lambda messages: {"max_price": 20, "summary": "Almuerzo"})
    response = client.post("/api/ai/interpret", json={"text": "Un almuerzo"}, headers=headers)
    assert response.status_code == 200
    assert response.json["filters"]["max_price"] == 20

    def forbidden(messages):
        response = httpx.Response(403, text="provider diagnostic test-router-key", request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
        raise PermissionDeniedError("rejected", response=response, body=None)

    monkeypatch.setattr("views.ai_routes._llm_json", forbidden)
    response = client.post("/api/ai/interpret", json={"text": "Un almuerzo"}, headers=headers)
    assert response.status_code == 502
    assert "HTTP 403" in caplog.text
    assert "provider diagnostic" in caplog.text
    assert "test-router-key" not in caplog.text
    assert b"provider diagnostic" not in response.data
