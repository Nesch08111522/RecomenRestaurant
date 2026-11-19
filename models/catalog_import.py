"""Importación confirmada: ninguna fila opera fuera del propietario del lote."""
from collections import defaultdict
from uuid import uuid4
import hashlib
from datetime import date
from models import catalog as model
from models.dish import DishModel
from models.restaurant import RestaurantModel
from models.market import kitchen,save_kitchen
from database.repository import document_transaction,PostgresDocumentRepository as Repo
from logic.product_catalog import normalize_product,validate_for_publication,base_quantity,money
from models.business_site import slugify
from logic.business_radar import now
from utils.audit import record_event


def grouped(rows):
    groups=defaultdict(list)
    for row in rows:groups[row['sheet']].append(row)
    return groups


def product_plan(rows):
    groups=grouped(rows)
    categories={r['data']['ref']:r['data'] for r in groups['Categorias']}
    ingredients={r['data']['ref']:r['data'] for r in groups['Ingredientes']}
    products=[]
    for row in groups['Platos']:
        d=row['data'];ref=d['ref'];category=categories.get(d.get('category_ref'),{})
        product={'name':d.get('name',''),'product_type':d.get('product_type','plato'),
            'category':category.get('name') or {'plato':'Fondo','bebida':'Bebida','postre':'Postre'}.get(d.get('product_type'),'Fondo'),
            'subcategory':category.get('parent_ref') or '','description':d.get('description') or '',
            'price':d.get('price'),'portion':d.get('portion') or '','ingredients':d.get('ingredients',[]),
            'allergens':d.get('allergens'),'ingredients_confirmed':d.get('ingredients_confirmed',False),
            'allergens_confirmed':d.get('allergens_confirmed',False),'rights_confirmed':True,
            'availability':d.get('availability') or 'available','menu_type':d.get('menu_type') or 'carta',
            'menu_date':d.get('menu_date') or '', 'images':[d['image']] if d.get('image') else [],
            'videos':[d['video']] if d.get('video') else [],'variants':[],'recipe':[]}
        for line in groups['Precios']:
            if line['data']['product_ref']==ref:product['price']=line['data']['price']
        for line in groups['Variantes']:
            if line['data']['product_ref']==ref:
                v=line['data'];product['variants'].append({'name':v['name'],'portion':v.get('portion',''),'price':v.get('price')})
        for line in groups['Recetas']:
            r=line['data']
            if r['product_ref']==ref:
                ingredient=ingredients[r['ingredient_ref']]
                product['recipe'].append({'ingredient':ingredient['name'],'quantity':r['quantity'],'unit':r['unit']})
        products.append({'sheet':row['sheet'],'row':row['row'],'ref':ref,'branch_ref':d.get('branch_ref') or 'actual','product':product})
    return products


IMPORT_VERSION = 2


