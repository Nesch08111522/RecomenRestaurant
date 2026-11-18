"""Resumen conservador de carta para la revisión administrativa."""

import re
import math
from statistics import median

from utils.menu_auditor import auditar_plato

_FOOD_TERMS = ("pollo", "carne", "res", "cerdo", "pescado", "salmon", "atun", "huevo", "queso", "leche", "camaron")


def audit_restaurant_menu(restaurant, dishes, peer_prices=()):
    findings = []
    unknown = 0
    reviewed = 0
    for dish in dishes:
        try:
            audit = auditar_plato(dish)
        except (TypeError, ValueError):
            unknown += 1
            continue
        reviewed += 1
        observations = [
            item["reason"] for item in audit["observations"]
            if item["code"] not in {"missing_description", "not_certified"}
        ]
        ingredients = dish.get("ingredients")
        description = str(dish.get("description") or "").casefold()
        if not ingredients:
            unknown += 1
        elif description:
            declared = " ".join(ingredients).casefold() if isinstance(ingredients, list) else str(ingredients).casefold()
            for term in _FOOD_TERMS:
                if re.search(rf"\b{term}\b", description) and not re.search(rf"\b{term}\b", declared):
                    observations.append(f"La descripción menciona «{term}», pero no aparece en los ingredientes declarados; verifica la receta.")
        if observations:
            findings.append({"name": dish.get("name") or "Plato sin nombre", "observations": observations[:5], "result": audit["result"]})

    prices = []
    for value in peer_prices:
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value) and value > 0:
            prices.append(value)
    own = restaurant.get("avg_price")
    price_note = None
    if own in (None, "") or len(prices) < 5:
        price_note = "Precio comparativo desconocido: faltan datos suficientes del distrito."
    else:
        try:
            own = float(own)
            typical = median(prices)
            if math.isfinite(own) and own > 0 and typical > 0 and (own >= typical * 10 or own <= typical / 10):
                price_note = f"Precio promedio atípico frente al distrito: S/{own:g} versus mediana local S/{typical:g}; requiere verificación."
        except (TypeError, ValueError):
            price_note = "Precio comparativo desconocido: el valor registrado no es válido."

    return {
        "reviewed": reviewed,
        "unknown": unknown,
        "findings": findings,
        "price_note": price_note,
        "state": "por_verificar" if unknown else "revisado_con_observaciones" if findings or price_note else "sin_alertas_detectadas",
    }
