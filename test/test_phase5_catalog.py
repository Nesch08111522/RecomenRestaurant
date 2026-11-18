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
