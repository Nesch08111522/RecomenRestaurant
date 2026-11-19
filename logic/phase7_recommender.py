"""Personalize published catalog and commerce options using the user's own signals."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import chain
from math import isfinite, log2
from statistics import median
import re

from core.food_experience import safe_media_url
from logic.context import MOOD_TAGS, MOMENTS, MOMENT_TAGS
from logic.market import CHANNELS, LIMA, key, now
from logic.product_catalog import published_menu_dish
from utils.geo import calculate_distance, normalize_coordinates


PASTA_TERMS = {"pasta", "fetuccini", "fettuccini", "fettuccine", "linguine", "linguini", "tagliatelle",
               "gnocchi", "lasana", "lasagna", "ravioli", "espagueti", "spaghetti"}
CUISINES = {
    "Cocina marina": {"ceviche", "cebiche", "cevicheria", "marina", "marino", "marisco", "mariscos",
                     "pescado", "leche de tigre", "jalea marina", "jalea mixta", "parihuela"},
    "Cocina criolla": {"criolla", "criollo", "lomo saltado", "aji de gallina", "cabrito", "causa limena"},
    "Cocina norteña": {"nortena", "norteno", "seco de cabrito", "shambar"},
    "Cocina italiana": {"italiana", "italiano", "pizza", "risotto"} | PASTA_TERMS,
    "Pasta": PASTA_TERMS,
    "Chifa": {"chifa", "chaufa", "wantan", "tallarin saltado"},
    "Parrilla": {"parrilla", "parrillas", "anticucho", "brasas", "brasa"},
    "Cafés y postres": {"cafe", "cafeteria", "postre", "pasteleria", "torta", "flan"},
    "Cocina japonesa": {"japonesa", "makis", "maki", "sushi", "ramen"},
    "Cocina mexicana": {"mexicana", "taco", "tacos", "quesadilla", "burrito"},
    "Cocina vegetal": {"vegano", "vegana", "vegetariano", "vegetariana", "ensalada"},
    "Opciones ligeras": {"saludable", "saludables", "ligero", "ligera", "bajo en grasa"},
    "Comida picante": {"picante", "rocoto", "aji picante"},
}
CUISINE_PATTERNS = {
    label: re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, sorted(cues))) + r")(?!\w)")
    for label, cues in CUISINES.items()
}
DIET_ALIASES = {
    "vegan": "vegano", "vegana": "vegano", "vegetarian": "vegetariano",
    "vegetariana": "vegetariano", "celiaco": "sin gluten", "celiaca": "sin gluten",
    "gluten free": "sin gluten", "lactose free": "sin lactosa",
}
ALLERGEN_GROUPS = (
    {"marisco", "mariscos", "crustaceo", "crustaceos", "molusco", "moluscos", "camaron", "camarones",
     "langostino", "langostinos", "cangrejo", "cangrejos", "pulpo", "calamar", "calamares", "conchas",
     "almeja", "almejas", "mejillon", "mejillones", "ostras", "choros", "langosta"},
    {"mani", "cacahuate", "cacahuates", "cacahuete", "cacahuetes", "peanut"},
    {"leche", "lacteo", "lacteos", "queso", "mantequilla", "lactosa", "crema de leche"},
    {"soya", "soja", "soy"},
    {"huevo", "huevos", "clara de huevo", "yema", "mayonesa", "egg"},
    {"pescado", "pescados", "salmon", "atun", "merluza", "trucha", "anchoa"},
    {"nuez", "nueces", "frutos secos", "almendra", "almendras", "avellana", "avellanas",
     "castanas", "pistacho", "pistachos", "pecanas", "cashews"},
    {"gluten", "trigo", "cebada", "centeno", "malta", "espelta", "seitan"},
)
SEARCH_STOPWORDS = {"quiero", "busco", "tengo", "antojo", "algo", "comer", "un", "una", "de", "del", "la",
                    "el", "los", "las", "con", "para", "hoy", "favor", "por", "y", "me", "probar", "gustaria"}
GENERIC_TOPICS = {"plato", "platos", "fondo", "plato de fondo", "entrada", "acompanamiento", "bebida",
                  "bebidas", "menu", "carta", "otro", "otros", "general", "especial", "tradicional",
                  "economico", "premium", "familiar", "turistico", "rapido", "artesanal", "promocion",
                  "plato principal", "platos principales", "entradas", "fondos", "fresco", "fresca", "clasica",
                  "clasico", "gourmet", "delivery", "recojo", "local", "desayuno", "almuerzo", "cena",
                  "vista al mar"}
FOOD_STOPWORDS = SEARCH_STOPWORDS | {"al", "en", "sin", "plato", "menu", "casa", "casero", "casera", "version",
                                     "porcion", "especial", "tradicional", "estilo", "combo", "extra"}
HISTORY_STOPWORDS = FOOD_STOPWORDS | {"comida", "cocina", "desayuno", "almuerzo", "cena", "delivery", "restaurante",
                                      "restaurantes", "negocio", "negocios", "cerca", "buscar", "rico", "rica"}
COMMON_PANTRY_TERMS = {"agua", "sal", "aceite", "azucar", "cebolla", "ajo", "pimienta"}
NEGATED_SEARCH = re.compile(r"\b(?:sin|no|evito|evitar|alergia|intolerancia)\b")
SEARCH_HISTORY_REASON = "Coincide con lo que has buscado antes"
INACTIVE = {"archived", "draft", "hidden", "paused", "rejected", "sold_out", "suspended",
            "unavailable", "unpublished", "out_of_stock", "rechazado", "suspendido"}
PURCHASE_STATES = {"confirmado", "preparando", "listo", "en reparto", "entregado"}
MEALS = {"desayuno", "almuerzo", "cena"}
SEASONS = ("verano", "otoño", "invierno", "primavera")
KIND_GROUPS = {"dish": "dishes", "restaurant": "restaurants", "experience": "experiences"}
SERVICE_CHANNELS = {
    "dine_in_only": {"Local"},
    "dine_in_and_delivery": {"Local", "Delivery"},
    "delivery_only": {"Delivery"},
    "pickup_only": {"Recojo"},
}


def _strings(value):
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [part for part in value if isinstance(part, str) and part.strip()] if isinstance(value, (list, tuple, set)) else []


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) and number >= 0 else None


def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _clock(value):
    try:
        return time.fromisoformat(str(value)).replace(tzinfo=None)
    except ValueError:
        return None


def _instant(value):
    try:
        stamp = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return stamp.replace(tzinfo=LIMA) if stamp.tzinfo is None else stamp.astimezone(LIMA)


def _point(value):
    if isinstance(value, dict):
        value = value.get("lat"), value.get("lng")
    return normalize_coordinates(*value) if isinstance(value, (list, tuple)) and len(value) == 2 else None


def _distance(origin, point):
    return calculate_distance(*origin, *point) if origin and point else None


def _open(row, at):
    opening, closing = _clock(row.get("open_time")), _clock(row.get("close_time"))
    if opening is None or closing is None:
        return None
    local_time = at.time()
    return opening <= local_time < closing if opening < closing else local_time >= opening or local_time < closing


def _published(row):
    return (row.get("name") and row.get("is_available") is not False and not row.get("suspended")
            and not row.get("rejected") and all(key(row.get(field)) not in INACTIVE
                                                for field in ("status", "availability", "publication_status")))


def _price(row, offer=False):
    cents = _number(row.get("price") if offer else row.get("price_cents"))
    return cents / 100 if cents is not None else _number(row.get("price", row.get("avg_price")))


def _diet(value):
    name = key(value).replace("_", " ")
    return DIET_ALIASES.get(name, name)


def _requirements(profile, market_profile):
    diets = {_diet(value) for value in _strings(market_profile.get("diets"))}
    excluded = {key(value) for value in _strings(market_profile.get("avoid"))}
    for value in _strings(profile.get("restrictions")):
        allergy = re.match(r"(?:alergia|intolerancia)(?:\s+a(?:l| la| los| las)?)?\s+(.+)", key(value))
        if allergy:
            excluded.add(allergy[1])
        else:
            diets.add(_diet(value))
    return diets, excluded


def _words(text):
    return set(re.findall(r"[a-z0-9]+", key(text)))


def _contains(haystack, term):
    return bool(re.search(r"(?<!\w)" + re.escape(key(term)) + r"(?!\w)", haystack))


def _ingredients(row):
    recipe = row.get("recipe")
    parts = _strings(row.get("ingredients"))
    if isinstance(recipe, dict):
        return parts + _strings(list(recipe))
    if isinstance(recipe, list):
        return parts + _strings([entry.get("ingredient") if isinstance(entry, dict) else entry for entry in recipe])
    return parts


def _dietary_match(dish, listing, diets, excluded):
    if listing:
        stated_diets = _strings(listing.get("diets"))
        allergens = listing.get("allergens")
        confirmed = listing.get("cross") == "declared"
    else:
        stated_diets = _strings(dish.get("dietary_info")) + _strings(dish.get("diets"))
        allergens = dish.get("allergens")
        confirmed = dish.get("allergens_confirmed") is True
    available_diets = {_diet(diet) for diet in stated_diets}
    if "vegano" in available_diets:
        available_diets.add("vegetariano")
    if not diets.issubset(available_diets):
        return False
    ingredients = _strings(allergens) + _ingredients(dish) + _ingredients(listing or {})
    declared = key(" ".join(ingredients))
    if "sin gluten" in diets and any(_contains(declared, term) for term in ALLERGEN_GROUPS[-1]):
        return False
    if not excluded:
        return True
    if not confirmed or not isinstance(allergens, list):
        return False
    forbidden = set(excluded)
    for aliases in ALLERGEN_GROUPS:
        if excluded & aliases:
            forbidden.update(aliases)
    return not any(_contains(declared, term) for term in forbidden)


def _record_text(row, *fields):
    parts = []
    for field in fields:
        value = row.get(field)
        parts.extend(_strings(list(value) if isinstance(value, dict) else value))
    return key(" ".join(parts))


def _cuisines(text):
    return {label for label, pattern in CUISINE_PATTERNS.items() if pattern.search(text)}


def _category(row, categories):
    return categories.get(str(row.get("category_id"))) or row.get("category") or row.get("cuisine") or ""


def _restaurant_text(row, categories):
    return key(f"{_category(row, categories)} " + _record_text(
        row, "name", "description", "tags", "cuisine", "cuisine_type", "specialties",
    ))


def _dish_text(row):
    descriptions = _record_text(row, "name", "description", "category", "subcategory", "cuisine", "cuisine_type",
                                "tags", "variant", "diets", "dietary_info", "occasion", "context_tags")
    return key(" ".join((descriptions, *_ingredients(row))))


def _topics(row, text, category=""):
    """Learn declared topics even when the catalog uses a cuisine outside the built-in aliases."""
    known = _cuisines(text)
    topics = {key(label): label for label in known}
    labels = [category, *_strings(row.get("category")), *_strings(row.get("subcategory")),
              *_strings(row.get("cuisine")), *_strings(row.get("cuisine_type")), *_strings(row.get("tags"))]
    for label in labels:
        name = key(label)
        if name and name not in GENERIC_TOPICS and not _cuisines(name):
            topics[name] = label.capitalize()
    return topics


def _dish_topics(row):
    # Traits of a side or a recipe ingredient do not classify the whole meal.
    return _topics(row, _record_text(row, "name", "category", "subcategory", "cuisine", "cuisine_type",
                                     "tags", "dietary_info", "diets"))


def _food_terms(row, name=""):
    terms = _words(" ".join((name or row.get("name") or "", *_ingredients(row))))
    return {term for term in terms - FOOD_STOPWORDS if len(term) > 2 and not term.isdigit()}


def _freshness(day, today):
    """Recent purchases and interactions outweigh stale ones without erasing the latter."""
    return max(0.25, 1 - (today - day).days / 180) if day and day < today else 1


def _history_words(text):
    return {word for word in _words(text) - HISTORY_STOPWORDS if len(word) > 2 and not word.isdigit()}


def _recipe_words(row):
    return _history_words(" ".join(_ingredients(row))) - COMMON_PANTRY_TERMS


@dataclass(frozen=True)
class SearchInterest:
    words: frozenset[str]
    topics: frozenset[str]
    ingredients: frozenset[str]
    strength: float


def _search_signals(history, catalog_topics, today):
    """Retain each search's own catalogue evidence in chronological order."""
    interests, recurring = [], Counter()
    repeated = set()
    if not history:
        return interests, recurring, repeated

    titles = defaultdict(set)
    for title, labels, ingredients in catalog_topics:
        for text in (title, *labels):
            words = frozenset(_history_words(text))
            signature = (words, frozenset(labels), frozenset(ingredients if text == title else ()))
            for word in words:
                titles[word].add(signature)

    oldest = datetime.min.replace(tzinfo=LIMA)
    ordered = sorted(history, key=lambda row: _instant(row.get("last_searched_at")) or oldest, reverse=True)
    for entry in ordered:
        query = key(entry.get("query"))
        # A negative or allergy search is recorded, but its vocabulary isn't a positive taste.
        if NEGATED_SEARCH.search(query):
            continue
        count = min(40, _number(entry.get("count")) or 0)
        searched_on = _date(entry.get("last_searched_at"))
        words = frozenset(_history_words(query))
        if not words or count < 1 or (searched_on is not None and searched_on > today):
            continue
        strength = log2(1 + count) * _freshness(searched_on, today)
        if count >= 2 and strength >= 1.5:
            repeated.add(words)
        explicit = {key(label) for label in _cuisines(query)}
        matches = {entry for word in words for entry in titles[word] if words <= entry[0]}
        if matches:
            best_length = min(len(entry[0]) for entry in matches)
            matches = [entry for entry in matches if len(entry[0]) == best_length]
        votes = Counter(label for _, labels, _ in matches for label in labels)
        # A declared cuisine is better evidence than incidental topic labels on a matching entry.
        top_vote = max(votes.values(), default=0)
        recognized = explicit or {label for label, count in votes.items() if count == top_vote}
        if len(recognized) > 3:
            recognized = set()
        recipe = {word for _, labels, ingredients in matches if not recognized or recognized & labels
                  for word in ingredients}
        interests.append(SearchInterest(words, frozenset(recognized), frozenset(recipe), strength))
        recurring.update({label: int(count) for label in recognized})
    return interests, recurring, repeated


