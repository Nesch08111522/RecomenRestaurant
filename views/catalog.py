import base64
from flask import Blueprint,request,session,jsonify,render_template,Response,abort,current_app,redirect,url_for
from views.business_sites import owner,owned,action,data
from models import catalog as model
from models.catalog_import import preview_import,confirm_import
from models.dish import DishModel
from models.restaurant import RestaurantModel
from models.business_site import consume_ai_quota
from utils.product_ai import prepare_photo,propose_product
from utils.llm_provider import AIUnavailable,log_provider_error
from logic.context import SEASONS
from logic.product_catalog import normalize_product,AVAILABILITY
from logic.business_radar import now

bp=Blueprint('catalog',__name__)


def drafts_for(rid):
    return [r for r in model.CatalogDraftModel.all() if r['rid']==rid and r['owner_id']==session['user_id'] and r['status']=='pending']


@bp.get('/owner/catalog')
@owner
def dashboard():
    restaurants=RestaurantModel.get_by_owner(session['user_id'])
    rid=request.args.get('restaurant_id',type=int)
    restaurant=owned(rid) if rid else restaurants[0] if restaurants else None
    products=DishModel.get_by_restaurant(restaurant['id']) if restaurant else []
    categories=[r for r in model.CatalogCategoryModel.all() if restaurant and r['rid']==restaurant['id'] and r['owner_id']==session['user_id']]
    return render_template('catalog/dashboard.html',restaurants=restaurants,restaurant=restaurant,products=products,categories=categories,seasons=SEASONS,
        api_url=f"/owner/api/catalog/{restaurant['id']}" if restaurant else '')


@bp.get('/owner/api/catalog/<int:rid>')
@owner
def catalog_api(rid):
    owned(rid)
    return jsonify(success=True,products=DishModel.get_by_restaurant(rid),drafts=drafts_for(rid),
        categories=[r for r in model.CatalogCategoryModel.all() if r['rid']==rid and r['owner_id']==session['user_id']])


@bp.post('/owner/api/catalog/<int:rid>/draft')
@owner
@action
def draft(rid):
    owned(rid);body=data();pid=body.get('product_id')
    if pid is not None and (not isinstance(pid,int) or isinstance(pid,bool)):raise ValueError('Identificador de producto inválido')
    row=model.create_draft(rid,session['user_id'],body.get('product',{}),pid)
    return jsonify(success=True,draft=row)


@bp.put('/owner/api/catalog/<int:rid>/drafts/<int:draft_id>')
@owner
@action
def update_draft(rid,draft_id):
    owned(rid);row=model.update_draft(draft_id,rid,session['user_id'],data().get('product',{}))
    return jsonify(success=True,draft=row)


@bp.post('/owner/api/catalog/<int:rid>/drafts/<int:draft_id>/confirm')
@owner
@action
def confirm(rid,draft_id):
    owned(rid)
    if data().get('confirm') is not True:raise ValueError('Confirma explícitamente el producto revisado')
    product=model.confirm_draft(draft_id,rid,session['user_id'])
    return jsonify(success=True,product=product)


@bp.patch('/owner/api/catalog/<int:rid>/products/<int:product_id>/availability')
@owner
@action
def availability(rid,product_id):
    owned(rid);product=model.change_availability(rid,product_id,session['user_id'],data().get('availability'))
    return jsonify(success=True,product=product)


def quota():
    try:consume_ai_quota(session['user_id'])
    except ValueError as error:return jsonify(success=False,error=str(error)),429


@bp.post('/owner/api/catalog/<int:rid>/photo')
@owner
@action
def photo(rid):
    owned(rid);upload=request.files.get('file')
    if not upload:raise ValueError('Selecciona una fotografía')
    image=prepare_photo(upload.read(8*1024*1024+1))
    limited=quota()
    if limited:return limited
    try:product,ai_model=propose_product('photo',image=image)
    except AIUnavailable:raise
    except Exception as error:
        log_provider_error(current_app.logger,'catalog_photo',error)
        return jsonify(success=False,error='La IA no completó el análisis de foto; revisa proveedor y soporte de imágenes'),502
    media=model.CatalogMediaModel.create({**image,'rid':rid,'owner_id':session['user_id'],'created_at':now()})
    product['images']=[f"/catalog-media/{media['id']}"]
    row=model.create_draft(rid,session['user_id'],product,source='photo',media_id=media['id'])
    return jsonify(success=True,draft=row,model=ai_model,
        notice='Preparación e ingredientes probables. Confirma receta, ingredientes, alérgenos y precio antes de publicar.')


