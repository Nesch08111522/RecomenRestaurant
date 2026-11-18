"""Pure ranking and onboarding safeguards. No DB, network or model/provider calls."""
import importlib.util
import pytest

def module():
    assert importlib.util.find_spec('core.food_experience') is not None, 'Missing real food selection processor'
    from core import food_experience
    return food_experience

def test_favorites_and_preferences_select_real_catalog_images():
    m=module();p={'preferences':['ceviche']}
    rows=[{'id':1,'name':'Lomo saltado','restaurant_id':1,'image':'https://example.test/lomo.webp','is_available':True},
          {'id':2,'name':'Ceviche clásico','restaurant_id':2,'images':['/catalog-media/23'],'is_available':True}]
    selected=m.select_food_scene('home',p,rows,{2})
    assert selected[0]['id']=='dish-2'
    assert selected[0]['image']=='/catalog-media/23'
    assert selected[0]['scene']=='ceviche'
    assert selected[0]['source']=='catalog'
    assert selected[0]['model_kind']=='reference'

def test_scene_url_rejects_untrusted_schemes_and_protocol_relative():
    m=module()
    for url in ['javascript:alert(1)','//example.test/img','data:text/html,test','https://user:secret@example.test/img','/static/a\\b']:
        assert m.safe_media_url(url)==''
    assert m.safe_media_url('/static/photo.webp')=='/static/photo.webp'

def test_restrictions_are_respected_even_for_favorites():
    m=module();rows=[{'id':1,'name':'Ceviche','restaurant_id':2,'ingredients':['pescado'],'allergens':['pescado'],'is_available':True},
                       {'id':2,'name':'Ensalada de verduras','restaurant_id':1,'ingredients':['lechuga'],'dietary_info':['vegano'],'is_available':True}]
    selected=m.select_food_scene('home',{'restrictions':['alergia pescado','vegano']},rows,{2})
    assert selected and selected[0]['id']=='dish-2'
    assert all(x['id']!='dish-1' for x in selected)

def test_no_restriction_safe_catalog_never_claims_an_allergen_free_reference():
    m=module()
    selected=m.select_food_scene('home',{'restrictions':['alergia leche']},[],set())
    assert selected==[]

def test_editorial_views_have_different_models():
    m=module()
    assert m.select_food_scene('login',{},[],set())[0]['scene']=='lomo'
    assert m.select_food_scene('register',{},[],set())[0]['scene']=='ceviche'
    assert m.select_food_scene('recover',{},[],set())[0]['scene']=='dessert'
    assert m.select_food_scene('business',{},[],set())[0]['scene']=='signature'

def test_business_onboarding_is_normalized_not_a_role_escalation():
    m=module()
    data=m.normalize_business_details({'business_name':'  Mesa   Norte ','ruc':'12345678901','phone':'+51 999 123 456','district':'Trujillo','role':'admin'})
    assert data['business_name']=='Mesa Norte'
    assert 'role' not in data
    with pytest.raises(ValueError):m.normalize_business_details({'ruc':'abc'})
