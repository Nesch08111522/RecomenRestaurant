from copy import deepcopy
import pytest
from utils.functional import filter_restaurants


@pytest.fixture
def rows():
    return [dict(id=1, name='Cafe', district='Centro', avg_price=20, rating=4.5,
                 category_id=2, market_channels=['Recojo'], business_type='cafeteria',
                 tags=['familia'], promo='Oferta', is_available=True,
                 open_time='22:00', close_time='03:00', lat=-8.1, lng=-79.0),
            dict(id=2, name='Otro', district='Norte', avg_price=50, rating=3,
                 category_id=3, market_channels=['Delivery'], is_available=False)]


def test_combined_filters_and_no_mutation(rows):
    original=deepcopy(rows)
    result=filter_restaurants(rows,dict(category_ids=[2], min_price=10,max_price=25,
        min_rating=4,channel='Recojo',business_type='cafeteria',promo_only=True,
        available_only=True,keywords=['familia'],at_time='01:00'))
    assert [r['id'] for r in result]==[1]
    assert rows==original


@pytest.mark.parametrize('clock,expected',[('23:00',[1]),('01:00',[1]),('03:00',[]),('12:00',[])])
def test_overnight_hours(rows,clock,expected):
    assert [r['id'] for r in filter_restaurants(rows,{'at_time':clock})]==expected


def test_geo_filters_exclude_unknown_points(rows):
    assert [r['id'] for r in filter_restaurants(rows,dict(lat=-8.1,lng=-79,radius=1))]==[1]
    assert [r['id'] for r in filter_restaurants(rows,dict(bounds=[-8.2,-79.1,-8,-78.9]))]==[1]


@pytest.mark.parametrize('filters',[{'nearby':True},{'max_price':'nan'},{'min_rating':6},
    {'at_time':'99:10'},{'radius':-1,'lat':-8,'lng':-79},{'bounds':[1,2,0,0]}, {'category_ids':'x'}])
def test_invalid_filters(rows,filters):
    with pytest.raises(ValueError):filter_restaurants(rows,filters)


@pytest.fixture
def client(monkeypatch, rows):
    from app import create_app
    from models.restaurant import RestaurantModel
    from models.dish import DishModel
    from models.category import CategoryModel
    from models.favorite import FavoriteModel
    from models.review import ReviewModel
    import views.main as main
    monkeypatch.setattr(RestaurantModel,'get_approved',lambda:deepcopy(rows))
    monkeypatch.setattr(DishModel,'all',lambda:[dict(id=11,restaurant_id=1,name='Cafe',price=8,
        ingredients=['cafe'],is_available=True),dict(id=12,restaurant_id=2,name='Pan',price=5,is_available=False)])
    monkeypatch.setattr(CategoryModel,'all',lambda:[{'id':2,'name':'Cafe'}])
    monkeypatch.setattr(FavoriteModel,'all',lambda:[])
    monkeypatch.setattr(ReviewModel,'all',lambda:[])
    monkeypatch.setattr(main,'recommender',None)
    return create_app({'TESTING':True,'SECRET_KEY':'test'*8,'WTF_CSRF_ENABLED':False}).test_client()


def test_search_http(client):
    response=client.post('/api/search',json=dict(dish_query='cafe',available_only=True,max_price=25))
    assert response.status_code==200
    assert [r['id'] for r in response.json]==[1]
    assert client.post('/api/search',json={'max_price':'nan'}).status_code==400


def test_search_product_constraints_cannot_match_different_dishes(client,monkeypatch):
    from models.dish import DishModel
    monkeypatch.setattr(DishModel,'all',lambda:[
        dict(id=11,restaurant_id=1,name='Cafe',price=8,is_available=True,dietary_info=['vegano']),
        dict(id=13,restaurant_id=1,name='Cafe especial',price=40,is_available=True,dietary_info=[])])
    response=client.post('/api/search',json={'max_price':25})
    assert [d['id'] for d in response.json[0]['matching_dishes']]==[11]
    response=client.post('/api/search',json={'dish_query':'especial','dietary_restrictions':['vegano']})
    assert response.json==[]
    response=client.post('/api/search',json={'dish_query':'especial','max_price':25})
    assert response.json==[]