def moderate_rows(rows):
    """Local policy only: importing never calls an external AI."""
    import re
    from models.moderation_filter import _norm
    from utils.restaurant_review import check_restaurant
    from utils.content_filter import deobfuscate
    from utils.catalog_workbook import SHEETS, _REQUIRED, _validate_references, _ref_sets, _validate_unique_refs
    if not isinstance(rows, list) or not 0 < len(rows) <= 1500:
        raise ValueError('El lote requiere entre 1 y 1500 filas')
    for row in rows:
        sheet = row.get('sheet'); data = row.get('data')
        if sheet not in SHEETS or not isinstance(data, dict) or set(data) - set(SHEETS[sheet]):
            raise ValueError('Hoja o campos no permitidos')
        if any(data.get(key) in (None, '') for key in _REQUIRED[sheet]):
            raise ValueError('Campos obligatorios incompletos en ' + sheet)
        text = _norm(deobfuscate(' '.join(str(v or '') for v in data.values())))
        if len(text) > 10000 or any(len(str(v)) > 2000 for v in data.values()):
            raise ValueError('Texto fuera del limite de 2000 caracteres por campo')
        if re.search(r'(ignora|ignore|omite|bypass).{0,60}(instrucciones|instructions|reglas|rules|moderacion|seguridad)|system prompt|drop table|<script|javascript:', text):
            raise ValueError('Se rechazan instrucciones maliciosas en el documento')
        name = _norm(deobfuscate(str(data.get('name') or '')))
        if sheet in {'Platos', 'Ingredientes', 'Variantes'}:
            if re.search(r'\b(personas?|ninos?|ninas?|bebes?|humanos?|menores|children|people|person|child)\b', name) and not re.search(r'\b(menu|porcion|para|infantil)\b', name):
                raise ValueError('Personas o menores no son productos gastronomicos')
            if re.search(r'\b(carne|asado|estofado|venta|vender|comprar)\b.{0,30}\b(human[oa]s?|personas?|ninos?|bebes?|menores)\b', text):
                raise ValueError('Contenido humano incompatible con gastronomia')
        if sheet in {'Restaurantes', 'Negocios', 'Sucursales', 'Platos', 'Ingredientes', 'Categorias', 'Variantes'}:
            check_restaurant({'name': data.get('name', ''), 'description': data.get('description', ''), 'tags': data.get('ingredients', [])})
    errors = []
    _validate_unique_refs(rows, errors, None)
    _validate_references(rows, errors, _ref_sets(rows, None))
    if errors:
        raise ValueError(errors[0]['message'])
    groups = grouped(rows)
    categories = {r['data']['ref']: r['data'] for r in groups['Categorias']}
    ingredients = {r['data']['ref']: r['data'] for r in groups['Ingredientes']}
    products = {r['data']['ref']: r['data'] for r in groups['Platos']}
    for row in rows:
        d = row['data']; branch = d.get('branch_ref') or 'actual'
        for key, refs in [('category_ref', categories), ('parent_ref', categories), ('ingredient_ref', ingredients)]:
            ref = d.get(key)
            if ref and ref in refs:
                expected = products[d['product_ref']].get('branch_ref') if d.get('product_ref') else branch
                if (refs[ref].get('branch_ref') or 'actual') != (expected or 'actual'):
                    raise ValueError('Referencia cruzada entre sucursales en ' + row['sheet'])
    for row in groups['Restaurantes']:
        from models.category import CategoryModel
        from config import Config
        d = row['data']
        try: category_id = int(d['category_id'])
        except (ValueError, TypeError): raise ValueError('category_id invalido') from None
        if not CategoryModel.get_by_id(category_id) or d['district'] not in Config.DISTRITOS:
            raise ValueError('Categoria o distrito inexistente')
        if d['service_mode'] not in {'dine_in_only','dine_in_and_delivery','delivery_only','pickup_only'}:
            raise ValueError('Modalidad invalida')
        d['category_id'] = category_id
    for plan in product_plan(rows):
        validate_for_publication(plan['product'])
    for row in groups['Inventario']:
        d = row['data']; base_quantity(d['quantity'], d['unit'])
        if not d.get('expires') or date.fromisoformat(d['expires']) < date.today():
            raise ValueError('Inventario: vencimiento vigente obligatorio')
        if money(d.get('cost')) is None or base_quantity(d.get('basis') or 1, d['unit'])[0] < 1:
            raise ValueError('Inventario: costo y base validos obligatorios')
    for row in groups['Mesas']:
        capacity = float(row['data']['capacity'])
        if not capacity.is_integer() or not 1 <= capacity <= 100:
            raise ValueError('Capacidad de mesa: entero entre 1 y 100')


def context_hash(rid, actor):
    if rid is None:
        return model.fingerprint({'actor': actor, 'new': True})
    restaurant = model.require_owner(rid, actor)
    return model.fingerprint({'restaurant': restaurant, 'products': DishModel.get_by_restaurant(rid), 'kitchen': kitchen(rid)})


def preview_import(raw,rid,actor):
    from utils.catalog_workbook import validate_catalog_workbook
    from flask import current_app
    from itsdangerous import URLSafeTimedSerializer
    context = context_hash(rid, actor)
    digest=hashlib.sha256(raw).hexdigest()
    parsed=validate_catalog_workbook(raw)
    errors=list(parsed['errors'])
    if not errors:
        try:
            moderate_rows(parsed['rows'])
            if rid is None and any(r['data'].get('branch_ref') == 'actual' or r['data'].get('business_ref') == 'actual' for r in parsed['rows']):
                raise ValueError('actual requiere un restaurante propio seleccionado; usa referencias nuevas')
            for plan in product_plan(parsed['rows']):
                if plan['branch_ref'] == 'actual':
                    model.validate_media(validate_for_publication(plan['product']), rid, actor)
                elif any(url.startswith('/catalog-media/') for url in plan['product']['images']):
                    raise ValueError('Una sucursal nueva no puede usar imagen privada existente')
        except (ValueError, KeyError, TypeError) as error:
            errors.append({'sheet':'Validacion','row':0,'field':'contenido','message':str(error)})
    if not errors:
        try:
            for plan in product_plan(parsed['rows']):
                try:validate_for_publication(plan['product'])
                except ValueError as error:errors.append({'sheet':plan['sheet'],'row':plan['row'],'field':'producto','message':str(error)})
            for row in parsed['rows']:
                if row['sheet']=='Inventario':
                    d=row['data'];base_quantity(d['quantity'],d['unit'])
                    if not d.get('expires') or date.fromisoformat(d['expires'])<date.today():raise ValueError('Inventario: indica un vencimiento vigente')
                    if money(d.get('cost')) is None:raise ValueError('Inventario: confirma costo y base de costo')
                    base_quantity(d.get('basis') or 1,d['unit'])
        except (KeyError,ValueError,TypeError) as error:
            errors.append({'sheet':'Validacion','row':0,'field':'referencias','message':str(error)})
    status='invalid' if errors or not parsed['rows'] else 'pending'
    job = {'rid':rid,'owner_id':actor,'fingerprint':digest,'rows':parsed['rows'],
        'errors':errors,'warnings':parsed['warnings'],'counts':parsed['counts'],'status':status,
        'version':IMPORT_VERSION,'context_hash':context,'created_at':now()}
    token = URLSafeTimedSerializer(current_app.secret_key, salt='catalog-import-v2').dumps(job)
    return {**job, 'id': token, 'token': token}


