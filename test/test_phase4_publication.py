import pytest
from test_phase3_sources_claims import memory_repo
from models import business_site as site
from models import discovery


@pytest.fixture
def repo(memory_repo,monkeypatch):
    monkeypatch.setattr(site,'document_transaction',discovery.document_transaction)
    monkeypatch.setattr(site,'record_event',lambda *a,**kw:None)
    return memory_repo


def test_draft_changes_do_not_change_public_snapshot(repo):
    business={'id':1,'owner_id':5,'name':'Café Norte','verified':True}
    site.save_draft(business,{'rights_confirmed':True},5)
    public=site.publish(business,5)
    site.save_draft(business,{'tagline':'Nuevo borrador'},5)
    stored=site.find_site(1)
    assert stored['draft']['tagline']=='Nuevo borrador'
    assert stored['published']['tagline']==''
    site.publish(business,5,False)
    assert site.find_site(1)['published'] is None


def test_unverified_business_cannot_publish(repo):
    business={'id':1,'name':'Café Norte','verified':False}
    site.save_draft(business,{'rights_confirmed':True},5)
    with pytest.raises(ValueError):site.publish(business,5)
    assert site.find_site(1)['published'] is None


def test_custom_slug_cannot_take_another_business_address(repo):
    site.save_draft({'id':1,'name':'Uno'},{'slug':'mi-cafe'},5)
    with pytest.raises(ValueError):site.save_draft({'id':2,'name':'Dos'},{'slug':'mi-cafe'},6)
