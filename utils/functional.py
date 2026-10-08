from functools import reduce
from utils.geo import calculate_distance, normalize_coordinates

def filter_restaurants(restaurants, filters):
    """
    Aplica múltiples filtros a la lista de restaurantes.
    Paradigma: Funcional.
    """
    if not restaurants:
        return []
    
    filtered = restaurants
    
    if filters.get('category_id'):
        try:
            cat_id = int(filters['category_id'])
            filtered = list(filter(lambda r: r.get('category_id') == cat_id, filtered))
        except (ValueError, TypeError):
            pass
        
    if filters.get('district'):
        filtered = list(filter(lambda r: r.get('district', '').lower() == filters['district'].lower(), filtered))
        
    if filters.get('max_price'):
        try:
            max_price = float(filters['max_price'])
            filtered = list(filter(lambda r: r.get('avg_price', 0) <= max_price, filtered))
        except (ValueError, TypeError):
            pass
        
    if filters.get('min_rating'):
        try:
            min_rating = float(filters['min_rating'])
            filtered = list(filter(lambda r: r.get('rating', 0) >= min_rating, filtered))
        except (ValueError, TypeError):
            pass
        
    if filters.get('has_promo'):
        filtered = list(filter(lambda r: r.get('promo') is not None, filtered))
        
    if filters.get('dietary_tags'):
        tags = filters['dietary_tags']
        if isinstance(tags, list):
            filtered = list(filter(lambda r: any(t in r.get('dietary_restrictions', []) for t in tags), filtered))
        
    if filters.get('search_query'):
        query = filters['search_query'].lower()
        filtered = list(filter(lambda r: query in r.get('name', '').lower() or 
                              query in r.get('description', '').lower() or
                              any(query in tag.lower() for tag in r.get('tags', [])), filtered))
        
    return filtered

def score_restaurant(restaurant, user_lat, user_lng, user_profile):
    """
    Calcula un score de 0 a 100 para un restaurante.
    Paradigma: Funcional.
    """
    # 1. Rating normalizado (0-5 -> 0-100) * 0.4
    rating = restaurant.get('rating', 0)
    rating_score = (rating / 5.0) * 100 * 0.4
    
    # 2. Distancia inversa (peso 0.3)
    dist = calculate_distance(user_lat, user_lng, restaurant.get('lat'), restaurant.get('lng'))
    # Si está a 0km -> 100, si está a 10km o más -> 0
    dist_score = max(0, (10 - dist) / 10) * 100 * 0.3
    
    # 3. Coincidencia de preferencias (peso 0.2)
    pref_match = 0
    user_prefs = user_profile.get('preferences', [])
    tags = restaurant.get('tags', [])
    if user_prefs and tags:
        if any(pref.lower() in [tag.lower() for tag in tags] for pref in user_prefs):
            pref_match = 100 * 0.2
        
    # 4. Promoción (peso 0.1)
    promo_score = (100 if restaurant.get('promo') else 0) * 0.1
    
    return round(rating_score + dist_score + pref_match + promo_score, 2)

def rank_restaurants(restaurants, user_lat, user_lng, user_profile):
    """
    Ordena restaurantes por score descendente.
    Paradigma: Funcional.
    """
    return sorted(
        restaurants, 
        key=lambda r: score_restaurant(r, user_lat, user_lng, user_profile), 
        reverse=True
    )

def enrich_with_metadata(restaurants, user_lat, user_lng):
    """
    Añade metadatos calculados a cada restaurante.
    Paradigma: Funcional.
    """
    def enrich_single(r):
        lat = r.get('lat')
        lng = r.get('lng')
        distance = calculate_distance(user_lat, user_lng, lat, lng)
        enriched = {**r, 'distance_km': distance}
        # No se inventa disponibilidad horaria: solo se conserva si una fuente
        # previa la calculó de forma explícita.
        if 'is_open_now' in r:
            enriched['is_open_now'] = bool(r['is_open_now'])
        return enriched
    
    return list(map(enrich_single, restaurants)) if restaurants else []

def get_statistics(restaurants):
    """
    Calcula estadísticas agregadas.
    Paradigma: Funcional.
    """
    if not restaurants:
        return {}
    
    total_count = len(restaurants)
    avg_price = reduce(lambda x, y: x + y, [r.get('avg_price', 0) for r in restaurants]) / total_count
    avg_rating = reduce(lambda x, y: x + y, [r.get('rating', 0) for r in restaurants]) / total_count
    
    return {
        'total_count': total_count,
        'avg_price': round(avg_price, 2),
        'avg_rating': round(avg_rating, 2)
    }