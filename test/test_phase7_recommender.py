from logic.hybrid_recommender import recommend, suggest_menu


def test_recommendation_uses_explicit_cold_start_fallback():
    rows = recommend(
        [
            {"id": 2, "name": "Casa Vegana", "tags": ["vegano"], "rating": 4.8, "distance_km": 1.2, "avg_price": 20},
            {"id": 1, "name": "Otro", "tags": [], "rating": 3.0, "distance_km": 8, "avg_price": 80},
        ],
        {"id": 99, "preferences": ["vegano"], "restrictions": []},
        {"max_price": 40},
        favorites=[],
        reviews=[],
    )
    assert rows[0]["id"] == 2
    assert rows[0]["recommendation"]["method"] == "content_rules_context"
    assert rows[0]["recommendation"]["cold_start"] is True
    assert "Coincide con tus preferencias registradas" in rows[0]["recommendation"]["reasons"]


def test_recommendation_activates_collaborative_signal_only_with_enough_data():
    favorites = [
        {"user_id": 7, "restaurant_id": 1}, {"user_id": 7, "restaurant_id": 2},
        {"user_id": 8, "restaurant_id": 1}, {"user_id": 8, "restaurant_id": 3},
        {"user_id": 9, "restaurant_id": 2},
    ]
    rows = recommend(
        [{"id": 3, "tags": [], "rating": 3.5, "distance_km": 3}],
        {"id": 7, "preferences": [], "restrictions": []},
        {},
        favorites=favorites,
        reviews=[],
    )
    assert rows[0]["recommendation"]["method"] == "hybrid"
    assert rows[0]["recommendation"]["score_breakdown"]["collaborative"] > 0


def test_menu_suggestion_uses_only_available_catalog_data():
    suggestion = suggest_menu([
        {"id": 1, "name": "Entrada", "category": "Entrada", "price": 10, "is_available": True, "is_recommended": True},
        {"id": 2, "name": "Agotado", "category": "Fondo", "price": 20, "is_available": False},
        {"id": 3, "name": "Fondo", "category": "Fondo", "price": 30, "is_available": True},
    ])
    assert [dish["id"] for dish in suggestion["entradas"]] == [1]
    assert [dish["id"] for dish in suggestion["fondos"]] == [3]
    assert suggestion["evidence"]
