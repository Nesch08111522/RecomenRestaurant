from datetime import datetime

from logic.phase7_recommender import recommend


AT = datetime.fromisoformat("2026-11-18T12:00:00-05:00")
RESTAURANTS = [
    {"id": 1, "name": "Costa", "category": "Cevichería", "lat": -8.1, "lng": -79, "avg_price": 36,
     "open_time": "11:00", "close_time": "18:00", "rating": 4.7},
    {"id": 2, "name": "Marea", "category": "Cevichería", "lat": -8.11, "lng": -79,
     "open_time": "11:00", "close_time": "23:00", "avg_price": 40},
    {"id": 3, "name": "Pampa", "category": "Criolla", "lat": -8.2, "lng": -79,
     "open_time": "18:00", "close_time": "02:00", "avg_price": 30},
]
DISHES = [
    {"id": 11, "restaurant_id": 1, "name": "Ceviche de pescado", "price": 36},
    {"id": 12, "restaurant_id": 2, "name": "Arroz con mariscos", "price": 25},
    {"id": 13, "restaurant_id": 3, "name": "Emoliente", "price": 8, "dietary_info": ["vegano"]},
    {"id": 14, "restaurant_id": 2, "name": "Jalea mixta", "is_available": False, "price": 26},
]


def test_cold_start_uses_declared_preferences_without_inventing_history():
    result = recommend(restaurants=RESTAURANTS, dishes=DISHES, at=AT,
                       profile={"preferences": ["Cocina marina"]})
    personal = result["for_you"]["items"]
    assert personal
    assert all(card["personalization_basis"] == "declared_preferences" for card in personal)
    assert result["history"] == {"dishes": [], "restaurants": []}
    assert all("compras confirmadas" not in " ".join(card["reasons"]) for card in personal)


def test_confirmed_purchases_learn_affinity_but_surface_new_merchants():
    delivered = {"rid": 1, "business": "Costa", "day": "2026-11-16", "state": "Entregado", "channel": "Local",
                 "paid": True, "lines": [{"dish_id": 11, "name": "Ceviche de pescado", "qty": 2, "unit": 3600}]}
    invalid_order = {"rid": 3, "state": "Entregado", "paid": True, "refunded": True,
                     "lines": [{"dish_id": 13, "name": "Emoliente", "qty": 1}]}
    dismissed = {"id": 21, "restaurant_id": 2, "name": "Leche de tigre", "price": 20}
    result = recommend(
        restaurants=RESTAURANTS, dishes=[*DISHES, dismissed], at=AT,
        orders=[delivered, {**delivered, "channel": "Delivery", "day": "2026-11-17"}, invalid_order],
        visits=[{"restaurant_id": 3, "date": "2026-11-17", "status": "confirmada"}],
        feedback={"dish-21": "dismissed"}, options={"discovery": True},
    )
    assert result["dishes"][0]["id"] == 12
    assert "Afinidad con tu historial: cocina marina" in result["dishes"][0]["reasons"]
    assert "Cuesta menos que opciones similares de tus compras confirmadas" in result["dishes"][0]["reasons"]
    assert all(card["id"] not in {11, 14, 21} for card in result["dishes"])
    assert result["restaurants"][0]["id"] == 2
    assert result["history"]["dishes"][0]["quantity"] == 4
    assert result["history"]["dishes"][0]["count"] == 2
    assert [(visit["id"], visit["visits"]) for visit in result["history"]["restaurants"]] == [(1, 1)]
    assert result["recurring"] == [{"label": "Cocina marina", "count": 2}]


