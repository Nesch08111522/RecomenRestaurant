# context_processors.py
from config import Config
from models.category import CategoryModel
from flask import session

def inject_globals():
    """Inyecta variables globales en todos los templates"""
    categories = CategoryModel.all()
    
    return {
        'APP_NAME': Config.NOMBRE_APP,
        'PRIMARY_COLOR': Config.PALETA_PRIMARIA,
        'SECONDARY_COLOR': Config.PALETA_SECUNDARIA,
        'MONEDA': Config.MONEDA,
        'CIUDAD': Config.CIUDAD,
        'CENTER_COORDS': Config.COORDENADAS_CENTRO,
        'RADIO_MAXIMO_KM': Config.RADIO_MAXIMO_KM,
        'categories': categories,
        'session': session
    }
