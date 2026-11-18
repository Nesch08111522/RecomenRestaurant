from contextlib import contextmanager
from copy import deepcopy
import pytest
from app import create_app
from models import discovery as model
from utils import discovery_sources as sources


@pytest.fixture
def memory_repo(monkeypatch):
    store={}
    class Conn:
        def execute(self,*args,**kwargs):
            return None
    @contextmanager
    def transaction():
        snapshot=deepcopy(store)
        try:
            yield Conn()
        except Exception:
            store.clear(); store.update(snapshot); raise
    def all_rows(collection):
        return deepcopy(list(store.get(collection,{}).values()))
    def create(collection,row):
        rows=store.setdefault(collection,{})
        item={**deepcopy(row),'id':len(rows)+1}; rows[item['id']]=item; return deepcopy(item)
    def get(collection,key,**kwargs):
        return deepcopy(store.get(collection,{}).get(key))
    def update(collection,key,changes):
        store[collection][key].update(deepcopy(changes)); return get(collection,key)
    monkeypatch.setattr(model,'document_transaction',transaction)
    monkeypatch.setattr(model.Repo,'all',all_rows)
    monkeypatch.setattr(model.Repo,'create',create)
    monkeypatch.setattr(model.Repo,'get_by_id',get)
    monkeypatch.setattr(model.Repo,'update',update)
    monkeypatch.setattr(model,'event',lambda *args,**kwargs:None)
    return store


def test_dns_private_address_is_rejected_even_with_public_address(monkeypatch):
    monkeypatch.setattr(sources.socket,'getaddrinfo',lambda *args,**kw:[(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError):
        sources.public_addresses('official.example')


def test_official_source_requires_permission_before_network(monkeypatch):
    monkeypatch.setattr(sources,'request_bytes',lambda *args,**kw:pytest.fail('No debe consultar una fuente sin permiso'))
    with pytest.raises(ValueError):
        sources.official_fetch({'url':'https://official.example','rights':'unknown'})
    with pytest.raises(ValueError):
        sources.official_fetch({'url':'https://www.facebook.com/restaurant','rights':'owner_permission','permission_evidence':'owner-supplied'})


def test_duplicate_ingestion_is_idempotent_and_does_not_publish(memory_repo):
    from logic.business_radar import from_osm
    row=from_osm({'type':'node','id':1,'tags':{'name':'Café Norte','amenity':'cafe'}})
    first=model.ingest([row],1)
    second=model.ingest([row],1)
    assert first['created']==1 and second['updated']==1
    assert len(model.CandidateModel.all())==1
    assert not model.RestaurantModel.all()


def test_invitation_is_hashed_one_time_and_does_not_transfer_owner(memory_repo,monkeypatch):
    app=create_app({'TESTING':True,'SECRET_KEY':'x'*32})
    monkeypatch.setattr(model.UserModel,'get_by_id',lambda uid:{'id':uid,'role':'business_owner','profile':{}})
    row=model.CandidateModel.create({'status':'approved','data':{'name':'Café Norte'},'business_id':1})
    with app.app_context():
        invitation=model.invite(row['id'],10)
        saved=model.InvitationModel.all()[0]
        assert invitation['token'] not in str(saved)
        claim=model.request_claim(invitation['token'],20,'Registro comercial verificable del propietario')
        assert claim['status']=='pending'
        assert model.CandidateModel.get_by_id(row['id'])['status']=='claim_pending'
        assert not model.CandidateModel.get_by_id(row['id']).get('owner_verified')
        with pytest.raises(ValueError):
            model.request_claim(invitation['token'],20,'Registro comercial verificable del propietario')


def test_changed_source_creates_proposal_and_preserves_reviewed_fields(memory_repo):
    from logic.business_radar import from_osm
    row=from_osm({'type':'node','id':1,'tags':{'name':'Café Norte','amenity':'cafe'}})
    model.ingest([row],1)
    current=model.CandidateModel.all()[0]
    model.CandidateModel.update(current['id'],{'status':'approved'})
    changed=from_osm({'type':'node','id':1,'tags':{'name':'Nombre nuevo','amenity':'cafe'}})
    model.ingest([changed],1)
    saved=model.CandidateModel.get_by_id(current['id'])
    assert saved['data']['name']=='Café Norte'
    assert saved['proposed_update']['data']['name']=='Nombre nuevo'
    assert saved['update_pending'] is True
