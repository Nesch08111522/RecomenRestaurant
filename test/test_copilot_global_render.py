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
            if endpoint == 'copilot.page':
                session['user']['username'] = 'Nancy "<real>&'
                page_html = render_template('copilot.html', shops=[])
                assert 'data-username="Nancy &#34;&lt;real&gt;&amp;"' in page_html


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


@pytest.mark.parametrize('hour,salutation', [(0, 'Buenas noches'), (4, 'Buenas noches'),
    (5, 'Buenos días'), (11, 'Buenos días'), (12, 'Buenas tardes'),
    (18, 'Buenas tardes'), (19, 'Buenas noches'), (23, 'Buenas noches')])
def test_browser_wake_greeting(hour, salutation):
    from playwright.sync_api import sync_playwright
    from flask import session
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    app.secret_key = 'offline-browser'
    app.jinja_env.globals.update(csrf_token=lambda: 'test', APP_NAME='SmartResto',
        website={'brand': 'Test', 'social': {}}, url_for=lambda name, **kw: '/copilot' if name == 'copilot.page' else '/test/' + name)
    app.jinja_env.filters['soles'] = str
    with app.test_request_context('/copilot'):
        session['user'] = {'id': 1, 'role': 'user', 'username': 'Nancy "<real>&'}
        html = render_template('copilot.html', shops=[])
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/*', lambda route: route.fulfill(body=html, content_type='text/html')
                       if route.request.resource_type == 'document' else route.abort())
            page.goto('http://offline.test/copilot?voice=1&voice_intent=abre+pedidos', wait_until='domcontentloaded')
            page.evaluate('''hour => {
                const RealDate = Date;
                window.Date = class extends RealDate { getHours() { return hour; } };
                window.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
                window.recognizers = [];
                window.SpeechRecognition = class extends EventTarget {
                    constructor() { super(); this.starts = 0; recognizers.push(this); }
                    start() { this.starts++; }
                    abort() { this.dispatchEvent(new Event('end')); }
                };
                Object.defineProperty(window, 'speechSynthesis', {value: {
                    cancel() {}, getVoices() { return [{lang: 'es-PE'}]; },
                    speak(u) { window.spoken = u; window.speakCount = (window.speakCount || 0) + 1; }
                }});
                Object.defineProperty(navigator, 'mediaDevices', {value: undefined});
            }''', hour)
            page.add_script_tag(content=(ROOT / 'static/js/copilot-wake.js').read_text(encoding='utf8'))
            page.add_script_tag(content=(ROOT / 'static/js/copilot.js').read_text(encoding='utf8'))
            assert not errors, errors
            assert page.evaluate('spoken.text') == f'{salutation}, Nancy "<real>&. ¿Qué desea hacer hoy?'
            assert page.evaluate('spoken.lang') == 'es-PE'
            assert page.evaluate('recognizers[1].starts') == 0
            assert page.locator('#copilot-message').input_value() == 'abre pedidos'
            assert page.url == 'http://offline.test/copilot'
            page.evaluate("document.dispatchEvent(new CustomEvent('smartresto:copilot-wake', {detail: {}}))")
            assert page.evaluate('speakCount') == 1
            page.evaluate('spoken.onend()')
            assert page.evaluate('recognizers[1].starts') == 1
            page.evaluate("document.dispatchEvent(new CustomEvent('smartresto:copilot-wake', {detail: {}})); spoken.onerror({error: 'not-allowed'})")
            assert 'Audio no disponible' in page.locator('#copilot-status').inner_text()
            page.wait_for_timeout(350)
            assert page.evaluate('recognizers[1].starts') == 1
            page.reload(wait_until='domcontentloaded')
            page.evaluate('''() => {
                window.speakCount = 0;
                Object.defineProperty(window, 'speechSynthesis', {value: {
                    cancel() {}, getVoices() { return []; }, speak() { speakCount++; }
                }});
            }''')
            page.add_script_tag(content=(ROOT / 'static/js/copilot.js').read_text(encoding='utf8'))
            assert page.evaluate('speakCount') == 0, 'consumed URL does not greet on reload'
        finally:
            browser.close()
