"""Safe XLSX catalogue workbook builder and preview validator.

Generation has no database, network, AI, or environment dependencies.
Spanish category-name parsing performs a lazy, read-only registered-category lookup.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from typing import Any, Iterable, Mapping
from unicodedata import normalize as unicode_normalize
from zipfile import BadZipFile, ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation


MAX_XLSX_BYTES = 5 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_ZIP_RATIO = 100
MAX_ZIP_MEMBERS = 1000
MAX_TOTAL_ROWS = 1500

SHEETS: dict[str, tuple[str, ...]] = {
    "Restaurantes": ("ref", "name", "category_id", "district", "service_mode", "avg_price", "address", "phone", "description", "open_time", "close_time"),
    "Negocios": ("ref", "name", "description", "business_type"),
    "Sucursales": ("ref", "business_ref", "name", "address", "district", "lat", "lng", "open_time", "close_time"),
    "Categorias": ("ref", "branch_ref", "name", "parent_ref", "product_type"),
    "Platos": ("ref", "branch_ref", "name", "product_type", "category_ref", "description", "price", "portion", "ingredients", "allergens", "ingredients_confirmed", "allergens_confirmed", "availability", "menu_type", "menu_date", "image", "video"),
    "Ingredientes": ("ref", "branch_ref", "name", "allergens"),
    "Recetas": ("product_ref", "ingredient_ref", "quantity", "unit"),
    "Variantes": ("product_ref", "name", "portion", "price"),
    "Precios": ("product_ref", "price"),
    "Inventario": ("branch_ref", "ingredient_ref", "quantity", "unit", "cost", "basis", "expires", "lot"),
    "Mesas": ("ref", "branch_ref", "floor", "zone", "name", "capacity"),
}

# Header aliases are normalized before lookup: accents, case, whitespace and punctuation
# are ignored. English canonical names always win in the generated template.
_ALIASES: dict[str, set[str]] = {
    "ref": {"ref", "reference", "referencia", "id", "codigo", "código"},
    "name": {"name", "nombre", "nombre comercial", "nombre del negocio", "producto", "plato", "ingrediente", "categoria", "categoría"},
    "description": {"description", "descripcion", "descripción", "detalle"},
    "business_type": {"business_type", "tipo de negocio", "tipo negocio", "giro", "business type"},
    "business_ref": {"business_ref", "business reference", "negocio_ref", "referencia negocio", "negocio", "empresa"},
    "branch_ref": {"branch_ref", "branch reference", "sucursal_ref", "referencia sucursal", "sucursal", "local"},
    "address": {"address", "direccion", "dirección", "domicilio"},
    "district": {"district", "barrio", "colonia", "zona", "municipio"},
    "lat": {"lat", "latitude", "latitud"},
    "lng": {"lng", "lon", "longitude", "longitud"},
    "open_time": {"open_time", "opening time", "hora apertura", "apertura"},
    "close_time": {"close_time", "closing time", "hora cierre", "cierre"},
    "parent_ref": {"parent_ref", "parent reference", "categoria padre", "categoría padre", "padre_ref"},
    "product_type": {"product_type", "product type", "tipo producto", "tipo de producto", "tipo"},
    "category_ref": {"category_ref", "category reference", "categoria_ref", "categoría_ref", "referencia categoria", "referencia categoría"},
    "product_ref": {"product_ref", "product reference", "producto_ref", "referencia producto", "plato_ref"},
    "ingredient_ref": {"ingredient_ref", "ingredient reference", "ingrediente_ref", "referencia ingrediente"},
    "category": {"category", "categoria", "categoría"},
    "portion": {"portion", "porcion", "porción", "tamaño", "tamano"},
    "ingredients": {"ingredients", "ingredientes", "ingredient list", "lista ingredientes"},
    "allergens": {"allergens", "alergenos", "alérgenos", "alergenos list", "alérgenos list"},
    "ingredients_confirmed": {"ingredients_confirmed", "ingredients confirmed", "ingredientes confirmados", "ingredientes_confirmados"},
    "allergens_confirmed": {"allergens_confirmed", "allergens confirmed", "alergenos confirmados", "alérgenos confirmados", "alergenos_confirmed"},
    "availability": {"availability", "disponibilidad", "estado disponibilidad", "status"},
    "menu_type": {"menu_type", "menu type", "tipo menu", "tipo menú", "menu"},
    "menu_date": {"menu_date", "menu date", "fecha menu", "fecha menú", "fecha"},
    "image": {"image", "imagen", "foto", "url imagen", "image url"},
    "video": {"video", "url video", "video url"},
    "quantity": {"quantity", "cantidad"},
    "unit": {"unit", "unidad", "unidades"},
    "price": {"price", "precio", "importe"},
    "cost": {"cost", "costo", "coste"},
    "basis": {"basis", "base", "criterio"},
    "expires": {"expires", "expiration", "caduca", "vencimiento", "fecha caducidad", "fecha de caducidad"},
    "lot": {"lot", "lote"},
    "floor": {"floor", "piso", "nivel"},
    "zone": {"zone", "zona", "área", "area"},
    "capacity": {"capacity", "capacidad", "comensales"},
}


def _key(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicode_normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.lower())


_ALIASES.update({key: {key} for key in ("category_id", "service_mode", "avg_price", "phone")})
_ALIAS_INDEX: dict[str, str] = {}
for _canonical, _values in _ALIASES.items():
    for _value in {_canonical, *_values}:
        _ALIAS_INDEX[_key(_value)] = _canonical


def _message(sheet: str, row: int, field: str, text: str) -> dict[str, Any]:
    return {"sheet": sheet, "row": row, "field": field, "message": text}


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _text(value: Any) -> str | None:
    if _blank(value):
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value).strip()


def _list_text(value: Any) -> list[str]:
    if _blank(value):
        return []
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = re.split(r"[,;\n|]", str(value))
    return [str(item).strip() for item in values if not _blank(item)]


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or _blank(value):
        return None
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not result.is_finite() or result < 0:
        return None
    return result


def _money(value: Any) -> tuple[str | None, str | None]:
    if _blank(value):
        return None, None
    decimal = _decimal(value)
    if decimal is None:
        return None, "debe ser un número monetario no negativo y finito"
    cents = decimal.quantize(Decimal("0.01"))
    if cents != decimal:
        return None, "debe tener como máximo dos decimales"
    return format(cents, ".2f"), None


def _number(value: Any) -> tuple[str | None, str | None]:
    if _blank(value):
        return None, None
    decimal = _decimal(value)
    if decimal is None:
        return None, "debe ser un número no negativo y finito"
    rendered = format(decimal, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0", None


def _boolean(value: Any) -> tuple[bool | None, str | None]:
    if _blank(value):
        return None, None
    if not isinstance(value, str):
        return None, "debe ser exactamente yes/no o sí/no"
    normalized = _key(value)
    if normalized in {"yes", "si"}:
        return True, None
    if normalized == "no":
        return False, None
    return None, "debe ser exactamente yes/no o sí/no"


def _date(value: Any) -> tuple[str | None, str | None]:
    if _blank(value):
        return None, None
    if isinstance(value, datetime):
        return value.date().isoformat(), None
    if isinstance(value, date):
        return value.isoformat(), None
    text = str(value).strip()
    try:
        return date.fromisoformat(text).isoformat(), None
    except ValueError:
        # Dates in spreadsheet exports are frequently ISO datetimes; only accept
        # unambiguous ISO forms, never locale-dependent day/month swapping.
        try:
            return datetime.fromisoformat(text).date().isoformat(), None
        except ValueError:
            return None, "debe ser una fecha ISO válida (AAAA-MM-DD)"


def _time(value: Any) -> tuple[str | None, str | None]:
    if _blank(value):
        return None, None
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return value.strftime("%H:%M"), None
    text = str(value).strip()
    try:
        parsed = time.fromisoformat(text)
        return parsed.strftime("%H:%M"), None
    except ValueError:
        return None, "debe ser una hora válida HH:MM"


def _safe_zip(raw: bytes) -> tuple[ZipFile | None, list[str]]:
    errors: list[str] = []
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        return None, ["raw debe ser bytes"]
    raw_bytes = bytes(raw)
    if len(raw_bytes) > MAX_XLSX_BYTES:
        return None, ["el XLSX comprimido supera el límite de 5 MB"]
    try:
        archive = ZipFile(BytesIO(raw_bytes))
    except (BadZipFile, OSError, ValueError):
        return None, ["el archivo no es un XLSX ZIP válido"]
    infos = archive.infolist()
    if len(infos) >= MAX_ZIP_MEMBERS:
        errors.append("el XLSX supera el límite de miembros ZIP")
    total = 0
    for info in infos:
        total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            errors.append("el XLSX supera el límite de 50 MB sin comprimir")
            break
        if info.file_size and (not info.compress_size or info.file_size / info.compress_size > MAX_ZIP_RATIO):
            errors.append("el XLSX contiene una relación de compresión ZIP insegura")
            break
        name = info.filename.lower()
        if "vbaproject" in name or name.endswith((".bin", ".xlsm", ".xltm")):
            errors.append("se rechazan macros o contenido ejecutable")
            break
    if errors:
        archive.close()
        return None, errors
    # Scan XML parts before openpyxl: formulas with cached values still contain <f>.
    for info in infos:
        name = info.filename.lower()
        if not name.endswith((".xml", ".rels")):
            continue
        try:
            content = archive.read(info)
        except (BadZipFile, OSError):
            errors.append("no se pudo leer un miembro XML del XLSX")
            break
        lowered = content.lower()
        if re.search(rb"<(?:[a-z0-9]+:)?f(?:\s|>)", lowered) or b":f=" in lowered:
            errors.append("se rechazan fórmulas, incluso si tienen valor cacheado")
            break
        if (
            b"externallink" in lowered
            or b"external=" in lowered
            or b"external:" in lowered
            or b'targetmode="external"' in lowered
            or b"targetmode='external'" in lowered
        ):
            errors.append("se rechazan enlaces externos")
            break
    if errors:
        archive.close()
        return None, errors
    return archive, []


ES_HEADERS = dict(zip(
    ('ref name category_id district service_mode avg_price address phone description open_time close_time '
     'business_type business_ref branch_ref lat lng parent_ref product_type category_ref product_ref '
     'ingredient_ref portion ingredients allergens ingredients_confirmed allergens_confirmed availability '
     'menu_type menu_date image video quantity unit price cost basis expires lot floor zone capacity').split(),
    ('Código|Nombre|Categoría registrada|Distrito|Modalidad de servicio|Precio medio|Dirección|Teléfono|Descripción|Hora apertura|Hora cierre|'
     'Tipo de negocio|Código negocio|Código sucursal|Latitud|Longitud|Código categoría padre|Tipo de producto|Código categoría|Código producto|'
     'Código ingrediente|Porción|Ingredientes|Alérgenos|Ingredientes confirmados|Alérgenos confirmados|Disponibilidad|'
     'Tipo menú|Fecha menú|Imagen|Vídeo|Cantidad|Unidad|Precio|Costo|Base de costo|Vencimiento|Lote|Piso|Zona|Capacidad').split('|')))
ES_VALUES = {
    'availability': {'disponible': 'available', 'agotado': 'sold_out', 'pausado': 'paused'},
    'service_mode': {'solo salón': 'dine_in_only', 'salón y reparto': 'dine_in_and_delivery',
                     'solo reparto': 'delivery_only', 'solo recojo': 'pickup_only'},
}


def build_catalog_workbook_es() -> BytesIO:
    """Spanish presentation; canonical legacy fields remain unchanged on import."""
    workbook = load_workbook(build_catalog_workbook())
    for name, headers in SHEETS.items():
        sheet = workbook[name]
        sheet.freeze_panes = 'C2'
        sheet.row_dimensions[1].height = 48
        sheet.data_validations.dataValidation = []
        required = _REQUIRED[name] | ({'price', 'ingredients_confirmed', 'allergens_confirmed'} if name == 'Platos' else set())
        required |= {'expires', 'cost'} if name == 'Inventario' else set()
        for col, field in enumerate(headers, 1):
            cell = sheet.cell(1, col)
            cell.value = ES_HEADERS[field]
            cell.fill = PatternFill('solid', fgColor='9B4424' if field in required else '17324D')
            explanation = 'Obligatorio al completar esta fila.' if field in required else 'Opcional.'
            if field.endswith('_ref') or field == 'ref':
                explanation += ' Código de enlace del archivo, no ID de base de datos. Respeta mayúsculas. Consulta README.'
            if field == 'category_id':
                explanation += ' Nombre exacto de una categoría registrada; el servidor resuelve su ID. No crea categorías.'
            if field in {'price', 'cost', 'avg_price'}:
                explanation += ' Soles, importe no negativo, hasta dos decimales; sin símbolo ni fórmulas.'
            if field in {'ingredients', 'allergens'}:
                explanation += ' Lista separada por punto y coma. Vacío en alérgenos significa ninguno declarado solo si confirmado.'
            if field in {'ingredients_confirmed', 'allergens_confirmed'}:
                explanation += ' sí/no; publicación requiere sí. Ejemplos ficticios, no certificación sanitaria.'
            if field in {'menu_date', 'expires'}:
                explanation += ' AAAA-MM-DD; vencimiento vigente; fecha menú obligatoria para menú variable.'
            cell.comment = Comment(explanation, 'SmartResto')
            sheet.column_dimensions[get_column_letter(col)].width = max(22, min(38, len(cell.value) + 5))
            sheet.column_dimensions[get_column_letter(col)].hidden = False
            choices = {'product_type': 'plato,bebida,postre', 'availability': 'disponible,agotado,pausado',
                       'service_mode': 'solo salón,salón y reparto,solo reparto,solo recojo',
                       'menu_type': 'carta,variable', 'unit': 'g,kg,ml,l,unidad',
                       'ingredients_confirmed': 'sí,no', 'allergens_confirmed': 'sí,no'}
            validation = None
            if field in choices:
                validation = DataValidation(type='list', formula1='"' + choices[field] + '"', allow_blank=field not in required)
            elif field in {'price', 'cost', 'avg_price', 'quantity', 'basis'}:
                validation = DataValidation(type='decimal', operator='greaterThanOrEqual', formula1='0', allow_blank=field not in required)
            elif field == 'capacity':
                validation = DataValidation(type='whole', operator='between', formula1='1', formula2='100', allow_blank=False)
            elif field in required:
                validation = DataValidation(type='textLength', operator='greaterThan', formula1='0', allow_blank=False)
            if validation:
                validation.showErrorMessage = True
                validation.showInputMessage = True
                validation.showDropDown = False
                validation.errorStyle = 'stop'
                validation.errorTitle = 'Dato no válido'
                validation.error = 'Consulta el comentario del encabezado y README.'
                validation.promptTitle = cell.value[:32]
                validation.prompt = explanation[:255]
                sheet.add_data_validation(validation)
                letter = get_column_letter(col)
                validation.add(f'{letter}2:{letter}1501')
    instructions = workbook['Instrucciones']
    instructions.title = 'README'
    instructions['B3'] = 'Encabezados en castellano. No cambiar nombres ni duplicar columnas. El formato inglés anterior sigue admitido.'
    instructions['B6'] = 'Usa sí/no en las columnas de confirmación; para publicar se requiere sí.'
    instructions['B15'] = 'Categoría registrada: nombre exacto existente, no un ID. Distrito: nombre registrado. Modalidad: elige la lista.'
    instructions.append(['Ficticio', 'Todos los ejemplos son DATOS FICTICIOS para pruebas offline. No confirmar ni insertar en producción.'])
    instructions.append(['Leyenda', 'Encabezado naranja: obligatorio si completas la fila. Azul: opcional. Todas las columnas son visibles. Comentarios explican formato.'])
    instructions.append(['Relaciones', 'Negocios.Código → Sucursales.Código negocio; Sucursales.Código → Código sucursal; Categorias.Código → Código categoría/padre; Platos.Código → Código producto; Ingredientes.Código → Código ingrediente.'])
    instructions.append(['Restaurantes', 'Hoja independiente: su código NO enlaza sucursales. Sucursales crea sus propios locales. actual solo se usa con un restaurante propio seleccionado.'])
    instructions.append(['Precios', 'Precios reemplaza el precio base por Código producto; si hay varias filas, gana la última (compatibilidad existente). Evita duplicarlas.'])
    instructions.append(['Validación', 'Dropdowns orientan, no sustituyen al servidor. El preview verifica relaciones, publicación y moderación sin insertar. Los datos rechazados no se confirman.'])
    for name in SHEETS:
        for col, field in enumerate(SHEETS[name], 1):
            instructions.append([name + '.' + ES_HEADERS[field], workbook[name].cell(1, col).comment.text])
    samples = workbook['Ejemplos']
    for row in samples.iter_rows(min_row=2):
        if row[0].value in SHEETS:
            row[1].value = ' | '.join(ES_HEADERS[f] for f in SHEETS[row[0].value])
    samples['C2'] = 'R-DEMO,Restaurante ficticio,Marina,Trujillo,solo salón,25'
    for sheet in workbook:
        sheet.sheet_state = 'visible'
        for row in sheet:
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                cell.font = Font(name='Arial', size=11, bold=cell.row == 1)
        if sheet.title in {'README', 'Ejemplos'}:
            for col in range(1, sheet.max_column + 1):
                sheet.column_dimensions[get_column_letter(col)].width = 38 if col == 1 else 85
            for row in range(2, sheet.max_row + 1):
                sheet.row_dimensions[row].height = 48
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    output.seek(0)
    return output


def build_catalog_workbook() -> BytesIO:
    """Build a blank, import-safe catalogue template in memory."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    navy = "17324D"
    teal = "00A6A6"
    light = "E8F1F5"
    white = "FFFFFF"
    thin = Side(style="thin", color="D5E2E8")
    border = Border(bottom=thin)
    for sheet_name, headers in SHEETS.items():
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(list(headers))
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
        sheet.sheet_view.showGridLines = False
        sheet.row_dimensions[1].height = 28
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(1, col)
            cell.font = Font(name="Aptos Display", size=11, bold=True, color=white)
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border
            width = max(14, min(28, len(header) + 4))
            if header in {"description", "ingredients", "allergens", "address"}:
                width = 32
            sheet.column_dimensions[get_column_letter(col)].width = width
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        # Empty input row formatting does not create importable data.
        for col in range(1, len(headers) + 1):
            cell = sheet.cell(2, col)
            cell.fill = PatternFill("solid", fgColor="F7FAFB")
            cell.border = border
        for cell in sheet[1]:
            cell.comment = Comment("Obligatorio" if cell.value in _REQUIRED[sheet_name] else "Opcional", "SmartResto")

    instructions = workbook.create_sheet("Instrucciones")
    instructions.sheet_view.showGridLines = False
    instructions.column_dimensions["A"].width = 28
    instructions.column_dimensions["B"].width = 112
    instructions.append(["Tema", "Guía de importación segura"])
    guidance = [
        ("Objetivo", "Completa solo las hojas necesarias. No hay filas de ejemplo: la plantilla vacía no crea un negocio falso."),
        ("Encabezados", "Conserva los encabezados canónicos en inglés; el validador también acepta alias español/inglés con acentos normalizados."),
        ("Referencias", "Usa refs únicas por hoja. branch_ref y business_ref vacíos se normalizan a actual; las referencias cruzadas deben existir."),
        ("Dinero", "Escribe precios y costos como importes no negativos con hasta dos decimales (por ejemplo 18.35), nunca fórmulas."),
        ("Booleanos", "Usa exactamente yes/no o sí/no en ingredients_confirmed y allergens_confirmed."),
        ("Listas", "Separa ingredientes y alérgenos con coma, punto y coma o salto de línea."),
        ("Seguridad", "No se importan macros, enlaces externos, fórmulas, valores negativos o archivos que superen los límites de tamaño."),
        ("Flujo", "Sube el XLSX y revisa el preview: las filas normalizables se conservan y cada error incluye hoja, fila y campo."),
    ]
    for row in guidance:
        instructions.append(list(row))
    for cell in instructions[1]:
        cell.font = Font(name="Aptos Display", size=12, bold=True, color=white)
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row in instructions.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border
        row[0].font = Font(bold=True, color=teal)
        row[0].fill = PatternFill("solid", fgColor=light)
        row[1].fill = PatternFill("solid", fgColor="F7FAFB")
    instructions.freeze_panes = "A2"
    instructions.auto_filter.ref = "A1:B9"
    instructions.row_dimensions[1].height = 32
    for row_number in range(2, instructions.max_row + 1):
        instructions.row_dimensions[row_number].height = 34

    # Cell validations are intentionally on blank rows only; they do not insert examples.
    for sheet_name, headers in SHEETS.items():
        sheet = workbook[sheet_name]
        for field, values in {
            "product_type": "plato,bebida,postre",
            "availability": "available,sold_out,paused",
            "menu_type": "carta,variable",
            "unit": "g,kg,ml,l,unidad",
        }.items():
            if field in headers:
                col = get_column_letter(headers.index(field) + 1)
                validation = DataValidation(type="list", formula1=f'"{values}"', allow_blank=True)
                validation.error = "Selecciona un valor permitido."
                validation.errorTitle = "Valor no permitido"
                validation.prompt = "Usa uno de los valores de la lista."
                validation.promptTitle = field
                sheet.add_data_validation(validation)
                validation.add(f"{col}2:{col}1501")
        for field in {"ingredients_confirmed", "allergens_confirmed"} & set(headers):
            col = get_column_letter(headers.index(field) + 1)
            validation = DataValidation(type="list", formula1='"yes,no,sí,no"', allow_blank=True)
            sheet.add_data_validation(validation)
            validation.add(f"{col}2:{col}1501")
        for field in {"price", "cost"} & set(headers):
            col = get_column_letter(headers.index(field) + 1)
            validation = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
            sheet.add_data_validation(validation)
            validation.add(f"{col}2:{col}1501")

    instructions.append(["Limites", "5 MB comprimidos, 50 MB internos, 1500 filas totales; solo altas, sin eliminar ni modificar registros existentes."])
    instructions.append(["Contexto", "Marca comercial se representa por Negocios. No se importan usuarios, pedidos, pagos ni produccion. actual requiere un restaurante propio seleccionado."])
    instructions.append(["Restaurantes", "category_id debe existir; district debe estar registrado; service_mode: dine_in_only, dine_in_and_delivery, delivery_only, pickup_only. Nuevos locales quedan pendientes de moderacion."])
    instructions.append(["Confirmacion", "Preview sin escrituras. Confirmacion caduca a los 15 minutos y se invalida si cambia el contexto. Toda la carga usa una transaccion."])
    for name, required in _REQUIRED.items():
        instructions.append([name, "Obligatorios: " + ", ".join(sorted(required)) + ". En Platos: precio, ingredientes y alergenos confirmados. Inventario: expires vigente, cost y basis."])
    examples = workbook.create_sheet("Ejemplos")
    examples.append(["Hoja (NO IMPORTAR)", "Campos", "Valores ilustrativos; copiar a hoja real y adaptar referencias"])
    examples.append(["Restaurantes", "ref,name,category_id,district,service_mode,avg_price", "r1,Restaurante La Cocina,1,Trujillo,dine_in_only,25"])
    examples.append(["Negocios", "ref,name,description,business_type", "marca1,Sabores del Norte,Cocina criolla,restaurante"])
    examples.append(["Sucursales", "ref,business_ref,name", "local1,marca1,Restaurante Centro"])
    examples.append(["Platos", "ref,branch_ref,name,product_type,price,ingredients,allergens,ingredients_confirmed,allergens_confirmed", "p1,actual,Arroz con pollo,plato,22,arroz;pollo,,yes,yes"])
    sample_values = {
        'Categorias': 'cat1,actual,Fondos,,plato',
        'Ingredientes': 'i1,actual,Arroz,',
        'Recetas': 'p1,i1,100,g',
        'Variantes': 'p1,Grande,Doble,30',
        'Precios': 'p1,22',
        'Inventario': 'actual,i1,5,kg,20,1,2027-12-31,lote1',
        'Mesas': 'm1,actual,1,Salon,Mesa 1,4',
    }
    for name, values in sample_values.items():
        examples.append([name, ','.join(SHEETS[name]), values])
    for sheet in workbook:
        for row in sheet:
            for cell in row:
                cell.font = Font(name="Arial", size=11, bold=cell.row == 1, color=white if cell.row == 1 else navy)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