def test_stock_purchase_time_and_coverage_filter_market_experiences():
    listing = {"dish_id": 12, "name": "Arroz con mariscos", "rid": 2, "day": "2026-11-19",
               "ends": "2026-11-19T20:00:00-05:00", "price": 2000, "available": 3,
               "channels": ["Delivery"], "pin": [-8.11, -79], "radius": 3, "occasion": "Cena",
               "context_tags": ["Para compartir"], "image": "/mercado/foto/40"}
    result = recommend(
        restaurants=RESTAURANTS, dishes=DISHES, offers=[{**listing, "id": 40}, {**listing, "id": 41, "available": 0}],
        options={"q": "quiero arroz con mariscos", "budget": 25, "channel": "Delivery", "day": "2026-11-19",
                 "time": "19:00", "moment": "familia"}, profile={"location_consent": True}, location=(-8.1, -79),
        weather={"apparent_temperature": 32, "precipitation": 0}, at=AT,
    )
    cards = result["experiences"]
    assert [card["id"] for card in cards] == [40]
    assert result["dishes"][0]["offer_id"] == 40
    assert cards[0]["image"] == "/mercado/foto/40"
    assert cards[0]["price"] == 20
    assert "Encaja con la ocasión que elegiste" in cards[0]["reasons"]
    assert "Opción para la cena" in cards[0]["reasons"]
    assert result["context"]["weather_used"] is False
    assert result["context"]["meal"] == "Cena"
    assert result["restaurants"][0]["id"] == 2
    assert result["restaurants"][0]["price_from"]
    late = recommend(
        restaurants=RESTAURANTS, dishes=DISHES, offers=[{**listing, "id": 40}], at=AT,
        options={"day": "2026-11-19", "time": "21:00", "channel": "Delivery"},
    )
    assert late["items"] == []


def test_allergen_declarations_are_required_and_known_aliases_are_excluded():
    confirmed = {"id": 40, "dish_id": 13, "rid": 3, "name": "Emoliente", "day": "2026-11-18", "price": 800,
                 "available": 4, "channels": ["Recojo"], "diets": ["Vegano"], "cross": "declared", "allergens": []}
    result = recommend(
        restaurants=RESTAURANTS, dishes=DISHES, at=AT,
        offers=[confirmed, {**confirmed, "id": 41, "cross": "unknown"}, {**confirmed, "id": 42, "allergens": ["camarones"]}],
        profile={"restrictions": ["vegetariano", "alergia a los mariscos"]},
        location=(-8.1, -79), weather={"apparent_temperature": 32, "latitude": -8.1},
    )
    assert [card["id"] for card in result["experiences"]] == [40]
    assert [card["id"] for card in result["dishes"]] == [13]
    assert [card["id"] for card in result["restaurants"]] == [3]
    assert result["context"]["location_used"] is False
    assert result["context"]["weather"] is None
    assert all(card["distance_km"] is None for card in result["items"])


def test_budget_uses_remaining_limits_and_craving_preserves_empty_results():
    orders = [{"rid": 3, "day": "2026-11-16", "total": 2000, "state": "Entregado", "paid": True, "lines": []}]
    result = recommend(restaurants=RESTAURANTS, dishes=DISHES, profile={"weekly_budget": 30}, orders=orders, at=AT)
    assert result["context"]["budget"] == 10
    assert [card["id"] for card in result["dishes"]] == [13]
    empty = recommend(restaurants=RESTAURANTS, dishes=DISHES, options={"q": "quiero una pizza"}, at=AT)
    assert empty["items"] == []


def test_context_uses_season_and_authorized_weather_without_echoing_coordinates():
    dish = {"id": 21, "restaurant_id": 2, "name": "Ensalada de estación", "price": 19,
            "seasons": ["primavera"], "context_tags": ["Fresco"]}
    result = recommend(
        restaurants=RESTAURANTS, dishes=[dish], at=AT, profile={"location_consent": True},
        options={"q": "ensalada"}, location=(-8.1, -79),
        weather={"apparent_temperature": 27, "precipitation": 0, "latitude": -8.1},
    )
    reasons = result["dishes"][0]["reasons"]
    assert "Opción de temporada publicada por el negocio" in reasons
    assert "Encaja con el clima local consultado" in reasons
    assert "latitude" not in result["context"]["weather"]


def test_paid_confirmed_order_affects_rank_without_claiming_consumption_or_visit():
    order = {"rid": 1, "state": "Confirmado", "paid": True, "channel": "Local", "day": "2026-11-19",
             "lines": [{"dish_id": 11, "name": "Ceviche de pescado", "qty": 1}]}
    result = recommend(restaurants=RESTAURANTS, dishes=DISHES, orders=[order], at=AT)
    recommended = {card["id"]: card for card in result["dishes"]}
    assert "Afinidad con tu historial: cocina marina" in recommended[12]["reasons"]
    assert "Ya figura en una compra confirmada" in recommended[11]["reasons"]
    assert "Ya lo probaste" not in recommended[11]["reasons"]
    assert result["history"] == {"dishes": [], "restaurants": []}


