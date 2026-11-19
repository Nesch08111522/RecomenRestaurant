# context_processors.py
from config import Config
from models.category import CategoryModel
from flask import session, request
from models.site_settings import site_settings

def inject_globals():
    """Inyecta variables globales en todos los templates"""
    categories = CategoryModel.all()
    website = site_settings()
    role = (session.get("user") or {}).get("role")
    internal = role in {"admin", "business_owner"} and request.blueprint not in {"main", "food_experience", "recommendations"} and request.endpoint != "sites.public_page"
    from pathlib import Path
    from datetime import date
    editorial = {}
    for view, fallback in [("home","lomo"),("offers","ceviche"),("business","signature")]:
        filename = "images/editorial/" + view + ".webp"
        editorial[view] = "/static/" + filename if (Path(__file__).parent / "static" / filename).is_file() else "/static/images/auth/" + fallback + ".webp"
    return {
        'APP_NAME': website['brand'],
        'website': website,
        'editorial_images': editorial,
        'now_year': date.today().year,
        'show_public_footer': not internal,
        'PRIMARY_COLOR': Config.PALETA_PRIMARIA,
        'SECONDARY_COLOR': Config.PALETA_SECUNDARIA,
        'MONEDA': Config.MONEDA,
        'CIUDAD': Config.CIUDAD,
        'CENTER_COORDS': Config.COORDENADAS_CENTRO,
        'RADIO_MAXIMO_KM': Config.RADIO_MAXIMO_KM,
        'categories': categories,
        'session': session
    }
