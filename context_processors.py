# context_processors.py
from config import Config
from models.category import CategoryModel
from flask import session
import logging
from psycopg import OperationalError
from database.connection import DatabaseConnectionError, DatabaseConfigurationError

def inject_globals():
    """Inyecta variables globales en todos los templates"""
    try:
        categories = CategoryModel.all()
    except (OperationalError, DatabaseConnectionError, DatabaseConfigurationError):
        logging.getLogger(__name__).warning("Las categorías no están disponibles temporalmente.")
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
