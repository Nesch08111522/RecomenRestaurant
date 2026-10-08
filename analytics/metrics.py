"""Métricas BI derivadas únicamente de registros existentes en SmartResto."""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Any, Iterable


def _rows(values: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [value for value in (values or []) if isinstance(value, dict)]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_bi_snapshot(*, users=(), restaurants=(), dishes=(), menus=(), favorites=(), reviews=(), audit_events=(), categories=()) -> dict[str, Any]:
    users = _rows(users)
    restaurants = _rows(restaurants)
    dishes = _rows(dishes)
    menus = _rows(menus)
    favorites = _rows(favorites)
    reviews = _rows(reviews)
    audit_events = _rows(audit_events)
    categories = _rows(categories)

    role_counts = Counter(str(user.get("role", "user")) for user in users)
    restaurant_status = Counter()
    for restaurant in restaurants:
        if restaurant.get("suspended") is True:
            restaurant_status["SUSPENDIDO"] += 1
        elif restaurant.get("verified") is True or restaurant.get("approval_status") == "APROBADO_AUTOMATICAMENTE":
            restaurant_status["APROBADO"] += 1
        else:
            restaurant_status[str(restaurant.get("approval_status", "PENDIENTE_REVISION"))] += 1

    rating_values = [_number(row.get("rating")) for row in reviews if row.get("rating") is not None]
    restaurant_rating_values = [_number(row.get("rating")) for row in restaurants if row.get("rating") is not None]
    available_dishes = [dish for dish in dishes if dish.get("is_available", True) is not False]
    user_interactions = Counter()
    for row in favorites:
        if row.get("user_id") is not None:
            user_interactions[str(row["user_id"])] += 1
    for row in reviews:
        if row.get("user_id") is not None:
            user_interactions[str(row["user_id"])] += 1

    restaurant_favorites = Counter(str(row.get("restaurant_id")) for row in favorites if row.get("restaurant_id") is not None)
    audit_actions = Counter(str(row.get("action")) for row in audit_events if row.get("action"))
    category_counts = Counter()
    category_names = {category.get("id"): category.get("name") for category in categories}
    for restaurant in restaurants:
        category = category_names.get(restaurant.get("category_id"), restaurant.get("category_id", "SIN_CATEGORIA"))
        category_counts[str(category)] += 1

    return {
        "generated_from": {
            "users": len(users), "restaurants": len(restaurants), "dishes": len(dishes),
            "menus": len(menus), "favorites": len(favorites), "reviews": len(reviews),
            "audit_events": len(audit_events),
        },
        "users": {
            "total": len(users),
            "by_role": dict(role_counts),
            "with_interactions": sum(1 for value in user_interactions.values() if value > 0),
            "interaction_events": sum(user_interactions.values()),
        },
        "business": {
            "restaurants_total": len(restaurants),
            "restaurants_by_status": dict(restaurant_status),
            "restaurants_by_category": dict(category_counts),
            "available_dishes": len(available_dishes),
            "menus_total": len(menus),
            "favorite_events": len(favorites),
            "top_restaurants_by_favorites": [
                {"restaurant_id": int(identifier), "favorites": count}
                for identifier, count in restaurant_favorites.most_common(10)
                if identifier.isdigit()
            ],
        },
        "quality": {
            "reviews_total": len(reviews),
            "average_review_rating": round(mean(rating_values), 2) if rating_values else None,
            "average_restaurant_rating": round(mean(restaurant_rating_values), 2) if restaurant_rating_values else None,
            "recommendation_feedback_status": "INSUFICIENTE_PARA_EVALUACION" if len(favorites) + len(reviews) < 20 else "DISPONIBLE_PARA_EVALUACION",
            "recommendation_feedback_events": len(favorites) + len(reviews),
        },
        "admin": {
            "audit_events_total": len(audit_events),
            "audit_actions": dict(audit_actions),
        },
        "export": {
            "schema_version": "bi.v1",
            "privacy": "No incluye contraseñas, hashes, tokens, IP en claro ni contenido privado de mensajes.",
        },
    }
