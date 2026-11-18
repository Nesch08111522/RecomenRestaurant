from utils import discovery_sources as sources


def test_pinned_https_announces_http11_with_custom_tls_context(monkeypatch):
    protocols=[]
    monkeypatch.setattr(sources.ssl.SSLContext,'set_alpn_protocols',lambda self,values:protocols.append(values))
    connection=sources.PinnedHTTPS('official.example','8.8.8.8')
    connection.close()
    assert protocols==[['http/1.1']]