def test_only_approved_market_listing_can_surface_market_only_dish():
    market_only = {"id": 31, "restaurant_id": 2, "name": "Jalea peruana", "menu_date": "2026-11-18", "price": 30}
    menu_item = {"id": 32, "restaurant_id": 2, "name": "Jalea peruana", "menu_date": "2026-11-18",
                 "day_of_week": "miércoles", "price": 30}
    market_listing = {"id": 41, "dish_id": 31, "name": "Jalea peruana", "day": "2026-11-18", "rid": 2,
                      "price": 3000, "available": 2, "channels": ["Delivery"], "review_state": "pending"}
    result = recommend(restaurants=RESTAURANTS, dishes=[market_only, menu_item], offers=[market_listing], at=AT)
    assert [card["id"] for card in result["dishes"]] == [32]
    assert result["experiences"] == []

    result = recommend(
        restaurants=RESTAURANTS, dishes=[{**market_only, "market_only": True}],
        offers=[{**market_listing, "review_state": "approved"}], at=AT,
    )
    assert [card["id"] for card in result["dishes"]] == [31]
    assert [card["id"] for card in result["experiences"]] == [41]


def test_custom_catalog_categories_learn_from_cash_on_delivery_confirmation():
    restaurants = [
        {"id": 1, "name": "Antojos de Cali", "category_id": 8},
        {"id": 2, "name": "Rincón del Valle", "category_id": 8},
        {"id": 3, "name": "La Quinta"},
    ]
    categories = [{"id": 8, "name": "Cocina colombiana"}]
    dishes = [
        {"id": 51, "restaurant_id": 1, "name": "Arepa de choclo", "price": 22},
        {"id": 52, "restaurant_id": 2, "name": "Pandebono", "price": 12},
        {"id": 53, "restaurant_id": 3, "name": "Quinua cocida", "price": 8},
    ]
    confirmation = {"id": 90, "rid": 1, "state": "Confirmado", "method": "Contraentrega",
                    "paid": False, "day": "2026-11-18", "total": 2200,
                    "lines": [{"dish_id": 51, "name": "Arepa de choclo", "qty": 1, "unit": 2200}]}
    orders = [
        confirmation,
        {**confirmation, "id": 91, "state": "Recibido"},
        {**confirmation, "id": 92, "state": "Entregado", "paid": True, "payment_incident": True},
    ]
    result = recommend(restaurants=restaurants, categories=categories, dishes=dishes, orders=orders, at=AT)
    pandebono = result["dishes"][0]
    assert pandebono["name"] == "Pandebono" and pandebono["business"] == "Rincón del Valle"
    assert "Afinidad con tu historial: cocina colombiana" in pandebono["reasons"]
    assert "Cuesta menos que opciones similares de tus compras confirmadas" in pandebono["reasons"]
    assert result["history"] == {"dishes": [], "restaurants": []}
    assert result["recurring"] == []


def test_repeated_views_improve_related_catalog_ranking_without_faking_recurring_tastes():
    restaurants = [{"id": rid, "name": f"Negocio {rid}"} for rid in range(1, 4)]
    dishes = [
        {"id": 51, "restaurant_id": 1, "name": "Brocheta de kofta", "price": 18},
        {"id": 52, "restaurant_id": 2, "name": "Kofta de berenjena", "price": 16},
        {"id": 53, "restaurant_id": 3, "name": "Pastel de camote", "price": 11},
    ]

    def ranking(views, last_seen):
        return recommend(
            restaurants=restaurants, dishes=dishes, feedback={"dish-51": "viewed"},
            feedback_signals={"dish-51": {"views": views, "last_seen": last_seen}}, at=AT,
        )

    recent = ranking(8, "2026-11-18T11:30:00-05:00")
    once = ranking(1, "2026-11-18T11:30:00-05:00")
    stale = ranking(8, "2025-11-18T11:30:00-05:00")
    recent_scores = {row["id"]: row["score"] for row in recent["dishes"]}
    assert recent_scores[51] > next(row["score"] for row in once["dishes"] if row["id"] == 51)
    assert recent_scores[52] > next(row["score"] for row in stale["dishes"] if row["id"] == 52)
    assert recent_scores[52] > recent_scores[53]
    assert "Consultaste esta opción anteriormente" in recent["dishes"][0]["reasons"]
    assert recent["recurring"] == []


