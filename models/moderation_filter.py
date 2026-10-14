"""
Filtro automático de restaurantes.

Devuelve para cada restaurante:
  - food_score  (0-100): qué tan relacionado con comida parece
  - risk_score  (0-100): grado de incompatibilidad / riesgo (más alto = peor)
  - level       : "bajo" | "medio" | "alto"
  - issues      : lista de textos para mostrar en la tarjeta
  - flagged_words: palabras reservadas encontradas
  - is_clean    : True si se puede mostrar en "Aprobación rápida"

Las listas de palabras están en minúsculas y SIN tildes (el texto se normaliza).
"""

import re
import unicodedata

# ---------------------------------------------------------------- CONFIG
# Palabras que indican comida (aporte de confianza). Peso: fuerte / medio.
FOOD_STRONG = {
    "restaurante",
    "restaurant",
    "cevicheria",
    "ceviche",
    "pollo a la brasa",
    "polleria",
    "chifa",
    "pizzeria",
    "pizza",
    "parrilla",
    "parrillada",
    "anticucho",
    "marisqueria",
    "sushi",
    "hamburguesa",
    "hamburgueseria",
    "cocina",
    "menu",
    "almuerzo",
    "cena",
    "comida",
    "picanteria",
    "criollo",
    "cafeteria",
    "pasteleria",
    "panaderia",
    "sangucheria",
    "broaster",
    "tacos",
    "pasta",
    "trattoria",
    "buffet",
    "gastro",
}
FOOD_MEDIUM = {
    "cafe",
    "coffee",
    "bar",
    "grill",
    "sabor",
    "sazon",
    "delicia",
    "gourmet",
    "fusion",
    "nikkei",
    "postre",
    "dulce",
    "jugo",
    "cocteleria",
    "bistro",
    "snack",
    "fritanga",
    "rico",
    "casero",
    "arroz",
    "carne",
    "pescado",
    "sopa",
    "caldo",
    "cuy",
    "lomo",
    "tallarin",
}

# Palabras reservadas: no deberían aparecer en un restaurante.
BLOCKED_HIGH = {  # +45 de riesgo c/u
    "casino",
    "apuesta",
    "apuestas",
    "tragamonedas",
    "prestamo",
    "prestamos",
    "escort",
    "xxx",
    "porno",
    "droga",
    "marihuana",
    "arma",
    "armas",
    "hackeo",
    "estafa",
    "bitcoin",
    "inversion segura",
}
BLOCKED_MEDIUM = {  # +20 de riesgo c/u
    "ferreteria",
    "farmacia",
    "botica",
    "inmobiliaria",
    "taller",
    "repuestos",
    "abogado",
    "seguros",
    "gimnasio",
    "hotel",
    "hostal",
    "discoteca",
    "licoreria",
    "venta de",
    "oferta",
    "gratis",
    "click",
    "promo",
    "whatsapp",
}

PRICE_MAX = 500  # precio promedio sospechoso si lo supera (en tu moneda)
RISK_MEDIUM, RISK_HIGH = 30, 60
EXTRA_FIELDS = (
    "description",
    "category",
    "cuisine",
    "cuisine_type",
    "tags",
    "specialties",
)
# ---------------------------------------------------------------------


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _compile(words):
    ordered = sorted(words, key=len, reverse=True)
    return re.compile(r"\b(?:%s)(?:s|es)?\b" % "|".join(re.escape(w) for w in ordered))


_RX = {
    "strong": _compile(FOOD_STRONG),
    "medium": _compile(FOOD_MEDIUM),
    "high": _compile(BLOCKED_HIGH),
    "mid": _compile(BLOCKED_MEDIUM),
}


def _get(obj, field):
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)


def _found(rx, text):
    return {m.group(0) for m in rx.finditer(text)}


def analyze_restaurant(r):
    name_raw = str(_get(r, "name") or "")
    name = _norm(name_raw)
    extra = _norm(" ".join(str(_get(r, f) or "") for f in EXTRA_FIELDS))
    full = f"{name} {extra}"

    # ---- Score de comida: lo que aparece en el nombre pesa el doble
    points = 0
    points += 40 * len(_found(_RX["strong"], name)) + 20 * len(
        _found(_RX["strong"], extra)
    )
    points += 20 * len(_found(_RX["medium"], name)) + 10 * len(
        _found(_RX["medium"], extra)
    )
    food = min(100, points)

    # ---- Palabras reservadas
    high = _found(_RX["high"], full)
    mid = _found(_RX["mid"], full)
    flagged_words = sorted(high | mid)

    penalties, issues = 0, []

    if food < 20:
        issues.append("Parece no estar relacionado con comida")
    elif food < 40:
        issues.append("Pocas señales de que sea un negocio de comida")

    if high:
        penalties += 45 * len(high)
        issues.append("Palabras prohibidas: " + ", ".join(sorted(high)))
    if mid:
        penalties += 20 * len(mid)
        issues.append(
            "Palabras de otro rubro o promocionales: " + ", ".join(sorted(mid))
        )

    # ---- Señales estructurales
    if len(name_raw.strip()) < 3:
        penalties += 15
        issues.append("Nombre demasiado corto")
    if re.search(r"https?://|www\.|\d{7,}|@", name_raw.lower()):
        penalties += 20
        issues.append("El nombre contiene enlace, correo o teléfono")
    if re.search(r"(.)\1{3,}", name_raw):
        penalties += 10
        issues.append("Nombre con caracteres repetidos")
    digits = sum(c.isdigit() for c in name_raw)
    if name_raw and digits / len(name_raw) > 0.3:
        penalties += 10
        issues.append("Demasiados números en el nombre")
    if not str(_get(r, "description") or "").strip():
        penalties += 10
        issues.append("Sin descripción")
    price = _get(r, "avg_price")
    try:
        if price is not None and (float(price) <= 0 or float(price) > PRICE_MAX):
            penalties += 10
            issues.append("Precio promedio sospechoso")
    except (TypeError, ValueError):
        pass

    # ---- Riesgo final: la mitad de lo que "falta" de comida + penalizaciones
    risk = max(0, min(100, round((100 - food) * 0.5 + penalties, 1)))
    level = "alto" if risk >= RISK_HIGH else "medio" if risk >= RISK_MEDIUM else "bajo"

    return {
        "food_score": food,
        "risk_score": risk,
        "level": level,
        "issues": issues,
        "flagged_words": flagged_words,
        "is_clean": level == "bajo" and not flagged_words,
    }


if __name__ == "__main__":
    pruebas = [
        {
            "name": "Cevichería El Pescador",
            "description": "Ceviche y arroz con mariscos",
            "avg_price": 35,
        },
        {"name": "Coffee Break", "description": "", "avg_price": 20},
        {
            "name": "Casino Royal Apuestas 24h",
            "description": "Gana dinero gratis",
            "avg_price": 0,
        },
        {
            "name": "Ferretería Don Pepe",
            "description": "Venta de herramientas",
            "avg_price": 15,
        },
    ]
    for p in pruebas:
        res = analyze_restaurant(p)
        print(
            f"{p['name']:<28} comida={res['food_score']:>5}  riesgo={res['risk_score']:>5}  {res['level']}"
        )
        for i in res["issues"]:
            print("   -", i)
