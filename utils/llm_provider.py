"""Shared configuration for OpenAI-compatible providers, including OpenRouter."""
import os
from typing import NamedTuple

from openai import OpenAI


OPENROUTER_URL = "https://openrouter.ai/api/v1"


class AIUnavailable(RuntimeError):
    def __init__(self, code="provider_unavailable"):
        self.code = code
        super().__init__(code)


class ProviderSettings(NamedTuple):
    key: str
    base: str
    model: str
    timeout: float

    def client(self):
        return OpenAI(
            api_key=self.key, base_url=self.base, timeout=self.timeout, max_retries=0,
            default_headers={
                "User-Agent": "SmartResto-Backend/1.0",
                "HTTP-Referer": "http://127.0.0.1:5000",
                "Content-Type": "application/json",
            },
        )


def settings(*, admin=False):
    from urllib.parse import urlsplit
    key = (os.getenv("AI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "").strip()
    base = os.getenv("AI_BASE_URL") or OPENROUTER_URL
    model = os.getenv("AI_MODEL", "openai/gpt-4o-mini")
    if admin:
        base = os.getenv("ADMIN_AI_BASE_URL") or base
        model = os.getenv("ADMIN_AI_MODEL") or model
        key = (os.getenv("ADMIN_AI_API_KEY") or key).strip()
    base = base.strip().rstrip("/")
    parsed = urlsplit(base)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed.hostname or parsed.scheme not in {"https", "http"} or (parsed.scheme == "http" and not local) or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AIUnavailable("invalid_endpoint")
    if parsed.hostname == "openrouter.ai":
        # The SDK appends /chat/completions. Accept the origin or a pasted
        # full endpoint, and always supply the canonical API base once.
        base = OPENROUTER_URL
    if not key and local:
        key = "local"
    if not key or not model.strip():
        raise AIUnavailable("provider_not_configured")
    try:
        timeout = float(os.getenv("ADMIN_AI_TIMEOUT", "12") if admin else os.getenv("AI_TIMEOUT", "45"))
        if not 0 < timeout < float("inf"):
            raise ValueError
    except ValueError as exc:
        raise AIUnavailable("invalid_timeout") from exc
    return ProviderSettings(key, base, model.strip(), max(2, min(timeout, 25)) if admin else timeout)


def log_provider_error(logger, operation, error):
    """Keep upstream HTTP diagnostics in server logs, with credentials redacted."""
    response = getattr(error, "response", None)
    if response is None:
        logger.exception("%s: %s", operation, type(error).__name__)
        return
    body = response.text
    for name in ("AI_API_KEY", "OPENROUTER_API_KEY", "ADMIN_AI_API_KEY"):
        secret = (os.getenv(name) or "").strip()
        if secret:
            body = body.replace(secret, "[clave ocultada]")
    logger.error("%s: HTTP %s; respuesta=%s", operation, response.status_code, body)
