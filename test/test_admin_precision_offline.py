"""Offline ADMIN rendering; no application import or database connection."""
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import json
import re
import unittest
from flask import Flask, render_template, session

ROOT = Path(__file__).resolve().parents[1]
app = Flask(__name__, template_folder=str(ROOT / 'templates'))
app.secret_key = 'offline-admin-fixture'
app.jinja_env.globals.update(csrf_token=lambda: 'fixture-csrf',
    url_for=lambda endpoint, **kw: '/static/' + kw['filename'] if endpoint == 'static' else '/fixture/' + endpoint,
    APP_NAME='SmartResto', MONEDA='S/', website={'brand': 'SmartResto'}, current_year=2026,
    platform_context={})
app.jinja_env.filters['soles'] = lambda value: f'S/ {value}'


def render(name, endpoint, role='admin', **extra):
    with app.test_request_context('/') as context:
        context.request.url_rule = SimpleNamespace(endpoint=endpoint)
        session['user'] = dict(id=1, role=role, username='fixture', profile={'name': 'Fixture'})
        values = dict(restaurants=[], categories=[], districts=[], users=[], rows=[], events=[],
            pending=[], claims=[], signals=[], unsettled=[], charts=[], cid='',
            start=datetime(2026, 11, 1), end=datetime(2026, 11, 19),
            report=dict(income=70, count=3, completed=2, active_clients=2), total_users=4,
            owners=1, published=2, states=[], payments=[], state='', payment='', page=1, more=False,
            settings=dict(threshold=5, diets=['Vegetal']), is_admin=True, total_restaurants=0,
            avg_rating=0, total_favorites=0, recent_activities=[],
            stats=dict(pending=0, approved=0, rejected=0, flagged=0), auto_flagged=[], clean_pending=[], flagged=[],
            candidates=[], sources=[], runs=[], offers=[], zones=[], supply={}, demand={}, campaigns=0,
            threads=[], cases=[], priorities=[], q='', notifications=[],
            item=dict(business='Fixture', state='Entregado', total=70, paid='true', history=[]), oid=1)
        values.update(extra)
        return render_template(name, **values)


class AdminPrecisionTests(unittest.TestCase):
    def test_views_render(self):
        cases = [('admin/' + name + '.html', 'admin.' + endpoint) for name, endpoint in [
            ('dashboard', 'dashboard'), ('restaurants', 'restaurants'), ('restaurant_form', 'new_restaurant'),
            ('categories', 'categories'), ('users', 'users'), ('operations', 'operations'),
            ('operation_detail', 'operation_detail'), ('controls', 'controls'), ('analytics', 'analytics_page'),
            ('moderation', 'moderation_dashboard')]]
        cases += [('discovery/dashboard.html', 'discovery.dashboard'),
            ('ecosystem/publications.html', 'ecosystem.publications'), ('ecosystem/city.html', 'ecosystem.city'),
            ('communication/inbox.html', 'comunicacion.inbox'), ('communication/cases.html', 'comunicacion.cases'),
            ('communication/notifications.html', 'comunicacion.notifications'),
            ('admin/website_settings.html', 'admin.website_settings'),
            ('admin/business_verifications.html', 'business_access.admin_verifications')]
        for name, endpoint in cases:
            with self.subTest(view=name):
                html = render(name, endpoint)
                self.assertIn('sr-admin-precision', html)
                self.assertIn('fixture-csrf', html)
                links = re.findall(r'<link[^>]+href="([^"]+)"', html.split('</head>', 1)[0])
                self.assertTrue(links[-1].endswith('admin-precision.css'))

    def test_role_and_public_scope(self):
        for endpoint, role in [('admin.dashboard', 'business_owner'), ('main.index', 'admin'),
                               ('intelligence.dashboard', 'admin'), ('admin.dashboard', 'user')]:
            self.assertNotIn('admin-precision.css', render('base.html', endpoint, role))
        html = render('base.html', 'admin.dashboard')
        self.assertIn('/fixture/admin.users', html)
        self.assertIn('/fixture/admin.operations', html)
        self.assertNotIn('/fixture/admin.users', render('base.html', 'auth.profile', 'user'))

    def test_real_graph_values_and_empty(self):
        rows = [('2026-11-01', 2), ('2026-11-02', 1)]
        html = render('admin/dashboard.html', 'admin.dashboard', charts=[('Pedidos recibidos', rows)])
        payload = re.search(r"data-admin-chart='([^']+)'", html).group(1)
        self.assertEqual(json.loads(payload), [list(row) for row in rows])
        self.assertIn('S/ 70', html)
        self.assertIn('Sin actividad en este período', render('admin/dashboard.html', 'admin.dashboard', charts=[('Pedidos', [('Día', 0)])]))

    def test_local_chart_order_and_navigation_contract(self):
        html = render('base.html', 'admin.dashboard')
        self.assertNotIn('cdn.jsdelivr.net/npm/chart.js', html)
        self.assertEqual(html.count('chart-4.5.1.umd.min.js'), 1)
        self.assertLess(html.index('chart-4.5.1'), html.index('theme-charts.js'))
        self.assertGreater((ROOT / 'static/vendor/chartjs/chart-4.5.1.umd.min.js').stat().st_size, 10000)
        js = (ROOT / 'static/js/admin-precision.js').read_text(encoding='utf-8')
        for forbidden in ['preventDefault', 'beforeunload', 'pushState', 'replaceState', 'location.href']:
            self.assertNotIn(forbidden, js)
        css = (ROOT / 'static/css/admin-precision.css').read_text(encoding='utf-8')
        self.assertIn('prefers-reduced-motion', css)
        template = (ROOT / 'templates/admin/analytics.html').read_text(encoding='utf-8')
        self.assertNotIn('total_users * 0.08', template)

    def test_template_syntax(self):
        for path in (ROOT / 'templates').rglob('*.html'):
            app.jinja_env.parse(path.read_text(encoding='utf-8-sig'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