def _search_support(interests, title, topics, text, recipes, menu_words):
    title_words = _history_words(title)
    catalogue_words = (title_words | _history_words(text), *menu_words)
    support = {}
    for index, interest in enumerate(interests):
        title_match = interest.words <= title_words
        direct_match = title_match or any(interest.words <= words for words in catalogue_words)
        kitchens = interest.topics & topics.keys()
        recipe_overlap = max((len(interest.ingredients & ingredients) for ingredients in recipes), default=0)
        if not (direct_match or kitchens or recipe_overlap >= 2):
            continue
        score = (5 if title_match else 3.5 if direct_match else 0) + min(4.5, 3 * len(kitchens))
        if recipe_overlap >= 2:
            score += min(recipe_overlap, 3)
        support[index] = (score * interest.strength, title_match, direct_match, kitchens)
    return support


def _confirmed_orders(orders):
    confirmed = []
    for order in orders:
        state = key(order.get("state"))
        cash_commitment = key(order.get("method")) == "contraentrega" and state != "entregado"
        if (state in PURCHASE_STATES and not order.get("refunded") and not order.get("payment_incident")
                and (order.get("paid") is True or cash_commitment)):
            confirmed.append(order)
    return confirmed


def _budget(options, profile, market_profile, orders, target):
    cap = _number(options.get("budget"))
    if cap is None:
        cap = _number(market_profile.get("budget"))
    boundaries = [cap] if cap is not None else []
    week_start = target - timedelta(days=target.weekday())
    expenses = Counter()
    for order in orders:
        day = _date(order.get("day") or order.get("slot"))
        if day:
            expenses[day] += (_number(order.get("total")) or 0) / 100
    daily_spent = expenses[target]
    weekly_spent = sum(amount for day, amount in expenses.items() if week_start <= day < week_start + timedelta(days=7))
    for spent, values in ((daily_spent, (profile.get("daily_budget"), market_profile.get("daily"))),
                          (weekly_spent, (profile.get("weekly_budget"), market_profile.get("week")))):
        for value in values:
            if (amount := _number(value)) is not None:
                boundaries.append(round(max(0, amount - spent), 2))
    return min(boundaries) if boundaries else None


