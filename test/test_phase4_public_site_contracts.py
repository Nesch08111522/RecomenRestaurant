from pathlib import Path
import re
from urllib.parse import urlsplit

import models.business_site as business_site
from models.business_site import default_site, normalize_site


def test_whatsapp_social_link_is_preserved_by_site_normalization(monkeypatch):
    monkeypatch.setattr(business_site, "validate_source_url", urlsplit)
    base = default_site({"id": 7, "name": "Café Norte"})
    saved = normalize_site({"social": {"whatsapp": "https://wa.me/51999999999"}}, base)
    assert saved["social"] == {"whatsapp": "https://wa.me/51999999999"}


def test_public_site_renders_validated_social_links():
    source = (Path(__file__).resolve().parents[1] / "templates/sites/public.html").read_text(encoding="utf-8")
    assert "site.get('social', {}).items()" in source
    assert 'target="_blank" rel="noopener noreferrer"' in source
    assert "class=\"bs-social-links\"" in source


def test_site_logo_upload_does_not_advertise_unsupported_svg():
    source = (Path(__file__).resolve().parents[1] / "templates/sites/editor.html").read_text(encoding="utf-8")
    upload = re.search(r'<input[^>]*data-logo-input[^>]*>', source)
    assert upload, "No se encontró el control de carga de logo"
    assert "image/svg+xml" not in upload.group(0)
    assert "PNG, JPG o WebP" in source


def test_immersive_hero_video_is_user_controlled_and_not_autoplayed():
    source = (Path(__file__).resolve().parents[1] / "templates/sites/public.html").read_text(encoding="utf-8")
    match = re.search(r'<video\b[^>]*class="bs-hero-video"[^>]*>', source)
    assert match, "No se encontró el vídeo de portada inmersivo"
    tag = match.group(0)
    assert "controls" in tag
    assert 'preload="none"' in tag
    assert not re.search(r"\bautoplay\b|\bloop\b", tag)
