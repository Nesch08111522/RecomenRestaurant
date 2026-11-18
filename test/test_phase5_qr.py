import importlib.util
import pytest


def test_qr_svg_uses_explicit_origin_not_request_host(monkeypatch):
    assert importlib.util.find_spec('utils.catalog_qr') is not None
    from utils.catalog_qr import build_table_qr
    monkeypatch.setenv('SMARTRESTO_PUBLIC_ORIGIN','https://mi-negocio.example')
    content,url=build_table_qr('a'*32)
    assert b'<svg' in content and url=='https://mi-negocio.example/catalog/qr/'+'a'*32
    with pytest.raises(ValueError):build_table_qr('../bad')
