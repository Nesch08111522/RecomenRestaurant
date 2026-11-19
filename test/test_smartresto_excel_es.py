import io
import unittest
from unittest.mock import patch
from flask import Flask
from openpyxl import load_workbook
from outputs.generate_smartresto_es import example_bytes
from utils.catalog_workbook import SHEETS, ES_HEADERS, build_catalog_workbook_es, validate_catalog_workbook
from models import catalog_import as service
from models.category import CategoryModel
from config import Config


class SpanishExcelTests(unittest.TestCase):
    def test_spanish_template(self):
        raw = build_catalog_workbook_es().getvalue()
        self.assertEqual(validate_catalog_workbook(raw)['errors'], [])
        wb = load_workbook(io.BytesIO(raw))
        for name, fields in SHEETS.items():
            ws = wb[name]
            self.assertEqual([c.value for c in ws[1]], [ES_HEADERS[f] for f in fields])
            self.assertEqual(ws.freeze_panes, 'C2')
            self.assertTrue(all(c.comment for c in ws[1]))
            self.assertTrue(all(not d.hidden for d in ws.column_dimensions.values()))
            self.assertTrue(all(d.showErrorMessage for d in ws.data_validations.dataValidation))
        wb.close()

    def test_examples_preview_mocked_no_writes(self):
        app = Flask(__name__)
        app.secret_key = 'offline-excel-test'
        categories = [{'id': 481, 'name': 'Marina'}, {'id': 927, 'name': 'Cafetería'}]
        with app.app_context(), patch.object(CategoryModel, 'all', return_value=categories), patch.object(CategoryModel, 'get_by_id', side_effect=lambda cid: next((c for c in categories if c['id'] == cid), None)), patch.object(Config, 'DISTRITOS', ['Trujillo']), patch('utils.restaurant_review.check_restaurant', return_value={}), patch.object(service.model.CatalogImportModel, 'create') as create, patch.object(service.RestaurantModel, 'create') as restaurant, patch.object(service.DishModel, 'create') as dish, patch.object(service, 'document_transaction') as transaction:
            for cafe in (False, True):
                with self.subTest(cafe=cafe):
                    raw = example_bytes(cafe=cafe)
                    parsed = validate_catalog_workbook(raw)
                    self.assertEqual(parsed['errors'], [])
                    self.assertEqual(parsed['counts']['total'], 11)
                    self.assertEqual(parsed['rows'][0]['data']['category_id'], str(927 if cafe else 481))
                    job = service.preview_import(raw, None, 7)
                    self.assertEqual(job['errors'], [])
                    self.assertEqual(job['status'], 'pending')
            raw = example_bytes(invalid=True)
            self.assertEqual(validate_catalog_workbook(raw)['errors'], [])
            job = service.preview_import(raw, None, 7)
            self.assertEqual(job['status'], 'invalid')
            self.assertTrue(any('Personas o menores' in e['message'] for e in job['errors']))
            create.assert_not_called()
            restaurant.assert_not_called()
            dish.assert_not_called()
            transaction.assert_not_called()

    def test_ambiguous_category_rejected(self):
        with patch.object(CategoryModel, 'all', return_value=[{'id': 1, 'name': 'Marina'}, {'id': 2, 'name': 'Marina'}]):
            parsed = validate_catalog_workbook(example_bytes())
            self.assertFalse(parsed['can_import'])
            self.assertTrue(any('ambigua' in e['message'] for e in parsed['errors']))


if __name__ == '__main__':
    unittest.main()
