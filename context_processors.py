# context_processors.py
from config import Config
import json
import os
from flask import session

def inject_globals():
    """Inyecta variables globales en todos los templates"""
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        try:
            with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except Exception as e:
            print(f"Error cargando categorías: {e}")
            categories = []
    
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