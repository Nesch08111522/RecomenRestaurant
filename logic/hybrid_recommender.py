"""Recomendación híbrida determinista y explicable para SmartResto.

No entrena un modelo estadístico con datos insuficientes. Usa únicamente señales
persistidas: preferencias, restricciones, etiquetas, rating, precio, favoritos,
reseñas, disponibilidad explícita y distancia calculada por el sistema.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def _tokens(values: Any) -> set[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _content_score(restaurant: dict[str, Any], profile: dict[str, Any]) -> tuple[float, list[str]]:
    preferences = _tokens(profile.get("preferences"))
    restrictions = _tokens(profile.get("restrictions"))
    tags = _tokens(restaurant.get("tags"))
    dietary = _tokens(restaurant.get("dietary_restrictions"))
    category = _tokens([restaurant.get("category"), restaurant.get("category_id")])
    available = restaurant.get("is_available", restaurant.get("available", True)) is not False
    reasons: list[str] = []
    score = 0.0
    if preferences:
        matches = preferences.intersection(tags | category | dietary)
        if matches:
            score += min(35.0, 35.0 * len(matches) / max(1, len(preferences)))
            reasons.append("Coincide con tus preferencias registradas")
    if restrictions:
        if restrictions.intersection(dietary):
            score += 25.0
            reasons.append("Tiene opciones relacionadas con tus restricciones registradas")
        elif any(restriction in {"vegano", "vegan", "vegetariano", "vegetarian", "celiaco", "sin gluten", "gluten free"} for restriction in restrictions):
            # No se afirma compatibilidad si no hay una señal explícita.
            score -= 40.0
    if available:
        score += 10.0
    else:
        score -= 60.0
    if restaurant.get("promo"):
        score += 5.0
        reasons.append("Tiene una promoción registrada")
    return max(0.0, min(100.0, score)), reasons


def _context_score(restaurant: dict[str, Any], context: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    rating = max(0.0, min(5.0, _safe_number(restaurant.get("rating"))))
    score += rating / 5.0 * 30.0
    if rating >= 4.5:
        reasons.append("Valoración registrada de 4.5 o superior")
    distance = _safe_number(restaurant.get("distance_km"), 999.0)
    if distance < 999:
        score += max(0.0, 20.0 - min(distance, 20.0))
        if distance <= 5:
            reasons.append("Se encuentra dentro de la proximidad calculada")
    max_price = context.get("max_price", context.get("budget"))
    if max_price not in (None, ""):
        limit = _safe_number(max_price, -1)
        price = _safe_number(restaurant.get("avg_price"), -1)
        if limit >= 0 and price >= 0:
            if price <= limit:
                score += 15.0
                reasons.append("El precio registrado está dentro del presupuesto indicado")
            else:
                score -= 25.0
    if restaurant.get("is_open_now") is True:
        score += 10.0
        reasons.append("El sistema indica disponibilidad horaria actual")
    return max(0.0, min(100.0, score)), reasons


def _collaborative_scores(user_id: Any, favorites: Iterable[dict[str, Any]], reviews: Iterable[dict[str, Any]]) -> tuple[dict[int, float], bool]:
    """Calcular señal colaborativa solo si existen interacciones suficientes."""
    try:
        current_user = int(user_id)
    except (TypeError, ValueError):
        current_user = None
    favorite_rows = [row for row in favorites if isinstance(row, dict)]
    review_rows = [row for row in reviews if isinstance(row, dict)]
    if current_user is None or len(favorite_rows) + len(review_rows) < 5:
        return {}, False
    user_items: dict[int, set[int]] = defaultdict(set)
    for row in favorite_rows:
        try:
            user_items[int(row["user_id"])].add(int(row["restaurant_id"]))
        except (KeyError, TypeError, ValueError):
            continue
    current_items = user_items.get(current_user, set())
    if not current_items:
        return {}, False
    scores: dict[int, float] = defaultdict(float)
    for other_user, items in user_items.items():
        if other_user == current_user:
            continue
        overlap = len(current_items.intersection(items))
        if not overlap:
            continue
        for item in items.difference(current_items):
            scores[item] += min(1.0, overlap / max(1, len(current_items)))
    for row in review_rows:
        try:
            if int(row["user_id"]) == current_user:
                continue
            rating = _safe_number(row.get("rating"))
            if rating >= 4:
                scores[int(row["restaurant_id"])] += 0.15
        except (KeyError, TypeError, ValueError):
            continue
    if not scores:
        return {}, False
    maximum = max(scores.values())
    return ({key: value / maximum * 100.0 for key, value in scores.items()} if maximum else {}), True


def recommend(restaurants: list[dict[str, Any]], profile: dict[str, Any] | None = None, context: dict[str, Any] | None = None, favorites: Iterable[dict[str, Any]] = (), reviews: Iterable[dict[str, Any]] = ()) -> list[dict[str, Any]]:
    profile = profile or {}
    context = context or {}
    collaborative, collaborative_active = _collaborative_scores(profile.get("id"), favorites, reviews)
    results: list[dict[str, Any]] = []
    for restaurant in restaurants:
        content, content_reasons = _content_score(restaurant, profile)
        contextual, context_reasons = _context_score(restaurant, context)
        collaborative_score = collaborative.get(restaurant.get("id"), 0.0)
        # El colaborativo solo pesa si existe señal real; de lo contrario se usa
        # contenido + reglas/contexto para evitar falsos patrones de cold start.
        if collaborative_active:
            final_score = content * 0.45 + contextual * 0.35 + collaborative_score * 0.20
        else:
            final_score = content * 0.55 + contextual * 0.45
        enriched = dict(restaurant)
        enriched["hybrid_score"] = round(final_score, 2)
        enriched["recommendation"] = {
            "method": "hybrid" if collaborative_active else "content_rules_context",
            "cold_start": not collaborative_active,
            "score_breakdown": {
                "content": round(content, 2),
                "context": round(contextual, 2),
                "collaborative": round(collaborative_score, 2),
            },
            "reasons": content_reasons + context_reasons,
        }
        results.append(enriched)
    return sorted(results, key=lambda item: (-item.get("hybrid_score", 0), item.get("id", 0)))


def suggest_menu(dishes: list[dict[str, Any]], *, max_items_per_category: int = 3) -> dict[str, Any]:
    """Proponer combinaciones solo con platos existentes, disponibles y con precio registrado."""
    category_map = {
        "entrada": "entradas", "entradas": "entradas",
        "fondo": "fondos", "fondos": "fondos", "principal": "fondos",
        "postre": "postres", "postres": "postres",
        "bebida": "bebidas", "bebidas": "bebidas",
    }
    selected: dict[str, list[dict[str, Any]]] = {key: [] for key in {"entradas", "fondos", "postres", "bebidas"}}
    for dish in sorted(dishes, key=lambda item: (not bool(item.get("is_recommended")), _safe_number(item.get("price"), 999999), item.get("id", 0))):
        if dish.get("is_available", True) is False or dish.get("price") in (None, ""):
            continue
        bucket = category_map.get(str(dish.get("category", "")).strip().lower())
        if bucket and len(selected[bucket]) < max_items_per_category:
            selected[bucket].append(dish)
    selected["evidence"] = [
        "Propuesta construida exclusivamente con platos disponibles del restaurante.",
        "Los nombres, categorías y precios proceden del catálogo registrado.",
    ]
    return selected
