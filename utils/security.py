"""Controles de sesión y seguridad compartidos por los blueprints."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

from flask import flash, g, request, session
from flask_wtf.csrf import CSRFProtect

from models.user import UserModel


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


def fresh_session_user():
    """Revalida el rol contra el almacenamiento antes de autorizar."""
    if hasattr(g, "session_user_error"):
        raise g.session_user_error
    if hasattr(g, "session_identity"):
        return g.session_identity
    raw_id = session.get("user_id")
    try:
        user_id = int(raw_id)
    except (TypeError, ValueError):
        g.session_identity = None
        return None
    from database.connection import DatabaseConfigurationError, DatabaseConnectionError
    from psycopg import OperationalError
    try:
        user = UserModel.get_by_id(user_id)
    except (DatabaseConfigurationError, DatabaseConnectionError, OperationalError) as error:
        g.session_user_error = error
        raise
    if not UserModel.is_active(user) or session.get('auth_epoch', 0) != user.get('auth_epoch', 0):
        g.session_identity = None
        session.clear()
        flash("Tu sesión expiró o se cerró en otro dispositivo. Inicia sesión de nuevo.", "warning")
        return None
    g.account_record = user
    identity = session_identity(user)
    session["user"] = identity
    session["role"] = identity["role"]
    session["username"] = identity["username"]
    g.session_identity = identity
    return identity
