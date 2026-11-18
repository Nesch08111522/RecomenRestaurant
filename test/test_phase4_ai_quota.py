import pytest
from test_phase3_sources_claims import memory_repo
from test_phase4_publication import repo
from models import business_site as service


def test_paid_ai_quota_is_persistent_per_user(repo):
    assert hasattr(service,'consume_ai_quota'),'Falta cuota persistente del proveedor pagado'
    service.consume_ai_quota(5,clock=1000)
    with pytest.raises(ValueError):service.consume_ai_quota(5,clock=1001)
    service.consume_ai_quota(6,clock=1001)
    for index in range(1,20):service.consume_ai_quota(5,clock=1000+index*30)
    with pytest.raises(ValueError):service.consume_ai_quota(5,clock=1700)
    service.consume_ai_quota(5,clock=5000)
