import pytest
from app import create_app
from models.restaurant import RestaurantModel
from models.category import CategoryModel
from models.user import UserModel

@pytest.mark.parametrize('role',['admin','business_owner'])
def test_management_handles_unknown_and_overnight_hours(monkeypatch,role):
    user={'id':7,'username':'test','role':role,'profile':{}}
    monkeypatch.setattr(UserModel,'get_by_id',lambda uid:user)
    rows=[{'id':1,'name':'Sin horario','owner_id':7},{'id':2,'name':'Nocturno','owner_id':7,'open_time':'20:00','close_time':'02:00'}]
    monkeypatch.setattr(RestaurantModel,'all',lambda:rows)
    monkeypatch.setattr(CategoryModel,'all',lambda:[])
    monkeypatch.setattr('context_processors.site_settings',lambda:{'brand':'SmartResto'})
    app=create_app({'TESTING':True,'SECRET_KEY':'test-hours'})
    with app.test_client() as client:
        with client.session_transaction() as s:s['user_id']=7
        response=client.get('/admin/restaurants')
        assert response.status_code==200
        assert 'Sin horario' in response.get_data(as_text=True)
