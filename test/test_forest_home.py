"""Visual contracts against real templates/JS; all restaurant data is an isolated fixture.
Breaks caught: default map competing with results, clipped controls, loss of filters
when switching views, and recommendation input not reaching the existing AI form.
No operational database, accounts or AI provider calls are used.
"""
from pathlib import Path
from threading import Thread
import pytest
from flask import render_template, session, request
from werkzeug.serving import make_server
from app import create_app
from models.category import CategoryModel

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = [{'id': 1, 'name': 'Comida marina'}, {'id': 2, 'name': 'Comida criolla'}, {'id': 3, 'name': 'Cafeterías'}]
RESTAURANTS = [dict(id=i, name=name, district=district, rating=4.7, review_count=12,
                    avg_price=35, image='/static/images/ceviche.webp', tags=['Peruana', 'Marina', 'Local'],
                    category_id=1, promo=i == 1, lat=-8.11, lng=-79.03, open_time='08:00', close_time='23:00')
               for i, name, district in [(1, 'Restaurante de prueba', 'Víctor Larco'), (2, 'Cocina local', 'Trujillo'), (3, 'Mesa norteña', 'Moche')]]

@pytest.fixture(scope='module')
def visual_origin():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'visual-test-only-' * 3})
    # CategoryModel.all is the only external operation in template rendering.
    original = CategoryModel.all
    CategoryModel.all = staticmethod(lambda: CATEGORIES)
    @app.route('/__forest_test')
    def forest_test():
        session.clear()
        role = request.args.get('role')
        if role in ('user', 'business_owner', 'admin'):
            session['user'] = {'id': 99, 'username':'visual', 'role':role, 'profile':{'name':'Comensal'}}
        return render_template('index.html', restaurants=RESTAURANTS, categories=CATEGORIES,
                               user_profile={}, home_offers=[], home_new=[], home_reviews=[])
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    CategoryModel.all = original

@pytest.mark.parametrize('consent,available', [(False,False),(True,False),(True,True)])
def test_save_location_weather_requires_consent(monkeypatch, consent, available):
    from flask import Flask
    from views.main import main_bp
    from utils import weather
    app = Flask(__name__)
    app.secret_key = 'isolated-location-test'
    app.register_blueprint(main_bp)
    calls = []
    forecast = {'apparent_temperature': 25, 'source': 'Open-Meteo'} if available else None
    def conditions(lat, lng):
        calls.append((lat, lng))
        return forecast
    monkeypatch.setattr(weather, 'conditions', conditions)
    client = app.test_client()
    response = client.post('/api/save-location', json={'lat': -8.11, 'lng': -79.03, 'context_consent': consent})
    assert response.status_code == 200
    assert response.json['weather'] == (forecast if consent else None)
    assert calls == ([(-8.11, -79.03)] if consent else [])
    with client.session_transaction() as saved:
        assert saved['user_lat'] == -8.11
        assert bool(saved.get('food_context', {}).get('weather')) == consent


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel='msedge', headless=True)
        yield b
        b.close()

@pytest.fixture
def page(browser, visual_origin):
    context = browser.new_context(locale='es-PE', reduced_motion='reduce')
    p = context.new_page()
    # External map tiles/provider calls are irrelevant to local layout contracts.
    p.route('**/*', lambda route: route.continue_() if route.request.url.startswith(visual_origin) else route.abort())
    p.route('**/auth/api/favorites', lambda route: route.fulfill(status=200, json={'favorites': []}))
    p.route('**/api/search', lambda route: route.fulfill(json={'results': RESTAURANTS[:1]}))
    p.route('**/api/save-location', lambda route: route.fulfill(json={'success': True, 'weather': None}))
    p.goto(visual_origin + '/__forest_test')
    p.wait_for_load_state('networkidle')
    yield p
    context.close()

@pytest.mark.parametrize('width,columns', [(320,1),(375,1),(640,2),(768,2),(1024,2),(1440,3),(1920,3)])
def test_home_keeps_results_visible_without_horizontal_clipping(page, width, columns):
    page.set_viewport_size({'width': width, 'height': 900})
    assert not page.locator('.map-column').is_visible(), 'Map must be opt-in, not the default half-page'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    grid = page.locator('#resultsGrid')
    assert grid.evaluate('(el) => getComputedStyle(el).gridTemplateColumns.split(" ").length') == columns
    card = page.locator('#resultsGrid .restaurant-card').first
    image = card.locator('.card-image').bounding_box()
    assert image['height'] / card.bounding_box()['height'] >= .55
    assert len(card.locator('.tag').all()) <= 2
    assert page.locator('#resultsColumn').evaluate('(el) => getComputedStyle(el).overflowY') != 'auto'


def test_map_switch_preserves_current_results_and_query(page):
    page.locator('input[name=q]').fill('prueba')
    page.wait_for_timeout(500)
    assert page.locator('#resultsGrid .restaurant-card').count() == 1
    page.get_by_role('button', name='Ver mapa', exact=True).first.click()
    assert page.locator('.map-column').is_visible()
    assert page.locator('input[name=q]').input_value() == 'prueba'
    assert page.locator('#resultsGrid .restaurant-card').count() == 1
    page.get_by_role('button', name='Cerrar mapa', exact=True).click()
    assert not page.locator('.map-column').is_visible()