@dataclass
class HistorySignals:
    history: dict
    purchase_affinity: Counter
    visit_affinity: Counter
    terms: Counter
    recurring: Counter
    businesses: set
    dish_ids: set
    dishes_by_business: set
    prices: dict


def _signals(orders, visits, restaurants, dishes, restaurant_topics, dish_topics, at):
    meal_history, visit_history = {}, {}
    recurring, purchase_affinity, visit_affinity, food_affinity = Counter(), Counter(), Counter(), Counter()
    purchase_prices = defaultdict(list)
    purchased_restaurants, bought_ids, bought_at = set(), set(), set()

    def record_visit(rid, name, when):
        if not rid:
            return
        row = visit_history.setdefault(str(rid), {"id": rid, "name": name, "count": 0, "last_date": ""})
        row["count"] += 1
        row["last_date"] = max(row["last_date"], when)

    for order in orders:
        delivered = key(order.get("state")) == "entregado"
        rid = order.get("rid", order.get("restaurant_id"))
        rest = restaurants.get(str(rid), {})
        if rid:
            purchased_restaurants.add(str(rid))
        name = order.get("business") or rest.get("name") or "Negocio"
        when = str(order.get("day") or order.get("slot") or order.get("created") or "")[:10]
        labels = set()
        terms = set()
        fallback_terms = set()
        seen_in_order = set()
        for line in order.get("lines") or ():
            did = line.get("dish_id")
            dish = dishes.get(str(did), {})
            title = line.get("name") or dish.get("name")
            if not title:
                continue
            if did is not None:
                bought_ids.add(str(did))
            bought_at.add((str(rid), key(title)))
            topics = dish_topics.get(str(did)) or _topics(line, key(title)) or restaurant_topics.get(str(rid), {})
            labels.update(topics)
            line_terms = _food_terms(dish, title)
            terms.update(line_terms)
            if not topics:
                fallback_terms.update(line_terms)
            unit_price = _number(line.get("unit"))
            if unit_price is not None:
                for topic in topics:
                    purchase_prices[topic].append(unit_price / 100)
            if not delivered:
                continue
            identifier = str(did) if did is not None else (str(rid), key(title))
            meal = meal_history.setdefault(identifier, {"id": did, "name": title, "restaurant_id": rid,
                                                         "business": name, "count": 0, "quantity": 0,
                                                         "last_date": ""})
            meal["count"] += identifier not in seen_in_order
            seen_in_order.add(identifier)
            meal["quantity"] += int(_number(line.get("qty")) or 1)
            meal["last_date"] = max(meal["last_date"], when)
        labels = labels or set(restaurant_topics.get(str(rid), ()))
        strength = _freshness(_date(order.get("created") or when), at.date())
        purchase_affinity.update({label: strength for label in labels})
        food_affinity.update({term: strength for term in terms})
        recurring.update(labels)
        recurring.update(f"term:{term}" for term in fallback_terms)
        if delivered and key(order.get("channel")) == "local":
            record_visit(rid, name, when)

    for visit in visits:
        when = _date(visit.get("date") or visit.get("day"))
        if key(visit.get("status")) not in {"asistida", "completed", "attended"} or not when or when > at.date():
            continue
        rid = visit.get("restaurant_id")
        rest = restaurants.get(str(rid), {})
        record_visit(rid, visit.get("business") or rest.get("name") or "Negocio", when.isoformat())
        labels = restaurant_topics.get(str(rid), {})
        visit_affinity.update({label: _freshness(when, at.date()) for label in labels})
        recurring.update(labels.keys())

    for row in visit_history.values():
        row["visits"] = row["count"]
    history = {name: sorted(rows.values(), key=lambda row: (row["last_date"], row["count"]), reverse=True)
               for name, rows in (("dishes", meal_history), ("restaurants", visit_history))}
    usual_prices = {topic: median(prices) for topic, prices in purchase_prices.items()}
    return HistorySignals(history, purchase_affinity, visit_affinity, food_affinity, recurring, purchased_restaurants,
                          bought_ids, bought_at, usual_prices)


