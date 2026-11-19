from pathlib import Path
from types import SimpleNamespace
import re
import subprocess

from jinja2 import ChainableUndefined, Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
CHANGED = (
    'detail.html', 'favorites.html', 'admin/moderation.html',
    'admin/restaurant_form.html', 'owner/menu_management.html',
    'partials/dish_item.html', 'partials/theme_toggle.html',
    'sites/public.html', 'sites/editor.html', 'auth/experience.html',
    'partials/discover_hero.html',
)
EMOJI = re.compile('[\U0001f000-\U0001faff\u2300-\u23ff\u2600-\u27bf]')


def environment():
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'),
                      undefined=ChainableUndefined, autoescape=True)
    env.globals.update(url_for=lambda endpoint, **kw: '/' + endpoint,
                       csrf_token=lambda: 'fixture',
                       get_flashed_messages=lambda **kw: [], MONEDA='S/')
    env.filters['soles'] = lambda value: str(value)
    return env


def test_all_templates_parse():
    env = environment()
    names = env.list_templates()
    for name in names:
        env.parse(env.loader.get_source(env, name)[0])
    print('Jinja templates parsed:', len(names))


def test_changed_templates_have_no_emoji_literals():
    for name in CHANGED:
        assert not EMOJI.search((ROOT / 'templates' / name).read_text(encoding='utf-8'))


def test_dish_render_preserves_human_text_and_permissions():
    env = environment()
    dish = dict(id=7, name='Human \U0001f600 <script>', menu_date='2026-11-01',
                meal_time='almuerzo', category='Fondo', price=12,
                is_recommended=True, is_available=False, spiciness=3,
                preparation_time=20, ingredients=['Human \U0001f600'], dietary_info=[])
    for readonly in (False, True):
        html = env.get_template('partials/dish_item.html').render(
            dish=dish, meal_times=[], is_read_only=readonly)
        assert 'Human \U0001f600 &lt;script&gt;' in html
        assert 'Human \U0001f600' in html
        assert 'fa-pepper-hot' in html and 'Picante: 3 de 5' in html
        assert 'fa-stopwatch' in html and 'fa-utensils' in html
        assert ('editDish' in html) is (not readonly)
        assert ('deleteDish' in html) is (not readonly)


def test_modified_views_render_with_fixtures():
    env = environment()
    restaurant = dict(id=1, name='Human \U0001f600', description='Description',
                      district='Trujillo', address='Street', rating=4.5,
                      avg_price=20, open_time='12:00', close_time='22:00', promo='',
                      tags=[], features=[], lat=None, lng=None)
    common = dict(restaurant=restaurant, session={},
                  request=SimpleNamespace(endpoint='main.detail', blueprint='main',
                                          path='/', args={}, base_url='http://localhost/'),
                  dishes=[], restaurants=[], total=0, categories=[], districts=[],
                  user_profile=dict(restrictions=[], preferences=[]),
                  explanation=dict(compatible=False, reasons=['Reason'], exclusions=['Caution'],
                                   dietary_options=dict(vegan=True, vegetarian=True, gluten_free=True)),
                  login_url='/login', stats=dict(pending=0, approved=0, rejected=0, flagged=0),
                  clean_pending=[dict(restaurant, owner_name='Human \U0001f600')],
                  auto_flagged=[], pending=[], menu_type='fixed',
                  selected_date_iso='2026-11-01', today_date_iso='2026-11-01',
                  selected_date_label='November', meal_times=[], dish_categories=[],
                  carta_dishes=[], date_dishes=[])
    for name in CHANGED[:5]:
        html = env.get_template(name).render(**common)
        assert html
    print('Changed full views rendered: 5')


def test_public_editor_auth_and_index_render_and_script_syntax():
    env = environment()
    human = 'Human \U0001f600 <script>'
    restaurant = dict(id=1, name=human, description=human, district='Trujillo',
                      rating=4.5, avg_price=20, tags=[], features=[], promo='',
                      open_time='12:00', close_time='22:00', lat=None, lng=None)
    common = dict(restaurant=restaurant, restaurants=[restaurant], dishes=[],
                  reviews=[dict(rating=3, comment=human)], branches=[], session={},
                  site=dict(name=human, slug='fixture', template='atelier'),
                  categories=[], user_profile={}, editorial_images=dict(home='/static/fixture.webp'), CENTER_COORDS=[-8.11, -79.03],
                  RADIO_MAXIMO_KM=10, CIUDAD='Trujillo', PRIMARY_COLOR='', SECONDARY_COLOR='',
                  request=SimpleNamespace(endpoint='auth.login', blueprint='auth',
                                          path='/login', args={}, form={}, method='GET'))
    for name in ('sites/public.html', 'sites/editor.html', 'login.html', 'register.html', 'index.html'):
        html = env.get_template(name).render(**common)
        assert 'Human \U0001f600 &lt;script&gt;' in html or name in ('login.html', 'register.html')
        for script in re.findall(r'<script\b([^>]*)>([\s\S]*?)</script>', html):
            if 'src=' in script[0] or 'application/ld+json' in script[0]:
                continue
            subprocess.run(['node', '--check'], input=script[1], text=True, encoding='utf-8', check=True)
        if name == 'sites/public.html':
            assert html.count('m12 3 2.8 5.7') == 3
            assert 'Human \U0001f600 &lt;script&gt;' in html
    print('Public/editor/login/register/index rendered; inline scripts syntax checked')


def test_ui_source_scan_excludes_only_logs_comments_and_reserved_shell():
    reserved = {'templates/base.html', 'templates/partials/header.html',
                'static/css/shell.css', 'static/js/private-shell.js', 'static/js/shell.js'}
    count = 0
    non_ui = 0
    for directory in ('templates', 'static/js', 'static/css', 'views', 'logic', 'utils', 'core', 'analytics'):
        for file in (ROOT / directory).rglob('*'):
            if file.suffix not in ('.html', '.js', '.css', '.py'):
                continue
            relative = file.relative_to(ROOT).as_posix()
            if relative in reserved:
                continue
            count += 1
            source = file.read_text(encoding='utf-8')
            comment_lines = set()
            if file.suffix == '.py':
                import io
                import tokenize
                comment_lines = {token.start[0] for token in tokenize.generate_tokens(io.StringIO(source).readline)
                                 if token.type == tokenize.COMMENT and EMOJI.search(token.string)}
            for number, line in enumerate(source.splitlines(), 1):
                if not EMOJI.search(line):
                    continue
                stripped = line.strip()
                if number in comment_lines:
                    non_ui += 1
                    continue
                if stripped.startswith(('#', '//', 'logger.', 'console.')):
                    non_ui += 1
                    continue
                assert False, f'{relative}:{number}: deterministic UI symbol remains'
    print(f'UI scan: {count} files; 0 visible literal matches; {non_ui} log/comment lines retained; 5 reserved files excluded')


def test_javascript_syntax_and_human_message_contract():
    for name in ('ai-assistant.js', 'map.js', 'theme.js', 'business-sites.js'):
        subprocess.run(['node', '--check', str(ROOT / 'static/js' / name)], check=True)
    source = (ROOT / 'static/js/ai-assistant.js').read_text(encoding='utf-8')
    assert "addBubble('user', text);" in source
    assert "addBubble('bot', data.reply);" in source
    assert 'if (text != null) n.textContent = text;' in source
    assert not EMOJI.search(source)
