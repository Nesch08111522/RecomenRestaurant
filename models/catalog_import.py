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


def preview_import(raw,rid,actor):
    from utils.catalog_workbook import validate_catalog_workbook
    model.require_owner(rid,actor)
    digest=hashlib.sha256(raw).hexdigest()
    previous=next((job for job in model.CatalogImportModel.all() if job['rid']==rid and job['owner_id']==actor and job['fingerprint']==digest and job['status']=='confirmed'),None)
    if previous:return previous
    parsed=validate_catalog_workbook(raw)
    errors=list(parsed['errors'])
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
    return model.CatalogImportModel.create({'rid':rid,'owner_id':actor,'fingerprint':digest,'rows':parsed['rows'],
        'errors':errors,'warnings':parsed['warnings'],'counts':parsed['counts'],'status':status,'created_at':now()})


def confirm_import(import_id,rid,actor):
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731051)')
        restaurant=model.require_owner(rid,actor)
        job=model.CatalogImportModel.get_by_id(import_id)
        if not job or job['rid']!=rid or job['owner_id']!=actor:raise ValueError('Importación ajena o inexistente')
        if job['status']=='confirmed':return job['result']
        if job['status']!='pending' or job['errors']:raise ValueError('Corrige el archivo antes de importar')
        rows=job['rows'];groups=grouped(rows)
        businesses={};branches={'actual':rid};ingredient_names={};created=defaultdict(list)
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
