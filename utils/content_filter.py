# utils/content_filter.py
"""
Filtro de contenido por diccionario (primera capa de moderación).

Principio: el diccionario solo puede decir "esto está mal" o "no sé".
Solo aprueba cuando además ENTIENDE el texto (idioma/alfabeto reconocido).
Todo lo demás se deriva a la IA (ASK_AI) o a un humano (HUMAN).

    result = ContentFilter.check_content(text)
    route  = ContentFilter.triage(result, missing_fields=missing)
    # route: "HUMAN" | "AUTO_OK" | "ASK_AI"

    # o todo junto:
    result, route = ContentFilter.evaluate(text, missing_fields=missing)
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Any

__all__ = ["ContentFilter", "normalize", "deobfuscate"]

HUMAN, AUTO_OK, ASK_AI = "HUMAN", "AUTO_OK", "ASK_AI"

# ---------------------------------------------------------------------------
# Normalización y anti-evasión (cacheadas: textos repetidos cuestan ~0)
# ---------------------------------------------------------------------------

_REPEAT_RE = re.compile(r"(.)\1{2,}")
_DESPACE_RE = re.compile(r"\b(?:\w[\s.\-_*]){2,}\w\b")
_SEP_RE = re.compile(r"[\s.\-_*]")
_TOKEN_RE = re.compile(r"[a-z]+")

LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)

# Cirílico/griego que se parece a letras latinas (aplicado tras .lower()).
HOMOGLYPHS = {
    0x0430: "a",
    0x0435: "e",
    0x043E: "o",
    0x0440: "p",
    0x0441: "c",
    0x0445: "x",
    0x0443: "y",
    0x0456: "i",
    0x0455: "s",
    0x043A: "k",
    0x03BF: "o",
    0x03B1: "a",
}


@lru_cache(maxsize=4096)
def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _REPEAT_RE.sub(r"\1", text)


def normalize(text: Any) -> str:
    """minúsculas, sin tildes, full-width -> ASCII, 'puuuta' -> 'puta'."""
    return _normalize(str(text or ""))


@lru_cache(maxsize=4096)
def _deobfuscate(raw: str) -> str:
    t = raw.lower().translate(HOMOGLYPHS)
    t = _DESPACE_RE.sub(lambda m: _SEP_RE.sub("", m.group()), t)  # 'p.u.t.a' -> 'puta'
    return _normalize(t.translate(LEET))


def deobfuscate(raw: Any) -> str:
    return _deobfuscate(str(raw or ""))


def _is_latin(ch: str) -> bool:
    """Chequeo por rango Unicode (mucho más rápido que unicodedata.name)."""
    o = ord(ch)
    return o < 0x250 or 0x1E00 <= o <= 0x1EFF or 0xFF21 <= o <= 0xFF5A


def non_latin_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(not _is_latin(c) for c in letters) / len(letters)


def has_mixed_script(text: str) -> bool:
    """True si alguna palabra mezcla letras latinas y no latinas (homoglifos)."""
    for word in str(text or "").split():
        flags = {_is_latin(c) for c in word if c.isalpha()}
        if len(flags) == 2:
            return True
    return False


# ---------------------------------------------------------------------------
# Listas (patrones SIN tildes; se aplican sobre texto normalizado)
# ---------------------------------------------------------------------------

BANNED_PATTERNS: dict[str, list[str]] = {
    # Siempre a revisión humana
    "critical": [
        r"pedofil\w*",
        r"pedophil\w*",
        r"incest\w*",
        r"terroris\w*",
        r"nazis?",
        r"nazismo",
        r"neonazi\w*",
        r"hitler",
        r"genocid\w*",
        r"suicid\w*",
        r"porn\w*",
    ],
    # Insultos graves, drogas duras (ES / EN / PT)
    "high": [
        r"put[ao]s?",
        r"zorras?",
        r"malparid\w*",
        r"cocaina",
        r"heroina",
        r"marihuana",
        r"violacion\w*",
        r"violador\w*",
        r"mierda",
        r"cabron\w*",
        r"pendej\w*",
        r"hijueputa",
        r"hdp",
        r"joder",
        r"jodid\w*",
        r"fuck\w*",
        r"shit\w*",
        r"bitch\w*",
        r"cunt\w*",
        r"asshole\w*",
        r"whore\w*",
        r"slut\w*",
        r"bastard\w*",
        r"nigg\w*",
        r"fag(?:got)?s?",
        r"rapist\w*",
        r"cocaine",
        r"heroin",
        r"marijuana",
        r"meth",
        r"caralho",
        r"merda",
        r"buceta",
        r"porra",
        r"fodas?",
        r"viado",
    ],
    # Dependen del contexto (platos, promos): se derivan a la IA
    "context": [
        r"muert\w*",
        r"mat(?:a|ar|an|anza)",
        r"asesin\w*",
        r"sangre",
        r"sangue",
        r"armas?",
        r"pistolas?",
        r"droga\w*",
        r"odio",
        r"violencia",
        r"racis\w*",
        r"discriminacion",
        r"sexo",
        r"sexual\w*",
        r"maldit[ao]s?",
        r"morte",
        r"kill\w*",
        r"murder\w*",
        r"blood\w*",
        r"guns?",
        r"weapons?",
        r"drugs?",
        r"hate",
        r"death",
        r"dead",
        r"sex",
        r"nude",
        r"naked",
    ],
}

_LEVELS = tuple(BANNED_PATTERNS)
BANNED_RE = {
    lvl: re.compile(r"\b(?:%s)\b" % "|".join(pats))
    for lvl, pats in BANNED_PATTERNS.items()
}

# Frases legítimas con palabras de contexto; se eliminan antes de buscar.
SAFE_PHRASES = [
    "muerte por chocolate",
    "death by chocolate",
    "matar el hambre",
    "mata el hambre",
    "mata hambre",
    "arma tu",
    "arma tus",
    "blood orange",
    "blood sausage",
    "bloody mary",
]
SAFE_RE = re.compile(
    r"\b(?:%s)\b"
    % "|".join(
        sorted((re.escape(normalize(p)) for p in SAFE_PHRASES), key=len, reverse=True)
    )
)


def _strip_safe(norm: str) -> str:
    return SAFE_RE.sub(" ", norm)


def _scan_clean(clean: str) -> dict[str, list[str]]:
    """Escanea texto YA normalizado y sin frases seguras."""
    return {lvl: sorted(set(BANNED_RE[lvl].findall(clean))) for lvl in _LEVELS}


def _hard(sev: dict[str, list[str]]) -> set[str]:
    return set(sev["critical"]) | set(sev["high"])


# ---------------------------------------------------------------------------
# Vocabulario culinario / idioma
# ---------------------------------------------------------------------------

FOOD_STRONG = frozenset(
    normalize(w)
    for w in [
        "restaurante",
        "restaurant",
        "comida",
        "cocina",
        "chef",
        "plato",
        "menu",
        "carta",
        "desayuno",
        "almuerzo",
        "cena",
        "postre",
        "bebida",
        "gourmet",
        "carne",
        "pollo",
        "pescado",
        "marisco",
        "mariscos",
        "verdura",
        "fruta",
        "queso",
        "pasta",
        "pizza",
        "sushi",
        "taco",
        "ceviche",
        "ramen",
        "hamburguesa",
        "papas",
        "helado",
        "chocolate",
        "ajo",
        "brasa",
        "arroz",
        "frijoles",
        "cebolla",
        "aji",
        "limon",
        "camarones",
        "pulpo",
        "caldo",
        "sopa",
        "ensalada",
        "guiso",
        "tallarin",
        "lomo",
        "saltado",
        "chaufa",
        "rocoto",
        "quinua",
        "cabrito",
        "parrilla",
        "polleria",
        "cevicheria",
        "chifa",
        "criollo",
        "criolla",
        "norteno",
        "italiana",
        "japonesa",
        "mexicana",
        "cafe",
        "jugo",
        "jugos",
        "chicha",
        "pisco",
        "sour",
        "cerveza",
        "vino",
        "vinos",
        "tragos",
        "capuchino",
        "latte",
        "refresco",
        "entrada",
        "comer",
        "almorzar",
        "cenar",
        "degustar",
        "sabor",
        "sabroso",
        "delicioso",
        "receta",
        "ingrediente",
        "bar",
        "pasteleria",
        "panaderia",
        "pan",
        "huevo",
        "huevos",
        "salsa",
        "anticucho",
        "anticuchos",
        "empanada",
    ]
)  # ojo: "te" fuera a propósito (es pronombre: "te invitamos")

FOOD_WEAK = frozenset(
    normalize(w)
    for w in [
        "precio",
        "calidad",
        "servicio",
        "familia",
        "familiar",
        "amigos",
        "pareja",
        "especial",
        "delivery",
        "wifi",
        "terraza",
        "reserva",
        "reservas",
        "parking",
        "estacionamiento",
        "fresco",
        "casero",
        "tradicional",
        "autentico",
        "ambiente",
        "atencion",
        "local",
        "lugar",
        "fusion",
        "tradicion",
        "mesa",
    ]
)

STOPWORDS_ES = frozenset(
    {
        "de",
        "la",
        "el",
        "en",
        "y",
        "con",
        "para",
        "por",
        "los",
        "las",
        "un",
        "una",
        "del",
        "al",
        "se",
        "que",
        "es",
        "muy",
        "su",
        "sus",
        "a",
        "o",
        "tu",
        "mi",
        "nuestro",
        "nuestra",
        "nuestros",
        "nuestras",
        "te",
        "lo",
        "como",
        "mas",
        "no",
        "si",
        "ni",
        "ya",
        "e",
        "u",
        "le",
        "les",
        "nos",
        "este",
        "esta",
        "estos",
        "estas",
        "ese",
        "esa",
        "hay",
        "son",
        "ser",
        "desde",
        "hasta",
        "sobre",
        "entre",
        "sin",
        "tambien",
        "pero",
        "mejor",
        "donde",
        "cada",
        "todo",
        "toda",
        "todos",
        "todas",
        "ofrecemos",
        "tenemos",
        "disfruta",
        "ven",
        "visitanos",
        "somos",
        "estamos",
        "ubicado",
        "ubicada",
        "tus",
        "dos",
        "tres",
        "mas",
    }
)

# Palabras funcionales de inglés/portugués (sin falsos amigos del español como "dos").
FOREIGN_MARKERS = frozenset(
    {
        "the",
        "and",
        "with",
        "of",
        "in",
        "is",
        "are",
        "for",
        "our",
        "your",
        "you",
        "this",
        "that",
        "from",
        "at",
        "we",
        "it",
        "by",
        "on",
        "best",
        "town",
        "owned",
        "good",
        "great",
        "muito",
        "nosso",
        "nossa",
        "uma",
        "com",
        "das",
        "em",
        "voce",
        "nao",
        "os",
        "as",
        "da",
        "do",
    }
)


@lru_cache(maxsize=8192)
def _classify(token: str) -> tuple[bool, bool, bool]:
    """(es_comida_fuerte, es_comida_débil, es_conocida) con plural -s / -es."""
    stems = [token]
    if token.endswith("s"):
        stems.append(token[:-1])
    if token.endswith("es"):
        stems.append(token[:-2])
    strong = any(s in FOOD_STRONG for s in stems)
    weak = any(s in FOOD_WEAK for s in stems)
    known = strong or weak or any(s in STOPWORDS_ES for s in stems)
    return strong, weak, known


# ---------------------------------------------------------------------------
# Filtro
# ---------------------------------------------------------------------------

_EMPTY_COVERAGE = {
    "script_ratio": 0,
    "known_ratio": 0,
    "foreign_markers": 0,
    "unknown_language": True,
}


class ContentFilter:
    """Detecta contenido inapropiado y no culinario, sin aprobar lo que no entiende."""

    BANNED_PATTERNS = BANNED_PATTERNS
    FOOD_STRONG = FOOD_STRONG
    FOOD_WEAK = FOOD_WEAK

    @staticmethod
    def _coverage(
        raw: str, n_tokens: int, known: int, foreign_hits: int
    ) -> dict[str, Any]:
        script_ratio = non_latin_ratio(raw)
        known_ratio = known / n_tokens if n_tokens else 0.0
        foreign = n_tokens > 0 and (foreign_hits >= 2 or foreign_hits / n_tokens >= 0.2)
        unknown = (
            script_ratio > 0.10
            or n_tokens == 0
            or foreign
            or (n_tokens >= 3 and known_ratio < 0.25)
        )
        return {
            "script_ratio": round(script_ratio, 2),
            "known_ratio": round(known_ratio, 2),
            "foreign_markers": foreign_hits,
            "unknown_language": unknown,
        }

    @classmethod
    def detect_evasion(
        cls, raw: str, plain_severity: dict | None = None
    ) -> tuple[bool, set[str]]:
        """
        (hay_evasión, palabras_graves_ocultas).
        Evasión = palabra grave que solo aparece tras desofuscar, o alfabetos mezclados.
        """
        raw = str(raw or "")
        plain = plain_severity or _scan_clean(_strip_safe(normalize(raw)))
        deob = _deobfuscate(raw)
        hidden = (
            _hard(_scan_clean(_strip_safe(deob))) - _hard(plain)
            if deob != normalize(raw)
            else set()
        )
        return bool(hidden) or has_mixed_script(raw), hidden

    @classmethod
    def check_content(cls, text: str) -> dict[str, Any]:
        raw = str(text or "")
        if not raw.strip():
            return {
                "is_appropriate": True,
                "needs_context_review": False,
                "is_food_related": False,
                "banned_words": [],
                "context_words": [],
                "severity": {"critical": [], "high": [], "context": []},
                "food_score": 0,
                "food_words_found": [],
                "coverage": dict(_EMPTY_COVERAGE),
                "evasion_suspected": False,
                "dictionary_can_judge": False,
                "issues": ["El contenido está vacío"],
                "notes": [],
                "suggestions": ["El contenido está vacío"],
            }

        clean = _strip_safe(normalize(raw))  # normaliza y quita frases seguras UNA vez
        severity = _scan_clean(clean)
        evasion, hidden = cls.detect_evasion(raw, severity)

        banned_words = sorted(
            set(severity["critical"]) | set(severity["high"]) | hidden
        )
        context_words = severity["context"]

        # Una sola pasada sobre los tokens
        strong: set[str] = set()
        weak: set[str] = set()
        known = foreign_hits = n_tokens = 0
        for t in _TOKEN_RE.findall(clean):
            n_tokens += 1
            s, w, k = _classify(t)
            known += k
            foreign_hits += t in FOREIGN_MARKERS
            if s:
                strong.add(t)
            elif w:
                weak.add(t)

        denom = max(3, min(n_tokens, 15))  # textos largos no se penalizan
        score = min(100.0, (len(strong) + 0.3 * len(weak)) / denom * 100)

        coverage = cls._coverage(raw, n_tokens, known, foreign_hits)
        can_judge = not coverage["unknown_language"]

        issues: list[str] = []
        notes: list[str] = []
        if banned_words:
            issues.append(f"Lenguaje inapropiado: {', '.join(banned_words)}")
        if context_words:
            issues.append(f"Revisar contexto de: {', '.join(context_words)}")
        if evasion:
            issues.append(
                "Posible intento de evasión del filtro (texto ofuscado o alfabetos mezclados)"
            )
        if can_judge and n_tokens > 5 and score < 15:
            issues.append("Parece no estar relacionado con comida")
        if not can_judge:
            notes.append(
                "Idioma o alfabeto no reconocido por el diccionario; requiere análisis con IA"
            )
        elif not issues and score > 20:
            notes.append("Contenido culinario verificado")

        return {
            "is_appropriate": not banned_words,
            "needs_context_review": bool(context_words),
            "is_food_related": score > 15,
            "banned_words": banned_words,
            "context_words": context_words,
            "severity": severity,
            "food_score": round(score, 2),
            "food_words_found": sorted(strong)[:5],
            "coverage": coverage,
            "evasion_suspected": evasion,
            "dictionary_can_judge": can_judge,
            "issues": issues,  # problemas reales (marcan el contenido)
            "notes": notes,  # informativos (NO marcan)
            "suggestions": list(issues),  # compatibilidad con código anterior
        }

    @classmethod
    def triage(
        cls, result: dict[str, Any], missing_fields: list[str] | None = None
    ) -> str:
        """
        HUMAN   -> señal crítica/alta o evasión: revisión humana, sin gastar IA.
        AUTO_OK -> español reconocido, limpio, culinario y completo.
        ASK_AI  -> cualquier otro caso (idioma desconocido, contexto dudoso, score bajo).
        """
        if result["banned_words"] or result["evasion_suspected"]:
            return HUMAN
        if (
            result["dictionary_can_judge"]
            and not result["needs_context_review"]
            and result["is_food_related"]
            and not missing_fields
        ):
            return AUTO_OK
        return ASK_AI

    @classmethod
    def evaluate(
        cls, text: str, missing_fields: list[str] | None = None
    ) -> tuple[dict, str]:
        """Atajo: (resultado, ruta)."""
        result = cls.check_content(text)
        return result, cls.triage(result, missing_fields)

    @classmethod
    def filter_restaurant(cls, restaurant_data: dict) -> dict[str, Any]:
        """Filtra un restaurante completo (tolera campos None)."""
        data = restaurant_data or {}
        name = str(data.get("name") or "")
        description = str(data.get("description") or "")
        address = str(data.get("address") or "")
        tags = [str(t) for t in (data.get("tags") or [])]

        result = cls.check_content(f"{name} {description} {' '.join(tags)} {address}")
        issues = list(result["issues"])

        # Tags: solo escaneo de palabras graves (ya no se re-analiza todo el texto por tag).
        tag_results = []
        for tag in tags:
            ok = not (
                _hard(_scan_clean(_strip_safe(normalize(tag))))
                or _hard(_scan_clean(_strip_safe(_deobfuscate(tag))))
            )
            tag_results.append({"tag": tag, "is_appropriate": ok})
            if not ok:
                issues.append(f"Tag inapropiado: {tag}")

        missing = [
            f
            for f, v in (("name", name), ("description", description))
            if not v.strip()
        ]
        route = cls.triage(result, missing)
        if any(not t["is_appropriate"] for t in tag_results):
            route = HUMAN

        return {
            "name": name,
            "description": description,
            "tags": tag_results,
            "result": result,
            "route": route,
            "missing_fields": missing,
            "overall_appropriate": result["is_appropriate"],
            "overall_food_related": result["is_food_related"],
            "issues": issues,
            "is_ok": result["is_appropriate"]
            and result["is_food_related"]
            and not issues,
        }
