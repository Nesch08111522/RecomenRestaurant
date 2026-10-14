# pytest tests/ -v
import pytest
from utils.content_filter import ContentFilter, normalize

F = ContentFilter
route = lambda text, missing=None: F.triage(F.check_content(text), missing)


@pytest.mark.parametrize(
    "text",
    [
        "Ceviche fresco y parrilla familiar",
        "Postre muerte por chocolate con helado y fruta",
        "Sangrecita al ajo y pollo a la brasa",
        "Arma tu hamburguesa con papas y queso",
        "Matar el hambre con sopa y pan",
        "Dos ceviches y tres chicharrones",  # 'dos' no es portugués
    ],
)
def test_auto_ok(text):
    r = F.check_content(text)
    assert r["banned_words"] == [] and r["context_words"] == []
    assert route(text) == "AUTO_OK"


@pytest.mark.parametrize(
    "text",
    [
        "pizza fucking shit",
        "Comida muito boa, que merda",
        "pedofilia",
        "puuuuta comida",
        "comida de cocaína",
        "comida de cocaina",
    ],
)
def test_goes_to_human(text):
    assert route(text) == "HUMAN"


@pytest.mark.parametrize(
    "text",
    [
        "p u t a comida",
        "p.u.t.a comida",
        "pu7a comida",
        "Сafé аmigos",
    ],
)
def test_evasion_detected(text):
    r = F.check_content(text)
    assert r["evasion_suspected"] is True
    assert route(text) == "HUMAN"


def test_hidden_word_is_reported():
    assert "puta" in F.check_content("p.u.t.a comida")["banned_words"]


@pytest.mark.parametrize(
    "text",
    [
        "Best ramen in town, family owned",
        "餐厅 美味 chifa",
        "Chaypi mikuna wasi sumaq mikhuy",
        "!!!",
    ],
)
def test_unknown_language_goes_to_ai(text):
    r = F.check_content(text)
    assert r["dictionary_can_judge"] is False
    assert route(text) == "ASK_AI"


def test_context_word_goes_to_ai():
    assert route("Hamburguesas asesinas del sabor y papas") == "ASK_AI"


@pytest.mark.parametrize(
    "text",
    [
        "Computadora reputación disputa",
        "Estudio custodio",
        "Farmacia sangrecita",
    ],
)
def test_no_substring_false_positives(text):
    r = F.check_content(text)
    assert r["banned_words"] == [] and r["context_words"] == []


def test_non_food_text_not_auto_approved():
    assert route("Venta de computadoras y reputación en línea") == "ASK_AI"


def test_notes_do_not_become_issues():
    r = F.check_content("Ceviche fresco y parrilla familiar")
    assert r["issues"] == [] and r["suggestions"] == [] and r["notes"]


def test_duplicate_words_not_counted_twice():
    assert (
        F.check_content("cafe cafe cafe")["food_score"]
        == F.check_content("cafe")["food_score"]
    )


def test_missing_fields_prevent_auto_ok():
    assert (
        F.triage(F.check_content("Ceviche fresco y parrilla familiar"), ["description"])
        == "ASK_AI"
    )


def test_empty_text():
    r = F.check_content("")
    assert r["dictionary_can_judge"] is False
    assert F.triage(r) == "ASK_AI"


def test_normalize():
    assert normalize("Cocaína") == "cocaina"
    assert normalize("puuuta") == "puta"
    assert normalize(None) == ""


def test_filter_restaurant_tolerates_none():
    out = F.filter_restaurant({"name": "Chifa Wong", "description": None, "tags": None})
    assert out["route"] == "ASK_AI" and out["missing_fields"] == ["description"]
    bad = F.filter_restaurant({"name": "X", "description": "comida", "tags": ["porno"]})
    assert bad["is_ok"] is False and bad["route"] == "HUMAN"


def test_filter_restaurant_clean_auto_ok():
    out = F.filter_restaurant(
        {
            "name": "Chifa Wong",
            "description": "Chaufa y lomo saltado criollo",
            "tags": ["chifa", "familiar"],
        }
    )
    assert out["route"] == "AUTO_OK" and out["is_ok"]
