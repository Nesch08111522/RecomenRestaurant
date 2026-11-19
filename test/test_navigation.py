from copy import deepcopy
from html.parser import HTMLParser
import pytest
from flask import render_template, session
from app import create_app
from models.review import ReviewModel
from models.user import UserModel
from models.favorite import FavoriteModel
from models.restaurant import RestaurantModel
from models.site_settings import DEFAULTS


@pytest.fixture
def app(monkeypatch):
    import app as app_module
    monkeypatch.setattr(RestaurantModel, 'all', lambda: [])
    monkeypatch.setattr(app_module, 'inject_globals', lambda: {
        'website': dict(DEFAULTS), 'categories': [], 'APP_NAME': 'SmartResto',
        'MONEDA': 'S/.', 'CIUDAD': 'Trujillo', 'now_year': 2026,
        'show_public_footer': False, 'editorial_images': {},
    })
    return create_app({'TESTING': True, 'SECRET_KEY': 'navigation-test-key-with-32-characters'})


def test_reviews_are_scoped_and_ordered(monkeypatch):
    rows=[{'id':1,'user_id':7,'created_at':'2026-01-01'},
          {'id':2,'user_id':8,'created_at':'2026-11-01'},
          {'id':3,'user_id':7,'created_at':'2026-02-01'},
          {'id':4,'user_id':7,'created_at':None}]
    monkeypatch.setattr(ReviewModel, '_load_data', lambda: deepcopy(rows))
    assert [r['id'] for r in ReviewModel.get_by_user(7)] == [3,1,4]
    assert ReviewModel.get_by_user(99) == []


@pytest.mark.parametrize('role', ['admin','user'])
def test_sidebar_profile_renders_reviews(app, monkeypatch, role):
    account={'id':7,'username':'test','role':role,'profile':{'name':'Test'}}
    monkeypatch.setattr(UserModel,'get_by_id',lambda uid:deepcopy(account))
    monkeypatch.setattr(FavoriteModel,'get_by_user',lambda uid:[])
    monkeypatch.setattr(ReviewModel,'_load_data',lambda:[
        {'user_id':7,'restaurant_id':12,'rating':5,'comment':'Mi reseña de prueba'},
        {'user_id':8,'restaurant_id':12,'rating':2,'comment':'Reseña privada ajena'}])
    client=app.test_client()
    with client.session_transaction() as state:
        state['user_id']=7
    response=client.get('/auth/profile')
    assert response.status_code == 200
    assert 'Mi reseña de prueba' in response.get_data(as_text=True)
    assert 'Reseña privada ajena' not in response.get_data(as_text=True)


class SidebarLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside=False; self.links=[]; self.forms=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='nav' and attrs.get('id')=='sr-navigation': self.inside=True
        if self.inside and tag=='a': self.links.append(attrs['href'])
        if self.inside and tag=='form': self.forms.append((attrs['action'],attrs.get('method','get')))
    def handle_endtag(self, tag):
        if tag=='nav': self.inside=False


@pytest.mark.parametrize('role',['admin','business_owner','user','guest'])
def test_every_sidebar_target_is_registered(app, role):
    with app.test_request_context('/'):
        if role!='guest':
            session['user']={'id':7,'username':'test','role':role,'profile':{'name':'Test'}}
        parser=SidebarLinks(); parser.feed(render_template('partials/header.html'))
        adapter=app.url_map.bind('localhost')
        assert parser.links
        for url in parser.links:
            assert url.startswith('/') and url != '#'
            adapter.match(url,method='GET')
        for url, method in parser.forms:
            endpoint, _ = adapter.match(url,method=method.upper())
            assert endpoint == 'auth.logout'
            assert method.lower() == 'post'