_REQUIRED: dict[str, set[str]] = {
    "Restaurantes": {"ref", "name", "category_id", "district", "service_mode"},
    "Negocios": {"ref", "name"},
    "Sucursales": {"ref", "business_ref", "name"},
    "Categorias": {"ref", "branch_ref", "name"},
    "Platos": {"ref", "branch_ref", "name", "product_type"},
    "Ingredientes": {"ref", "branch_ref", "name"},
    "Recetas": {"product_ref", "ingredient_ref", "quantity", "unit"},
    "Variantes": {"product_ref", "name", "price"},
    "Precios": {"product_ref", "price"},
    "Inventario": {"branch_ref", "ingredient_ref", "quantity", "unit"},
    "Mesas": {"ref", "branch_ref", "name", "capacity"},
}

_ENUMS = {
    "product_type": {"plato", "bebida", "postre"},
    "availability": {"available", "sold_out", "paused"},
    "menu_type": {"carta", "variable"},
    "unit": {"g", "kg", "ml", "l", "unidad"},
}
_NUMBERS = {"lat", "lng", "quantity", "capacity", "floor"}
_MONEY = {"price", "cost"}
_LISTS = {"ingredients", "allergens"}
_DATES = {"menu_date", "expires"}
_TIMES = {"open_time", "close_time"}
_BOOLEANS = {"ingredients_confirmed", "allergens_confirmed"}


