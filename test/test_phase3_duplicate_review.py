from test_phase3_sources_claims import memory_repo
from models import discovery as model


def test_admin_can_mark_close_by_branches_as_distinct(memory_repo):
    row=model.CandidateModel.create({'status':'duplicate','duplicate_of':{'kind':'candidate','id':3},
        'data':{'name':'Café Norte','business_type':'cafeteria','address':'Segundo piso'}})
    result=model.review(row['id'],'mark_distinct',5,'Son dos sucursales en pisos distintos, con evidencia independiente')
    assert result['status']=='pending_review'
    assert not result.get('duplicate_of')
    assert result['duplicate_reviewed_by']==5
