"""Shared configuration for OpenAI-compatible Qwen clients."""
import os
from typing import NamedTuple

from openai import OpenAI


GROQ_URL = "https://api.groq.com/openai/v1"


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
        return OpenAI(api_key=self.key, base_url=self.base, timeout=self.timeout, max_retries=0)


def settings(*, admin=False):
    key = (os.getenv("QWEN_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
    base = os.getenv("QWEN_BASE_URL") or GROQ_URL
    model = os.getenv("QWEN_MODEL") or "qwen/qwen3-32b"
    if admin:
        base = os.getenv("ADMIN_QWEN_BASE_URL") or base
        model = os.getenv("ADMIN_QWEN_MODEL") or model
    base = base.strip().rstrip("/")
    if not key or not model.strip() or (admin and base != GROQ_URL):
        raise AIUnavailable("provider_not_configured")
    try:
        timeout = float(os.getenv("ADMIN_AI_TIMEOUT", "12") if admin else os.getenv("QWEN_TIMEOUT", "45"))
        if not 0 < timeout < float("inf"):
            raise ValueError
    except ValueError as exc:
        raise AIUnavailable("invalid_timeout") from exc
    return ProviderSettings(key, base, model.strip(), max(2, min(timeout, 25)) if admin else timeout)
