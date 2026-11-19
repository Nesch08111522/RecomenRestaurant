from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import openpyxl
import pytest

from utils.catalog_workbook import build_catalog_workbook, validate_catalog_workbook


EXPECTED_SHEETS = {
    "Negocios",
    "Sucursales",
    "Categorias",
    "Platos",
    "Ingredientes",
    "Recetas",
    "Variantes",
    "Precios",
    "Inventario",
    "Mesas",
    "Instrucciones",
    "Restaurantes",
    "Ejemplos",
}


def make_book(rows_by_sheet: dict[str, list[dict[str, object]]]) -> bytes:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for sheet, rows in rows_by_sheet.items():
        worksheet = workbook.create_sheet(sheet)
        headers = list(rows[0]) if rows else []
        worksheet.append(headers)
        for row in rows:
            worksheet.append([row.get(header) for header in headers])
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_builder_has_all_sheets_canonical_headers_and_premium_usability():
    raw = build_catalog_workbook()
    assert isinstance(raw, BytesIO)
    assert raw.getbuffer().nbytes <= 5 * 1024 * 1024
    workbook = openpyxl.load_workbook(BytesIO(raw.getvalue()), data_only=False)
    assert set(workbook.sheetnames) == EXPECTED_SHEETS
    assert workbook["Negocios"].freeze_panes == "A2"
    assert workbook["Negocios"].auto_filter.ref
    assert workbook["Negocios"]["A1"].value == "ref"
    assert workbook["Platos"]["Q1"].value == "video"
    assert workbook["Instrucciones"].max_row >= 5


def test_template_does_not_import_an_example_business_and_is_valid_empty():
    result = validate_catalog_workbook(build_catalog_workbook().getvalue())
    assert result["errors"] == []
    assert result["rows"] == []
    assert result["can_import"] is True
    assert result["counts"]["total"] == 0


def test_validate_aliases_defaults_lists_money_booleans_and_json_safe_rows():
    raw = make_book(
        {
            "Negocios": [{"Referencia": "neg-1", "Nombre": "Mi negocio"}],
            "Sucursales": [{"ref": "s-1", "business_ref": "neg-1", "name": "Centro", "address": "Calle 1", "district": "Centro"}],
            "Categorias": [{"ref": "cat-1", "branch_ref": "s-1", "name": "Platos"}],
            "Ingredientes": [{"ref": "ing-1", "branch_ref": "s-1", "name": "Arroz", "alérgenos": "gluten, huevo"}],
            "Platos": [
                {
                    "ref": "p-1",
                    "branch_ref": "",
                    "name": "Arroz",
                    "product_type": "plato",
                    "category_ref": "cat-1",
                    "price": "18.35",
                    "ingredients": "arroz, pollo",
                    "allergens": "gluten",
                    "ingredients_confirmed": "sí",
                    "allergens_confirmed": "no",
                    "availability": "available",
                    "menu_type": "carta",
                }
            ],
        }
    )
    result = validate_catalog_workbook(raw)
    assert result["errors"] == []
    plate = next(item["data"] for item in result["rows"] if item["sheet"] == "Platos")
    assert plate["branch_ref"] == "actual"
    assert plate["price"] == "18.35"
    assert plate["ingredients"] == ["arroz", "pollo"]
    assert plate["allergens"] == ["gluten"]
    assert plate["ingredients_confirmed"] is True
    assert plate["allergens_confirmed"] is False
    assert result["can_import"] is True


def test_unknown_columns_are_reported_and_not_silently_dropped():
    raw = make_book({"Negocios": [{"ref": "n-1", "name": "X", "columna_nueva": "dato"}]})
    result = validate_catalog_workbook(raw)
    assert any(error["field"] == "columna_nueva" and "desconocida" in error["message"] for error in result["errors"])
    assert result["can_import"] is False


@pytest.mark.parametrize("value", ["nan", "NaN", "Infinity", "-Infinity", "-1", "10.001", True])
def test_money_is_exact_nonnegative_and_finite(value):
    raw = make_book({"Platos": [{"ref": "p-1", "branch_ref": "actual", "name": "X", "product_type": "plato", "price": value}]})
    result = validate_catalog_workbook(raw)
    assert any(error["field"] == "price" for error in result["errors"])


def test_boolean_requires_explicit_yes_or_no_and_invalid_date_blocks_import():
    raw = make_book(
        {
            "Platos": [
                {
                    "ref": "p-1",
                    "branch_ref": "actual",
                    "name": "X",
                    "product_type": "plato",
                    "ingredients_confirmed": "quizá",
                    "menu_date": "31/02/2026",
                }
            ]
        }
    )
    result = validate_catalog_workbook(raw)
    assert any(error["field"] == "ingredients_confirmed" for error in result["errors"])
    assert any(error["field"] == "menu_date" for error in result["errors"])
    assert result["can_import"] is False


def test_references_duplicates_existing_tenant_refs_and_cycles_are_detected():
    raw = make_book(
        {
            "Categorias": [
                {"ref": "cat-a", "branch_ref": "actual", "name": "A", "parent_ref": "cat-b"},
                {"ref": "cat-b", "branch_ref": "actual", "name": "B", "parent_ref": "cat-a"},
            ],
            "Platos": [
                {"ref": "p-1", "branch_ref": "actual", "name": "Tacos", "product_type": "plato", "category_ref": "missing"},
                {"ref": "p-1", "branch_ref": "actual", "name": "Tacos", "product_type": "plato"},
            ],
        }
    )
    result = validate_catalog_workbook(raw, {"Platos": {"p-1"}})
    messages = " ".join(error["message"] for error in result["errors"])
    assert "referencia" in messages.lower()
    assert "ciclo" in messages.lower()
    assert any("duplic" in warning["message"].lower() for warning in result["warnings"] + result["errors"])
    assert result["can_import"] is False


def test_cross_sheet_foreign_keys_and_allowed_enums_are_strict():
    raw = make_book(
        {
            "Platos": [{"ref": "p-1", "branch_ref": "unknown", "name": "X", "product_type": "pizza", "availability": "hidden", "menu_type": "menu"}],
            "Recetas": [{"product_ref": "missing", "ingredient_ref": "missing", "quantity": "1", "unit": "oz"}],
        }
    )
    result = validate_catalog_workbook(raw)
    assert result["can_import"] is False
    assert len(result["errors"]) >= 4


def test_workbook_rejects_macro_external_links_formulas_and_unsafe_zip():
    formula_raw = make_book({"Negocios": [{"ref": "n-1", "name": "=1+1"}]})
    formula_result = validate_catalog_workbook(formula_raw)
    assert any("fórmula" in error["message"].lower() for error in formula_result["errors"])

    unsafe = BytesIO()
    with ZipFile(unsafe, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/vbaProject.bin", b"macro")
    result = validate_catalog_workbook(unsafe.getvalue())
    assert result["can_import"] is False
    assert result["errors"]


def test_total_rows_are_limited_without_loading_more_than_the_cap():
    rows = [{"ref": f"n-{index}", "name": "N"} for index in range(1501)]
    raw = make_book({"Negocios": rows})
    result = validate_catalog_workbook(raw)
    assert result["can_import"] is False
    assert any("1500" in error["message"] for error in result["errors"])
