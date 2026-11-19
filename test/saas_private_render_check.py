"""Offline template contract checks. Run directly; never imports the application."""
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import re
import unittest
from flask import Flask, render_template, session

ROOT = Path(__file__).resolve().parents[1]
app = Flask(__name__, template_folder=str(ROOT / 'templates'), static_folder=str(ROOT / 'static'))
app.secret_key = 'offline-template-fixture-only'
app.jinja_env.globals.update(csrf_token=lambda: 'mock-csrf',
    url_for=lambda endpoint, **kw: '/static/' + kw['filename'] if endpoint == 'static' else '/mock/' + endpoint,
    APP_NAME='SmartResto', MONEDA='S/', website={'brand': 'SmartResto'},
    platform_context={'authenticated': True, 'scope': 'business'},
    current_year=2026)
app.jinja_env.filters['soles'] = lambda value: f'S/ {value or 0}'

CASES = {
    'owner/dashboard.html': 'owner.dashboard',
    'admin/restaurants.html': 'admin.restaurants',
    'intelligence.html': 'intelligence.dashboard',
    'copilot.html': 'copilot.page',
    'catalog/dashboard.html': 'catalog.dashboard',
    'salon/manage.html': 'salon.manage',
    'sites/editor.html': 'sites.editor',
    'discovery/owner.html': 'discovery.owner_space',
    'ecosystem/groups.html': 'ecosystem.groups',
    'ecosystem/group.html': 'ecosystem.group',
    'ecosystem/rewards.html': 'ecosystem.rewards',
    'ecosystem/scan.html': 'ecosystem.scan',
    'communication/inbox.html': 'comunicacion.inbox',
    'communication/notifications.html': 'comunicacion.notifications',
    'communication/cases.html': 'comunicacion.cases',
    'auth/profile.html': 'auth.profile',
    'auth/security.html': 'auth.account_security',
}

def render(name, endpoint, role='business_owner', authenticated=True):
    with app.test_request_context('/') as context:
        context.request.url_rule = SimpleNamespace(endpoint=endpoint)
        user = {'id': 1, 'role': role, 'username': 'fixture', 'profile': {
            'name': 'Fixture', 'email': '', 'preferences': [], 'restrictions': []}}
        if authenticated:
            session['user'] = user
        return render_template(name, user=user, shops=0 if name == 'ecosystem/rewards.html' else [], restaurants=[], restaurant={'id': 1, 'name': 'Fixture', 'description': ''} if name in ['salon/manage.html', 'sites/editor.html'] else None,
            business=None, groups=[], rows=[], balances=[], purchases=0, dishes=0,
            data=dict(income=0, known_costs=0, margin=None, forecast=[], forecast_method='No history',
                income_change=None, cost_coverage=None, critical_ingredients=[], waste=[],
                customers=0, new_customers=0, frequent_customers=0, inactive_customers=0,
                website_views=0, published_offers=0, daily=[], hours=[], top_products=[], least_products=[],
                missing_metrics=[], service=dict(sessions=0, average_minutes=None,
                    rotation_per_table_day=None, median_wait_minutes=None)),
            tables=[], service_enabled=True, site={}, businesses=[], claims=[],
            threads=[], q='', states=[], priorities=[], cases=[], result={}, recovery=False,
            coupons=[], reviews=[], seasons=[], products=[], drafts=[], categories=[], districts=[], is_admin=role == 'admin',
            group={'title': 'Fixture group', 'members': [1], 'until': '2026-12-01', 'invite': 'mock'},
            host=True, mine={}, votes={}, pending=lambda *a: False, uid=1,
            start=datetime(2026, 11, 1), end=datetime(2026, 11, 19))

class PrivateRenderChecks(unittest.TestCase):
    def test_all_template_syntax(self):
        for path in (ROOT / 'templates').rglob('*.html'):
            with self.subTest(template=str(path.relative_to(ROOT))):
                app.jinja_env.parse(path.read_text(encoding='utf-8-sig'))

    def test_private_views(self):
        for name, endpoint in CASES.items():
            for role in ('user', 'business_owner', 'admin'):
                with self.subTest(template=name, role=role):
                    html = render(name, endpoint, role)
                    self.assertRegex(html, r'<body[^>]*sr-saas-private')
                    links = re.findall(r'<link[^>]+href="([^"]+)"', html)
                    saas = '/static/css/saas-private.css'
                    admin = '/static/css/admin-precision.css'
                    wake = '/static/css/copilot-wake.css'
                    self.assertEqual(links.count(saas), 1)
                    self.assertEqual(links.count(wake), 1)
                    self.assertLess(links.index(wake), links.index(saas))
                    if role == 'admin' and endpoint.split('.', 1)[0] != 'intelligence':
                        self.assertEqual(links[-2:], [saas, admin])
                        self.assertEqual(links.count(admin), 1)
                        self.assertRegex(html, r'<body[^>]*sr-admin-precision')
                    else:
                        self.assertEqual(links[-1], saas)
                        self.assertNotIn(admin, links)
                        self.assertNotRegex(html, r'<body[^>]*sr-admin-precision')
                    self.assertNotRegex(html.split('</head>', 1)[1], r'<link\b')
                    self.assertIn('mock-csrf', html)
                    self.assertNotIn('cdn.tailwindcss.com', html)

    def test_private_shell_contract(self):
        for role in ('user', 'business_owner', 'admin'):
            html = render('communication/inbox.html', 'comunicacion.inbox', role)
            self.assertEqual(html.count('<header'), 1)
            self.assertEqual(html.count('id="themeToggle"'), 1)
            sidebar = html.split('<nav class="sr-sidebar"', 1)[1].split('</nav>', 1)[0]
            self.assertNotIn('data-theme-toggle', sidebar)
            self.assertIn('data-account-toggle', html)
            self.assertIn('aria-controls="private-account-menu"', html)
            self.assertIn('/mock/auth.account_security', html)
            self.assertIn('/mock/' + {'user': 'market.orders', 'business_owner': 'owner.dashboard', 'admin': 'admin.dashboard'}[role], html)
            if role == 'user':
                self.assertNotIn('/mock/admin.users', sidebar)
                self.assertNotIn('/mock/catalog.dashboard', sidebar)
            if role == 'business_owner':
                self.assertNotIn('/mock/admin.users', sidebar)

    def test_shared_and_public_gating(self):
        endpoints = ['main.index', 'market.browse', 'market.offer_detail',
            'ecosystem.home', 'sites.public_page', 'sites.branch_page',
            'salon.menu', 'flow.public', 'auth.login']
        for endpoint in endpoints:
            for authenticated in (False, True):
                with self.subTest(endpoint=endpoint, authenticated=authenticated):
                    html = render('base.html', endpoint, authenticated=authenticated)
                    self.assertNotIn('saas-private.css', html)
                    self.assertNotIn('admin-precision.css', html)
                    self.assertNotRegex(html, r'<body[^>]*sr-saas-private')

    def test_guest_private_routes_have_no_private_css(self):
        for endpoint in CASES.values():
            for role in ('user', 'business_owner', 'admin'):
                html = render('base.html', endpoint, role, authenticated=False)
                self.assertNotIn('saas-private.css', html)
                self.assertNotIn('admin-precision.css', html)

if __name__ == '__main__':
    unittest.main(verbosity=2)