def test_expired_experience_retains_taste_signal_without_counting_the_same_dish_twice():
    restaurants = [{"id": 1, "name": "La Cala"}, {"id": 2, "name": "Sabores de Oriente"}]
    dishes = [
        {"id": 51, "restaurant_id": 1, "name": "Brocheta de kofta", "price": 18},
        {"id": 52, "restaurant_id": 2, "name": "Kofta de berenjena", "price": 16},
    ]
    result = recommend(
        restaurants=restaurants, dishes=dishes, offers=[], at=AT,
        feedback={"experience-40": "liked", "dish-51": "liked"},
        feedback_signals={"experience-40": {"dish_id": 51}},
    )
    related = next(card for card in result["dishes"] if card["id"] == 52)
    assert "Se relaciona con opciones que te gustaron" in related["reasons"]
    assert result["recurring"] == []


def test_default_selection_includes_novel_options_across_merchants_even_with_repeated_purchases():
    familiar = [{"id": item, "restaurant_id": 1, "name": f"Ceviche {item}", "price": 25}
                for item in range(50, 56)]
    purchases = [{"rid": 1, "state": "Entregado", "paid": True, "day": "2026-11-18",
                  "lines": [{"dish_id": dish["id"], "name": dish["name"]} for dish in familiar]}]
    other = {"id": 60, "restaurant_id": 3, "name": "Chocoteja", "price": 5}
    result = recommend(
        restaurants=RESTAURANTS, dishes=[*familiar, other], orders=purchases,
        feedback={f"dish-{dish['id']}": "liked" for dish in familiar}, at=AT, limit=3,
    )
    assert {row["restaurant_id"] for row in result["dishes"]} == {1, 3}
    assert any(row["id"] == 60 and row["is_new"] for row in result["dishes"])


def test_delivery_preference_respects_coverage_and_season_uses_available_listing_metadata():
    dish = {**DISHES[1], "seasons": ["Verano"]}
    listing = {"id": 40, "dish_id": 12, "rid": 2, "name": dish["name"], "day": "2026-11-18",
               "price": 2500, "available": 2, "channels": ["Delivery", "Recojo"], "pin": [-8.11, -79],
               "radius": 1, "ends": "2026-11-18T20:00:00-05:00", "seasons": ["Primavera"]}
    result = recommend(
        restaurants=RESTAURANTS, dishes=[dish], offers=[listing], at=AT,
        profile={"location_consent": True}, market_profile={"channel": "Delivery"}, location=(-8.2, -79),
    )
    card = result["dishes"][0]
    assert card["channels"] == ["Recojo"]
    assert all("delivery" not in reason for reason in card["reasons"])
    assert card["is_seasonal"] is True
    assert result["context"]["preferred_channel"] == "Delivery"
    result = recommend(
        restaurants=RESTAURANTS, dishes=[dish], offers=[listing], at=AT,
        profile={"location_consent": True}, options={"channel": "Delivery"}, location=(-8.2, -79),
    )
    assert result["items"] == []


def test_structured_recipe_allergens_and_exact_catalog_date_are_authoritative():
    dish = {"id": 61, "restaurant_id": 2, "name": "Salpicón de verduras", "price": 18,
            "recipe": [{"ingredient": "Mayonesa", "quantity": "10", "unit": "g"}],
            "allergens_confirmed": True, "allergens": [], "menu_type": "variable", "menu_date": "2026-11-19",
            "meal_time": "almuerzo"}
    result = recommend(restaurants=RESTAURANTS, dishes=[dish], at=AT)
    assert not result["dishes"]
    result = recommend(restaurants=RESTAURANTS, dishes=[dish], options={"day": "2026-11-19"}, at=AT)
    assert [card["id"] for card in result["dishes"]] == [61]
    result = recommend(restaurants=RESTAURANTS, dishes=[dish], options={"day": "2026-11-19", "time": "20:00"}, at=AT)
    assert not result["dishes"]
    result = recommend(restaurants=RESTAURANTS, dishes=[dish], options={"day": "2026-11-19"},
                       market_profile={"avoid": ["huevo"]}, at=AT)
    assert not result["dishes"]


def test_known_dish_name_at_another_merchant_does_not_count_as_novel_consumption():
    delivered = {"rid": 1, "state": "Entregado", "paid": True, "day": "2026-11-18",
                 "lines": [{"dish_id": 11, "name": "Ceviche de pescado"}]}
    duplicated_name = {**DISHES[0], "id": 20, "restaurant_id": 2}
    result = recommend(restaurants=RESTAURANTS, dishes=[*DISHES, duplicated_name], orders=[delivered], at=AT)
    card = next(row for row in result["dishes"] if row["id"] == 20)
    assert not card["is_new"]
    assert "Ya lo probaste" not in card["reasons"]
    assert any("en otro negocio" in reason for reason in card["reasons"])


