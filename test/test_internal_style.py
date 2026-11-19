"""Isolated presentation harness: real Jinja/assets, simulated data, no DB requests."""
from datetime import date
from pathlib import Path
from threading import Thread
from uuid import uuid4
import json
import re

import pytest
from flask import Flask, render_template, session
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ('admin.users', '/admin/users', 'admin/users.html', 'admin', {'users': [{'id': 2, 'username': 'qa-user', 'role': 'user', 'status': 'ACTIVE', 'profile': {'name': 'QA User', 'email': 'qa@example.test', 'preferences': []}}]}),
    ('commercial_radar.dashboard', '/admin/radar-comercial', 'admin/commercial_radar.html', 'admin', {'center': [-8.1, -79.0], 'states': [], 'prospects': [], 'companies': []}),
    ('companies.admin_companies', '/admin/empresas', 'admin/companies.html', 'admin', {'demo_owners': [], 'companies': [{'id': 1, 'name': 'Empresa QA', 'metadata': {'subscription': {'plan': 'Basic'}}}], 'plans': ['Basic'], 'capabilities': []}),
    ('salon.desk', '/salon/1', 'salon/desk.html', 'business_owner', {'restaurant': {'id': 1, 'name': 'Negocio QA'}, 'seats': {}, 'pending': [], 'queue': [], 'rows': [], 'service_enabled': True}),
    ('intelligence.dashboard', '/inteligencia', 'intelligence.html', 'admin', {'start': date(2026, 11, 1), 'end': date(2026, 11, 19), 'shops': [], 'data': {'income': 0, 'known_costs': 0, 'margin': None, 'income_change': None, 'orders': 0, 'cost_coverage': None, 'forecast': [], 'forecast_method': 'Sin muestra QA', 'critical_ingredients': [], 'waste': [], 'customers': 0, 'new_customers': 0, 'frequent_customers': 0, 'inactive_customers': 0, 'website_views': 0, 'published_offers': 0, 'service': {'sessions': 0, 'average_minutes': None, 'rotation_per_table_day': None, 'median_wait_minutes': None}, 'daily': [], 'hours': [], 'top_products': [], 'least_products': [], 'missing_metrics': []}}),
    ('companies.owner_subscriptions', '/owner/suscripciones', 'owner/subscriptions.html', 'business_owner', {'companies': []}),
    ('business_access.access', '/owner/acceso/1', 'owner/business_access.html', 'business_owner', {'business': {'id': 1, 'name': 'Negocio QA'}, 'roles': ['manager'], 'members': [], 'verification': None}),
    ('flow.desk', '/salon/1/cola', 'flow/desk.html', 'business_owner', {'restaurant': {'id': 1, 'name': 'Negocio QA'}, 'seats': {'by_floor': {'Principal': {'occupied': 2, 'seats': 8, 'busy': 1, 'tables': 2}}, 'by_zone': {}}, 'settings': {'accepting': True, 'max_capacity': 8, 'note': ''}, 'queue': [], 'pattern': [], 'history': []}),
    ('sites.editor', '/owner/sites', 'sites/editor.html', 'business_owner', {'restaurant': {'id': 1, 'name': 'Negocio QA'}, 'restaurants': [{'id': 1, 'name': 'Negocio QA'}], 'site': {}}),
    ('catalog.dashboard', '/owner/catalog', 'catalog/dashboard.html', 'business_owner', {'restaurant': None, 'restaurants': []}),
    ('copilot.page', '/copilot', 'copilot.html', 'user', {'shops': []}),
    ('auth.account_security', '/auth/seguridad', 'auth/security.html', 'user', {'result': {}, 'recovery': False}),
    ('auth.favorites', '/auth/favorites', 'favorites.html', 'user', {'restaurants': [], 'total': 0}),
    ('home_kitchen.index', '/home/', 'home_kitchen.html', 'user', {'pantry': [], 'recipes': [], 'plans': [], 'shopping': [], 'preparations': [], 'today': '2026-11-19', 'week': '2026-11-16', 'meals': ['Almuerzo'], 'request_key': 'qa', 'recipe_map': {}}),
    ('comunicacion.inbox', '/mensajes', 'communication/inbox.html', 'user', {'threads': [], 'businesses': []}),
    ('loyalty.reservations', '/mis-reservas', 'loyalty/wallet.html', 'user', {'reservations_only': True, 'reservations': []}),
    ('market.orders', '/mercado/pedidos', 'market/orders.html', 'user', {'spent': 0, 'points': 0, 'repeat': None, 'due': [], 'orders': [], 'cases': []}),
    ('discovery.dashboard', '/admin/discovery', 'discovery/dashboard.html', 'admin', {'candidates': [], 'sources': [], 'runs': [], 'claims': []}),
]