def _normalize_headers(sheet: str, header_values: list[Any], errors: list[dict[str, Any]]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    seen: set[str] = set()
    allowed = set(SHEETS.get(sheet, ()))
    for index, value in enumerate(header_values, 1):
        if _blank(value):
            continue
        normalized = next((field for field in allowed if _key(ES_HEADERS[field]) == _key(value)), None)
        if normalized is None:
            normalized = _ALIAS_INDEX.get(_key(value))
        if normalized not in allowed:
            errors.append(_message(sheet, 1, str(value), "columna desconocida; no se descartará silenciosamente"))
            continue
        if normalized in seen:
            errors.append(_message(sheet, 1, normalized, "columna duplicada"))
            continue
        seen.add(normalized)
        mapping[index] = normalized
    return mapping


def _canonical_sheet_name(value: str) -> str | None:
    target = _key(value)
    for sheet in SHEETS:
        if _key(sheet) == target:
            return sheet
    if _key(value) in {_key("Instrucciones"), _key("Ejemplos"), _key("README")}:
        return "Instrucciones"
    return None


def _parse_row(sheet: str, row_number: int, raw_data: dict[str, Any], errors: list[dict[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in SHEETS[sheet]:
        value = raw_data.get(field)
        if field in ES_VALUES and isinstance(value, str):
            value = next((canonical for label, canonical in ES_VALUES[field].items()
                          if _key(label) == _key(value)), value)
        if field in {"branch_ref", "business_ref"} and _blank(value):
            data[field] = "actual"
        elif field in _LISTS:
            data[field] = _list_text(value)
        elif field in _MONEY:
            parsed, problem = _money(value)
            data[field] = parsed
            if problem:
                errors.append(_message(sheet, row_number, field, problem))
        elif field in {'lat', 'lng'}:
            parsed, problem = None, None
            if not _blank(value):
                try:
                    number = Decimal(str(value))
                    limit = 90 if field == 'lat' else 180
                    if not number.is_finite() or not -limit <= number <= limit:
                        raise ValueError()
                    parsed = str(number)
                except (InvalidOperation, ValueError):
                    problem = 'coordenada fuera de rango'
            data[field] = parsed
            if problem:
                errors.append(_message(sheet, row_number, field, problem))
        elif field in _NUMBERS:
            parsed, problem = _number(value)
            data[field] = parsed
            if problem:
                errors.append(_message(sheet, row_number, field, problem))
        elif field in _BOOLEANS:
            parsed, problem = _boolean(value)
            data[field] = parsed
            if problem:
                errors.append(_message(sheet, row_number, field, problem))
        elif field in _DATES:
            parsed, problem = _date(value)
            data[field] = parsed
            if problem:
                errors.append(_message(sheet, row_number, field, problem))
        elif field in _TIMES:
            parsed, problem = _time(value)
            data[field] = parsed
            if problem:
                errors.append(_message(sheet, row_number, field, problem))
        elif field in _ENUMS:
            parsed = _text(value)
            if parsed is not None:
                if field == "unit":
                    parsed = parsed.lower()
                else:
                    parsed = _key(parsed).replace("soldout", "sold_out")
                if parsed not in _ENUMS[field]:
                    errors.append(_message(sheet, row_number, field, f"valor no permitido; usa {sorted(_ENUMS[field])}"))
            data[field] = parsed
        else:
            data[field] = _text(value)

    for field in _REQUIRED.get(sheet, set()):
        if _blank(data.get(field)):
            errors.append(_message(sheet, row_number, field, "campo requerido"))
    return data


def _ref_sets(rows: list[dict[str, Any]], existing_refs: Mapping[str, Iterable[Any]] | None) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = defaultdict(set)
    for item in rows:
        sheet = item["sheet"]
        ref = item["data"].get("ref")
        if not _blank(ref):
            refs[sheet].add(str(ref))
    if existing_refs:
        for sheet, values in existing_refs.items():
            try:
                refs[sheet].update(str(value) for value in values if not _blank(value))
            except TypeError:
                continue
    return refs


def _validate_references(rows: list[dict[str, Any]], errors: list[dict[str, Any]], refs: Mapping[str, set[str]]) -> None:
    for item in rows:
        sheet, row_number, data = item["sheet"], item["row"], item["data"]
        for field, target, allow_actual in (
            ("business_ref", "Negocios", True),
            ("branch_ref", "Sucursales", True),
            ("category_ref", "Categorias", False),
            ("parent_ref", "Categorias", False),
            ("product_ref", "Platos", False),
            ("ingredient_ref", "Ingredientes", False),
        ):
            value = data.get(field)
            if _blank(value) or (allow_actual and value == "actual"):
                continue
            if str(value) not in refs.get(target, set()):
                errors.append(_message(sheet, row_number, field, f"referencia inexistente en {target}: {value}"))


def _validate_unique_refs(rows: list[dict[str, Any]], errors: list[dict[str, Any]], existing_refs: Mapping[str, Iterable[Any]] | None) -> None:
    seen: dict[str, dict[str, int]] = defaultdict(dict)
    external: dict[str, set[str]] = {}
    if existing_refs:
        for sheet, values in existing_refs.items():
            external[sheet] = {str(value) for value in values}
    for item in rows:
        sheet, row_number, data = item["sheet"], item["row"], item["data"]
        if "ref" not in data or _blank(data.get("ref")):
            continue
        ref = str(data["ref"])
        if ref in seen[sheet]:
            errors.append(_message(sheet, row_number, "ref", f"referencia duplicada; también aparece en la fila {seen[sheet][ref]}"))
        else:
            seen[sheet][ref] = row_number
        if ref in external.get(sheet, set()):
            errors.append(_message(sheet, row_number, "ref", "referencia ya existente para este tenant"))


def _validate_category_cycles(rows: list[dict[str, Any]], errors: list[dict[str, Any]]) -> None:
    graph: dict[str, tuple[str, int]] = {}
    for item in rows:
        if item["sheet"] == "Categorias":
            ref, parent = item["data"].get("ref"), item["data"].get("parent_ref")
            if ref and parent:
                graph[str(ref)] = (str(parent), item["row"])
    state: dict[str, int] = {}
    reported: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in trail:
            cycle = " -> ".join(trail[trail.index(node):] + [node])
            if cycle not in reported:
                reported.add(cycle)
                row_number = graph.get(node, ("", 1))[1]
                errors.append(_message("Categorias", row_number, "parent_ref", f"ciclo de categorías detectado: {cycle}"))
            return
        if state.get(node) == 2:
            return
        state[node] = 1
        if node in graph:
            visit(graph[node][0], trail + [node])
        state[node] = 2

    for ref in graph:
        visit(ref, [])


def validate_catalog_workbook(raw: bytes, existing_refs: Mapping[str, Iterable[Any]] | None = None) -> dict[str, Any]:
    """Validate an XLSX and return a JSON-safe preview without writing to a DB."""
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    archive, zip_errors = _safe_zip(raw)
    if zip_errors:
        errors.extend(_message("__archivo__", 0, "file", error) for error in zip_errors)
        return {"rows": rows, "errors": errors, "warnings": warnings, "counts": {"total": 0, "by_sheet": {}, "errors": len(errors), "warnings": 0}, "can_import": False}
    assert archive is not None
    workbook = None
    try:
        workbook = load_workbook(BytesIO(bytes(raw)), read_only=True, data_only=False, keep_links=False)
        if not workbook.sheetnames:
            errors.append(_message("__archivo__", 0, "sheets", "el workbook no contiene hojas"))
        seen_sheet_names: set[str] = set()
        total_rows = 0
        for worksheet in workbook.worksheets:
            sheet = _canonical_sheet_name(worksheet.title)
            if sheet == "Instrucciones":
                continue
            if sheet is None:
                errors.append(_message(worksheet.title, 1, "sheet", "hoja desconocida"))
                continue
            if sheet in seen_sheet_names:
                errors.append(_message(sheet, 1, "sheet", "hoja duplicada tras normalizar el nombre"))
                continue
            seen_sheet_names.add(sheet)
            if worksheet.max_column and worksheet.max_column > 40 or worksheet.max_row and worksheet.max_row > 1502:
                errors.append(_message(sheet, 0, 'dimension', 'maximo 40 columnas y 1501 filas por hoja'))
                continue
            iterator = worksheet.iter_rows(max_col=40, max_row=1502, values_only=True)
            try:
                header_values = list(next(iterator))
            except StopIteration:
                continue
            mapping = _normalize_headers(sheet, header_values, errors)
            if not mapping:
                errors.append(_message(sheet, 1, "headers", "no se detectaron columnas canónicas"))
                continue
            for row_number, values in enumerate(iterator, 2):
                if all(_blank(value) for value in values):
                    continue
                total_rows += 1
                if total_rows > MAX_TOTAL_ROWS:
                    errors.append(_message(sheet, row_number, "rows", "el workbook supera el máximo de 1500 filas de datos"))
                    break
                raw_data = {field: values[index - 1] if index - 1 < len(values) else None for index, field in mapping.items()}
                if sheet == 'Restaurantes' and not _blank(raw_data.get('category_id')):
                    category = str(raw_data['category_id']).strip()
                    if not re.fullmatch(r'[0-9]+', category):
                        # Lazy read only for Spanish category names; never create records.
                        from models.category import CategoryModel
                        candidates = [item for item in CategoryModel.all()
                                      if _key(item.get('name')) == _key(category)]
                        if len(candidates) == 1:
                            raw_data['category_id'] = str(candidates[0]['id'])
                        else:
                            errors.append(_message(sheet, row_number, 'category_id', 'Categoría registrada inexistente o ambigua'))
                parsed = _parse_row(sheet, row_number, raw_data, errors)
                rows.append({"sheet": sheet, "row": row_number, "data": parsed})
            if total_rows > MAX_TOTAL_ROWS:
                break

        _validate_unique_refs(rows, errors, existing_refs)
        refs = _ref_sets(rows, existing_refs)
        _validate_references(rows, errors, refs)
        _validate_category_cycles(rows, errors)

        products: dict[tuple[str, str], tuple[str, int]] = {}
        for item in rows:
            if item["sheet"] != "Platos":
                continue
            data = item["data"]
            key = (str(data.get("branch_ref") or "actual").casefold(), str(data.get("name") or "").strip().casefold())
            if key[1] and key in products:
                previous_sheet, previous_row = products[key]
                warnings.append(_message("Platos", item["row"], "name", f"posible duplicado idéntico nombre+branch; también aparece en {previous_sheet} fila {previous_row}"))
            elif key[1]:
                products[key] = (item["sheet"], item["row"])
    except Exception as exc:  # malformed XLSX should be a validation result, not a server exception
        errors.append(_message("__archivo__", 0, "file", f"no se pudo leer el XLSX de forma segura: {exc}"))
    finally:
        if workbook is not None:
            workbook.close()
        archive.close()

    by_sheet: dict[str, int] = defaultdict(int)
    for item in rows:
        by_sheet[item["sheet"]] += 1
    counts = {"total": len(rows), "by_sheet": dict(by_sheet), "errors": len(errors), "warnings": len(warnings)}
    return {"rows": rows, "errors": errors, "warnings": warnings, "counts": counts, "can_import": not errors}


__all__ = ["build_catalog_workbook", "validate_catalog_workbook"]
