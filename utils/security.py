"""Controles de seguridad compartidos por la aplicación.

La capa mantiene la compatibilidad con Flask y con el almacenamiento JSON actual,
pero evita duplicar reglas críticas en cada blueprint.
"""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

from flask import request, session
from flask_wtf.csrf import CSRFProtect


csrf = CSRFProtect()


def is_safe_redirect_url(target: str | None) -> bool:
    """Acepta únicamente destinos locales del mismo host.

    Se conserva el parámetro ``next`` existente, pero se evita que pueda ser
    utilizado como redirección abierta hacia un dominio externo.
    """
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in {"http", "https"} and test.netloc == ref.netloc


def session_identity(user: dict) -> dict:
    """Construye el mínimo de identidad necesario para la sesión Flask."""
    profile = user.get("profile") or {}
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "role": user.get("role", "user"),
        "profile": {
            "name": profile.get("name"),
            "email": profile.get("email"),
        },
    }


def current_user_id() -> int | None:
    """Devuelve el identificador de sesión como entero válido."""
    raw_id = session.get("user_id")
    try:
        return int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        return None


def normalize_text(value: object, *, max_length: int = 500) -> str:
    """Normaliza texto recibido por formulario/API y limita su tamaño."""
    if value is None:
        return ""
    return " ".join(str(value).strip().split())[:max_length]


def valid_coordinate(value: object, minimum: float, maximum: float) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return minimum <= numeric <= maximum
