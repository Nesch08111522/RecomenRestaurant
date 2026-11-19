"""Procesadores puros para el perfil personal de SmartResto."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Mapping


_ALLOWED = {
    "name", "email", "preferences", "restrictions", "daily_budget", "weekly_budget",
    "addresses", "notification_preferences", "location_consent", "cookies_consent",
    "birthday",
}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _list(value: Any, limit: int = 30, item_length: int = 80) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:limit]:
        clean = _text(item, item_length).lower()
        if clean and clean not in result:
            result.append(clean)
    return result


def _money(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 2) if 0 <= number <= 1_000_000 else None


def normalize_profile_patch(source: Mapping[str, Any] | None) -> dict[str, Any]:
    """Allowlist profile data and keep consent channels independent."""
    data = source or {}
    result: dict[str, Any] = {}
    for key in set(data) & _ALLOWED:
        value = data[key]
        if key == "name":
            result[key] = _text(value, 120)
        elif key == "email":
            email = _text(value, 254).lower()
            if email and not _EMAIL.fullmatch(email):
                raise ValueError("El correo electrónico no tiene un formato válido")
            result[key] = email
        elif key in {"preferences", "restrictions"}:
            result[key] = _list(value)
        elif key in {"daily_budget", "weekly_budget"}:
            amount = _money(value)
            if amount is None and value not in (None, ""):
                raise ValueError("El presupuesto debe ser un monto válido")
            result[key] = amount
        elif key == "addresses":
            result[key] = _list(value, 5, 220)
        elif key == "birthday":
            birthday = _text(value, 10)
            if birthday:
                try:
                    parsed = date.fromisoformat(birthday)
                except ValueError:
                    raise ValueError("La fecha de cumpleaños debe usar el formato AAAA-MM-DD") from None
                if parsed > date.today() or parsed.year < 1900:
                    raise ValueError("La fecha de cumpleaños no es válida")
                result[key] = parsed.isoformat()
            else:
                result[key] = ""
        elif key == "notification_preferences":
            if not isinstance(value, Mapping):
                raise ValueError("Las preferencias de notificación deben ser un objeto")
            channels = ("transactional", "marketing", "reviews", "waitlist")
            if any(not isinstance(value[channel], bool) for channel in channels if channel in value):
                raise ValueError("Los consentimientos deben ser booleanos true o false")
            result[key] = {channel: value[channel] for channel in channels if channel in value}
        elif key in {"location_consent", "cookies_consent"}:
            if not isinstance(value, bool):
                raise ValueError("Los consentimientos deben ser booleanos true o false")
            result[key] = value
    return result
