"""Borradores auxiliares del catálogo; el producto confirmado vive en DishModel."""
from copy import deepcopy
import hashlib,json
from models.base import DataModel
from models.dish import DishModel
from models.restaurant import RestaurantModel
from database.repository import document_transaction
from logic.product_catalog import normalize_product,validate_for_publication,AVAILABILITY
from logic.business_radar import now
from utils.audit import record_event

class CatalogDraftModel(DataModel):collection='catalog_drafts'
class CatalogMediaModel(DataModel):collection='catalog_media'
class CatalogCategoryModel(DataModel):collection='catalog_categories'
class CatalogIngredientModel(DataModel):collection='catalog_ingredients'
class CatalogImportModel(DataModel):collection='catalog_imports'
class CatalogTableModel(DataModel):collection='restaurant_tables'


def fingerprint(product):
    return hashlib.sha256(json.dumps(product,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()


def require_owner(rid,actor):
    restaurant=RestaurantModel.get_by_id(rid)
    if not restaurant or restaurant.get('owner_id')!=actor:raise ValueError('No puedes gestionar este establecimiento')
    return restaurant


def create_draft(rid,actor,product,product_id=None,source='manual',media_id=None):
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731051)')
        require_owner(rid,actor)
        previous=DishModel.get_by_id(product_id) if product_id else None
        if product_id and (not previous or previous.get('restaurant_id')!=rid):raise ValueError('Producto ajeno o inexistente')
        normalized=normalize_product(product,previous)
        return CatalogDraftModel.create({'rid':rid,'owner_id':actor,'product_id':product_id,'source':source,
            'product':normalized,'status':'pending','previous_hash':fingerprint(previous) if previous else None,
            'media_id':media_id,'created_at':now()})


def get_draft(draft_id,rid,actor):
    row=CatalogDraftModel.get_by_id(draft_id)
    if not row or row['rid']!=rid or row['owner_id']!=actor:raise ValueError('Borrador ajeno o inexistente')
    return row


def validate_media(product,rid,actor):
    for url in product['images']:
        if url.startswith('/catalog-media/'):
            media=CatalogMediaModel.get_by_id(int(url.rsplit('/',1)[1]))
            if not media or media['rid']!=rid or media['owner_id']!=actor:raise ValueError('Imagen de otro establecimiento')
        elif url.startswith('/portal-media/'):
            raise ValueError('Usa fotografía del catálogo, no un logo privado de otro módulo')


def update_draft(draft_id,rid,actor,product):
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731051)');require_owner(rid,actor)
        row=get_draft(draft_id,rid,actor)
        if row['status']!='pending':raise ValueError('El borrador ya fue confirmado')
        normalized=normalize_product(product,row['product']);validate_media(normalized,rid,actor)
        return CatalogDraftModel.update(draft_id,{'product':normalized,'updated_at':now()})


def confirm_draft(draft_id,rid,actor):
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731051)');require_owner(rid,actor)
        row=get_draft(draft_id,rid,actor)
        if row['status']=='confirmed':return DishModel.get_by_id(row['confirmed_product_id'])
        product=validate_for_publication(row['product']);validate_media(product,rid,actor)
        if row.get('product_id'):
            previous=DishModel.get_by_id(row['product_id'])
            if not previous or previous.get('restaurant_id')!=rid or fingerprint(previous)!=row.get('previous_hash'):
                raise ValueError('El producto cambió desde que abriste el borrador; vuelve a editarlo')
            if previous.get('market_only'):
                product['market_only']=False
            saved=DishModel.update(previous['id'],{**product,'updated_at':now()})
        else:
            if any(d.get('name','').casefold()==product['name'].casefold() and (d.get('menu_date') or '')==product['menu_date'] for d in DishModel.get_by_restaurant(rid)):
                raise ValueError('Este producto ya existe; edita su registro en vez de duplicarlo')
            saved=DishModel.create({**product,'restaurant_id':rid,'created_at':now(),'updated_at':now()})
        CatalogDraftModel.update(draft_id,{'status':'confirmed','confirmed_product_id':saved['id'],'confirmed_at':now()})
        record_event('ADMIN_RESTAURANT_UPDATE',resource_type='catalog_product',resource_id=saved['id'],metadata={'operation':'product_confirm','source':row['source']})
        return saved


def change_availability(rid,product_id,actor,state):
    if state not in AVAILABILITY:raise ValueError('Disponibilidad inválida')
    with document_transaction() as conn:
        # Same restaurant row lock as checkout: no sale races with manual closure.
        conn.execute('SELECT id FROM public.app_records WHERE collection=%s AND id=%s FOR UPDATE',('restaurants',rid))
        require_owner(rid,actor)
        product=DishModel.get_by_id(product_id)
        if not product or product.get('restaurant_id')!=rid:raise ValueError('Producto ajeno o inexistente')
        saved=DishModel.update(product_id,{'availability':state,'is_available':state=='available','updated_at':now()})
        record_event('ADMIN_RESTAURANT_UPDATE',resource_type='catalog_product',resource_id=product_id,metadata={'operation':'availability','state':state})
        return saved