def test_search_history_learns_catalog_affinity_and_leaves_variety_in_discovery():
    restaurants = [
        {"id": 1, "name": "Antojos de Cali", "category_id": 8},
        {"id": 2, "name": "Rincón del Valle", "category_id": 8},
        {"id": 3, "name": "Tostaduría"},
    ]
    dishes = [
        {"id": 51, "restaurant_id": 1, "name": "Arepa de choclo", "price": 22},
        {"id": 52, "restaurant_id": 2, "name": "Pandebono", "price": 12},
        {"id": 53, "restaurant_id": 3, "name": "Té de hierbas", "price": 8},
    ]
    search = {"query": "Quiero una ÁREPA de choclo", "count": 8, "last_searched_at": "2026-11-18T11:30:00-05:00"}
    inputs = dict(restaurants=restaurants, categories=[{"id": 8, "name": "Cocina colombiana"}], dishes=dishes, at=AT)
    result = recommend(**inputs, search_history=[search])
    familiar = result["for_you"]["dishes"]
    explore = result["discovery_items"]["dishes"]
    assert [card["id"] for card in familiar] == [51, 52]
    assert [card["id"] for card in explore] == [53]
    assert result["context"]["personalized"] is True
    assert result["history"]["dishes"] == []
    assert all("Coincide con lo que has buscado antes" in card["reasons"] for card in familiar)
    assert result["recurring"] == [{"label": "Cocina colombiana", "count": 8}]

    def score(history):
        return next(row["score"] for row in recommend(**inputs, search_history=history)["dishes"] if row["id"] == 51)

    assert score([search]) > score([{**search, "count": 1}]) > score([])
    assert score([search]) > score([{**search, "last_searched_at": "2025-11-18"}])
    unrelated_query = recommend(**inputs, search_history=[search], options={"q": "mango"})
    assert unrelated_query["dishes"] == []
    assert unrelated_query["for_you"]["dishes"] == []


def test_personal_feed_shows_related_plates_and_restaurants_beside_direct_matches():
    restaurants = [
        {"id": 1, "name": "El Muelle", "category": "Cevichería"},
        {"id": 2, "name": "Las Olas"},
        {"id": 3, "name": "La Terraza"},
    ]
    menu = [
        {"id": 1, "restaurant_id": 1, "name": "Ceviche de pescado", "tags": ["fresco"]},
        {"id": 2, "restaurant_id": 2, "name": "Ceviche de pescado"},
        {"id": 3, "restaurant_id": 2, "name": "Arroz con mariscos"},
        {"id": 4, "restaurant_id": 2, "name": "Jalea mixta"},
        {"id": 5, "restaurant_id": 3, "name": "Limonada", "tags": ["fresco"]},
    ]
    history = [{"query": "ceviche", "count": 8, "last_searched_at": "2026-11-18T11:00:00-05:00"}]
    result = recommend(restaurants=restaurants, dishes=menu, at=AT, search_history=history)
    assert [card["name"] for card in result["for_you"]["dishes"]] == [
        "Ceviche de pescado", "Arroz con mariscos", "Jalea mixta",
    ]
    visible = result["for_you"]["items"][:3]
    assert {"dish", "restaurant"} == {card["kind"] for card in visible}
    assert {"Ceviche de pescado", "Arroz con mariscos"} <= {card["name"] for card in visible}
    assert {"El Muelle", "Las Olas"} == {card["name"] for card in result["for_you"]["restaurants"]}
    assert [card["name"] for card in result["discovery_items"]["dishes"]] == ["Limonada"]


