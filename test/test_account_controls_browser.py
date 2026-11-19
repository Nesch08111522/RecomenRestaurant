"""Offline browser shell tests. No application import, server, environment or DB."""
import ast
from pathlib import Path

import pytest
from flask import Flask, session
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def offline_app():
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    app.secret_key = 'offline-controls'
    # Register paths extracted from the real route declarations, not guessed URLs.
    for module, prefix, names in [('auth', '', ['profile', 'account_security']),
                                  ('admin', '/admin', ['dashboard']),
                                  ('owner', '/owner', ['dashboard']),
                                  ('market', '/market', ['orders'])]:
        tree = ast.parse((ROOT / 'views' / (module + '.py')).read_text(encoding='utf8'))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in names:
                decorator = next(d for d in node.decorator_list if isinstance(d, ast.Call)
                                 and isinstance(d.func, ast.Attribute) and d.func.attr in ['route', 'get'])
                app.add_url_rule(prefix + ast.literal_eval(decorator.args[0]), module + '.' + node.name, lambda: '')
    app.add_url_rule('/', 'main.index', lambda: '')
    from flask import url_for
    real = {rule.endpoint for rule in app.url_map.iter_rules()}
    app.jinja_env.globals.update(csrf_token=lambda: 'test', APP_NAME='SmartResto',
        website={'brand': 'SmartResto', 'social': {}},
        url_for=lambda name, **kw: url_for(name, **kw) if name in real else '/fixture/' + name)
    app.jinja_env.filters['soles'] = str
    return app


@pytest.mark.parametrize('role', ['user', 'admin', 'business_owner'])
@pytest.mark.parametrize('width', [320, 390, 768, 1100, 1920])
def test_native_navigation_and_controls(role, width):
    app = offline_app()
    with app.test_request_context('/'):
        session['user'] = {'id': 1, 'role': role, 'username': 'Test'}
        html = app.jinja_env.from_string('{% extends "base.html" %}{% block content %}Offline{% endblock %}').render()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': width, 'height': 900}, has_touch=True)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def serve(route):
            url = route.request.url
            if route.request.resource_type == 'document':
                with app.test_request_context(url.replace('http://offline.test', '')):
                    session['user'] = {'id': 1, 'role': role, 'username': 'Test'}
                    rendered = app.jinja_env.from_string('{% extends "base.html" %}{% block content %}Offline{% endblock %}').render()
                route.fulfill(body=rendered, content_type='text/html')
            elif '/static/css/' in url or url.endswith('/static/js/shell.js') or url.endswith('/static/js/private-shell.js') or url.endswith('/static/js/copilot-wake.js'):
                file = ROOT / url.split('offline.test/')[1].split('?')[0]
                route.fulfill(body=file.read_bytes(), content_type='text/css' if file.suffix == '.css' else 'application/javascript')
            else:
                route.abort()

        page.route('**/*', serve)
        try:
            expected = ['/profile', '/seguridad', {'user': '/market/pedidos', 'admin': '/admin/dashboard', 'business_owner': '/owner/dashboard'}[role]]
            for index, path in enumerate(expected):
                page.goto('http://offline.test/', wait_until='load')
                page.locator('[data-account-toggle]').tap()
                anchor = page.locator('#private-account-menu a').nth(index)
                assert anchor.get_attribute('href') == path
                assert anchor.evaluate('el => { const r=el.getBoundingClientRect(); return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)); }')
                anchor.tap()
                page.wait_for_url('http://offline.test' + path)
            assert page.locator('#private-account-menu').get_attribute('hidden') is not None
            page.locator('[data-account-toggle]').click()
            assert page.locator('#private-account-menu a').nth(2).get_attribute('href') == '/'
            page.keyboard.press('Escape')
            page.locator('#sr-controls-open').tap()
            assert page.locator('#sr-controls-drawer').evaluate('el => el.open')
            assert page.locator('#sr-controls-open').get_attribute('aria-expanded') == 'true'
            assert page.locator('#sr-controls-close').evaluate('el => el === document.activeElement')
            page.keyboard.press('Shift+Tab')
            assert page.locator('#sr-controls-drawer').evaluate('el => el.contains(document.activeElement)')
            page.keyboard.press('Escape')
            assert not page.locator('#sr-controls-drawer').evaluate('el => el.open')
            assert page.locator('#sr-controls-open').evaluate('el => el === document.activeElement')
            page.locator('#sr-controls-open').tap()
            page.mouse.click(3, 450)
            assert not page.locator('#sr-controls-drawer').evaluate('el => el.open')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
        finally:
            browser.close()
