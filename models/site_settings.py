"""Public site metadata. Only explicit, validated fields may be persisted."""
import re
from urllib.parse import urlsplit
from database.repository import PostgresDocumentRepository as Repo, document_transaction

DEFAULTS = dict(brand="SmartResto", tagline="Descubre, disfruta y haz crecer la gastronomía local.", phone="+51976399537", email="", legal_name="", tax_id="", address="", instagram="", facebook="", tiktok="", youtube="")
SOCIAL_HOSTS = {"instagram": {"instagram.com", "www.instagram.com"}, "facebook": {"facebook.com", "www.facebook.com"}, "tiktok": {"tiktok.com", "www.tiktok.com"}, "youtube": {"youtube.com", "www.youtube.com", "youtu.be"}}

def validate_settings(source):
    fields = {}
    for name, default in DEFAULTS.items():
        value = str(source.get(name, default)).strip()
        if len(value) > (300 if name in SOCIAL_HOSTS else 180):
            raise ValueError("Un campo supera la longitud permitida.")
        if any(ord(c) < 32 for c in value):
            raise ValueError("El texto contiene caracteres no permitidos.")
        fields[name] = value
    if not fields["brand"] or not re.fullmatch(r"\+[1-9]\d{7,14}", fields["phone"]):
        raise ValueError("Indica el nombre y un teléfono internacional, por ejemplo +51976399537.")
    if fields["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", fields["email"]):
        raise ValueError("Revisa el correo de contacto.")
    if fields["tax_id"] and not re.fullmatch(r"\d{11}", fields["tax_id"]):
        raise ValueError("El RUC debe tener 11 dígitos.")
    for name, hosts in SOCIAL_HOSTS.items():
        if fields[name]:
            try:
                url = urlsplit(fields[name])
                port = url.port
            except ValueError:
                raise ValueError("Revisa el enlace de " + name + ".") from None
            if url.scheme != "https" or url.hostname not in hosts or url.username or url.password or port not in (None,443):
                raise ValueError("Usa un enlace HTTPS oficial para " + name + ".")
    return fields

def site_settings():
    return {**DEFAULTS, **{k:v for k,v in (Repo.get_by_id("site_settings",1) or {}).items() if k in DEFAULTS}}

def save_site_settings(source):
    fields = validate_settings(source)
    with document_transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('smartresto-site-settings',0))")
        if not Repo.update("site_settings",1,fields):
            Repo.create("site_settings",{"id":1,**fields})
    return fields
