from copy import deepcopy

import context_processors
from app import create_app
from models.site_settings import DEFAULTS


def _client(monkeypatch):
    monkeypatch.setattr(context_processors.CategoryModel, "all", lambda: [])
    monkeypatch.setattr(context_processors, "site_settings", lambda: deepcopy(DEFAULTS))
    app = create_app({"TESTING": True, "SECRET_KEY": "auth-performance-test-secret"})
    return app.test_client()


def test_auth_page_skips_unneeded_global_assets(monkeypatch):
    response = _client(monkeypatch).get("/auth/login")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "sr-unified-footer" not in html
    assert "sr-mobile-nav" not in html
    for unused_asset in (
        "fonts.googleapis.com/icon?family=Material+Icons",
        "cdnjs.cloudflare.com/ajax/libs/font-awesome",
        "unpkg.com/leaflet",
        "cdn.jsdelivr.net/npm/chart.js",
        "/static/vendor/chartjs/",
        "/static/js/app.js",
        "/static/js/map.js",
        "/static/js/search.js",
        "/static/js/admin.js",
        "/static/js/ai-assistant.js",
    ):
        assert unused_asset not in html


def test_login_uses_an_eager_poster_and_defers_the_three_scene(monkeypatch):
    html = _client(monkeypatch).get("/auth/login").get_data(as_text=True)

    assert 'data-scene-fallback' in html
    assert 'loading="eager"' in html
    assert 'fetchpriority="high"' in html
    assert "/static/js/auth/food-scene-loader.js" in html
    assert 'data-scene-module="/static/js/auth/food-scene.js"' in html
    assert '<script type="module" src="/static/js/auth/food-scene.js"' not in html


def test_auth_styles_include_the_food_scene_poster_and_caption_layout(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/static/css/auth.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)
    for selector in (
        ".ax-food-host",
        ".ax-food-intro",
        ".ax-food-canvas",
        ".ax-food-caption",
        '.ax-food-host[data-scene-state="ready"]',
    ):
        assert selector in css
