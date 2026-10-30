"""Reglas explicables para la revisión preliminar de restaurantes."""

import re
import unicodedata

_OFFENSIVE = re.compile(
    r"(?<![a-z0-9])(?:mrd|mierda|mierd[4a]|p(?:u|v)t[ao4]|c[o0]j[uú]d[eo]|csm|ctm)(?![a-z0-9])",
    re.I,
)
_REJECTED = {"rejected", "rechazado", "rejected_by_admin", "suspended", "suspendido"}
_APPROVED = {"approved", "aprobado", "automatic_approved", "published"}


def _normalizar(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def estado_pendiente(restaurante):
    if not isinstance(restaurante, dict):
        return False
    status = _normalizar(
        restaurante.get("approval_status") or restaurante.get("status")
    )
    if status in _REJECTED or status in _APPROVED:
        return False
    return not bool(
        restaurante.get("verified")
        or restaurante.get("rejected")
        or restaurante.get("suspended")
    )


def evaluar_restaurante(restaurante, filtro):
    """No toma decisiones: devuelve motivos verificables para revisión humana."""
    result = filtro.filter_restaurant(restaurante)
    details = result.get("result") or {}
    issues = []
    for issue in result.get("issues") or []:
        issue = str(issue).strip()
        if not issue:
            continue
        if (
            "no relacionado con comida" in _normalizar(issue)
            and float(details.get("food_score") or 0) > 20
        ):
            continue
        if issue not in issues:
            issues.append(issue)
    for field, label in (
        ("name", "nombre"),
        ("description", "descripción"),
        ("promo", "promoción"),
    ):
        match = _OFFENSIVE.search(_normalizar(restaurante.get(field)))
        if match:
            issue = f"Posible lenguaje ofensivo en {label}: «{match.group(0)}». Requiere revisión humana."
            if issue not in issues:
                issues.append(issue)
    return {
        "restaurant": restaurante,
        "issues": issues,
        "result": result,
        "food_score": details.get("food_score", 0),
        "needs_review": bool(issues),
    }


def motivo_contenido(item):
    """No confundir un motivo genérico con una infracción detectada."""
    reason = str(item.get("reason") or "").strip()
    if not reason or _normalizar(reason) in {
        "preevaluacion automatica",
        "revision automatica",
        "pendiente",
    }:
        return "En espera de revisión administrativa. No se registró una observación específica."
    return reason