def confirm_import(import_id,rid,actor):
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731051)')
        from flask import current_app
        from itsdangerous import URLSafeTimedSerializer, BadSignature
        try:
            job = URLSafeTimedSerializer(current_app.secret_key, salt='catalog-import-v2').loads(import_id, max_age=900)
        except BadSignature:
            raise ValueError('Preview invalido o caducado; vuelve a analizar') from None
        if job.get('rid') != rid or job.get('owner_id') != actor or job.get('version') != IMPORT_VERSION:
            raise ValueError('Preview ajeno o version obsoleta')
        if job['status']!='pending' or job['errors']:raise ValueError('Corrige el archivo antes de importar')
        previous = next((j for j in model.CatalogImportModel.all() if j.get('token_hash') == hashlib.sha256(import_id.encode()).hexdigest()), None)
        if previous and previous.get('status') == 'confirmed':
            return previous['result']
        if context_hash(rid, actor) != job['context_hash']:
            raise ValueError('El contexto cambio; vuelve a analizar el archivo')
        restaurant=model.require_owner(rid,actor) if rid is not None else {}
        rows=job['rows']; moderate_rows(rows); groups=grouped(rows)
        saved_job = model.CatalogImportModel.create({**job, 'token_hash':hashlib.sha256(import_id.encode()).hexdigest()})
        import_id = saved_job['id']
        from models.moderation import ModerationModel
        from utils.restaurant_review import check_restaurant
        created_restaurants = []
        for row in groups['Restaurantes']:
            d = {k:v for k,v in row['data'].items() if k != 'ref' and v is not None}
            evaluation = {'rules':check_restaurant(d), 'human_review_required':True, 'final_status':'PENDIENTE_REVISION'}
            saved = RestaurantModel.create({**d,'owner_id':actor,'verified':False,'status':'pending_review','automated_review':evaluation})
            ModerationModel.create_moderation_entry('restaurant',saved['id'],d,actor,ai_evaluation=evaluation)
            created_restaurants.append(saved['id'])
        businesses={};branches={'actual':rid};ingredient_names={};created=defaultdict(list)
        created['Restaurantes'] = created_restaurants
        def ensure_current_business():
            current=restaurant.get('business_id')
            if current:return current
            data=conn.execute('INSERT INTO public.sr_businesses(slug,name,status) VALUES (%s,%s,%s) RETURNING id',
                (slugify(restaurant['name'])+'-'+uuid4().hex[:8],restaurant['name'],'draft')).fetchone()
            current=data['id']
            conn.execute('INSERT INTO public.sr_memberships(user_id,business_id,role,status) VALUES (%s,%s,%s,%s)',(actor,current,'business_owner','active'))
            branch=conn.execute('INSERT INTO public.sr_branches(business_id,name,address,status) VALUES(%s,%s,%s,%s) RETURNING id',
                (current,restaurant['name'],restaurant.get('address',''),'active')).fetchone()['id']
            RestaurantModel.update(rid,{'business_id':current,'branch_id':branch})
            restaurant['business_id']=current
            return current
        for row in groups['Negocios']:
            d=row['data'];result=conn.execute('INSERT INTO public.sr_businesses(slug,name,status,metadata) VALUES (%s,%s,%s,%s) RETURNING id',
                (slugify(d['name'])+'-'+uuid4().hex[:8],d['name'],'draft',Repo._jsonb({'description':d.get('description',''),'business_type':d.get('business_type','')}))).fetchone()
            businesses[d['ref']]=result['id'];created['Negocios'].append(result['id'])
            conn.execute('INSERT INTO public.sr_memberships(user_id,business_id,role,status) VALUES (%s,%s,%s,%s)',(actor,result['id'],'business_owner','active'))
        for row in groups['Sucursales']:
            d=row['data'];business=ensure_current_business() if d.get('business_ref') in (None,'','actual') else businesses[d['business_ref']]
            branch=conn.execute('INSERT INTO public.sr_branches(business_id,name,address,district,latitude,longitude,status) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id',
                (business,d['name'],d.get('address',''),d.get('district',''),d.get('lat'),d.get('lng'),'draft')).fetchone()['id']
            business_description=next((b['data'].get('description','') for b in groups['Negocios'] if businesses.get(b['data']['ref'])==business),'')
            saved=RestaurantModel.create({'name':d['name'],'owner_id':actor,'business_id':business,'branch_id':branch,
                'address':d.get('address',''),'district':d.get('district',''),'lat':d.get('lat'),'lng':d.get('lng'),
                'open_time':d.get('open_time',''),'close_time':d.get('close_time',''),'description':business_description,
                'verified':False,'status':'pending_review','image':'','rating':0,'tags':[],'category_id':None})
            evaluation = {'rules':check_restaurant(saved), 'human_review_required':True, 'final_status':'PENDIENTE_REVISION'}
            ModerationModel.create_moderation_entry('restaurant',saved['id'],saved,actor,ai_evaluation=evaluation)
            branches[d['ref']]=saved['id'];created['Sucursales'].append(saved['id'])
        def branch_id(d):return branches[d.get('branch_ref') or 'actual']
        for row in groups['Categorias']:
            d=row['data'];saved=model.CatalogCategoryModel.create({**d,'rid':branch_id(d),'owner_id':actor})
            created['Categorias'].append(saved['id'])
        for row in groups['Ingredientes']:
            d=row['data'];ingredient_names[d['ref']]=d['name'].strip().lower()
            saved=model.CatalogIngredientModel.create({**d,'rid':branch_id(d),'owner_id':actor})
            created['Ingredientes'].append(saved['id'])
        products={}
        for plan in product_plan(rows):
            target=branches[plan['branch_ref']];product=validate_for_publication(plan['product'])
            model.validate_media(product,target,actor)
            if any(p.get('name','').casefold()==product['name'].casefold() and (p.get('menu_date') or '')==product['menu_date'] for p in DishModel.get_by_restaurant(target)):
                raise ValueError('Ya existe '+product['name']+' en el establecimiento; no se importó ninguna fila')
            saved=DishModel.create({**product,'restaurant_id':target,'created_at':now(),'updated_at':now(),'import_id':import_id})
            ModerationModel.create_moderation_entry('dish',saved['id'],product,actor,
                ai_evaluation={'rules':check_restaurant(product),'human_review_required':True,'final_status':'PENDIENTE_REVISION'})
            products[plan['ref']]=saved['id'];created['Platos'].append(saved['id'])
        for row in groups['Inventario']:
            d=row['data'];target=branch_id(d)
            conn.execute('SELECT id FROM public.app_records WHERE collection=%s AND id=%s FOR UPDATE',('restaurants',target))
            store=kitchen(target);name=ingredient_names[d['ingredient_ref']]
            qty,unit=base_quantity(d['quantity'],d['unit']);cost=money(d.get('cost'));basis,_=base_quantity(d.get('basis') or 1,d['unit'])
            if cost is None or basis<1:raise ValueError('Costo y base de inventario inválidos')
            old=store['pantry'].get(name);before=old['quantity'] if old else 0
            if old and before and any(old[key]!=value for key,value in [('unit',unit),('expires',d['expires']),('cost',cost),('basis',basis)]):
                raise ValueError('El insumo '+name+' tiene otro lote/costo; usa un nombre distinto antes de importar')
            store['pantry'][name]={'quantity':before+qty,'unit':unit,'expires':d['expires'],'cost':cost,'basis':basis,
                'lot':old['lot'] if old and before else d.get('lot') or uuid4().hex,'substitutes':[]}
            save_kitchen(store)
            move=Repo.create('market_movements',{'rid':target,'name':name,'move':'Entrada','delta':qty,'actor':actor,'at':now(),'import_id':import_id})
            created['Inventario'].append(move['id'])
        for row in groups['Mesas']:
            d=row['data'];saved=model.CatalogTableModel.create({**d,'rid':branch_id(d),'owner_id':actor,
                'qr_token':uuid4().hex,'status':'available','import_id':import_id,'created_at':now()})
            created['Mesas'].append(saved['id'])
        result={'created':dict(created),'products':products,'notice':'Productos enlazados a la carta; negocios nuevos pendientes de verificación. No se creó producción ni pedidos.'}
        model.CatalogImportModel.update(import_id,{'status':'confirmed','result':result,'confirmed_at':now()})
        record_event('ADMIN_RESTAURANT_UPDATE',resource_type='catalog_import',resource_id=import_id,metadata={'operation':'bulk_confirm','counts':{key:len(value) for key,value in created.items()}})
        return result
