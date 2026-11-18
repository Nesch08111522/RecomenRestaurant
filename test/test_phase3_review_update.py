from test_phase3_sources_claims import memory_repo
from models import discovery as model


def test_review_update_reuses_existing_canonical_business(memory_repo):
    row=model.CandidateModel.create({'status':'pending_review','data':{
        'name':'Café Norte','business_type':'cafeteria','address':'Calle 1'},
        'source_url':'https://www.openstreetmap.org/node/1','business_id':8,'branch_id':9})
    result=model.review(row['id'],'approve',5,'Se comprobó la nueva información de la fuente')
    assert result['business_id']==8
    assert result['branch_id']==9
    assert result['status']=='approved'


def test_source_update_does_not_revoke_verified_business_owner(memory_repo):
    proposed={'data':{'name':'Café Norte Nuevo','business_type':'cafeteria','address':'Calle 1'},
        'evidence':{},'channels':{},'menu_links':[],'media':[]}
    row=model.CandidateModel.create({'status':'claimed','owner_id':10,'owner_verified':True,
        'data':{'name':'Café Norte','business_type':'cafeteria','address':'Calle 1'},
        'source_url':'https://www.openstreetmap.org/node/1','business_id':8,'branch_id':9,'proposed_update':proposed})
    updated=model.review(row['id'],'accept_update',5,'Revisado cambio de nombre de la página oficial')
    assert updated['owner_verified'] is True
    approved=model.review(row['id'],'approve',5,'Se aprobó el cambio de los campos de la fuente')
    assert approved['status']=='claimed'
    assert approved['owner_id']==10
