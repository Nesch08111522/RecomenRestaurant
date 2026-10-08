# logic/recommender.py
import threading
from pyDatalog import pyDatalog
import sys
import logging

logger = logging.getLogger(__name__)

# ============================================
# CONFIGURACIÓN GLOBAL DE PYDATALOG
# ============================================

# Definir términos una sola vez a nivel global
if not hasattr(pyDatalog, '_terms_defined'):
    pyDatalog.create_terms(
        'restaurante, usuario, excluido, recomendado, justificacion, '
        'tiene_opcion_vegana, tiene_opcion_sin_gluten, tiene_opcion_vegetariana, '
        'rating, has_promo, X, Y, Z, J, R'
    )
    pyDatalog._terms_defined = True

# Candado para sincronizar el acceso a la lógica
datalog_lock = threading.Lock()
_engine_initialized = False

# ============================================
# RECOMMENDER ENGINE (SINGLETON)
# ============================================

class RecommenderEngine:
    """Motor de recomendación usando pyDatalog (Singleton)"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RecommenderEngine, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with datalog_lock:
                self._initialize_engine()
            self._initialized = True
    
    def _initialize_engine(self):
        """Inicializa el motor de pyDatalog con las reglas"""
        global _engine_initialized
        
        if _engine_initialized:
            return
        
        try:
            # Limpiar cualquier regla anterior
            pyDatalog.clear()
            
            # Definir reglas
            self._define_rules()
            _engine_initialized = True
            logger.info("✅ pyDatalog inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando pyDatalog: {e}")
            try:
                pyDatalog.clear()
                self._define_rules()
                _engine_initialized = True
            except Exception as e2:
                logger.error(f"❌ Error en reintento de inicialización: {e2}")

    def _define_rules(self):
        """Define las reglas lógicas de pyDatalog"""
        try:
            # ============================================
            # REGLAS DE EXCLUSIÓN (Restricciones alimenticias)
            # ============================================
            
            # Usuario vegano y restaurante no tiene opciones veganas
            excluido(X, Y) <= (usuario(Y, 'vegano') & ~tiene_opcion_vegana(X))
            
            # Usuario vegetariano y restaurante no tiene opciones vegetarianas
            excluido(X, Y) <= (usuario(Y, 'vegetariano') & ~tiene_opcion_vegetariana(X))
            
            # Usuario celiaco y restaurante no tiene opciones sin gluten
            excluido(X, Y) <= (usuario(Y, 'celiaco') & ~tiene_opcion_sin_gluten(X))

            # ============================================
            # REGLAS DE RECOMENDACIÓN POSITIVA
            # ============================================
            
            # Si el restaurante tiene rating >= 4.5
            justificacion(X, Y, 'Altamente valorado por la comunidad') <= (rating(X, R) & (R >= 4.5))
            
            # Si el restaurante tiene promoción activa
            justificacion(X, Y, 'Tiene promociones especiales hoy') <= (has_promo(X, 'si'))
            
            # Si el restaurante tiene rating entre 4.0 y 4.5
            justificacion(X, Y, 'Excelente relación calidad-precio') <= (rating(X, R) & (R >= 4.0) & (R < 4.5))
            
            # Si el restaurante tiene opciones veganas
            justificacion(X, Y, 'Ofrece opciones veganas') <= (tiene_opcion_vegana(X, 'si'))
            
            # Si el restaurante tiene opciones vegetarianas
            justificacion(X, Y, 'Ofrece opciones vegetarianas') <= (tiene_opcion_vegetariana(X, 'si'))
            
            # Si el restaurante tiene opciones sin gluten
            justificacion(X, Y, 'Ofrece opciones sin gluten') <= (tiene_opcion_sin_gluten(X, 'si'))
            
        except Exception as e:
            logger.error(f"Error definiendo reglas: {e}")
            raise

    def _clear_facts_for(self, r_id, u_id):
        """Limpia los hechos específicos para un restaurante y usuario"""
        facts_to_clear = [
            ('rating', r_id),
            ('tiene_opcion_vegana', r_id),
            ('tiene_opcion_vegetariana', r_id),
            ('tiene_opcion_sin_gluten', r_id),
            ('has_promo', r_id),
            ('usuario', u_id)
        ]
        
        for fact_name, entity_id in facts_to_clear:
            try:
                pyDatalog.retract_fact(fact_name, entity_id, None)
            except Exception:
                pass

    def _assert_fact_safe(self, fact_name, *args):
        """Asegura que un hecho se inserte de manera segura"""
        try:
            pyDatalog.assert_fact(fact_name, *args)
        except Exception as e:
            logger.warning(f"Error insertando hecho {fact_name}: {e}")
            try:
                pyDatalog.retract_fact(fact_name, args[0], None)
                pyDatalog.assert_fact(fact_name, *args)
            except Exception:
                pass

    def evaluate(self, restaurant_data, user_profile):
        """
        Evalúa si un restaurante es compatible con un usuario.
        
        Args:
            restaurant_data: Diccionario con datos del restaurante
            user_profile: Diccionario con datos del usuario
        
        Returns:
            tuple: (is_compatible, list_of_justifications)
        """
        with datalog_lock:
            r_id = restaurant_data.get('id', 0)
            u_id = user_profile.get('id', 999)
            
            # Limpiar hechos anteriores
            self._clear_facts_for(r_id, u_id)
            
            try:
                # --- Insertar hechos del restaurante ---
                rating = restaurant_data.get('rating', 0)
                self._assert_fact_safe('rating', r_id, rating)
                
                # Restricciones dietéticas
                dietary = restaurant_data.get('dietary_restrictions', [])
                if not isinstance(dietary, list):
                    dietary = []
                
                tiene_vegano = 'si' if any(t in ['vegano', 'opción vegana', 'vegan'] for t in dietary) else 'no'
                tiene_vegetariano = 'si' if any(t in ['vegetariano', 'opción vegetariana', 'vegetarian'] for t in dietary) else 'no'
                tiene_gluten = 'si' if any(t in ['sin gluten', 'gluten_free', 'celiaco'] for t in dietary) else 'no'
                
                self._assert_fact_safe('tiene_opcion_vegana', r_id, tiene_vegano)
                self._assert_fact_safe('tiene_opcion_vegetariana', r_id, tiene_vegetariano)
                self._assert_fact_safe('tiene_opcion_sin_gluten', r_id, tiene_gluten)
                
                # Promociones
                tiene_promo = 'si' if restaurant_data.get('promo') is not None else 'no'
                self._assert_fact_safe('has_promo', r_id, tiene_promo)
                
                # --- Insertar hechos del usuario ---
                restrictions = user_profile.get('restrictions', [])
                if not isinstance(restrictions, list):
                    restrictions = []
                
                if not restrictions:
                    self._assert_fact_safe('usuario', u_id, 'ninguna')
                else:
                    for restriction in restrictions:
                        if restriction in ['vegano', 'vegan']:
                            self._assert_fact_safe('usuario', u_id, 'vegano')
                        elif restriction in ['vegetariano', 'vegetarian']:
                            self._assert_fact_safe('usuario', u_id, 'vegetariano')
                        elif restriction in ['celiaco', 'sin gluten', 'gluten free']:
                            self._assert_fact_safe('usuario', u_id, 'celiaco')
                        else:
                            self._assert_fact_safe('usuario', u_id, restriction)
                
                # --- Consultar exclusión ---
                try:
                    excluded_results = list(excluido(r_id, u_id))
                    is_excluido = len(excluded_results) > 0
                except Exception:
                    is_excluido = False
                
                # --- Consultar justificaciones ---
                justifications = []
                if not is_excluido:
                    try:
                        just_results = list(justificacion(r_id, u_id, J))
                        justifications = [str(j[0]) for j in just_results if j and len(j) > 0]
                    except Exception:
                        justifications = []
                
                return not is_excluido, justifications
                
            except Exception as e:
                logger.error(f"Error en evaluate: {e}")
                return True, ['No se pudo evaluar completamente']

    def explain(self, restaurant_data, user_profile):
        """
        Explica por qué un restaurante es o no recomendado.
        
        Args:
            restaurant_data: Diccionario con datos del restaurante
            user_profile: Diccionario con datos del usuario
        
        Returns:
            dict: Explicación de la recomendación
        """
        with datalog_lock:
            r_id = restaurant_data.get('id', 0)
            u_id = user_profile.get('id', 999)
            
            # Limpiar hechos anteriores
            self._clear_facts_for(r_id, u_id)
            
            explanation = {
                'compatible': True,
                'reasons': [],
                'exclusions': [],
                'dietary_options': {
                    'vegan': False,
                    'vegetarian': False,
                    'gluten_free': False
                }
            }
            
            try:
                # --- Insertar hechos del restaurante ---
                rating = restaurant_data.get('rating', 0)
                self._assert_fact_safe('rating', r_id, rating)
                
                dietary = restaurant_data.get('dietary_restrictions', [])
                if not isinstance(dietary, list):
                    dietary = []
                
                tiene_vegano = 'si' if any(t in ['vegano', 'opción vegana', 'vegan'] for t in dietary) else 'no'
                tiene_vegetariano = 'si' if any(t in ['vegetariano', 'opción vegetariana', 'vegetarian'] for t in dietary) else 'no'
                tiene_gluten = 'si' if any(t in ['sin gluten', 'gluten_free', 'celiaco'] for t in dietary) else 'no'
                
                explanation['dietary_options'] = {
                    'vegan': tiene_vegano == 'si',
                    'vegetarian': tiene_vegetariano == 'si',
                    'gluten_free': tiene_gluten == 'si'
                }
                
                self._assert_fact_safe('tiene_opcion_vegana', r_id, tiene_vegano)
                self._assert_fact_safe('tiene_opcion_vegetariana', r_id, tiene_vegetariano)
                self._assert_fact_safe('tiene_opcion_sin_gluten', r_id, tiene_gluten)
                self._assert_fact_safe('has_promo', r_id, 'si' if restaurant_data.get('promo') is not None else 'no')
                
                # --- Insertar hechos del usuario ---
                restrictions = user_profile.get('restrictions', [])
                if not isinstance(restrictions, list):
                    restrictions = []
                
                if not restrictions:
                    self._assert_fact_safe('usuario', u_id, 'ninguna')
                else:
                    for restriction in restrictions:
                        if restriction in ['vegano', 'vegan']:
                            self._assert_fact_safe('usuario', u_id, 'vegano')
                        elif restriction in ['vegetariano', 'vegetarian']:
                            self._assert_fact_safe('usuario', u_id, 'vegetariano')
                        elif restriction in ['celiaco', 'sin gluten', 'gluten free']:
                            self._assert_fact_safe('usuario', u_id, 'celiaco')
                        else:
                            self._assert_fact_safe('usuario', u_id, restriction)
                
                # Verificar exclusiones
                try:
                    excluded_results = list(excluido(r_id, u_id))
                    if len(excluded_results) > 0:
                        explanation['compatible'] = False
                        explanation['exclusions'].append('No cumple con tus restricciones dietéticas')
                except Exception:
                    pass
                
                # Si es compatible, obtener justificaciones
                if explanation['compatible']:
                    try:
                        just_results = list(justificacion(r_id, u_id, J))
                        explanation['reasons'] = [str(j[0]) for j in just_results if j and len(j) > 0]
                    except Exception:
                        pass
                    
                    # Si no hay justificaciones, agregar basadas en datos
                    if not explanation['reasons']:
                        if restaurant_data.get('rating', 0) >= 4.5:
                            explanation['reasons'].append('Altamente valorado por la comunidad')
                        if restaurant_data.get('promo'):
                            explanation['reasons'].append('Tiene promociones especiales hoy')
                        if restaurant_data.get('distance_km', 10) <= 1:
                            explanation['reasons'].append('Muy cerca de tu ubicación')
                        if restaurant_data.get('dietary_restrictions'):
                            explanation['reasons'].append('Ofrece opciones dietéticas especiales')
                    
                    if not explanation['reasons']:
                        explanation['reasons'].append('Restaurante disponible para tus preferencias')
                
                return explanation
                
            except Exception as e:
                logger.error(f"Error en explain: {e}")
                return {
                    'compatible': True,
                    'reasons': ['No se pudo evaluar completamente'],
                    'exclusions': [],
                    'dietary_options': {'vegan': False, 'vegetarian': False, 'gluten_free': False}
                }

    def batch_evaluate(self, restaurants, user_profile):
        """
        Evalúa múltiples restaurantes para un usuario.
        
        Args:
            restaurants: Lista de diccionarios de restaurantes
            user_profile: Diccionario con datos del usuario
        
        Returns:
            list: Lista de tuplas (restaurant, is_compatible, justifications)
        """
        results = []
        for restaurant in restaurants:
            is_compatible, justifications = self.evaluate(restaurant, user_profile)
            results.append((restaurant, is_compatible, justifications))
        return results