def test_recent_distinct_searches_each_get_visibility_and_related_plates():
    categories = [{"id": 1, "name": "Cocina coreana"}]
    restaurants = [
        {"id": 1, "name": "El Muelle", "category": "Cevichería"},
        {"id": 2, "name": "La Toscana", "category": "Italiana"},
        {"id": 3, "name": "Casa Kim", "category_id": 1},
        {"id": 4, "name": "Seúl en la mesa", "category_id": 1},
        {"id": 5, "name": "Jugos al paso"},
    ]
    menu = [
        {"id": 1, "restaurant_id": 1, "name": "Ceviche"},
        {"id": 2, "restaurant_id": 1, "name": "Ceviche de pescado"},
        {"id": 3, "restaurant_id": 1, "name": "Arroz con mariscos"},
        {"id": 4, "restaurant_id": 2, "name": "Pizza Pepperoni"},
        {"id": 5, "restaurant_id": 2, "name": "Risotto de hongos"},
        {"id": 6, "restaurant_id": 3, "name": "Tteokbokki", "category": "Fondo"},
        {"id": 7, "restaurant_id": 4, "name": "Japchae", "category": "Plato principal"},
        {"id": 8, "restaurant_id": 5, "name": "Limonada"},
    ]
    history = [
        {"query": "ceviche", "count": 30, "last_searched_at": "2026-11-18T09:00:00-05:00"},
        {"query": "pizza pepperoni", "count": 1, "last_searched_at": "2026-11-18T11:20:00-05:00"},
        {"query": "tteokbokki", "count": 1, "last_searched_at": "2026-11-18T11:45:00-05:00"},
    ]
    result = recommend(restaurants=restaurants, categories=categories, dishes=menu, at=AT, search_history=history)
    names = [card["name"] for card in result["for_you"]["dishes"]]
    assert names[:3] == ["Tteokbokki", "Pizza Pepperoni", "Ceviche"]
    assert names[3:6] == ["Japchae", "Risotto de hongos", "Arroz con mariscos"]
    assert any(card["name"] == "Seúl en la mesa" for card in result["for_you"]["restaurants"])
    assert [card["name"] for card in result["discovery_items"]["dishes"]] == ["Limonada"]


def test_common_cuisine_terms_connect_to_available_dishes_without_rewriting_exact_search():
    restaurants = [{"id": 1, "name": "La Toscana"}, {"id": 2, "name": "Jugos al paso"}]
    menu = [
        {"id": 1, "restaurant_id": 1, "name": "Lasaña de hongos"},
        {"id": 2, "restaurant_id": 2, "name": "Limonada"},
        {"id": 3, "restaurant_id": 1, "name": "Pizza napolitana"},
    ]
    inputs = dict(restaurants=restaurants, dishes=menu, at=AT)
    for term in ("fetuccini", "fettuccine"):
        result = recommend(**inputs, search_history=[{"query": term, "count": 1, "last_searched_at": "2026-11-18"}])
        assert [card["id"] for card in result["for_you"]["dishes"]] == [1, 3]
        assert [card["id"] for card in result["for_you"]["restaurants"]] == [1]
        assert recommend(**inputs, options={"q": term})["dishes"] == []


def test_separate_searches_in_the_same_cuisine_can_keep_distinct_matches_visible():
    restaurants = [{"id": 1, "name": "La Toscana", "category": "Italiana"}]
    menu = [{"id": 1, "restaurant_id": 1, "name": "Pizza Napolitana"},
            {"id": 2, "restaurant_id": 1, "name": "Lasagna"},
            {"id": 3, "restaurant_id": 1, "name": "Ravioli de ricota"}]
    history = [{"query": "pizza napolitana", "count": 30, "last_searched_at": "2026-11-18T09:00:00-05:00"},
               {"query": "lasagna", "count": 1, "last_searched_at": "2026-11-18T11:00:00-05:00"}]
    result = recommend(restaurants=restaurants, dishes=menu, at=AT, search_history=history)
    assert [card["id"] for card in result["for_you"]["dishes"]][:2] == [2, 1]


def test_related_recipes_can_connect_unclassified_catalogue_entries():
    restaurants = [{"id": 1, "name": "Sabores de autor"}, {"id": 2, "name": "Mesa abierta"}]
    menu = [
        {"id": 1, "restaurant_id": 1, "name": "Galette de la casa", "ingredients": ["alforfón", "setas", "sal"]},
        {"id": 2, "restaurant_id": 2, "name": "Crepe de bosque", "ingredients": ["alforfón", "setas", "calabaza"]},
        {"id": 3, "restaurant_id": 2, "name": "Caldo de verduras", "ingredients": ["setas", "sal", "agua"]},
    ]
    result = recommend(restaurants=restaurants, dishes=menu, at=AT,
                       search_history=[{"query": "galette de la casa", "count": 1, "last_searched_at": "2026-11-18"}])
    dishes = result["for_you"]["dishes"]
    assert [card["id"] for card in dishes] == [1, 2]
    assert "Comparte ingredientes con lo que has buscado" in dishes[1]["reasons"]
    assert {card["name"] for card in result["for_you"]["restaurants"]} == {"Sabores de autor", "Mesa abierta"}


