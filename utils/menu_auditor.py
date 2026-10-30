import re
import unicodedata
from collections.abc import Mapping

VERSION = "1.0.0"
LABELS = {
    "vegano": "vegano",
    "vegan": "vegano",
    "vegana": "vegano",
    "sin gluten": "sin_gluten",
    "gluten free": "sin_gluten",
    "celiaco": "sin_gluten",
    "celiaca": "sin_gluten",
    "sin lactosa": "sin_lactosa",
    "lactose free": "sin_lactosa",
}
CONFLICTS = {
    "vegano": {
        "pollo",
        "carne",
        "res",
        "cerdo",
        "pescado",
        "atun",
        "salmon",
        "huevo",
        "huevos",
        "leche",
        "queso",
        "mantequilla",
        "miel",
        "yogur",
        "yogurt",
        "camaron",
        "camarones",
        "langostino",
        "mariscos",
        "tocino",
        "jamon",
        "chorizo",
        "mayonesa",
    },
    "sin_gluten": {
        "trigo",
        "harina de trigo",
        "cebada",
        "centeno",
        "seitan",
        "pan de trigo",
        "pasta de trigo",
        "fideos de trigo",
    },
    "sin_lactosa": {
        "leche",
        "leche evaporada",
        "leche condensada",
        "crema de leche",
        "queso",
        "queso fresco",
        "mantequilla",
        "yogur",
        "yogurt",
        "nata",
    },
}
AMBIGUOUS = {
    "salsa",
    "aderezo",
    "crema",
    "mezcla",
    "masa",
    "pan",
    "pasta",
    "fideos",
    "sillao",
    "salsa de soya",
    "mayonesa vegana",
}


def _norm(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value).strip()


def _items(value):
    if isinstance(value, str):
        value = re.split(r"[,;\n]", value)
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v).strip() for v in value[:100] if isinstance(v, str) and v.strip()]


def _matches(ingredient, word):
    return bool(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", ingredient))


def _explicit_exception(ingredient, label):
    if label == "sin_lactosa" and (
        "sin lactosa" in ingredient or "deslactosad" in ingredient
    ):
        return True
    if label == "vegano" and any(
        x in ingredient
        for x in (
            "vegano",
            "vegana",
            "vegetal",
            "de soya",
            "de soja",
            "sin huevo",
            "sin leche",
        )
    ):
        return True
    if label == "sin_gluten" and "sin gluten" in ingredient:
        return True
    return False


def auditar_plato(plato):
    if not isinstance(plato, Mapping):
        raise TypeError("El plato debe ser un diccionario.")
    nombre = str(plato.get("name") or "").strip()[:160]
    descripcion = str(plato.get("description") or "").strip()
    ingredientes = _items(plato.get("ingredients"))
    etiquetas = _items(plato.get("dietary_info"))
    observaciones = []

    def add(code, level, field, message, suggestion):
        observaciones.append(
            {
                "code": code,
                "severity": level,
                "field": field,
                "reason": message,
                "recommendation": suggestion,
            }
        )

    if not nombre:
        add(
            "missing_name",
            "mejora",
            "name",
            "Falta el nombre del plato.",
            "Agrega un nombre claro.",
        )
    if not descripcion:
        add(
            "missing_description",
            "mejora",
            "description",
            "Puedes agregar una descripción del plato.",
            "Es opcional y ayuda a tus clientes a conocerlo.",
        )
    if not ingredientes:
        add(
            "missing_ingredients",
            "informativa",
            "ingredients",
            "No se registraron ingredientes.",
            "Solicita al empresario que confirme los ingredientes reales.",
        )

    normalized_ingredients = [_norm(x) for x in ingredientes]
    detected = []
    for raw_label in etiquetas:
        label = LABELS.get(_norm(raw_label))
        if not label:
            continue
        if label in detected:
            continue
        detected.append(label)
        if not ingredientes:
            add(
                "unverifiable_label",
                "informativa",
                "dietary_info",
                f"No es posible comprobar la etiqueta «{raw_label}» sin ingredientes.",
                "Mantén la etiqueta sin verificar hasta que el empresario complete los datos.",
            )
            continue
        conflicts = []
        uncertain = []
        for original, normalized in zip(ingredientes, normalized_ingredients):
            if _explicit_exception(normalized, label):
                uncertain.append(original)
                continue
            if any(_matches(normalized, token) for token in CONFLICTS[label]):
                conflicts.append(original)
            elif any(_matches(normalized, token) for token in AMBIGUOUS):
                uncertain.append(original)
        if conflicts:
            add(
                "dietary_contradiction",
                "contradiccion",
                "dietary_info",
                f'La etiqueta «{raw_label}» contradice ingredientes declarados: {", ".join(conflicts)}.',
                "Retira la etiqueta si mantienes la receta, o sustituye los ingredientes incompatibles y confirma la nueva preparación.",
            )
        if uncertain:
            add(
                "ambiguous_ingredients",
                "informativa",
                "ingredients",
                f'Para «{raw_label}» falta aclarar la composición de: {", ".join(uncertain)}.',
                "Consulta los ingredientes de esa preparación antes de mantener la etiqueta.",
            )
        if not conflicts and not uncertain:
            add(
                "not_certified",
                "informativa",
                "dietary_info",
                f"«{raw_label}»: sin contradicciones detectadas en los ingredientes registrados.",
                "Verificación orientativa.",
            )

    has_conflict = any(x["severity"] == "contradiccion" for x in observaciones)
    has_uncertainty = any(
        x["code"] in ("unverifiable_label", "ambiguous_ingredients")
        for x in observaciones
    )
    status = (
        "incoherente"
        if has_conflict
        else (
            "desconocido"
            if has_uncertainty or not ingredientes
            else "sin_contradicciones_evidentes"
        )
    )
    return {
        "dish_id": plato.get("id"),
        "name": nombre,
        "version": VERSION,
        "result": status,
        "publication_action": (
            "revisar_etiqueta"
            if has_conflict
            else "permitir_sin_verificacion_dietetica" if etiquetas else "permitir"
        ),
        "requires_admin_review": has_conflict,
        "requires_owner_confirmation": has_conflict
        or has_uncertainty
        or not ingredientes,
        "observations": observaciones,
        "disclaimer": "Evaluación informativa basada en datos declarados; no certifica seguridad, higiene ni ausencia de alérgenos.",
    }


def auditar_menu(platos):
    if not isinstance(platos, (list, tuple)):
        raise TypeError("El menú debe ser una lista de platos.")
    if len(platos) > 500:
        raise ValueError("Máximo 500 platos por auditoría.")
    resultados = [auditar_plato(p) for p in platos]
    return {
        "total": len(resultados),
        "incoherentes": sum(r["result"] == "incoherente" for r in resultados),
        "desconocidos": sum(r["result"] == "desconocido" for r in resultados),
        "results": resultados,
    }