@pytest.mark.parametrize('width,height', [(320,568),(375,667),(390,844),(640,360),(768,900),(1440,900)])
def test_map_dialog_and_controls_fit_viewport(page, width, height):
    page.set_viewport_size({'width': width, 'height': height})
    page.locator('#forest-map').click()
    box = page.locator('.sr-map-dialog').bounding_box()
    assert box['x'] >= 0 and box['y'] >= 0
    assert box['x'] + box['width'] <= width
    assert box['y'] + box['height'] <= height
    assert abs(box['x'] + box['width']/2 - width/2) <= 1
    assert abs(box['y'] + box['height']/2 - height/2) <= 1
    location = page.locator('#locationBtn').bounding_box()
    controls = page.locator('.map-controls').bounding_box()
    assert location['y'] + location['height'] <= controls['y'] + 1 or location['x'] + location['width'] <= controls['x'] + 1
    assert page.locator('.sr-map-dialog').evaluate('(el) => el.scrollWidth <= el.clientWidth')


def test_location_requests_browser_without_closing_map(page):
    page.evaluate('''() => { navigator.geolocation.getCurrentPosition = success => {
      window.locationCalls = (window.locationCalls || 0) + 1;
      success({coords:{latitude:-8.11,longitude:-79.03}});
    }; }''')
    page.locator('#forest-map').click()
    page.locator('#locationBtn').click()
    page.wait_for_function('document.querySelector("#geo-status").textContent.includes("No hay datos")')
    assert page.evaluate('window.locationCalls') == 1
    assert page.locator('.sr-map-dialog').evaluate('(el) => el.open')
    assert page.locator('#location-consent input[required]').count() == 0


def test_location_denial_is_reported_in_open_map(page):
    page.evaluate('() => { navigator.geolocation.getCurrentPosition = (success, failure) => failure({code:1}); }')
    page.locator('#forest-map').click()
    page.locator('#locationBtn').click()
    assert 'denegó' in page.locator('#geo-status').inner_text()
    assert page.locator('.sr-map-dialog').evaluate('(el) => el.open')
    assert page.locator('#locationBtn').is_enabled()


@pytest.mark.parametrize('name', ['chef-reference', 'creole-inspiration', 'food-inspiration',
                                 'marine-inspiration', 'shop-reference'])
def test_forest_webp_http_type_and_body(visual_origin, name):
    from urllib.request import urlopen
    with urlopen(f'{visual_origin}/static/images/forest/{name}.webp') as response:
        assert response.status == 200
        assert response.headers.get_content_type() == 'image/webp'
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        body = response.read()
    assert body == (ROOT / 'static' / 'images' / 'forest' / f'{name}.webp').read_bytes()
    assert body[:4] == b'RIFF' and body[8:12] == b'WEBP'


def test_inspiration_images_load_and_are_not_covered(page):
    for image in page.locator('.forest-promo img,.forest-chef,.forest-business img').all():
        image.scroll_into_view_if_needed()
        image.evaluate('(el) => el.decode()')
        assert image.evaluate('(el) => el.complete && el.naturalWidth > 0')
        assert image.evaluate('''el => {
          const b = el.getBoundingClientRect();
          return document.elementFromPoint(b.right - 10, b.top + b.height/2) === el;
        }''')


def test_inline_recommendation_transfers_text_and_escape_restores_focus(page):
    page.locator('#forest-craving').fill('Algo ligero con pollo')
    page.get_by_role('button', name='Recomendar', exact=True).click()
    assert page.locator('#recommendationModal').is_visible()
    assert page.locator('#aiRecText').input_value() == 'Algo ligero con pollo'
    page.keyboard.press('Escape')
    assert not page.locator('#recommendationModal').is_visible()
    assert page.locator('#forest-recommend').evaluate('(el) => el === document.activeElement')


def test_featured_selection_can_expand_without_losing_other_sections(page):
    page.evaluate('''() => {
      const original = window.app.state.restaurants;
      window.app.state.restaurants = [...original, {...original[0],id:4,name:'Cuarta mesa'}, {...original[0],id:5,name:'Quinta mesa'}];
      window.app.state.filteredRestaurants = window.app.state.restaurants;
      window.app.renderRestaurants();
    }''')
    assert page.locator('#resultsGrid .restaurant-card').count() == 5
    page.evaluate('''() => { const rows=window.app.state.restaurants; window.app.state.filteredRestaurants=[...rows,...rows.map(r=>({...r,id:r.id+100}))];window.app.renderRestaurants(); }''')
    assert page.locator('#resultsGrid .restaurant-card').count() == 6
    page.locator('#restaurant-pagination').get_by_role('button',name='Siguiente',exact=True).click()
    assert page.locator('#resultsGrid .restaurant-card').count() == 4
    assert page.locator('#ofertas').is_visible()


@pytest.mark.parametrize('role', ['user', 'business_owner', 'admin'])
@pytest.mark.parametrize('width', [320,375,768,1440])
def test_authenticated_header_keeps_profile_and_navigation_reachable(page, visual_origin, role, width):
    page.set_viewport_size({'width':width,'height':900})
    page.goto(visual_origin + '/__forest_test?role=' + role)
    page.wait_for_load_state('networkidle')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    profile = page.get_by_role('link', name='Mi perfil', exact=True).first
    assert profile.is_visible()
    box = profile.bounding_box()
    assert box['x'] + box['width'] <= width + 1
    if width < 1100:
        page.get_by_role('button', name='Abrir navegación', exact=True).click()
        assert page.locator('#sr-navigation').is_visible()
        page.keyboard.press('Escape')
        assert page.locator('.sr-menu-button').get_attribute('aria-expanded') == 'false'
