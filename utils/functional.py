from functools import reduce
from utils.geo import calculate_distance, normalize_coordinates

def filter_restaurants(restaurants, filters):
    """
    Aplica múltiples filtros a la lista de restaurantes.
    Paradigma: Funcional.
    """
    from datetime import datetime, timedelta, timezone
    import math
    from logic.market import key

    filtered = [dict(r) for r in restaurants]
    clock = filters.get('at_time') or datetime.now(timezone(timedelta(hours=-5))).strftime('%H:%M')
    try:
        datetime.strptime(clock, '%H:%M')
    except (TypeError, ValueError):
        raise ValueError('Horario invalido')
    for row in filtered:
        opening, closing = row.get('open_time'), row.get('close_time')
        row['is_open_now'] = None
        if opening and closing:
            try:
                datetime.strptime(opening, '%H:%M')
                datetime.strptime(closing, '%H:%M')
                row['is_open_now'] = (opening <= clock < closing if opening < closing
                                      else clock >= opening or clock < closing)
            except (TypeError, ValueError):
                pass
    for field, source, lower in [('min_price', 'avg_price', True), ('max_price', 'avg_price', False),
                                  ('min_rating', 'rating', True)]:
        if filters.get(field) is not None:
            try:
                value = float(filters[field])
            except (TypeError, ValueError):
                raise ValueError('Filtro numerico invalido')
            if not math.isfinite(value) or value < 0 or (field == 'min_rating' and value > 5):
                raise ValueError('Filtro numerico fuera de rango')
            filtered = [r for r in filtered if isinstance(r.get(source), (int, float))
                        and (r[source] >= value if lower else r[source] <= value)]
    if filters.get('category_ids'):
        ids = filters['category_ids']
        if not isinstance(ids, list):
            raise ValueError('Categorias invalidas')
        filtered = [r for r in filtered if str(r.get('category_id')) in {str(i) for i in ids}]
    if filters.get('business_type'):
        filtered = [r for r in filtered if key(r.get('business_type') or r.get('market_kind') or '') == key(filters['business_type'])]
    if filters.get('channel'):
        filtered = [r for r in filtered if filters['channel'] in r.get('market_channels', [])]
    if filters.get('open_now') or filters.get('at_time'):
        filtered = [r for r in filtered if r['is_open_now'] is True]
    if filters.get('available_only'):
        filtered = [r for r in filtered if r.get('is_available', r.get('available')) is True]
    if filters.get('promo_only'):
        filtered = [r for r in filtered if r.get('promo')]
    if filters.get('keywords'):
        if not isinstance(filters['keywords'], list):
            raise ValueError('Etiquetas invalidas')
        filtered = [r for r in filtered if all(key(t) in {key(v) for v in r.get('tags', [])}
                                               for t in filters['keywords'])]
    origin = normalize_coordinates(filters.get('lat'), filters.get('lng'))
    if filters.get('nearby') or filters.get('radius') is not None:
        if not origin:
            raise ValueError('Se requiere ubicacion para buscar cercanos')
        try:
            radius = float(filters.get('radius', 5))
        except (TypeError, ValueError):
            raise ValueError('Radio invalido')
        if not math.isfinite(radius) or not 0 < radius <= 100:
            raise ValueError('Radio fuera de rango')
        filtered = [r for r in filtered if normalize_coordinates(r.get('lat'), r.get('lng'))
                    and calculate_distance(*origin, r['lat'], r['lng']) <= radius]
    if filters.get('bounds') is not None:
        bounds = filters['bounds']
        if not isinstance(bounds, list) or len(bounds) != 4:
            raise ValueError('Limites geograficos invalidos')
        south_west = normalize_coordinates(*bounds[:2])
        north_east = normalize_coordinates(*bounds[2:])
        if not south_west or not north_east or any(a > b for a, b in zip(south_west, north_east)):
            raise ValueError('Limites geograficos invalidos')
        filtered = [r for r in filtered if normalize_coordinates(r.get('lat'), r.get('lng'))
                    and south_west[0] <= float(r['lat']) <= north_east[0]
                    and south_west[1] <= float(r['lng']) <= north_east[1]]
    
    if filters.get('category_id'):
        try:
            cat_id = int(filters['category_id'])
            filtered = list(filter(lambda r: r.get('category_id') == cat_id, filtered))
        except (ValueError, TypeError):
            pass
        
    if filters.get('district'):
        filtered = list(filter(lambda r: key(r.get('district') or '') == key(filters['district']), filtered))
        
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
        distance = (calculate_distance(user_lat, user_lng, lat, lng)
                    if normalize_coordinates(user_lat, user_lng) and normalize_coordinates(lat, lng) else None)
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