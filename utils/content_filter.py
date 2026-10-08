# utils/content_filter.py
import re
from typing import Dict, List, Tuple, Any

class ContentFilter:
    """Filtro de contenido para detectar palabras inapropiadas y contenido no relacionado con comida"""
    
    # Palabras prohibidas (puedes expandir esta lista)
    BANNED_WORDS = [
        'muerte', 'muerto', 'matar', 'asesino', 'violencia', 'arma',
        'pistola', 'droga', 'cocaína', 'heroína', 'marihuana',
        'sexo', 'porno', 'puta', 'zorra', 'maldito', 'malparido',
        'odio', 'racismo', 'discriminación', 'suicidio', 'sangre',
        'incesto', 'pedofilia', 'violación', 'terrorismo', 'nazi',
        'hitler', 'genocidio', 'matanza', 'mata', 'asesinato'
    ]
    
    # ✅ Palabras relacionadas con comida (expandida)
    FOOD_WORDS = [
        # Tipos de comida
        'restaurante', 'comida', 'cocina', 'chef', 'plato', 'menú',
        'carta', 'mesa', 'servicio', 'reserva', 'delicioso', 'sabroso',
        'ingrediente', 'receta', 'gourmet', 'tradicional', 'casero',
        'desayuno', 'almuerzo', 'cena', 'postre', 'bebida',
        'carne', 'pescado', 'marisco', 'verdura', 'fruta',
        'queso', 'pasta', 'pizza', 'sushi', 'taco', 'ceviche',
        
        # Categorías de restaurantes
        'parrilla', 'pollería', 'cevichería', 'chifa', 'criollo',
        'norteño', 'italiana', 'japonesa', 'mexicana', 'saludable',
        'café', 'mariscos', 'tacos', 'vinos', 'tragos',
        
        # Términos culinarios
        'cabrito', 'arroz', 'frijoles', 'cebolla', 'ají', 'limón',
        'pescado', 'mariscos', 'camarones', 'pulpo', 'caldo',
        'sopa', 'ensalada', 'guiso', 'tallarín', 'lomo',
        'saltado', 'chaufa', 'rocoto', 'quinua', 'jugos',
        
        # Términos de servicio
        'delivery', 'wifi', 'parking', 'terraza', 'reservas',
        'estacionamiento', 'barra', 'música en vivo', 'pet friendly',
        'familia', 'amigos', 'pareja', 'romántico', 'negocios',
        
        # Bebidas
        'chicha', 'pisco', 'sour', 'jugo', 'refresco', 'cerveza',
        'vino', 'té', 'café', 'capuchino', 'latte',
        
        # Comida en general
        'comer', 'almorzar', 'cenar', 'degustar', 'sabor', 'aroma',
        'fresco', 'casero', 'auténtico', 'especial', 'fusión',
        'tradición', 'calidad', 'precio', 'menu', 'carta',
        'entrada', 'fondo', 'postre', 'bebida', 'acompañamiento'
    ]
    
    @classmethod
    def check_content(cls, text: str) -> Dict[str, Any]:
        """
        Verifica si el contenido es apropiado y relacionado con comida.
        Retorna: {
            'is_appropriate': bool,
            'is_food_related': bool,
            'banned_words': list,
            'food_score': float,
            'suggestions': list
        }
        """
        if not text:
            return {
                'is_appropriate': True,
                'is_food_related': False,
                'banned_words': [],
                'food_score': 0,
                'suggestions': ['El contenido está vacío']
            }
        
        text_lower = text.lower()
        
        # 1. Buscar palabras prohibidas
        banned_found = []
        for word in cls.BANNED_WORDS:
            # Buscar la palabra como palabra completa o como parte de una palabra
            if word in text_lower:
                banned_found.append(word)
        
        is_appropriate = len(banned_found) == 0
        
        # 2. Verificar si está relacionado con comida
        food_words_found = []
        for word in cls.FOOD_WORDS:
            if word in text_lower:
                food_words_found.append(word)
        
        # Calcular puntuación basada en la cantidad de palabras de comida encontradas
        # y la longitud del texto
        text_words = len(text.split())
        if text_words > 0:
            food_score = min(100, (len(food_words_found) / max(3, text_words)) * 100)
        else:
            food_score = 0
        
        # 3. Generar sugerencias
        suggestions = []
        if banned_found:
            suggestions.append(f"Contiene palabras inapropiadas: {', '.join(banned_found)}")
        
        # Si el texto tiene más de 5 palabras y no tiene palabras de comida
        if text_words > 5 and food_score < 15:
            suggestions.append("El contenido parece no estar relacionado con comida. Verifica que hable sobre restaurantes, platos o servicios culinarios.")
        
        if not suggestions and food_score > 20:
            suggestions.append("Contenido relacionado con comida verificado correctamente.")
        
        is_food_related = food_score > 15
        
        return {
            'is_appropriate': is_appropriate,
            'is_food_related': is_food_related,
            'banned_words': banned_found,
            'food_score': round(food_score, 2),
            'food_words_found': food_words_found[:5],  # Mostrar primeras 5 palabras encontradas
            'suggestions': suggestions
        }
    
    @classmethod
    def filter_restaurant(cls, restaurant_data: Dict) -> Dict[str, Any]:
        """Filtrar un restaurante completo"""
        # Extraer información relevante
        name = restaurant_data.get('name', '')
        description = restaurant_data.get('description', '')
        tags = restaurant_data.get('tags', [])
        address = restaurant_data.get('address', '')
        
        # Combinar todo el texto para una verificación general
        full_text = f"{name} {description} {' '.join(tags)} {address}"
        
        # Verificar el texto completo
        result = cls.check_content(full_text)
        
        # Verificar cada tag individualmente
        tag_results = []
        for tag in tags:
            tag_result = cls.check_content(tag)
            tag_results.append({
                'tag': tag,
                'is_appropriate': tag_result['is_appropriate'],
                'is_food_related': tag_result['is_food_related']
            })
        
        # Determinar si el restaurante es apropiado en general
        overall_appropriate = result['is_appropriate']
        overall_food_related = result['is_food_related']
        
        issues = []
        if not result['is_appropriate']:
            issues.append(f"Contenido inapropiado: {', '.join(result['banned_words'])}")
        if not result['is_food_related']:
            issues.append("Contenido no relacionado con comida")
        
        # Verificar tags
        for tag_res in tag_results:
            if not tag_res['is_appropriate']:
                issues.append(f"Tag inapropiado: {tag_res['tag']}")
            if not tag_res['is_food_related']:
                # No considerar tags de servicio como no relacionados con comida
                service_tags = ['delivery', 'wifi', 'parking', 'terraza', 'reservas', 'estacionamiento', 'barra']
                if tag_res['tag'].lower() not in service_tags:
                    issues.append(f"Tag no relacionado con comida: {tag_res['tag']}")
        
        return {
            'name': name,
            'description': description,
            'tags': tag_results,
            'result': result,
            'overall_appropriate': overall_appropriate,
            'overall_food_related': overall_food_related,
            'issues': issues,
            'is_ok': overall_appropriate and overall_food_related and len(issues) == 0
        }