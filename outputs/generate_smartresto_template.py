from pathlib import Path
from io import BytesIO
from openpyxl import load_workbook
from utils.catalog_workbook import build_catalog_workbook, validate_catalog_workbook, SHEETS

root = Path(__file__).resolve().parent
raw = build_catalog_workbook().getvalue()
target = root / 'Plantilla_carga_SmartResto.xlsx'
target.write_bytes(raw)
wb = load_workbook(BytesIO(target.read_bytes()), data_only=False)
assert set(wb.sheetnames) == set(SHEETS) | {'Instrucciones', 'Ejemplos'}
for name, headers in SHEETS.items():
    assert tuple(cell.value for cell in wb[name][1]) == headers
assert not any(cell.data_type == 'f' for ws in wb for row in ws for cell in row)
result = validate_catalog_workbook(target.read_bytes())
assert result['rows'] == [] and result['errors'] == [], result
print(str(target))
print('Readback OK:', ', '.join(wb.sheetnames))
print('Empty import rows; examples excluded; no formulas.')
wb.close()
