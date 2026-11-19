"""Procesadores puros para el perfil personal de SmartResto."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Mapping


_ALLOWED = {
    "name", "email", "preferences", "restrictions", "daily_budget", "weekly_budget",
    "addresses", "notification_preferences", "location_consent", "cookies_consent",
    "birthday", "phone",
}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def save_profile_image(upload, uid, kind):
    """Decode and re-encode images; never retain filenames, metadata or active content."""
    import io
    import secrets
    import warnings
    from pathlib import Path
    from flask import current_app
    from PIL import Image, ImageOps, UnidentifiedImageError
    if kind not in ('avatar', 'background'):
        raise ValueError('Tipo de foto no valido.')
    raw = upload.stream.read(2 * 1024 * 1024 + 1)
    if not raw or len(raw) > 2 * 1024 * 1024:
        raise ValueError('Cada foto debe pesar como maximo 2 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 16_000_000 or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Usa una foto JPEG, PNG o WebP estatica de hasta 16 megapixeles.')
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                clean = ImageOps.exif_transpose(image).convert('RGB')
                clean.thumbnail((1600, 1600) if kind == 'background' else (512, 512))
                root = Path(current_app.instance_path) / 'profile_images' / str(int(uid))
                root.mkdir(parents=True, exist_ok=True)
                filename = secrets.token_hex(24) + '.jpg'
                clean.save(root / filename, 'JPEG', quality=85)
                return filename
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('El archivo no es una imagen segura y valida.') from None


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
            email = str(value or '').strip().lower()
            if len(email) > 254 or '\r' in email or '\n' in email:
                raise ValueError('Revisa la longitud y formato del correo.')
            if email and not _EMAIL.fullmatch(email):
                raise ValueError("El correo electrónico no tiene un formato válido")
            result[key] = email
        elif key == 'phone':
            phone = str(value or '').strip()
            if phone and not re.fullmatch(r'\+[1-9][0-9]{7,14}', phone):
                raise ValueError('El celular requiere formato internacional E164.')
            result[key] = phone
        elif key in {"preferences", "restrictions"}:
            result[key] = _list(value)
            if key == 'restrictions' and (not isinstance(value, list) or len(value) > 30 or any(str(item).strip().lower() not in {'vegano', 'vegetariano', 'celiaco', 'sin gluten', 'alergia mariscos'} for item in value)):
                raise ValueError('Selecciona restricciones alimenticias reconocidas.')
        elif key in {"daily_budget", "weekly_budget"}:
            amount = _money(value)
            if amount is None and value not in (None, ""):
                raise ValueError("El presupuesto debe ser un monto válido")
            result[key] = amount
        elif key == "addresses":
            if not isinstance(value, list) or len(value) > 5 or any(len(str(item).strip()) > 220 for item in value):
                raise ValueError('Usa hasta cinco direcciones de 220 caracteres cada una.')
            result[key] = list(dict.fromkeys(_text(item, 220) for item in value if _text(item, 220)))
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