def harness():
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = Flask(__name__, template_folder=str(ROOT / 'templates'), static_folder=str(ROOT / 'static'))
    app.secret_key = uuid4().hex
    # Register endpoint names only; production before-request hooks never execute.
    from app import create_app
    names = {rule.endpoint for rule in create_app({'TESTING': True, 'SECRET_KEY': uuid4().hex}).url_map.iter_rules()}
    for endpoint in names - {'static'}:
        app.add_url_rule('/unused/' + endpoint, endpoint, lambda: '', methods=['GET', 'POST'])
    app.jinja_env.globals.update(APP_NAME='SmartResto QA', MONEDA='S/', website={'brand': 'SmartResto'}, csrf_token=lambda: 'qa-token', company_nav_allowed=lambda endpoint: True)
    app.jinja_env.filters['soles'] = lambda value: f'S/ {value / 100:.2f}'
    for endpoint, path, template, role, data in CASES:
        def render(template=template, role=role, data=data):
            session['user'] = {'id': 1, 'role': role, 'username': 'QA', 'profile': {'name': 'QA'}}
            return render_template(template, **data)
        app.view_functions[endpoint] = render
        app.add_url_rule(path, endpoint, render)
    return app


def test_jinja_and_scope_contract():
    app = harness()
    for path in (ROOT / 'templates').rglob('*.html'):
        app.jinja_env.parse(path.read_text(encoding='utf-8-sig'))
    with app.test_client() as client:
        for endpoint, path, template, role, data in CASES:
            response = client.get(path)
            assert response.status_code == 200, endpoint
            assert b'sr-workspace' in response.data and b'css/internal-workspace.css' in response.data
    css = (ROOT / 'static/css/internal-workspace.css').read_text(encoding='utf-8')
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d', css)
    assert 'background-image: none' in css
    assert not re.search(r'\.sr-workspace\s+\*', css)
    # Authenticated public requests must still use the public shell.
    for endpoint in ('main.index', 'market.browse', 'market.offer_detail', 'sites.public_page', 'flow.public', 'salon.menu', 'auth.login', 'auth.register', 'companies.activate', 'discovery.claim_page'):
        with app.test_request_context('/'):
            from flask import request
            from werkzeug.routing import Rule
            request.url_rule = Rule('/', endpoint=endpoint)
            session['user'] = {'id': 1, 'role': 'admin'}
            html = render_template('base.html')
            assert 'css/internal-workspace.css' not in html, endpoint


def test_edge_internal_matrix():
    app = harness()
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    evidence = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            context = browser.new_context()
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else route.abort())
            page = context.new_page()
            for endpoint, path, template, role, data in CASES:
                for width in (360, 768, 1280):
                    page.set_viewport_size({'width': width, 'height': 900})
                    response = page.goto(f'http://127.0.0.1:{server.server_port}{path}', wait_until='networkidle')
                    assert response.status == 200
                    for theme in ('dark', 'light'):
                        page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
                        page.wait_for_timeout(350)
                        measure = page.evaluate('''() => ({width: document.documentElement.scrollWidth, header: document.querySelector('.sr-header').getBoundingClientRect().height, sidebar: document.querySelector('.sr-sidebar').getBoundingClientRect().width, title: document.querySelector('h1') ? getComputedStyle(document.querySelector('h1')).fontSize : null})''')
                        if measure['width'] > width + 1:
                            print(page.evaluate("() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).map(e => ({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right,text:e.textContent.slice(0,100)})).slice(0,10)"))
                        assert measure['width'] <= width + 1, (endpoint, width, theme, measure)
                        assert measure['header'] == 54
                        if width == 1280:
                            assert measure['sidebar'] == 232
                        if measure['title']:
                            if measure['title'] != '22px':
                                print(page.evaluate("() => ({body:document.body.className,css:[...document.styleSheets].map(s=>({href:s.href,rules:(()=>{try{return [...s.cssRules].filter(r=>r.selectorText && document.querySelector('h1').matches(r.selectorText)).map(r=>r.cssText)}catch{return []}})()}))})"))
                            assert measure['title'] == '22px', (endpoint, width, measure)
                        evidence.append({'endpoint': endpoint, 'path': path, 'template': template, 'role': role, 'viewport': width, 'theme': theme, **measure})
                    if width < 1100:
                        page.locator('.sr-menu-button').click()
                        assert page.locator('.sr-sidebar').is_visible()
                        assert page.locator('.sr-menu-button').get_attribute('aria-expanded') == 'true'
                        page.keyboard.press('Escape')
                        assert not page.locator('.sr-sidebar').is_visible()
                if endpoint == 'admin.users':
                    page.locator('[data-action=edit]').click()
                    assert page.locator('#edit-modal').is_visible()
                    page.locator('#edit-cancel').click()
                    assert not page.locator('#edit-modal').is_visible()
                if endpoint == 'discovery.dashboard':
                    page.evaluate("document.querySelector('#radarDecision').showModal()")
                    assert page.locator('#radarDecision').is_visible()
                    page.keyboard.press('Escape')
                if endpoint == 'flow.desk':
                    assert page.locator('[role=region][tabindex="0"]').count() >= 2
                    assert page.locator('table').evaluate_all("tables => tables.every(t => getComputedStyle(t.parentElement).overflowX === 'auto')")
            browser.close()
        print('INTERNAL_MATRIX=' + json.dumps(evidence))
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
