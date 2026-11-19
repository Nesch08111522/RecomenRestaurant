from threading import Thread

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

import context_processors
from app import create_app
from models.site_settings import DEFAULTS


@pytest.fixture
def auth_origin(monkeypatch):
    monkeypatch.setattr(context_processors.CategoryModel, "all", lambda: [])
    monkeypatch.setattr(context_processors, "site_settings", lambda: dict(DEFAULTS))
    app = create_app({"TESTING": True, "SECRET_KEY": "auth-scene-lazy-test-secret"})
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_reduced_motion_login_does_not_download_three_bundle(auth_origin):
    scene_requests = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.route(
            "**/*",
            lambda route: route.continue_()
            if route.request.url.startswith(auth_origin)
            else route.abort(),
        )
        page.on(
            "request",
            lambda request: scene_requests.append(request.url)
            if "food-scene.js" in request.url
            else None,
        )
        response = page.goto(auth_origin + "/auth/login", wait_until="load", timeout=15000)
        assert response and response.status == 200
        page.wait_for_timeout(200)

        assert scene_requests == []
        assert page.locator('[data-pane="login"] .ax-card').is_visible()
        context.close()
        browser.close()


def test_inactive_register_panel_does_not_force_login_scroll(auth_origin):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        for width, height in ((1440, 900), (390, 844)):
            context = browser.new_context(
                viewport={"width": width, "height": height},
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.route(
                "**/*",
                lambda route: route.continue_()
                if route.request.url.startswith(auth_origin)
                else route.abort(),
            )
            response = page.goto(auth_origin + "/auth/login", wait_until="load", timeout=15000)
            assert response and response.status == 200
            page.locator('[data-pane="login"] .ax-card').wait_for(state="visible")
            geometry = page.evaluate(
                "({width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight})"
            )

            assert geometry["scrollWidth"] <= geometry["width"] + 2
            assert geometry["scrollHeight"] <= geometry["height"] + 2
            context.close()
        browser.close()
