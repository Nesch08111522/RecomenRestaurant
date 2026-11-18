from logic.product_catalog import ai_product


def test_optional_unknown_ai_fields_do_not_break_draft():
    value=ai_product({'name':'Arroz con pollo','price':18,'subcategory':None,'portion':None,'tags':None},'voice')
    assert value['price_cents']==1800
    assert value['tags']==[]
    assert value['allergens'] is None and not value['ingredients_confirmed']
