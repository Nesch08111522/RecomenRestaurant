"""Template rendering only: no operational app, environment or database."""
from pathlib import Path

import pytest
from flask import Flask, render_template, url_for

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('parent,endpoint,role', [
    ('base.html', 'main.index', None),
    ('base.html', 'auth.login', None),
    ('base.html', 'auth.register', None),
    ('market/base.html', 'market.browse', 'user'),
    ('owner/base.html', 'owner.dashboard', 'business_owner'),
    ('communication/base.html', 'comunicacion.inbox', 'admin'),
    ('base.html', 'copilot.page', 'user'),
])
def test_global_shell_render(parent, endpoint, role):
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    app.secret_key = 'render-only'
    app.add_url_rule('/copilot', 'copilot.page', lambda: '')
    app.jinja_env.globals.update(
        csrf_token=lambda: 'test', APP_NAME='SmartResto', website={'brand': 'Test', 'social': {}},
        url_for=lambda name, **kw: url_for(name, **kw) if name in ('copilot.page', 'static') else '/test/' + name,
    )
    app.jinja_env.filters['soles'] = str
    from flask import session, request
    with app.test_request_context('/'):
        request.url_rule = type('Rule', (), {'endpoint': endpoint})()
        if role:
            session['user'] = {'id': 1, 'role': role, 'name': 'Test', 'username': 'test', 'profile': {'name': 'Test'}}
        # Exercise the real inherited shell while isolating module data blocks.
        template = app.jinja_env.from_string(
            '{% extends "' + parent + '" %}{% block content %}Test{% endblock %}'
        )
        html = template.render()
        assert html.count('id="sr-wake"') == 1
        assert html.count('js/copilot-wake.js') == 1
        assert 'data-copilot-url="/copilot"' in html
        assert 'id="sr-wake-toggle" type="checkbox" checked' in html


def test_standalone_public_site_render():
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    app.jinja_env.globals['url_for'] = lambda name, **kw: '/copilot' if name == 'copilot.page' else '/static/' + kw.get('filename', 'test')
    with app.test_request_context('/'):
        html = render_template('sites/public.html', site={'name': 'Test'},
                               restaurant={'id': 1, 'name': 'Test'}, dishes=[],
                               branches=[], reviews=[], preview=False)
    assert html.count('id="sr-wake"') == 1
    assert html.count('js/copilot-wake.js') == 1