def test_discovery_excludes_consumed_dishes_and_does_not_repeat_listings():
    orders = [{"rid": 1, "state": "Entregado", "paid": True, "day": "2026-11-18",
               "lines": [{"dish_id": 11, "name": "Ceviche de pescado"}]}]
    menu = [*DISHES, {**DISHES[0], "id": 21, "restaurant_id": 2}]
    offers = [{"id": 41, "dish_id": 12, "name": "Arroz con mariscos en oferta", "rid": 2,
               "day": "2026-11-18", "price": 2000, "available": 3, "channels": ["Local"]}]
    result = recommend(restaurants=RESTAURANTS, dishes=menu, offers=offers, orders=orders, at=AT)
    assert result["for_you"]["dishes"][0]["id"] == 11
    assert all(card["is_new"] and card["dish_id"] not in {11, 21}
               for card in result["discovery_items"]["items"])
    for group in ("items", "dishes", "restaurants", "experiences"):
        familiar = result["for_you"][group]
        explore = result["discovery_items"][group]
        assert not ({card["key"] for card in familiar} & {card["key"] for card in explore})
        assert not ({card["dish_id"] for card in familiar if card["dish_id"] is not None}
                    & {card["dish_id"] for card in explore if card["dish_id"] is not None})

    only_one_novel = recommend(
        restaurants=RESTAURANTS, dishes=DISHES[:2], orders=orders, at=AT,
        search_history=[{"query": "Arroz con mariscos", "count": 20, "last_searched_at": "2026-11-18"}],
    )
    assert [card["id"] for card in only_one_novel["for_you"]["dishes"]] == [11, 12]
    assert only_one_novel["discovery_items"]["dishes"] == []


def test_a_search_for_excluding_an_ingredient_does_not_learn_it_as_a_taste():
    dish = {"id": 31, "restaurant_id": 1, "name": "Sándwich de queso", "price": 15}
    result = recommend(
        restaurants=RESTAURANTS, dishes=[dish], at=AT,
        search_history=[{"query": "algo sin queso", "count": 20, "last_searched_at": "2026-11-18"}],
    )
    assert "Coincide con lo que has buscado antes" not in result["dishes"][0]["reasons"]
    assert not result["context"]["personalized"]


def test_personal_feed_accepts_preferences_and_keeps_discovery_without_history():
    result = recommend(
        restaurants=RESTAURANTS, dishes=DISHES, at=AT,
        profile={"preferences": ["mariscos"]}, favorites=[2],
        feedback={"dish-12": "liked", "dish-13": "viewed"},
        visits=[{"restaurant_id": 1, "date": "2026-11-17", "status": "asistida"}],
    )
    assert not result["context"]["has_recommendation_history"]
    assert result["for_you"]["items"]
    assert all(card["personalization_basis"] == "declared_preferences"
               for card in result["for_you"]["items"])
    assert result["discovery_items"]["items"]
    assert all(card["is_new"] for card in result["discovery_items"]["items"])


def test_personal_feed_ranking_and_reasons_use_only_matching_history():
    order = {"rid": 1, "state": "Entregado", "paid": True, "day": "2026-11-17",
             "lines": [{"dish_id": 11, "name": "Ceviche de pescado"}]}
    history = [{"query": "arroz con mariscos", "count": 3, "last_searched_at": "2026-11-18"}]
    dessert = {"id": 21, "restaurant_id": 3, "name": "Arroz con leche", "price": 10}
    inputs = dict(restaurants=RESTAURANTS, dishes=[*DISHES, dessert], at=AT, orders=[order], search_history=history)
    baseline = recommend(**inputs)
    ranking = recommend(
        **inputs, profile={"preferences": ["postres"]}, favorites=[3],
        feedback={"dish-13": "liked", "dish-21": "viewed"},
        visits=[{"restaurant_id": 3, "date": "2026-11-17", "status": "asistida"}],
    )
    personal = ranking["for_you"]["dishes"]
    assert ranking["context"]["has_recommendation_history"]
    assert [card["id"] for card in personal] == [11, 12]
    assert personal == baseline["for_you"]["dishes"]
    assert all(card["id"] in {13, 21} for card in ranking["discovery_items"]["dishes"])
    assert "Está en tus compras confirmadas" in personal[0]["reasons"]
    assert "Coincide con lo que has buscado antes" in personal[1]["reasons"]


