"""Real local browser against a fixture-isolated DB and an owned ephemeral server."""
from threading import Thread
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app import create_app
from database.connection import test_schema as qa_schema
from models.home_kitchen import save_pantry, save_recipe
from logic.market import now
from service_fixtures import make_user


def test_home_responsive_light_dark(service_db):
    assert qa_schema(), 'Browser server requires the QA schema'
    user = make_user(uuid4().hex)
    save_pantry(user['id'], dict(name='arroz', quantity=300, unit='g', expires=now().date().isoformat()))
    save_recipe(user['id'], dict(name='Receta declarada', ingredients=[dict(name='arroz', quantity=100, unit='g')],
                                steps=['Paso declarado de prueba'], confirmed=True))
    app = create_app(dict(TESTING=True, SECRET_KEY=uuid4().hex))
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = user['id']
    cookie = client.get_cookie('session')
    # Port zero asks Windows for a free port, never borrowing the user's :5000.
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            context = browser.new_context()
            context.add_cookies([dict(name='session', value=cookie.value, domain='127.0.0.1', path='/')])
            # Block remote fonts/scripts and all external providers during verification.
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith('http://127.0.0.1:') else route.abort())
            page = context.new_page()
            for width in (360, 768, 1280):
                page.set_viewport_size(dict(width=width, height=900))
                response = page.goto(f'http://127.0.0.1:{server.server_port}/home/', wait_until='domcontentloaded')
                assert response.status == 200
                assert page.locator('h1').inner_text() == 'SmartResto Home'
                assert page.locator('#sr-navigation').count() == 1
                for theme in ('dark', 'light'):
                    page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
                    page.wait_for_timeout(200)
                    measurements = page.evaluate('''() => ({viewport: innerWidth, width: document.documentElement.scrollWidth,
                        theme: document.documentElement.dataset.theme, main: document.querySelector('#main-content').getBoundingClientRect().width})''')
                    assert measurements['theme'] == theme
                    assert measurements['main'] > 0
                    if measurements['width'] > width + 1:
                        print(page.evaluate("() => [...document.querySelectorAll('body *')].map(e => ({tag:e.tagName, cls:e.className, right:e.getBoundingClientRect().right, width:e.getBoundingClientRect().width})).filter(e => e.right > innerWidth + 1).slice(0,20)"))
                    assert measurements['width'] <= width + 1, measurements
                    print(f"Home browser {width}px {theme}: width={measurements['width']}, viewport={width}")
            # Exercise a real CSRF-protected form, no bypass route or seeded session endpoint.
            form = page.locator('#despensa > form')
            form.locator('[name=name]').fill('avena')
            form.locator('[name=quantity]').fill('100')
            form.locator('[name=expires]').fill(now().date().isoformat())
            form.locator('button').click()
            page.wait_for_url('**/home/')
            assert 'avena' in page.locator('#despensa').inner_text()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
