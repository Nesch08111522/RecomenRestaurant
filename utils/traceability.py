"""Construcción de trazabilidad histórica hacia atrás de un pedido."""
from __future__ import annotations

from typing import Any

TRACEABILITY_VERSION = 1


def build_order_traceability(order: dict[str, Any]) -> dict[str, Any]:
    """Devuelve plato, ingrediente y lote usando la instantánea del pedido.

    No consulta el inventario actual: la evidencia histórica debe permanecer
    estable aunque el negocio cambie o reponga el inventario.
    """
    lines = []
    complete = True
    for line in order.get("lines") or []:
        ingredients = []
        for name, used in (line.get("usage") or {}).items():
            used = used if isinstance(used, dict) else {}
            item = {
                "ingredient": name,
                "quantity": used.get("amount"),
                "unit": used.get("unit"),
                "lot": used.get("lot"),
                "expires": used.get("expires"),
                "recorded_at": used.get("recorded_at"),
            }
            if not item["lot"] or not item["unit"] or not item["expires"]:
                complete = False
            ingredients.append(item)
        lines.append({
            "offer_id": line.get("offer"),
            "dish_id": line.get("dish_id"),
            "name": line.get("name"),
            "quantity": line.get("qty"),
            "ingredients": ingredients,
        })
    return {
        "version": TRACEABILITY_VERSION,
        "order_id": order.get("id"),
        "restaurant_id": order.get("rid"),
        "business": order.get("business"),
        "state": order.get("state"),
        "recorded_at": order.get("created"),
        "complete": complete,
        "lines": lines,
    }
