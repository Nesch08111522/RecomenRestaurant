"""Build and read the spreadsheet and Word menu templates."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

Document = Workbook = load_workbook = Font = PatternFill = None
DataValidation = WD_ORIENT = None
try:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:  # Keep the rest of the app available until extra packages are installed.
    pass


MENU_HEADERS = (
    "Nombre",
    "Precio (S/)",
    "Categoría",
    "Horario",
    "Descripción actual",
    "Ingredientes",
    "Información dietética",
    "Tiempo de preparación (min)",
    "Nivel de picante (0-5)",
)
MAX_MENU_ROWS = 40
MAX_MENU_TEXT = 30000
MAX_ARCHIVE_MEMBERS = 500
MAX_ARCHIVE_UNPACKED_BYTES = 25 * 1024 * 1024


class MenuDocumentError(ValueError):
    """The uploaded document is empty, malformed, or outside supported limits."""


def _require_document_packages() -> None:
    if any(package is None for package in (Document, Workbook, load_workbook, Font, PatternFill, DataValidation, WD_ORIENT)):
        raise MenuDocumentError("Instala las dependencias openpyxl y python-docx para usar plantillas Excel y Word.")


def build_menu_template(file_format: str) -> BytesIO:
    """Return a blank XLSX or DOCX template as a rewound in-memory stream."""
    _require_document_packages()
    if file_format == "xlsx":
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Carta"
        sheet.append(MENU_HEADERS)
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="FF385C")
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:I{MAX_MENU_ROWS + 1}"
        category_validation = DataValidation(type="list", formula1='"Entrada,Fondo,Postre,Bebida"', allow_blank=True)
        meal_validation = DataValidation(type="list", formula1='"desayuno,almuerzo,cena"', allow_blank=True)
        sheet.add_data_validation(category_validation)
        sheet.add_data_validation(meal_validation)
        category_validation.add(f"C2:C{MAX_MENU_ROWS + 1}")
        meal_validation.add(f"D2:D{MAX_MENU_ROWS + 1}")
        for column, width in zip("ABCDEFGHI", (28, 16, 18, 18, 48, 36, 32, 25, 22)):
            sheet.column_dimensions[column].width = width

        instructions = workbook.create_sheet("Instrucciones")
        instructions.append(("Cómo completar la plantilla",))
        instructions.append(("Agrega un plato por fila en la hoja Carta.",))
        instructions.append(("Nombre y precio son obligatorios. El precio debe ser numérico.",))
        instructions.append(("Categoría: Entrada, Fondo, Postre o Bebida.",))
        instructions.append(("Horario: desayuno, almuerzo o cena. Se puede dejar vacío.",))
        instructions.append(("Separa ingredientes e información dietética con comas.",))
        instructions.append(("Las descripciones sugeridas por Qwen se revisan antes de guardar.",))

        stream = BytesIO()
        workbook.save(stream)
        stream.seek(0)
        return stream

    if file_format == "docx":
        document = Document()
        section = document.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
        document.add_heading("Plantilla de carta del restaurante", 0)
        document.add_paragraph(
            "Completa una fila por plato. Nombre y precio son obligatorios. "
            "Agrega más filas si las necesitas. Deja en blanco los datos que no tengas; podrás revisar las sugerencias de Qwen antes de guardarlas."
        )
        word_headers = MENU_HEADERS[:7]
        table = document.add_table(rows=9, cols=len(word_headers))
        table.style = "Table Grid"
        for cell, header in zip(table.rows[0].cells, word_headers):
            cell.text = header
        document.add_paragraph("Categorías: Entrada, Fondo, Postre o Bebida.")
        document.add_paragraph("Horarios: desayuno, almuerzo o cena.")
        document.add_paragraph("Separa ingredientes e información dietética con comas.")
        stream = BytesIO()
        document.save(stream)
        stream.seek(0)
        return stream

    raise MenuDocumentError("Formato de plantilla no compatible.")


def _header_key(value: object) -> str:
    text = " ".join(str(value or "").strip().lower().replace("\n", " ").split())
    return text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


_HEADER_ALIASES = {
    "name": {"nombre", "nombre del plato", "plato", "dish", "dish name"},
    "price": {"precio", "precio (s/)", "precio s/", "price", "price (s/)"},
    "category": {"categoria", "tipo", "tipo de plato", "category"},
    "meal_time": {"horario", "tiempo de comida", "meal time"},
    "description": {"descripcion actual", "descripcion", "description"},
    "ingredients": {"ingredientes", "ingredients"},
    "dietary_info": {"informacion dietetica", "info dietetica", "dietary info"},
    "preparation_time": {"tiempo de preparacion (min)", "tiempo de preparacion", "preparation time"},
    "spiciness": {"nivel de picante (0-5)", "nivel de picante", "picante", "spiciness"},
}
_HEADER_LOOKUP = {alias: field for field, aliases in _HEADER_ALIASES.items() for alias in aliases}


def _canonical_header(value: object) -> str | None:
    return _HEADER_LOOKUP.get(_header_key(value))


def _clean_cell(value: object, limit: int = 1000) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())[:limit]


def _rows_to_records(rows) -> list[dict]:
    rows = list(rows)
    if not rows:
        raise MenuDocumentError("La plantilla no contiene una tabla con platos.")

    header_row_index = None
    fields = []
    for index, row in enumerate(rows[:5]):
        candidate_fields = [_canonical_header(value) for value in row]
        if "name" in candidate_fields and "price" in candidate_fields:
            header_row_index = index
            fields = candidate_fields
            break
    if header_row_index is None:
        raise MenuDocumentError("No encontré las columnas Nombre y Precio de la plantilla.")

    records = []
    total_chars = 0
    for row in rows[header_row_index + 1:]:
        values = {}
        for field, value in zip(fields, row):
            if field:
                values[field] = _clean_cell(value)
        if not any(values.values()):
            continue
        if not values.get("name") and not values.get("price"):
            continue
        records.append({
            "name": values.get("name", "")[:120],
            "price": values.get("price", "")[:40],
            "category": values.get("category", "")[:60],
            "meal_time": values.get("meal_time", "")[:30],
            "description": values.get("description", "")[:500],
            "ingredients": values.get("ingredients", "")[:500],
            "dietary_info": values.get("dietary_info", "")[:300],
            "preparation_time": values.get("preparation_time", "")[:20],
            "spiciness": values.get("spiciness", "")[:10],
        })
        total_chars += sum(len(value) for value in records[-1].values())
        if len(records) > MAX_MENU_ROWS:
            raise MenuDocumentError(f"La plantilla admite hasta {MAX_MENU_ROWS} platos por carga.")
        if total_chars > MAX_MENU_TEXT:
            raise MenuDocumentError("El texto de la plantilla supera el límite permitido.")

    if not records:
        raise MenuDocumentError("Agrega al menos un plato debajo de los encabezados.")
    for index, record in enumerate(records, start=1):
        if not record["name"]:
            raise MenuDocumentError(f"Falta el nombre del plato en la fila {index + 1}.")
        if not record["price"]:
            raise MenuDocumentError(f"Falta el precio de {record['name']}.")
        try:
            price_text = record["price"].lower().replace("s/.", "").replace("s/", "").strip()
            price = float(price_text.replace(",", "."))
        except ValueError as exc:
            raise MenuDocumentError(f"El precio de {record['name']} debe ser numérico.") from exc
        if not 0 <= price <= 100000:
            raise MenuDocumentError(f"El precio de {record['name']} debe estar entre 0 y 100000.")
        record["price"] = round(price, 2)
    return records


def read_menu_document(file_stream, filename: str) -> list[dict]:
    """Extract bounded, normalized menu rows from XLSX or DOCX in memory."""
    _require_document_packages()
    suffix = Path(filename or "").suffix.lower()
    file_stream.seek(0)
    try:
        with ZipFile(file_stream) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise MenuDocumentError("El archivo contiene demasiados elementos para procesarlo.")
            if sum(member.file_size for member in members) > MAX_ARCHIVE_UNPACKED_BYTES:
                raise MenuDocumentError("El contenido descomprimido supera el límite permitido.")
    except MenuDocumentError:
        raise
    except (BadZipFile, OSError) as exc:
        raise MenuDocumentError("El archivo no es un Excel o Word válido. Descarga una plantilla nueva.") from exc
    finally:
        file_stream.seek(0)

    if suffix == ".xlsx":
        workbook = None
        try:
            workbook = load_workbook(file_stream, read_only=True, data_only=True)
            sheet = workbook["Carta"] if "Carta" in workbook.sheetnames else workbook.active
            rows = sheet.iter_rows(values_only=True)
            return _rows_to_records(rows)
        except MenuDocumentError:
            raise
        except Exception as exc:
            raise MenuDocumentError("No pude leer el archivo Excel. Descarga una plantilla nueva e inténtalo otra vez.") from exc
        finally:
            if workbook is not None:
                workbook.close()
    if suffix == ".docx":
        try:
            document = Document(file_stream)
            if not document.tables:
                raise MenuDocumentError("El documento Word no contiene la tabla de la plantilla.")
            rows = ([cell.text for cell in row.cells] for row in document.tables[0].rows)
            return _rows_to_records(rows)
        except MenuDocumentError:
            raise
        except Exception as exc:
            raise MenuDocumentError("No pude leer el archivo Word. Descarga una plantilla nueva e inténtalo otra vez.") from exc
    raise MenuDocumentError("Sube un archivo .xlsx o .docx.")