@bp.post('/owner/api/catalog/<int:rid>/voice')
@owner
@action
def voice(rid):
    owned(rid);body=data();transcript=body.get('transcript','')
    if not isinstance(transcript,str) or not transcript.strip() or len(transcript)>2000:raise ValueError('Transcripción inválida')
    previous=normalize_product(body.get('product') or {})
    limited=quota()
    if limited:return limited
    try:product,ai_model=propose_product('voice',transcript=transcript,previous=previous)
    except AIUnavailable:raise
    except Exception as error:
        log_provider_error(current_app.logger,'catalog_voice',error)
        return jsonify(success=False,error='La IA no completó la interpretación de voz'),502
    row=model.create_draft(rid,session['user_id'],product,body.get('product_id'),source='voice')
    return jsonify(success=True,draft=row,model=ai_model,notice='Revisa la transcripción y el borrador; no se publicó ningún producto.')


@bp.get('/catalog-media/<int:media_id>')
def media(media_id):
    from utils.security import fresh_session_user
    item=model.CatalogMediaModel.get_by_id(media_id)
    if not item:abort(404)
    user=fresh_session_user();restaurant=RestaurantModel.get_by_id(item['rid']);path=f'/catalog-media/{media_id}'
    allowed=bool(user and user['id']==item['owner_id'])
    if not allowed:
        allowed=bool(restaurant and restaurant.get('verified') and restaurant.get('status') not in {'suspended','archived'}
            and any(path in d.get('images',[]) for d in DishModel.get_by_restaurant(item['rid'])))
    if not allowed:abort(404)
    return Response(base64.b64decode(item['content']),mimetype='image/jpeg',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


@bp.get('/owner/catalog/<int:rid>/template.xlsx')
@owner
def template(rid):
    from utils.catalog_workbook import build_catalog_workbook
    owned(rid);stream=build_catalog_workbook()
    return Response(stream.getvalue(),mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition':'attachment; filename="Plantilla_SmartResto_Catalogo.xlsx"'})


@bp.post('/owner/api/catalog/<int:rid>/import-preview')
@owner
@action
def import_preview(rid):
    owned(rid);upload=request.files.get('file')
    if not upload or not upload.filename.lower().endswith('.xlsx'):raise ValueError('Usa la plantilla .xlsx')
    row=preview_import(upload.read(5*1024*1024+1),rid,session['user_id'])
    return jsonify(success=True,**{'import':row})


@bp.post('/owner/api/catalog/<int:rid>/imports/<import_id>/confirm')
@owner
@action
def import_confirm(rid,import_id):
    owned(rid)
    if data().get('confirm') is not True:raise ValueError('Confirma revisión de filas y derechos del contenido')
    result=confirm_import(import_id,rid,session['user_id'])
    return jsonify(success=True,result=result)


@bp.get('/catalog/qr/<token>')
def table_menu(token):
    table=next((r for r in model.CatalogTableModel.all() if r.get('qr_token')==token),None)
    restaurant=RestaurantModel.get_by_id(table['rid']) if table else None
    if not restaurant or not restaurant.get('verified'):abort(404)
    # Visiting this URL does not activate or occupy the table.
    return redirect(url_for('main.detail',restaurant_id=restaurant['id']))


@bp.after_request
def private_response(response):
    if request.path.startswith('/owner/'):
        response.headers['Cache-Control']='no-store';response.headers['X-Robots-Tag']='noindex, nofollow'
    return response


@bp.get('/owner/catalog/tables/<int:table_id>/qr.svg')
@owner
@action
def table_qr(table_id):
    from utils.catalog_qr import build_table_qr
    table=model.CatalogTableModel.get_by_id(table_id)
    if not table or table['owner_id']!=session['user_id']:abort(404)
    owned(table['rid']);content,url=build_table_qr(table['qr_token'])
    return Response(content,mimetype='image/svg+xml',headers={'Content-Disposition':f'attachment; filename="mesa-{table_id}.svg"','Cache-Control':'no-store'})
