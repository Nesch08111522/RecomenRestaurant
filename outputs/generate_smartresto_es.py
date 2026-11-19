"""Generate fictional Spanish fixtures without database or network access."""
from io import BytesIO
from pathlib import Path
from openpyxl import load_workbook
from utils.catalog_workbook import SHEETS, build_catalog_workbook_es


def example_bytes(cafe=False, invalid=False):
    wb = load_workbook(build_catalog_workbook_es())
    ingredient = 'Café molido' if cafe else 'Pescado'
    product = 'Café filtrado' if cafe else 'Pescado al vapor'
    category = 'Cafetería' if cafe else 'Marina'
    kind = 'bebida' if cafe else 'plato'
    name = 'Cafetería ficticia Brisa' if cafe else 'Restaurante ficticio Marea'
    rows = {
        'Restaurantes': [dict(ref='R-DEMO', name=name + ' independiente', category_id=category, district='Trujillo', service_mode='solo salón', avg_price=25, address='Calle Ficticia 100', phone='000000000', description='DATOS FICTICIOS - NO INSERTAR EN PRODUCCIÓN', open_time='09:00', close_time='18:00')],
        'Negocios': [dict(ref='N-DEMO', name=name, description='DATOS FICTICIOS - prueba offline', business_type='cafetería' if cafe else 'restaurante')],
        'Sucursales': [dict(ref='S-DEMO', business_ref='N-DEMO', name=name + ' local', address='Calle Ficticia 200', district='Trujillo', lat=-8.11, lng=-79.03, open_time='09:00', close_time='18:00')],
        'Categorias': [dict(ref='C-DEMO', branch_ref='S-DEMO', name='Bebidas calientes' if cafe else 'Fondos marinos', product_type=kind)],
        'Platos': [dict(ref='P-DEMO', branch_ref='S-DEMO', name='venta de personas' if invalid else product, product_type=kind, category_ref='C-DEMO', description='DATOS FICTICIOS - prueba de rechazo' if invalid else 'DATOS FICTICIOS - producto de demostración', price=18.50, portion='personal', ingredients=ingredient, allergens='' if cafe else 'pescado', ingredients_confirmed='sí', allergens_confirmed='sí', availability='disponible', menu_type='carta')],
        'Ingredientes': [dict(ref='I-DEMO', branch_ref='S-DEMO', name=ingredient, allergens='' if cafe else 'pescado')],
        'Recetas': [dict(product_ref='P-DEMO', ingredient_ref='I-DEMO', quantity=20 if cafe else 200, unit='g')],
        'Variantes': [dict(product_ref='P-DEMO', name='Grande', portion='doble', price=30)],
        'Precios': [dict(product_ref='P-DEMO', price=18.50)],
        'Inventario': [dict(branch_ref='S-DEMO', ingredient_ref='I-DEMO', quantity=5, unit='kg', cost=40, basis=1, expires='2099-12-31', lot='LOTE-FICTICIO')],
        'Mesas': [dict(ref='M-DEMO', branch_ref='S-DEMO', floor=1, zone='Salón', name='Mesa ficticia 1', capacity=4)],
    }
    for sheet, values in rows.items():
        for row in values:
            wb[sheet].append([row.get(field) for field in SHEETS[sheet]])
    wb['README'].append(['Escenario', 'DATOS FICTICIOS. Sin imágenes ni vídeos: campos opcionales vacíos. Vencimiento 2099-12-31 solo para pruebas. Restaurante independiente NO es el local S-DEMO.'])
    raw = BytesIO()
    wb.save(raw)
    wb.close()
    return raw.getvalue()


def generate():
    root = Path(__file__).resolve().parent
    outputs = {
        'Plantilla_carga_SmartResto_ES.xlsx': build_catalog_workbook_es().getvalue(),
        'Ejemplo_restaurante_marino_ES.xlsx': example_bytes(),
        'Ejemplo_cafeteria_ES.xlsx': example_bytes(cafe=True),
        'Ejemplo_invalido_moderacion_ES.xlsx': example_bytes(invalid=True),
    }
    for name, raw in outputs.items():
        target = root / name
        if target.exists():
            raise FileExistsError(f'No sobrescribir: {target}')
        target.write_bytes(raw)
        wb = load_workbook(BytesIO(target.read_bytes()))
        assert set(wb.sheetnames) == set(SHEETS) | {'README', 'Ejemplos'}
        assert all(ws.sheet_state == 'visible' for ws in wb)
        assert not any(cell.data_type == 'f' for ws in wb for row in ws for cell in row)
        assert all(not dim.hidden for ws in wb for dim in ws.column_dimensions.values())
        print(f'{target}: {len(raw)} bytes; readback OK; {len(wb.sheetnames)} hojas visibles; sin fórmulas')
        wb.close()


if __name__ == '__main__':
    generate()
