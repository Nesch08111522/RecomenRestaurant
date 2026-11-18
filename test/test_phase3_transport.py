from utils import discovery_sources as sources


def test_http_prefers_validated_ipv4_without_second_dns_lookup(monkeypatch):
    selected=[]
    monkeypatch.setattr(sources,'public_addresses',lambda host:['2606:4700:4700::1111','8.8.8.8'])
    class Response:
        status=200
        def getheader(self,name,default=None):
            return 'application/json' if name=='Content-Type' else default
        def read(self,limit):
            return b'{}'
    class Connection:
        def __init__(self,host,address):
            selected.append(address)
        def request(self,*args,**kwargs):
            pass
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setattr(sources,'PinnedHTTPS',Connection)
    assert sources.request_bytes('https://official.example')[0]==200
    assert selected==['8.8.8.8']