def test_discovery_nudges_cannot_reshuffle_which_history_matches_are_in_the_personal_feed():
    menu = [
        {"id": 61, "restaurant_id": 1, "name": "Ramen de verduras", "category": "Japonesa"},
        {"id": 62, "restaurant_id": 2, "name": "Tempura", "category": "Japonesa"},
        {"id": 63, "restaurant_id": 3, "name": "Maki", "category": "Japonesa"},
        {"id": 64, "restaurant_id": 3, "name": "Té de hierbas", "category": "Bebidas"},
    ]
    inputs = dict(restaurants=[{"id": rid, "name": f"Negocio {rid}"} for rid in range(1, 4)], dishes=menu, at=AT,
                  search_history=[{"query": "ramen de verduras", "count": 3, "last_searched_at": "2026-11-18"}])
    baseline = recommend(**inputs)
    with_feedback = recommend(**inputs, feedback={"dish-63": "liked"}, profile={"preferences": ["maki"]})
    assert baseline["for_you"]["dishes"] == with_feedback["for_you"]["dishes"]
    assert {card["id"] for card in baseline["for_you"]["dishes"]} == {61, 62, 63}
    assert {card["id"] for card in baseline["discovery_items"]["dishes"]} == {64}


def test_sharing_only_a_common_pantry_ingredient_does_not_count_as_a_purchase_match():
    menu = [
        {"id": 61, "restaurant_id": 1, "name": "Ramen de verduras", "ingredients": ["sal", "aceite", "fideos"]},
        {"id": 62, "restaurant_id": 2, "name": "Quinua", "ingredients": ["sal", "agua", "aceite"]},
    ]
    order = {"rid": 1, "state": "Entregado", "paid": True, "day": "2026-11-17",
             "lines": [{"dish_id": 61, "name": "Ramen de verduras"}]}
    result = recommend(restaurants=[{"id": rid, "name": f"Negocio {rid}"} for rid in range(1, 3)],
                       dishes=menu, orders=[order], at=AT)
    assert [card["id"] for card in result["for_you"]["dishes"]] == [61]
    assert [card["id"] for card in result["discovery_items"]["dishes"]] == [62]


def test_explicit_search_ignores_learned_nudges_and_keeps_query_matches():
    order = {"rid": 1, "state": "Entregado", "paid": True, "day": "2026-11-17", "total": 3600,
             "lines": [{"dish_id": 11, "name": "Ceviche de pescado"}]}
    result = recommend(
        restaurants=RESTAURANTS, dishes=DISHES, at=AT, orders=[order],
        profile={"weekly_budget": 20, "preferences": ["mariscos"]},
        market_profile={"budget": 15, "channel": "Delivery"}, feedback={"dish-11": "dismissed"}, favorites=[2],
        options={"search_mode": True, "q": "ceviche", "budget": 40},
    )
    assert result["context"]["budget"] == 40
    assert [card["id"] for card in result["dishes"]] == [11]
    assert result["dishes"][0]["reasons"] == ["Coincide con tu búsqueda", "Dentro del presupuesto indicado"]
    assert result["restaurants"] == []

    business_search = recommend(restaurants=RESTAURANTS, dishes=DISHES, at=AT,
                                options={"search_mode": True, "q": "Costa"})
    assert [card["id"] for card in business_search["restaurants"]] == [1]
    assert business_search["dishes"] == []


def test_explicit_occasion_filters_platos_and_restaurants_with_available_matches():
    menu = [
        {**DISHES[0], "context_tags": ["Para compartir"]},
        {**DISHES[1], "context_tags": ["Rápido"]},
        {**DISHES[2], "occasion": "Comida en familia"},
    ]
    result = recommend(restaurants=RESTAURANTS, dishes=menu, at=AT,
                       options={"search_mode": True, "moment": "familia"})
    assert {card["id"] for card in result["dishes"]} == {11, 13}
    assert {card["id"] for card in result["restaurants"]} == {1, 3}
    assert all(card["reasons"] == ["Coincide con la ocasión indicada"] for card in result["items"])


def test_explicit_search_preserves_exclusion_phrases():
    menu = [
        {"id": 41, "restaurant_id": 1, "name": "Pizza sin gluten con queso"},
        {"id": 42, "restaurant_id": 2, "name": "Pizza sin queso"},
    ]
    result = recommend(restaurants=RESTAURANTS, dishes=menu, at=AT,
                       options={"search_mode": True, "q": "pizza sin queso"})
    assert [card["id"] for card in result["dishes"]] == [42]
