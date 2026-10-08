import sys
import os
import unittest

# Añadir el directorio raíz al path para poder importar los módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models.restaurant import RestaurantModel
from utils.functional import filter_restaurants
from logic.recommender import RecommenderEngine

class SmokeTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.recommender = RecommenderEngine()

    def test_home_page(self):
        """Verificar que la home carga correctamente"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_api_search(self):
        """Verificar que el API de búsqueda funciona"""
        response = self.client.post('/api/search', json={'district': 'Huanchaco'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)

    def test_functional_filter(self):
        """Verificar filtros funcionales"""
        restaurants = RestaurantModel.all()
        if restaurants:  # Solo si hay datos
            filtered = filter_restaurants(restaurants, {'category_id': 1})
            for r in filtered:
                self.assertEqual(r.get('category_id'), 1)

    def test_logic_engine(self):
        """Verificar motor lógico"""
        restaurant = {
            'id': 99, 
            'rating': 4.8, 
            'category_id': 1, 
            'promo': '10% de descuento', 
            'dietary_restrictions': ['sin gluten']
        }
        user_profile = {
            'id': 999,
            'restrictions': ['celiaco'],
            'preferences': ['saludable']
        }
        is_compatible, justifications = self.recommender.evaluate(restaurant, user_profile)
        self.assertTrue(is_compatible)
        # Verificar que hay justificaciones o que el restaurante es compatible
        self.assertIsInstance(justifications, list)

    def test_explain_method(self):
        """Verificar método explain"""
        restaurant = {
            'id': 100, 
            'rating': 4.9, 
            'category_id': 6, 
            'promo': '20% de descuento', 
            'dietary_restrictions': ['vegano']
        }
        user_profile = {
            'id': 1000,
            'restrictions': ['vegano'],
            'preferences': ['vegano', 'saludable']
        }
        explanation = self.recommender.explain(restaurant, user_profile)
        self.assertIsInstance(explanation, dict)
        self.assertIn('compatible', explanation)
        self.assertIn('reasons', explanation)

if __name__ == '__main__':
    unittest.main()