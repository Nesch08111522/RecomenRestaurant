from copy import deepcopy

from app import create_app
import context_processors
import views.main as main_routes


def _client(monkeypatch, count=1):
    rows = [
        {
            "id": index,
            "name": f"Restaurante {index}",
            "promo": "Menú especial",
            "district": "Miraflores",
            "image": "/static/images/auth/ceviche.webp",
            "rating": 4.7,
            "avg_price": 32.5,
            "lat": None,
            "lng": None,
            "tags": ["criollo"],
            "justifications": [],
        }
        for index in range(1, count + 1)
    ]
    monkeypatch.setattr(context_processors.CategoryModel, "all", lambda: [])
    monkeypatch.setattr(context_processors, "site_settings", lambda: deepcopy(context_processors.DEFAULTS))
    monkeypatch.setattr(main_routes.RestaurantModel, "get_approved", lambda: deepcopy(rows))
    monkeypatch.setattr(main_routes, "filter_restaurants", lambda restaurants, filters: restaurants)
    app = create_app({"TESTING": True, "SECRET_KEY": "offers-ui-test-secret"})
    return app.test_client()


def test_offers_page_loads_its_premium_stylesheet(monkeypatch):
    response = _client(monkeypatch).get("/ofertas")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "/static/css/offers-premium.css" in html
    assert 'class="sr-offers-hero"' in html
    assert 'class="restaurant-card rc"' in html


def test_offers_filters_and_pagination_keep_the_current_query(monkeypatch):
    response = _client(monkeypatch, count=7).get(
        "/ofertas?q=pollo&district=Miraflores&max_price=40"
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'value="pollo"' in html
    assert 'value="40"' in html
    assert 'href="/ofertas?page=2&amp;q=pollo&amp;district=Miraflores&amp;max_price=40"' in html
