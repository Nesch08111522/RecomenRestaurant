import importlib
import pytest


def catalog():
    assert importlib.util.find_spec('logic.product_catalog') is not None,'Falta núcleo de catálogo Fase 5'
    return importlib.import_module('logic.product_catalog')


def base():
    return {'name':'Arroz con pollo','product_type':'plato','price':'18.00','ingredients':['arroz','pollo'],
        'ingredients_confirmed':True,'allergens_confirmed':True,'allergens':[], 'rights_confirmed':True}


def test_exact_cents_and_allergens_explicit_unknown():
    value=catalog().normalize_product({'name':'Ceviche','price':'18.35'})
    assert value['price_cents']==1835
    assert value['allergens'] is None and not value['ingredients_confirmed']


@pytest.mark.parametrize('price',['nan','Infinity','-2','10.001',True])
def test_invalid_money_rejected(price):
    with pytest.raises(ValueError):catalog().normalize_product({'name':'Plato','price':price})


def test_photo_ingredients_never_become_confirmed_declarations():
    value=catalog().ai_product({'name':'Ceviche','ingredients':['pescado'],'allergens':['pescado'],'price':40})
    assert value['ingredients']==[] and value['probable_ingredients']==['pescado']
    assert value['allergens'] is None and value['price'] is None
    with pytest.raises(ValueError):catalog().validate_for_publication(value)


def test_publication_requires_confirmed_ingredients_and_allergens():
    value=catalog().normalize_product(base())
    assert catalog().validate_for_publication(value)['is_available'] is True
    with pytest.raises(ValueError):catalog().validate_for_publication({**value,'allergens_confirmed':False})


def test_sold_out_keeps_product_but_prevents_commerce():
    value=catalog().normalize_product({**base(),'availability':'sold_out'})
    assert catalog().validate_for_publication(value)['is_available'] is False


def test_recipe_and_variant_price_are_structured():
    value=catalog().normalize_product({**base(),'recipe':[{'ingredient':'arroz','quantity':'0.2','unit':'kg'}],
        'variants':[{'name':'Familiar','portion':'4 personas','price':'60.50'}]})
    assert value['recipe'][0]['quantity']=='0.2'
    assert value['variants'][0]['price_cents']==6050


def test_merchant_seasons_survive_review_and_subsequent_edits():
    value = catalog().validate_for_publication({**base(), 'seasons': ['invierno', 'Otono', 'Invierno']})
    assert value['seasons'] == ['Otoño', 'Invierno']
    edited = catalog().normalize_product({'name': 'Arroz con pollo especial'}, value)
    assert edited['seasons'] == value['seasons']
    assert catalog().normalize_product({'seasons': []}, edited)['seasons'] == []
    with pytest.raises(ValueError, match='temporadas'):
        catalog().normalize_product({'seasons': ['Carnaval']})


def test_public_restaurant_menu_follows_explicit_date_without_leaking_market_items(monkeypatch):
    from datetime import datetime, timedelta

    from app import create_app
    from models.site_settings import DEFAULTS
    import context_processors
    from views import main

    today = datetime.now(main.LIMA_TIMEZONE).date()
    tomorrow = today + timedelta(days=1)
    restaurant = {'id': 7, 'name': 'Mesa del Valle', 'district': 'Moche', 'verified': True}
    dishes = [
        {'id': 1, 'name': 'Tacu tacu', 'category': 'Fondo', 'price': 22, 'is_available': True},
        {'id': 2, 'name': 'Carapulcra programada', 'category': 'Fondo', 'price': 24, 'is_available': True,
         'menu_type': 'variable', 'menu_date': tomorrow.isoformat()},
        {'id': 3, 'name': 'Oferta sin publicar', 'category': 'Fondo', 'price': 16, 'is_available': True,
         'menu_date': tomorrow.isoformat(), 'market_only': True},
        {'id': 4, 'name': 'Oferta antigua sin revisar', 'category': 'Fondo', 'price': 16, 'is_available': True,
         'menu_date': tomorrow.isoformat()},
    ]
    monkeypatch.setattr(main.RestaurantModel, 'get_by_id', staticmethod(lambda rid: restaurant if rid == 7 else None))
    monkeypatch.setattr(main, 'load_dishes', lambda rid: dishes)
    monkeypatch.setattr(main.DailyMenuModel, 'get_active', staticmethod(lambda rid: None))
    monkeypatch.setattr(main.DailyMenuModel, 'get_by_date', staticmethod(lambda rid, day: None))
    monkeypatch.setattr(main.ReviewModel, 'get_by_restaurant', staticmethod(lambda rid: []))
    monkeypatch.setattr(main, 'recommender', None)
    monkeypatch.setattr(context_processors.CategoryModel, 'all', staticmethod(list))
    monkeypatch.setattr(context_processors, 'site_settings', lambda: dict(DEFAULTS))

    client = create_app({'TESTING': True, 'SECRET_KEY': 'catalog-menu-date-test'}).test_client()
    current = client.get('/restaurant/7')
    assert current.status_code == 200 and 'Carta y menú de hoy' in current.get_data(as_text=True)
    assert b'id="plato-1"' in current.data and b'id="plato-2"' not in current.data
    assert client.get('/restaurant/7', query_string={'day': today.isoformat()}).data.count(b'id="plato-1"') == 1

    future = client.get('/restaurant/7', query_string={'day': tomorrow.isoformat()})
    assert future.status_code == 200 and tomorrow.strftime('%d/%m/%Y').encode() in future.data
    assert b'id="plato-1"' in future.data and b'id="plato-2"' in future.data
    assert b'id="plato-3"' not in future.data and b'id="plato-4"' not in future.data
    for day in ((today - timedelta(days=1)).isoformat(), (today + timedelta(days=31)).isoformat(), 'mañana'):
        assert client.get('/restaurant/7', query_string={'day': day}).status_code == 400
    restaurant['status'] = 'suspended'
    assert client.get('/restaurant/7', query_string={'day': tomorrow.isoformat()}).status_code == 404
