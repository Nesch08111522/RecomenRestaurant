import re
from pathlib import Path

from jinja2 import Environment


def test_table_plan_treats_zero_coordinates_as_valid_positions():
    template_path = Path(__file__).resolve().parents[1] / "templates/salon/desk.html"
    source = template_path.read_text(encoding="utf-8")
    match = re.search(r"\{%\s*set positioned = (.*?)\s*%\}", source, re.DOTALL)
    assert match, "No se encontró la expresión de selección de mesas posicionadas"
    expression = match.group(1)
    rendered = Environment().from_string("{{ (" + expression + ")|length }}").render(
        zone_rows=[{"table": {"x": 0, "y": 0}}]
    )
    assert rendered == "1", "Las coordenadas 0% deben contar como una posición válida"


def test_table_plan_omits_tables_without_both_coordinates():
    template_path = Path(__file__).resolve().parents[1] / "templates/salon/desk.html"
    source = template_path.read_text(encoding="utf-8")
    match = re.search(r"\{%\s*set positioned = (.*?)\s*%\}", source, re.DOTALL)
    assert match, "No se encontró la expresión de selección de mesas posicionadas"
    expression = match.group(1)
    rendered = Environment().from_string("{{ (" + expression + ")|length }}").render(
        zone_rows=[{"table": {"x": 20, "y": None}}]
    )
    assert rendered == "0", "El plano requiere coordenadas X e Y"
