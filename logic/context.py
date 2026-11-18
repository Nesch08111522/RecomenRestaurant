"""Rank contextual preferences only after mandatory commerce and dietary filters."""
from collections import Counter
from datetime import date
from logic.market import key, now

MOODS = {"cansado":"Estoy cansado", "reconfortante":"Quiero algo reconfortante", "estres":"Un día intenso",
         "celebrar":"Quiero celebrar", "contento":"Estoy de buen humor", "ligero":"Necesito algo ligero",
         "dulce":"Tengo antojo de dulce", "recovery":"Recovery Food"}
MOMENTS = {"cita":"Una cita", "familia":"Comida en familia", "amigos":"Con amigos",
           "cumpleanos":"Cumpleaños", "rapido":"Entre clases o trabajo", "especial":"Cena especial"}
TAGS = ("Fresco", "Caliente", "Ligero", "Reconfortante", "Dulce", "Sin alcohol", "Suave",
        "Para compartir", "Celebración", "Rápido")
SEASONS = ("Verano", "Otoño", "Invierno", "Primavera")
MOOD_TAGS = {"cansado":{"Reconfortante","Caliente"}, "reconfortante":{"Reconfortante"}, "estres":{"Suave"},
             "celebrar":{"Celebración"}, "contento":{"Para compartir"}, "ligero":{"Ligero"},
             "dulce":{"Dulce"}, "recovery":{"Sin alcohol","Suave"}}
MOMENT_TAGS = {"cita":{"Celebración"}, "familia":{"Para compartir"}, "amigos":{"Para compartir"},
              "cumpleanos":{"Celebración","Dulce"}, "rapido":{"Rápido"}, "especial":{"Celebración"}}


def normalize_seasons(values):
    if not isinstance(values, list) or len(values) > len(SEASONS) or any(not isinstance(value, str) for value in values):
        raise ValueError("Elige las temporadas entre las opciones disponibles.")
    selected = {key(value) for value in values}
    allowed = {key(season): season for season in SEASONS}
    if selected.difference(allowed):
        raise ValueError("Elige las temporadas entre las opciones disponibles.")
    return [season for name, season in allowed.items() if name in selected]


def contextualize(rows, context, weather, history):
    moment = now()
    wanted = MOOD_TAGS.get(context.get("mood"), set()) | MOMENT_TAGS.get(context.get("moment"), set())
    climate_tags = set()
    if weather:
        felt = weather["apparent_temperature"]
        if felt >= 26:
            climate_tags = {"Fresco", "Ligero"}
        elif felt <= 18 or weather["precipitation"] > 0:
            climate_tags = {"Caliente", "Reconfortante"}
    habitual = Counter()
    for order in history:
        if order.get("state") == "Entregado" and not order.get("refunded"):
            try:
                if date.fromisoformat(order["day"]).weekday() == moment.weekday():
                    habitual.update(line["dish_id"] for line in order["lines"])
            except (KeyError,ValueError):
                continue
    meal = "Desayuno" if moment.hour < 11 else "Almuerzo" if moment.hour < 17 else "Cena"
    output = []
    for row in rows:
        tags = set(row.get("context_tags") or [])
        if context.get("mood") == "recovery" and "Sin alcohol" not in tags:
            continue
        reasons = [row.get("why", "Oferta disponible")]
        score = row.get("score", 0)
        matches = wanted & tags
        if matches:
            score += len(matches) * 2
            reasons.append("declarado por el negocio como " + ", ".join(sorted(matches)).lower())
        if climate_tags & tags:
            score += 2
            reasons.append("coincide con las condiciones meteorológicas consultadas")
        if row.get("occasion") == meal:
            score += 1
            reasons.append("opción para " + meal.lower())
        if habitual[row["dish_id"]] >= 3:
            score += 2
            reasons.append("elegido en al menos tres compras de este día de la semana")
        output.append({**row,"score":score,"why":" · ".join(filter(None,reasons))})
    return sorted(output, key=lambda r:(-r["score"],r["day"],r["price"],r["id"]))
