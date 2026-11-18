from copy import deepcopy
from app import create_app
from database.connection import DatabaseConnectionError
from models.category import CategoryModel
from models.user import UserModel
from models.favorite import FavoriteModel


def test_login_still_renders_on_transient_database_connection_failure(monkeypatch):
    def unavailable():
        raise DatabaseConnectionError('safe-network-diagnostic')
    monkeypatch.setattr(CategoryModel, 'all', unavailable)
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32}).test_client()
    response=client.get('/auth/login')
    assert response.status_code==200
    assert b'safe-network-diagnostic' not in response.data


def test_favorites_api_uses_flask_session_not_unconfigured_login_manager(monkeypatch):
    account={'id':61,'username':'test','role':'user','profile':{'name':'Test'}}
    monkeypatch.setattr(UserModel,'get_by_id',lambda uid:deepcopy(account) if uid==61 else None)
    monkeypatch.setattr(FavoriteModel,'get_by_user',lambda uid:[{'restaurant_id':17,'user_id':61}])
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32}).test_client()
    anonymous=client.get('/auth/api/favorites')
    assert anonymous.status_code==401
    assert anonymous.is_json
    with client.session_transaction() as session:
        session['user_id']=61
    response=client.get('/auth/api/favorites')
    assert response.status_code==200
    assert response.json['favorites']==[{'restaurant_id':17,'user_id':61}]
