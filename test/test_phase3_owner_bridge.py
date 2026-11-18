from copy import deepcopy
from app import create_app
from models import discovery as model
from models.user import UserModel
from models.category import CategoryModel
from models.restaurant import RestaurantModel


def test_claimed_business_prefill_checks_actual_owner(monkeypatch):
    user={'id':10,'username':'owner','role':'business_owner','profile':{}}
    monkeypatch.setattr(UserModel,'get_by_id',lambda uid:deepcopy(user))
    monkeypatch.setattr(CategoryModel,'all',lambda:[])
    monkeypatch.setattr(RestaurantModel,'all',lambda:[])
    monkeypatch.setattr(model.CandidateModel,'get_by_id',lambda uid:{'id':uid,'status':'claimed','owner_id':11,'data':{'name':'Otro negocio'},'business_id':8,'branch_id':9})
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32}).test_client()
    with client.session_transaction() as session:
        session['user_id']=10
    assert client.get('/admin/restaurant/new?discovery_candidate_id=7').status_code==404


def test_owner_radar_space_is_not_accessible_to_diner(monkeypatch):
    user={'id':10,'username':'diner','role':'user','profile':{}}
    monkeypatch.setattr(UserModel,'get_by_id',lambda uid:deepcopy(user))
    client=create_app({'TESTING':True,'SECRET_KEY':'x'*32}).test_client()
    with client.session_transaction() as session:
        session['user_id']=10
    assert client.get('/owner/discovery').status_code==403
