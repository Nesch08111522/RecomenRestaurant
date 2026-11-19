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
        assert html.count('id="sr-wake"') == int(bool(role))
        assert html.count('js/copilot-wake.js') == int(bool(role))
        if role:
            assert 'data-copilot-url="/copilot"' in html
            assert 'id="sr-wake-toggle" type="checkbox" checked' in html


@pytest.mark.parametrize('identity', [None, {}, {'role': 'admin'}, {'id': 1, 'role': 'unknown'},
                                      {'id': 1, 'role': 'user'}, {'id': 1, 'role': 'admin'},
                                      {'id': 1, 'role': 'business_owner'}])
def test_standalone_public_site_render(identity):
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    app.secret_key = 'offline'
    app.jinja_env.globals['url_for'] = lambda name, **kw: '/copilot' if name == 'copilot.page' else '/static/' + kw.get('filename', 'test')
    from flask import session
    with app.test_request_context('/'):
        if identity is not None:
            session['user'] = identity
        html = render_template('sites/public.html', site={'name': 'Test'},
                               restaurant={'id': 1, 'name': 'Test'}, dishes=[],
                               branches=[], reviews=[], preview=False)
    expected = int(bool(identity and identity.get('id') and identity.get('role') in ['user', 'admin', 'business_owner']))
    assert html.count('id="sr-wake"') == expected
    assert html.count('js/copilot-wake.js') == expected


@pytest.mark.parametrize('role,destination', [('user', 'market.orders'), ('admin', 'admin.dashboard'),
                                             ('business_owner', 'owner.dashboard')])
@pytest.mark.parametrize('endpoint', ['main.index', 'market.orders', 'salon.manage'])
def test_account_menu(role, destination, endpoint):
    from flask import session
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    app.secret_key = 'offline'
    app.add_url_rule('/', 'main.index', lambda: '')
    app.add_url_rule('/system', endpoint, lambda: '') if endpoint != 'main.index' else None
    app.jinja_env.globals.update(csrf_token=lambda: 'test', APP_NAME='SmartResto',
                                website={'brand': 'Test', 'social': {}},
                                url_for=lambda name, **kw: '/' if name == 'main.index' else '/test/' + name)
    app.jinja_env.filters['soles'] = str
    with app.test_request_context('/' if endpoint == 'main.index' else '/system'):
        session['user'] = {'id': 1, 'role': role, 'username': 'test'}
        html = app.jinja_env.from_string('{% extends "base.html" %}{% block content %}Test{% endblock %}').render()
    assert html.count('<header ') == 1
    assert html.count('data-account-toggle') == 1
    menu = html.split('id="private-account-menu"')[1].split('</div>')[0]
    assert '/test/auth.profile' in menu and '/test/auth.account_security' in menu
    if endpoint == 'main.index':
        assert '/test/' + destination in menu and 'Ir al sistema' in menu
    else:
        assert '<a href="/">Ir al sitio web</a>' in menu
        assert 'Ir al sistema' not in menu


@pytest.mark.parametrize('identity', [None, {}, {'role': 'admin'}, {'id': 1, 'role': 'unknown'}, 'invalid'])
@pytest.mark.parametrize('endpoint', ['main.index', 'market.orders'])
def test_invalid_session_shell(identity, endpoint):
    from flask import session
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    app.secret_key = 'offline'
    app.add_url_rule('/', endpoint, lambda: '')
    app.jinja_env.globals.update(csrf_token=lambda: 'test', APP_NAME='SmartResto',
                                website={'brand': 'Test', 'social': {}},
                                url_for=lambda name, **kw: '/test/' + name)
    app.jinja_env.filters['soles'] = str
    with app.test_request_context('/'):
        session['user'] = identity
        html = app.jinja_env.from_string('{% extends "base.html" %}{% block content %}Test{% endblock %}').render()
    assert 'data-role="guest"' in html
    assert html.count('<header ') == 1
    assert 'data-account-toggle' not in html
    assert 'id="sr-wake"' not in html and 'js/copilot-wake.js' not in html
    assert 'css/copilot-wake.css' not in html
    assert 'Administración' not in html
