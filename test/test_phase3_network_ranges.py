import pytest
from utils import discovery_sources as sources
from logic.business_radar import validate_source_url


@pytest.mark.parametrize('address',['224.0.0.1','ff02::1','0.0.0.0','240.0.0.1'])
def test_non_unicast_addresses_are_rejected(monkeypatch,address):
    monkeypatch.setattr(sources.socket,'getaddrinfo',lambda *args,**kw:[(2,1,6,'',(address,443))])
    with pytest.raises(ValueError):
        sources.public_addresses('official.example')