def test_comparison_http(client):
    response=client.get('/api/catalog/compare?ids=1,2')
    assert response.status_code==200 and len(response.json['results'])==2
    assert client.get('/api/catalog/compare?ids=1,99').status_code==404
    assert client.get('/api/catalog/compare?ids=1').status_code==400
    assert client.get('/api/catalog/compare?kind=product&ids=11,12').status_code==200


def test_private_map_and_public_route(client,monkeypatch):
    from models import market
    monkeypatch.setattr(market,'kitchen',lambda rid:dict(kind='Cocina oculta',pickup='Plaza',zones=['Centro'],radius=3))
    response=client.get('/api/catalog/1/map?lat=-8.1&lng=-79')
    assert response.json['point'] is None and response.json['route_url'] is None
    monkeypatch.setattr(market,'kitchen',lambda rid:dict(kind='Cocina oculta',pin=[-8.1,-79],pickup='Plaza',zones=['Centro'],radius=3))
    response=client.get('/api/catalog/1/map?lat=-8.1&lng=-79')
    assert response.json['distance_km']==0 and response.json['delivery_covered'] is True
    assert response.json['route_url'].startswith('https://www.openstreetmap.org/directions?')
    assert client.get('/api/catalog/1/map?lat=nan&lng=-79').status_code==400


def test_ai_queries_server_catalog(client,monkeypatch):
    import views.ai_routes as ai
    ai._hits.clear()
    def interpret(messages):
        assert 'Cafe' in messages[0]['content'] and 'Inventada' not in messages[0]['content']
        return dict(max_price=25,category_ids=[2,999],dish_query='cafe',summary='Cafe economico')
    monkeypatch.setattr(ai,'_llm_json',interpret)
    response=client.post('/api/ai/interpret',json=dict(text='cafe hasta 25',categories=[{'id':999,'name':'Inventada'}]))
    assert response.status_code==200
    assert response.json['filters']['category_ids']==[2]
    assert [r['id'] for r in response.json['results']]==[1]


def test_approved_excludes_suspended(monkeypatch):
    from models.restaurant import RestaurantModel
    monkeypatch.setattr(RestaurantModel,'all',lambda:[dict(id=1,verified=True),dict(id=2,verified=True,status='suspended')])
    assert [r['id'] for r in RestaurantModel.get_approved()]==[1]


def test_explorer_renders(client):
    response=client.get('/explorar')
    assert response.status_code==200 and b'catalog-explore.js' in response.data
    assert b'catalog-compare-products' in response.data and b'catalog-product-card' in response.data


def test_products_returned_without_text_query(client):
    response=client.post('/api/search',json={})
    assert response.status_code==200
    assert [p['id'] for p in next(r for r in response.json if r['id']==1)['matching_dishes']]==[11]


def test_product_card_unknown_allergens(client,monkeypatch):
    from models.dish import DishModel
    monkeypatch.setattr(DishModel,'get_by_id',lambda pid:dict(id=11,restaurant_id=1,name='Cafe',price=8,allergens=None) if pid==11 else None)
    response=client.get('/api/catalog/products/11')
    assert response.status_code==200 and response.json['product']['allergens'] is None
    assert response.json['business_url']=='/restaurant/1'
    assert client.get('/api/catalog/products/999').status_code==404


def test_empty_catalog_still_validates():
    with pytest.raises(ValueError):filter_restaurants([],{'radius':-1})


def test_missing_database_safe_http(monkeypatch):
    from app import create_app
    from config import Config
    monkeypatch.setattr(Config,'DATABASE_URL',None)
    client=create_app({'TESTING':True,'SECRET_KEY':'test'*8}).test_client()
    assert client.get('/auth/login').status_code==200
    assert client.get('/explorar').status_code==503
    assert client.post('/api/search',json={}).status_code==503