def _media(row, name, plural):
    for candidate in (row.get(name), *_strings(row.get(plural))):
        try:
            if result := safe_media_url(candidate):
                return result
        except ValueError:
            continue
    return ""


def _catalog_channel(row):
    channels = row.get("market_channels", row.get("channels"))
    if channels:
        return set(_strings(channels)) & set(CHANNELS)
    return set(SERVICE_CHANNELS.get(row.get("service_mode"), {"Local"}))


def _season(row, on):
    season = SEASONS[((on.month % 12) // 3)]
    seasons = {key(value) for value in _strings(row.get("seasons")) + _strings(row.get("season"))}
    months = {_number(value) for value in row.get("season_months", ())} if isinstance(row.get("season_months"), (list, tuple)) else set()
    return season, key(season) in seasons or on.month in months or (not seasons and not months and row.get("seasonal") is True)


def _listing_season(dish, listing, on):
    if any(listing.get(field) for field in ("seasons", "season", "season_months")) or "seasonal" in listing:
        return _season(listing, on)[1]
    return _season(dish, on)[1]


def _diverse(rows, limit, *, prefer_new=True):
    """Preserve relevance while spreading adjacent cards across merchants and dishes."""
    counts = Counter()
    kinds = Counter()
    seen_dishes = set()
    seen_names = set()
    selected = []
    pending = sorted(rows, key=lambda row: (-row["score"], key(row["name"]), row["key"]))
    while pending and len(selected) < limit:
        candidates = range(len(pending))
        if len(selected) >= min(2, max(1, limit - 1)):
            if prefer_new and not any(row["is_new"] and row["kind"] != "restaurant" for row in selected):
                novel = [i for i in candidates if pending[i]["is_new"] and pending[i]["kind"] != "restaurant"]
                if novel:
                    candidates = novel
            if len(counts) == 1:
                other_merchants = [i for i in candidates if pending[i]["restaurant_id"] not in counts]
                if other_merchants:
                    candidates = other_merchants
        index = max(candidates, key=lambda i: pending[i]["score"]
                    - 8 * counts[pending[i]["restaurant_id"]]
                    - 4 * kinds[pending[i]["kind"]]
                    - 40 * (pending[i]["dish_id"] in seen_dishes)
                    - 14 * (key(pending[i]["name"]) in seen_names))
        row = pending.pop(index)
        selected.append(row)
        counts[row["restaurant_id"]] += 1
        kinds[row["kind"]] += 1
        if row["dish_id"] is not None:
            seen_dishes.add(row["dish_id"])
        seen_names.add(key(row["name"]))
    return selected


def _option_identity(card):
    if card["dish_id"] is not None:
        return ("dish", str(card["dish_id"]))
    return (card["kind"], str(card["id"]))


def _distinct_options(rows):
    distinct = {}
    for card in sorted(rows, key=lambda row: (-row["score"], key(row["name"]), row["key"])):
        distinct.setdefault(_option_identity(card), card)
    return list(distinct.values())


def _personal_choices(familiar, interests, history_support, limit):
    """Cover distinct recent interests before filling with the strongest historical matches."""
    selected, seen = [], set()

    def identity(card):
        return (card["kind"] == "restaurant", key(card["name"]))

    def choose(card):
        selected.append(card)
        seen.add(identity(card))

    def ranked_for(index):
        matches = [(card, history_support.get(card["key"], {}).get(index)) for card in familiar]
        return sorted(((card, match) for card, match in matches if match),
                      key=lambda pair: (-pair[1][1], -pair[1][0], -pair[0]["score"], pair[0]["key"]))

    active, leading_names, words_seen = [], set(), []
    for index, interest in enumerate(interests):
        if any(interest.words <= words or words <= interest.words for words in words_seen):
            continue
        if ranked := ranked_for(index):
            leading_name = identity(ranked[0][0])
            if leading_name in leading_names:
                continue
            active.append(ranked)
            leading_names.add(leading_name)
            words_seen.append(interest.words)

    if len(active) > 1:
        visible_limit = min(limit, 6)
        for ranked in active[:visible_limit]:
            if match := next((card for card, _ in ranked if identity(card) not in seen), None):
                choose(match)
        restaurant = None
        if len(selected) < visible_limit and not any(card["kind"] == "restaurant" for card in selected):
            restaurant = next((card for ranked in active for card, _ in ranked
                               if card["kind"] == "restaurant" and identity(card) not in seen), None)
        for ranked in active:
            if len(selected) >= visible_limit - bool(restaurant):
                break
            if related := next((card for card, support in ranked if card["kind"] == "dish"
                                and not support[2] and identity(card) not in seen), None):
                choose(related)
        if restaurant:
            choose(restaurant)
    elif active:
        choose(familiar[0])
        for related_kind in ("dish", "restaurant"):
            if len(selected) == limit:
                break
            related = next((card for card, support in active[0]
                            if card["kind"] == related_kind and identity(card) not in seen
                            and (related_kind == "restaurant" or not support[2])), None)
            if related:
                choose(related)

    pending = []
    for card in familiar:
        if identity(card) not in seen:
            pending.append(card)
            seen.add(identity(card))
    return selected + _diverse(pending, limit - len(selected), prefer_new=False)


def _split_feeds(rows, history_evidence, interests, history_support, limit):
    """Let purchase and search evidence qualify cards for the personal deck."""
    if not rows or not limit:
        return [], []
    familiar = _distinct_options([
        {**card, **history_evidence[card["key"]]} for card in rows if card["key"] in history_evidence
    ])
    candidates = _distinct_options(rows)
    novel = [card for card in candidates if card["is_new"]]
    if not familiar:
        return [], _diverse(novel, limit)

    personal = _personal_choices(familiar, interests, history_support, limit)
    personal_ids = {_option_identity(card) for card in personal}
    personal_titles = {key(card["name"]) for card in personal}
    discovery = _diverse([card for card in novel if _option_identity(card) not in personal_ids
                          and key(card["name"]) not in personal_titles], limit)
    return personal, discovery


def recommend(*, restaurants=(), dishes=(), categories=(), offers=(), profile=None, market_profile=None,
              orders=(), visits=(), favorites=(), feedback=None, feedback_signals=None, search_history=(),
              options=None, location=None, weather=None, at=None, limit=12):
    """Rank real menu items, businesses and bookable marketplace offers in Lima time."""
    profile, market_profile, feedback, options = profile or {}, market_profile or {}, feedback or {}, options or {}
    feedback_signals = feedback_signals or {}
    at = _instant(at) or now()
    today = at.date()
    requested_day = _date(options.get("day"))
    target_day = requested_day or today
    requested_time = _clock(options.get("time"))
    scheduled = datetime.combine(target_day, requested_time, LIMA) if requested_time is not None else None
    orders = _confirmed_orders(orders)
    search_mode = options.get("search_mode") is True
    budget = (_number(options.get("budget")) if search_mode
              else _budget(options, profile, market_profile, orders, target_day))
    channel = options.get("channel") or ""
    preferred_channel = "" if search_mode else market_profile.get("channel") or ""
    frequent_channels = Counter(order["channel"] for order in orders if order.get("channel") in CHANNELS)
    if not search_mode and not preferred_channel and frequent_channels:
        common_channel, count = frequent_channels.most_common(1)[0]
        if count >= 2:
            preferred_channel = common_channel
    origin = _point(location) if profile.get("location_consent") is True else None
    radius = _number(options.get("radius")) if origin else None
    if origin and isinstance(weather, dict):
        weather = {name: weather[name] for name in ("apparent_temperature", "precipitation", "rain_probability", "source")
                   if name in weather}
    else:
        weather = None
    hour = (scheduled or at).hour
    meal = "Desayuno" if hour < 11 else "Almuerzo" if hour < 17 else "Cena"
    season, _ = _season({}, target_day)
    moment_tags = {key(tag) for tag in MOMENT_TAGS.get(options.get("moment"), ())}
    mood_tags = {key(tag) for tag in MOOD_TAGS.get(options.get("mood"), ())}
    weather_tags = set()
    weather_used = False
    if weather and target_day == today:
        felt = weather.get("apparent_temperature")
        if type(felt) in (int, float) and isfinite(felt):
            weather_used = True
            if (_number(weather.get("precipitation")) or 0) > 0 or felt <= 18:
                weather_tags = {"caliente", "reconfortante"}
            elif felt >= 26:
                weather_tags = {"fresco", "ligero"}

    query = str(options.get("q") or "").strip()
    query_words = _words(query).difference(SEARCH_STOPWORDS)
    negative_terms = re.findall(r"\bsin\s+[a-z0-9]+", key(query)) if search_mode else []
    requested_moment = options.get("moment") if search_mode else ""
    preferences = set(_strings(profile.get("preferences")) + _strings(market_profile.get("likes")))
    preferred_topics = {key(label) for label in _cuisines(key(" ".join(preferences)))} | {key(label) for label in preferences}
    diets, excluded = _requirements(profile, market_profile)
    discovery = not search_mode and bool(options.get("discovery"))
    open_now = bool(options.get("open_now"))
    all_restaurants = {str(row["id"]): row for row in restaurants if row.get("id") is not None}
    all_dishes = {str(row["id"]): row for row in dishes if row.get("id") is not None}
    category_names = {str(row["id"]): row.get("name") for row in categories if row.get("id") is not None}
    restaurant_text = {rid: _restaurant_text(row, category_names) for rid, row in all_restaurants.items()}
    restaurant_topics = {rid: _topics(row, restaurant_text[rid], _category(row, category_names))
                         for rid, row in all_restaurants.items()}
    dish_text = {did: _dish_text(row) for did, row in all_dishes.items()}
    dish_topics = {did: _dish_topics(row) for did, row in all_dishes.items()}
    dish_terms = {did: _food_terms(row) for did, row in all_dishes.items()}
    dish_recipes = {did: _recipe_words(row) for did, row in all_dishes.items()}
    for did, row in all_dishes.items():
        if not dish_topics[did]:
            dish_topics[did] = restaurant_topics.get(str(row.get("restaurant_id")), {})
    eligible_restaurants = {rid: row for rid, row in all_restaurants.items()
                            if row.get("verified") is not False and _published(row)}
    eligible_dishes = {did: row for did, row in all_dishes.items() if _published(row)}
    interests, search_recurrence, repeated_searches = _search_signals(
        search_history,
        chain(
            ((restaurant["name"], restaurant_topics[rid], ()) for rid, restaurant in eligible_restaurants.items()),
            ((dish["name"], dish_topics[did], dish_recipes[did]) for did, dish in eligible_dishes.items()
             if str(dish.get("restaurant_id")) in eligible_restaurants),
        ),
        today,
    )
    activity = _signals(
        orders, visits, all_restaurants, all_dishes, restaurant_topics, dish_topics, at,
    )
    combined_affinity = activity.purchase_affinity + activity.visit_affinity
    bought_names = {dish_name for _, dish_name in activity.dishes_by_business}
    consumed_ids = {str(row["id"]) for row in activity.history["dishes"] if row["id"] is not None}
    consumed_at = {(str(row["restaurant_id"]), key(row["name"])) for row in activity.history["dishes"]}
    visited = {str(row["id"]) for row in activity.history["restaurants"]}
    favorite_ids = {str(row.get("restaurant_id") if isinstance(row, dict) else row) for row in favorites}
    interactions, term_interactions, business_interactions = Counter(), Counter(), Counter()
    liked_items, view_weights = defaultdict(set), {}
    offers_by_id = {str(row["id"]): row for row in offers if row.get("id") is not None}
    market_businesses = {str(offer.get("rid")) for offer in offers_by_id.values()}
    for identifier in feedback.keys() | feedback_signals.keys():
        kind, _, item_id = identifier.partition("-")
        answer = feedback.get(identifier)
        signal = feedback_signals.get(identifier) or {}
        visits_count = min(100, _number(signal.get("views")) or int(answer == "viewed"))
        view_weight = min(3, log2(visits_count + 1)) * _freshness(_date(signal.get("last_seen")), today)
        feedback_strength = {"liked": 3, "dismissed": -2}.get(answer, 0)
        strength = feedback_strength * _freshness(_date(signal.get("updated_at")), today)
        if answer != "dismissed" and view_weight:
            strength += view_weight
            view_weights[identifier] = view_weight
        if kind == "restaurant" and item_id in all_restaurants:
            topics, terms, business = restaurant_topics[item_id], set(), item_id
            distinct_item = ("restaurant", item_id)
        else:
            offer = offers_by_id.get(item_id, {}) if kind == "experience" else {}
            dish_id = str(offer.get("dish_id") or signal.get("dish_id")) if kind == "experience" else item_id
            if kind not in {"dish", "experience"} or dish_id not in all_dishes:
                continue
            source = all_dishes[dish_id]
            topics, terms = dish_topics[dish_id], dish_terms[dish_id]
            business = str(source.get("restaurant_id", offer.get("rid")))
            distinct_item = ("dish", dish_id)
        business_interactions[business] += strength
        interactions.update({topic: strength for topic in topics})
        term_interactions.update({term: strength for term in terms})
        if answer == "liked":
            for topic in topics or (f"term:{term}" for term in terms):
                liked_items[topic].add(distinct_item)
    labels = {key(label): label for label in CUISINES}
    for topics in (*restaurant_topics.values(), *dish_topics.values()):
        labels.update(topics)
    recurrence = (activity.recurring + search_recurrence
                  + Counter({topic: len(values) for topic, values in liked_items.items()}))
    recurring = [{"label": labels.get(label, label.removeprefix("term:").capitalize()), "count": count} for label, count in
                 sorted(recurrence.items(), key=lambda row: (-row[1], row[0])) if count >= 2]
    history_evidence = {}
    history_support = {}

    def matches(terms):
        return not query or bool(query_words and query_words.issubset(_words(terms))
                                 and all(_contains(terms, phrase) for phrase in negative_terms))

    def matches_moment(tags, *occasions):
        if not requested_moment:
            return True
        return (bool(moment_tags & {key(tag) for tag in tags})
                or bool({key(requested_moment), key(MOMENTS.get(requested_moment))}
                        & {key(value) for value in occasions if value}))

    def score_history(card, topics, terms, search_score, support):
        score, reasons = 0, []
        rid, name = str(card["restaurant_id"]), key(card["name"])
        if card["kind"] == "restaurant":
            if rid in activity.businesses:
                score += 20
                reasons.append("De un negocio donde ya hiciste una compra confirmada")
        elif str(card["dish_id"]) in activity.dish_ids or (rid, name) in activity.dishes_by_business:
            score += 24
            reasons.append("Está en tus compras confirmadas")
        elif name in bought_names:
            score += 12
            reasons.append("Comparte el nombre de un plato que compraste en otro negocio")
        purchased_topics = topics.keys() & activity.purchase_affinity.keys()
        if purchased_topics:
            topic = max(sorted(purchased_topics), key=activity.purchase_affinity.get)
            score += min(21, 9 + 4 * activity.purchase_affinity[topic])
            reasons.append(f"Afinidad con tus compras confirmadas: {topics[topic].lower()}")
        purchase_terms = (set(terms) & activity.terms.keys()) - COMMON_PANTRY_TERMS
        if purchase_terms:
            score += min(8, 2.5 * sum(activity.terms[term] for term in purchase_terms))
            if not purchased_topics:
                reasons.append("Comparte alimentos o nombres del catálogo con tus compras confirmadas")
        if support:
            score += search_score
            reasons.append(SEARCH_HISTORY_REASON)
            _, _, direct, cuisines = max(support.values(), key=lambda match: match[0])
            if cuisines and not direct:
                reasons.append(f"De la misma cocina que buscaste ({topics[min(cuisines)].lower()})")
            elif not direct:
                reasons.append("Comparte ingredientes con lo que has buscado")
        if reasons:
            history_evidence[card["key"]] = {"score": round(score, 2), "reasons": reasons}
            if support:
                history_support[card["key"]] = support

    def rank(card, text, topics, *, terms=(), tags=(), occasion="", seasonal=False, rating=None, featured=False,
             menu_search_words=(), recipes=()):
        if search_mode:
            reasons = []
            name_words = _words(card["name"]).difference(SEARCH_STOPWORDS)
            score = 0
            if query:
                score = 8 if query_words == name_words else 5 if query_words <= name_words else 1
                reasons.append("Coincide con tu búsqueda")
            if budget is not None:
                reasons.append("Dentro del presupuesto indicado")
            if requested_moment:
                reasons.append("Coincide con la ocasión indicada")
            return {**card, "score": score, "reasons": reasons, "is_seasonal": bool(seasonal),
                    "frequently_searched": False}

        rid = str(card["restaurant_id"])
        feedback_value = feedback.get(card["key"])
        if feedback_value == "dismissed" or discovery and not card["is_new"]:
            return None
        reasons = []
        score = 0
        declared = {preference for preference in preferences if _contains(text, preference)}
        if declared or topics.keys() & preferred_topics:
            score += min(19, 13 + 3 * len(declared))
            reasons.append("Coincide con tus preferencias gastronómicas")
        matched = sorted(topics.keys() & combined_affinity.keys(), key=lambda label: (-combined_affinity[label], label))
        if matched:
            top = matched[0]
            score += min(21, 9 + 4 * combined_affinity[top])
            reasons.append(f"Afinidad con tu historial: {topics[top].lower()}")
        shared_terms = sorted(set(terms) & activity.terms.keys(),
                              key=lambda term: (-activity.terms[term], term))[:2]
        if shared_terms:
            score += min(8, 2.5 * sum(activity.terms[term] for term in shared_terms))
            if not matched:
                reasons.append("Comparte alimentos o nombres del catálogo con tus compras confirmadas")
        support = _search_support(interests, card["name"], topics, text, recipes, menu_search_words) if interests else {}
        scores = sorted((match[0] for match in support.values()), reverse=True)
        search_score = min(30, scores[0] + 0.3 * sum(scores[1:])) if scores else 0
        if support:
            score += search_score
            reasons.append(SEARCH_HISTORY_REASON)
        score_history(card, topics, terms, search_score, support)
        if not orders and not interests and (declared or topics.keys() & preferred_topics):
            history_evidence[card["key"]] = {
                "score": min(19, 13 + 3 * len(declared)),
                "reasons": ["Coincide con tus preferencias gastronómicas"],
                "personalization_basis": "declared_preferences",
            }
        topic_strength = sum(interactions[topic] for topic in topics)
        term_strength = sum(sorted((term_interactions[term] for term in terms), reverse=True)[:2])
        signal = max(-5, min(9, topic_strength * 0.7 + term_strength * 0.45))
        score += signal
        if signal >= 1 and not matched and not shared_terms:
            related_liked = topics.keys() | {f"term:{term}" for term in terms}
            reasons.append("Se relaciona con opciones que te gustaron" if related_liked & liked_items.keys()
                           else "Se relaciona con opciones que exploraste")
        score += max(-3, min(5, business_interactions[rid]))
        if feedback_value == "liked":
            score += 8
            reasons.append("Marcaste esta opción como Me interesa")
        elif card["key"] in view_weights:
            score += 1.5 * view_weights[card["key"]]
            reasons.append("Consultaste esta opción anteriormente")
        elif rid in favorite_ids:
            score += 5
            reasons.append("De un negocio que guardaste en favoritos")
        if card["is_new"]:
            score += 10
            reasons.append({
                "restaurant": "Un negocio por descubrir",
                "dish": "Un plato por descubrir",
                "experience": "Una experiencia por descubrir",
            }[card["kind"]])
        elif card["kind"] == "restaurant":
            reasons.append("De tus visitas o compras confirmadas")
        elif str(card["dish_id"]) in consumed_ids or (rid, key(card["name"])) in consumed_at:
            reasons.append("Ya lo probaste")
        elif (str(card["dish_id"]) not in activity.dish_ids
              and (rid, key(card["name"])) not in activity.dishes_by_business):
            reasons.append("Una opción con el nombre de un plato de tu historial, en otro negocio")
        else:
            reasons.append("Ya figura en una compra confirmada")
        if budget is not None and card["price"] is not None:
            score += 4 + 4 * (card["price"] <= budget * 0.75)
            reasons.append("Dentro de tu presupuesto")
        if card["kind"] != "restaurant" and card["is_new"] and matched and card["price"] is not None:
            comparison = activity.prices.get(matched[0])
            if comparison and card["price"] <= comparison * 0.90:
                score += 4
                reasons.append("Cuesta menos que opciones similares de tus compras confirmadas")
        active_channel = channel or preferred_channel
        if active_channel and active_channel in card["channels"]:
            score += 6
            reasons.append({
                "Local": "Disponible en el local",
                "Delivery": "Ofrece delivery en las zonas de cobertura del negocio",
                "Recojo": "Disponible para recojo",
            }[active_channel])
        if card["distance_km"] is not None and card["distance_km"] <= 10:
            score += max(0, 8 - card["distance_km"])
            reasons.append(f"A {card['distance_km']:.1f} km de tu ubicación")
        if scheduled and card["is_open_at_time"] is True:
            score += 4
            reasons.append("Abierto a la hora que elegiste según el horario publicado")
        elif card["is_open_now"] is True and target_day == today:
            score += 4
            reasons.append("Abierto según el horario publicado")
        if key(occasion) == key(meal):
            score += 5
            reasons.append(f"Opción para el {meal.lower()}" if meal != "Cena" else "Opción para la cena")
        tags = {key(tag) for tag in tags}
        if tags & moment_tags:
            score += 7
            reasons.append("Encaja con la ocasión que elegiste")
        if tags & mood_tags:
            score += 5
            reasons.append("Encaja con lo que te apetece ahora")
        if tags & weather_tags and (not card["day"] or _date(card["day"]) == today):
            score += 5
            reasons.append("Encaja con el clima local consultado")
        if seasonal:
            score += 6
            reasons.append("Opción de temporada publicada por el negocio")
        if featured:
            score += 3
            reasons.append("El negocio recomienda este plato en su carta")
        if rating is not None:
            score += min(5, rating)
            if rating >= 4.5:
                reasons.append("Valoración de la comunidad de 4.5 o más")
        if (diets or excluded) and card["kind"] != "restaurant":
            reasons.append("Coincide con las declaraciones del catálogo sobre tus restricciones")
        if card["offer_id"] is not None:
            reasons.append("Oferta con porciones disponibles")
        name_words = _history_words(card["name"]) if repeated_searches else set()
        return {**card, "score": round(score, 2), "reasons": reasons, "is_seasonal": bool(seasonal),
                "frequently_searched": any(words <= name_words for words in repeated_searches)}

    def make_card(kind, row, restaurant, *, listing=None, source_dish=None, market_window=()):
        if target_day < today:
            return None
        dish = source_dish or {}
        rid = restaurant["id"]
        did = dish.get("id")
        offer_id = listing.get("id") if listing else None
        day = listing.get("day") if listing else dish.get("menu_date") or None
        point = _point(listing.get("pin")) if listing else None
        distance = _distance(origin, point or _point(restaurant))
        is_open = _open(restaurant, at)
        is_open_at_time = _open(restaurant, scheduled) if scheduled else None
        ends = _instant(listing.get("ends")) if listing else None
        starts = _instant(listing.get("starts")) if listing else None
        if scheduled and listing:
            lead = timedelta(minutes=_number(listing.get("lead")) or 0)
            discount_until = _instant(listing.get("rescue_until")) if _number(listing.get("saving")) else None
            if (day != target_day.isoformat() or scheduled <= at + lead
                    or (ends and ends < scheduled) or (starts and starts > scheduled)
                    or (discount_until and discount_until < scheduled)):
                return None
        if not listing and day and (scheduled or open_now):
            menu_meal = key(dish.get("meal_time"))
            if menu_meal in MEALS and menu_meal != key(meal):
                return None
        if scheduled and (scheduled < at or is_open_at_time is not True and channel not in market_window
                          and (not listing or channel == "Local")):
            return None
        if open_now:
            if target_day != today:
                return None
            if listing and (day != today.isoformat() or (ends and ends <= at) or (starts and starts > at)):
                return None
            if is_open is not True and channel not in market_window and (
                not listing or channel == "Local" or starts is None or ends is None
            ):
                return None
        if radius is not None and (distance is None or distance > radius):
            return None
        if listing:
            channels = set(_strings(listing.get("channels"))) & set(CHANNELS)
            delivery_radius = _number(listing.get("radius"))
            if origin and delivery_radius and (not point or distance > delivery_radius):
                channels.discard("Delivery")
            if not channels:
                return None
        else:
            channels = _catalog_channel(restaurant)
            if kind == "dish":
                channels &= {"Local"}
                if not channels:
                    return None
        if channel and channel not in channels:
            return None
        price = _price(listing, offer=True) if listing else _price(row)
        if budget is not None and (price is None or price > budget):
            return None
        image = _media(listing or {}, "image", "images") or _media(dish or row, "image", "images")
        model = _media(listing or {}, "model_url", "models") or _media(dish or row, "model_url", "models")
        return dict(kind=kind, key=f"{kind}-{row['id']}", id=row["id"], dish_id=did, offer_id=offer_id,
                    restaurant_id=rid, name=row["name"], business=restaurant["name"], description=row.get("description") or "",
                    image=image, model=model, variant=(listing or {}).get("variant") or "",
                    price=price, day=day, channels=[value for value in CHANNELS if value in channels], distance_km=distance,
                    is_open_now=is_open, is_open_at_time=is_open_at_time, district=restaurant.get("district") or "",
                    is_new=(str(rid) not in visited | activity.businesses if kind == "restaurant" else
                            str(did) not in activity.dish_ids
                            and key(dish.get("name", row["name"])) not in bought_names))

    dated_offers = defaultdict(list)
    for offer in offers_by_id.values():
        day = _date(offer.get("day"))
        ends = _instant(offer.get("ends"))
        if not day or day < today or (requested_day or scheduled) and target_day != day or open_now and day != today:
            continue
        ready_after = at + timedelta(minutes=_number(offer.get("lead")) or 0)
        if not _number(offer.get("available")) or offer.get("paused") or (ends and ends <= ready_after):
            continue
        if key(offer.get("review_state", "approved")) != "approved":
            continue
        did = str(offer.get("dish_id"))
        rid = str(offer.get("rid"))
        dish = eligible_dishes.get(did)
        if rid in eligible_restaurants and dish and str(dish.get("restaurant_id")) == rid:
            dated_offers[did].append(offer)

    items = []
    eligible_menu = defaultdict(list)
    menu_topics = defaultdict(dict)
    menu_terms = defaultdict(set)
    menu_words = defaultdict(list)
    menu_recipes = defaultdict(list)
    for did, dish in eligible_dishes.items():
        rid = str(dish.get("restaurant_id"))
        restaurant = eligible_restaurants.get(rid)
        if not restaurant:
            continue
        text = dish_text[did]
        topics = dish_topics[did]
        dish_tags = _strings(dish.get("context_tags")) + _strings(dish.get("tags"))
        available_listings = []
        for listing in dated_offers[did]:
            listing_text = _dish_text(listing)
            listing_tags = dish_tags + _strings(listing.get("context_tags"))
            if (not matches(f"{text} {listing_text}") or not _dietary_match(dish, listing, diets, excluded)
                    or not matches_moment(listing_tags, listing.get("occasion"), dish.get("occasion"))):
                continue
            if card := make_card("experience", listing, restaurant, listing=listing, source_dish=dish):
                available_listings.append((listing, card["channels"]))
                if experience := rank(
                    card, f"{text} {listing_text}", topics | _dish_topics(listing), terms=dish_terms[did],
                    tags=listing_tags,
                    occasion=listing.get("occasion"),
                    seasonal=_listing_season(dish, listing, _date(listing["day"]) or target_day),
                    recipes=(dish_recipes[did] | _recipe_words(listing),),
                ):
                    items.append(experience)
        dish_card = None
        applicable = None
        if available_listings:
            applicable, _ = min(available_listings, key=lambda entry: (
                preferred_channel not in entry[1], entry[0]["day"], _price(entry[0], offer=True) or 0, entry[0]["id"],
            ))
            dish_card = make_card("dish", dish, restaurant, listing=applicable, source_dish=dish)
        if (dish_card is None and target_day >= today and published_menu_dish(dish, target_day)
                and matches(text) and _dietary_match(dish, None, diets, excluded)
                and matches_moment(dish_tags, dish.get("occasion"))):
            dish_card = make_card("dish", dish, restaurant, source_dish=dish)
        if dish_card:
            eligible_menu[rid].append(dish_card)
            menu_topics[rid].update(topics)
            menu_terms[rid].update(dish_terms[did])
            listing = applicable or {}
            menu_words[rid].append(_history_words(f"{text} {_dish_text(listing)}"))
            recipe = dish_recipes[did] | _recipe_words(listing)
            menu_recipes[rid].append(recipe)
            if card := rank(
                dish_card, f"{text} {_dish_text(listing)}", topics, terms=dish_terms[did],
                tags=dish_tags + _strings(listing.get("context_tags")),
                occasion=listing.get("occasion") or dish.get("meal_time") or dish.get("occasion"),
                seasonal=_listing_season(dish, listing, _date(listing.get("day")) or target_day),
                featured=dish.get("is_recommended") is True,
                recipes=(recipe,),
            ):
                items.append(card)

    for rid, restaurant in eligible_restaurants.items():
        qualifying_menu = eligible_menu[rid]
        if (diets or excluded or channel in {"Delivery", "Recojo"}) and not qualifying_menu:
            continue
        terms = restaurant_text[rid]
        restaurant_tags = _strings(restaurant.get("context_tags")) + _strings(restaurant.get("tags"))
        text_matches = matches(terms)
        if search_mode and not text_matches:
            continue
        restaurant_matches = text_matches and matches_moment(restaurant_tags, restaurant.get("occasion"))
        if not (restaurant_matches or qualifying_menu):
            continue
        menu_channels = {value for row in qualifying_menu for value in row["channels"]}
        business_channels = _catalog_channel(restaurant)
        if origin and (restaurant.get("market_kind") or rid in market_businesses):
            business_channels.discard("Delivery")
        venue = {**restaurant, "market_channels": business_channels | menu_channels}
        market_window = menu_channels & {"Delivery", "Recojo"}
        card = make_card("restaurant", restaurant, venue, market_window=market_window)
        if not card and qualifying_menu:
            lowest = min((row["price"] for row in qualifying_menu if row["price"] is not None), default=None)
            card = make_card("restaurant", {**restaurant, "price": lowest}, venue, market_window=market_window)
            if card:
                card["price_from"] = True
        topics = restaurant_topics[rid] | menu_topics[rid]
        if card and requested_day and any(row["day"] == requested_day.isoformat() for row in qualifying_menu):
            card["day"] = requested_day.isoformat()
        if card and (ranked := rank(
            card, terms, topics, terms=menu_terms[rid], rating=_number(restaurant.get("rating")),
            seasonal=_season(restaurant, target_day)[1],
            menu_search_words=menu_words[rid], recipes=menu_recipes[rid],
        )):
            items.append(ranked)

    context = dict(budget=budget, channel=channel, day=requested_day.isoformat() if requested_day else "",
                   time=requested_time.isoformat(timespec="minutes") if requested_time else "", q=query,
                   open_now=open_now, moment=options.get("moment") or "", radius=radius,
                   discovery=discovery, location_used=bool(origin), weather_used=weather_used,
                   weather=weather, season=season, meal=meal,
                   preferred_channel=preferred_channel,
                   has_recommendation_history=bool(orders or search_history),
                   personalized=bool(preferences or diets or excluded or activity.businesses or
                                     any(activity.history.values()) or favorite_ids or feedback or
                                     feedback_signals or preferred_channel or
                                     any(SEARCH_HISTORY_REASON in card["reasons"] for card in items)))
    groups = {group: [row for row in items if row["kind"] == kind] for kind, group in KIND_GROUPS.items()}
    groups["items"] = items
    results = {group: _diverse(rows, limit, prefer_new=not search_mode) for group, rows in groups.items()}
    for_you, discovery_items = {}, {}
    for group, rows in groups.items():
        for_you[group], discovery_items[group] = (_split_feeds(rows, history_evidence, interests, history_support, limit)
                                                 if not query and not search_mode else ([], []))
    return {**results, "for_you": for_you, "discovery_items": discovery_items,
            "history": activity.history, "recurring": recurring, "context": context}
