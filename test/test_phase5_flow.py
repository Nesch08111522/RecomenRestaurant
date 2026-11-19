from io import BytesIO
from openpyxl import load_workbook
import pytest
from test_phase3_sources_claims import memory_repo
from models import catalog,discovery,catalog_import
from models.restaurant import RestaurantModel
from models.dish import DishModel
from logic.product_catalog import normalize_product
from utils.catalog_workbook import build_catalog_workbook


@pytest.fixture
def repo(memory_repo,monkeypatch):
    monkeypatch.setattr(catalog,'document_transaction',discovery.document_transaction)
    monkeypatch.setattr(catalog_import,'document_transaction',discovery.document_transaction)
    monkeypatch.setattr(catalog,'record_event',lambda *args,**kwargs:None)
    monkeypatch.setattr(catalog_import,'record_event',lambda *args,**kwargs:None)
    RestaurantModel.create({'owner_id':5,'name':'Café','verified':True})
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = 'isolated-unit-catalog-import-secret'
    with app.app_context():
        yield memory_repo


def product():
    return {'name':'Arroz con pollo','price':'18','ingredients':['arroz','pollo'],'ingredients_confirmed':True,
        'allergens':[],'allergens_confirmed':True,'rights_confirmed':True}


def test_confirm_creates_same_product_once_and_blocks_other_owner(repo):
    row=catalog.create_draft(1,5,product())
    assert not DishModel.all()
    first=catalog.confirm_draft(row['id'],1,5)
    second=catalog.confirm_draft(row['id'],1,5)
    assert first['id']==second['id'] and len(DishModel.all())==1
    with pytest.raises(ValueError):catalog.create_draft(1,6,product())
    catalog.change_availability(1,first['id'],5,'sold_out')
    assert DishModel.get_by_id(first['id'])['is_available'] is False


def workbook():
    wb=load_workbook(build_catalog_workbook());sheet=wb['Platos'];headers=[c.value for c in sheet[1]]
    values={'ref':'plato-1','name':'Arroz con pollo','product_type':'plato','branch_ref':'actual','price':'18',
        'ingredients':'arroz,pollo','allergens':'','ingredients_confirmed':'sí','allergens_confirmed':'sí'}
    sheet.append([values.get(h) for h in headers]);out=BytesIO();wb.save(out);return out.getvalue()


def test_excel_preview_optional_fields_and_idempotent_confirmation(repo):
    preview=catalog_import.preview_import(workbook(),1,5)
    assert preview['status']=='pending',preview['errors']
    assert not DishModel.all()
    first=catalog_import.confirm_import(preview['id'],1,5)
    second=catalog_import.confirm_import(preview['id'],1,5)
    assert first==second and len(DishModel.all())==1


def test_excel_with_unknown_allergens_never_imports_silently(repo):
    wb=load_workbook(BytesIO(workbook()));headers=[c.value for c in wb['Platos'][1]]
    wb['Platos'].cell(2,headers.index('allergens_confirmed')+1,'no');out=BytesIO();wb.save(out)
    preview=catalog_import.preview_import(out.getvalue(),1,5)
    assert preview['status']=='invalid' and preview['errors']
    with pytest.raises(ValueError):catalog_import.confirm_import(preview['id'],1,5)
    assert not DishModel.all()
