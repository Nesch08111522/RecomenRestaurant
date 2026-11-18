"""Ancla criptográfica de reseñas verificadas.

Este módulo es puro: no importa Flask, no importa la base de datos, no toca red.
Solo hashing determinista. Así se puede testear sin Supabase y sin pooler.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import unicodedata

ANCHOR_VERSION = "smre.v1"

KIND_VERIFIED = "review.verified"
KIND_AMENDED = "review.amended"


def _secret() -> bytes:
    """Secreto del servidor para pseudonimizar user_id. Falla si no está."""
    secret = os.environ.get("ANCHOR_PSEUDONYM_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError(
            "ANCHOR_PSEUDONYM_SECRET debe tener al menos 32 caracteres. "
            "Defínelo en el entorno del servidor."
        )
    return secret.encode("utf-8")


def pseudonym(user_id) -> str:
    """HMAC-SHA256 del user_id. No reversible sin el secreto del servidor."""
    return hmac.new(_secret(), str(user_id).encode("utf-8"), hashlib.sha256).hexdigest()


def normalize_comment(text: str | None) -> str:
    """Normaliza el comentario para que el hash sea estable.

    No altera el texto que se muestra al usuario; solo la forma que se hashea.
    - NFKD descompone acentos.
    - Se eliminan marcas combinantes.
    - Se colapsan espacios y se pasa a minúsculas.
    """
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def purchase_state_hash(order: dict) -> str:
    """Prueba que la reseña nació de una compra entregada, pagada y no reembolsada.

    No publica el pedido completo: solo un hash de su estado.
    """
    valid = (
        order.get("state") == "Entregado"
        and order.get("paid") is True
        and not order.get("refunded")
    )
    state = "Entregado|paid|not_refunded" if valid else "invalid"
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def canonical_hash(
    review: dict,
    order: dict,
    kind: str = KIND_VERIFIED,
    prev_hash: str | None = None,
) -> str:
    """Hash canónico de una reseña.

    Reglas:
    - Solo hashes, nunca PII ni texto completo.
    - `kind` distingue alta de edición.
    - `prev_hash` encadena una edición con la versión anterior.
    """
    parts = [
        ANCHOR_VERSION,
        kind,
        str(review["id"]),
        str(review["restaurant_id"]),
        str(review.get("order_id", "")),
        pseudonym(review["user_id"]),
        str(int(review["rating"])),
        hashlib.sha256(normalize_comment(review.get("comment", "")).encode("utf-8")).hexdigest(),
        str(review.get("updated_at") or review.get("created_at", "")),
        purchase_state_hash(order),
    ]
    if kind == KIND_AMENDED:
        parts.append(prev_hash or "")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()