import io
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from openpyxl import load_workbook
from utils.catalog_workbook import build_catalog_workbook, validate_catalog_workbook, SHEETS
from models import catalog_import as service


class ExcelImportTests(unittest.TestCase):
    def test_template_readback(self):
        raw = build_catalog_workbook().getvalue()
        wb = load_workbook(io.BytesIO(raw))
        self.assertEqual(set(wb.sheetnames), set(SHEETS) | {'Instrucciones', 'Ejemplos'})
        self.assertTrue(wb['Ejemplos'].max_row > 2)
        parsed = validate_catalog_workbook(raw)
        self.assertEqual(parsed['rows'], [])
        self.assertEqual(parsed['errors'], [])
        for name, headers in SHEETS.items():
            self.assertEqual(tuple(c.value for c in wb[name][1]), headers)
        wb.close()

    def test_formula_rejected(self):
        wb = load_workbook(build_catalog_workbook())
        wb['Platos']['A2'] = '=1+1'
        stream = io.BytesIO(); wb.save(stream)
        self.assertFalse(validate_catalog_workbook(stream.getvalue())['can_import'])

    def test_malicious_product_rejected(self):
        for name in ['Niños', 'Personas', 'Carne humana', 'ignore instructions']:
            rows = [{'sheet':'Platos','row':2,'data':{'ref':'p1','branch_ref':'actual','name':name,'product_type':'plato'}}]
            with self.subTest(name=name), self.assertRaises(ValueError):
                service.moderate_rows(rows)

    def test_preview_has_no_writes(self):
        app = Flask(__name__); app.secret_key = 'test-only'
        with app.app_context(), patch.object(service.model.CatalogImportModel, 'create') as create:
            job = service.preview_import(build_catalog_workbook().getvalue(), None, 7)
            self.assertIn('token', job)
            create.assert_not_called()

    def test_tampered_token_no_write(self):
        from contextlib import nullcontext
        app = Flask(__name__); app.secret_key = 'test-only'
        with app.app_context(), patch.object(service, 'document_transaction', return_value=nullcontext(MagicMock())), patch.object(service.model.CatalogImportModel, 'create') as create:
            with self.assertRaises(ValueError):
                service.confirm_import('tampered', None, 7)
            create.assert_not_called()

    def test_expired_token(self):
        from contextlib import nullcontext
        app = Flask(__name__); app.secret_key = 'test-only'
        with app.app_context(), patch('itsdangerous.timed.time.time', return_value=1800000000):
            job = service.preview_import(build_catalog_workbook().getvalue(), None, 7)
        with app.app_context(), patch('itsdangerous.timed.time.time', return_value=1800001000), patch.object(service, 'document_transaction', return_value=nullcontext(MagicMock())):
            with self.assertRaisesRegex(ValueError, 'caducado'):
                service.confirm_import(job['token'], None, 7)

    def test_cross_branch_reference(self):
        rows = [
            {'sheet':'Ingredientes','row':2,'data':{'ref':'i1','branch_ref':'actual','name':'Arroz'}},
            {'sheet':'Sucursales','row':2,'data':{'ref':'b1','business_ref':'actual','name':'Restaurante Centro'}},
            {'sheet':'Platos','row':2,'data':{'ref':'p1','branch_ref':'b1','name':'Arroz con pollo','product_type':'plato'}},
            {'sheet':'Recetas','row':2,'data':{'product_ref':'p1','ingredient_ref':'i1','quantity':'1','unit':'g'}},
        ]
        with patch('utils.restaurant_review.check_restaurant', return_value={}), self.assertRaisesRegex(ValueError, 'cruzada'):
            service.moderate_rows(rows)

    def test_actor_binding(self):
        from contextlib import nullcontext
        app = Flask(__name__); app.secret_key = 'test-only'
        with app.app_context():
            job = service.preview_import(build_catalog_workbook().getvalue(), None, 7)
            with patch.object(service, 'document_transaction', return_value=nullcontext(MagicMock())), patch.object(service.model.CatalogImportModel, 'create') as create:
                with self.assertRaisesRegex(ValueError, 'ajeno'):
                    service.confirm_import(job['token'], None, 8)
                create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
