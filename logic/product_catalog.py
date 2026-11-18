"""Contratos puros para productos gastronómicos, compartidos por formulario/IA/Excel."""
from copy import deepcopy
from datetime import date
from decimal import Decimal,InvalidOperation
import re
from models.business_site import safe_media_url

TYPES={'plato','bebida','postre'}
AVAILABILITY={'available','sold_out','paused'}
UNITS={'g','kg','ml','l','unidad'}


def money(value):
    if value is None or value=='':return None
    if isinstance(value,bool):raise ValueError('Precio inválido')
    try:amount=Decimal(str(value).strip())
    except InvalidOperation:raise ValueError('El precio debe ser numérico') from None
    if not amount.is_finite() or not 0<=amount<=1000000 or amount!=amount.quantize(Decimal('.01')):
        raise ValueError('El precio requiere importe finito, no negativo y máximo dos decimales')
    return int(amount*100)


def strings(value,limit=40,length=120):
    if value is None:return []
    if not isinstance(value,list) or len(value)>limit or any(not isinstance(x,str) for x in value):
        raise ValueError('Se requiere una lista de textos dentro del límite')
    result=[]
    for item in value:
        item=' '.join(item.split())[:length]
        if item and item.casefold() not in {v.casefold() for v in result}:result.append(item)
    return result


def defaults():
    return {'name':'','product_type':'plato','category':'Fondo','subcategory':'','description':'',
        'price':None,'price_cents':None,'portion':'personal','ingredients':[], 'probable_ingredients':[],
        'allergens':None,'allergens_confirmed':False,'ingredients_confirmed':False,
        'recipe':[],'variants':[],'addons':[],'tags':[],'images':[],'videos':[],
        'availability':'available','is_available':False,'promotional':False,'promo_text':'',
        'menu_type':'carta','menu_date':'','meal_time':'almuerzo','rights_confirmed':False}


def normalize_product(patch,previous=None):
    if not isinstance(patch,dict):raise ValueError('Producto debe ser un objeto JSON')
    result=defaults()
    if previous:
        for key in result:
            if key in previous:result[key]=deepcopy(previous[key])
        if not result['images'] and previous.get('image'):result['images']=[previous['image']]
    for field,limit in [('name',160),('category',100),('subcategory',100),('description',2000),('portion',120),('promo_text',500)]:
        if field in patch:
            if not isinstance(patch[field],str):raise ValueError(f'{field} debe ser texto')
            result[field]=patch[field].strip()[:limit]
    for key,allowed in [('product_type',TYPES),('availability',AVAILABILITY),('menu_type',{'carta','variable'}),('meal_time',{'desayuno','almuerzo','cena'})]:
        value=patch.get(key,result[key])
        if value not in allowed:raise ValueError(f'{key}: opción inválida')
        result[key]=value
    if 'category' not in patch and 'product_type' in patch:
        result['category']={'plato':'Fondo','bebida':'Bebida','postre':'Postre'}[result['product_type']]
    for flag in ('allergens_confirmed','ingredients_confirmed','rights_confirmed','promotional'):
        if flag in patch:
            if not isinstance(patch[flag],bool):raise ValueError(f'{flag}: confirma usando booleano')
            result[flag]=patch[flag]
    for key in ('ingredients','probable_ingredients','tags'):
        if key in patch:result[key]=strings(patch[key])
    if 'allergens' in patch:result['allergens']=None if patch['allergens'] is None else strings(patch['allergens'])
    if not result['allergens_confirmed']:result['allergens']=None
    if 'price' in patch or result['price'] is not None:
        cents=money(patch.get('price',result['price']));result['price_cents']=cents
        result['price']=None if cents is None else cents/100
    if 'menu_date' in patch:result['menu_date']=str(patch['menu_date'] or '')
    if result['menu_date']:
        try:date.fromisoformat(result['menu_date'])
        except ValueError:raise ValueError('Fecha de menú inválida') from None
    for key,max_items,video in [('images',12,False),('videos',5,True)]:
        if key in patch:
            urls=strings(patch[key],max_items,1200)
            result[key]=[safe_media_url(url,video) if not url.startswith('/catalog-media/') else url for url in urls]
            if any(url.startswith('/catalog-media/') and not re.fullmatch(r'/catalog-media/[0-9]+',url) for url in result[key]):
                raise ValueError('Referencia a imagen inválida')
    if 'recipe' in patch:
        recipe=patch['recipe']
        if not isinstance(recipe,list) or len(recipe)>60:raise ValueError('Receta: hasta sesenta insumos por porción')
        normalized=[];seen=set()
        for line in recipe:
            if not isinstance(line,dict):raise ValueError('Receta requiere ingrediente, cantidad y unidad')
            ingredient=str(line.get('ingredient','')).strip()[:100]
            if not ingredient or ingredient.casefold() in seen or line.get('unit') not in UNITS:
                raise ValueError('Insumo de receta vacío, duplicado o unidad inválida')
            try:qty=Decimal(str(line.get('quantity')))
            except InvalidOperation:raise ValueError('Cantidad de receta inválida') from None
            if not qty.is_finite() or not 0<qty<=1000000:raise ValueError('La cantidad por porción debe ser positiva y finita')
            normalized.append({'ingredient':ingredient,'quantity':str(qty),'unit':line['unit']});seen.add(ingredient.casefold())
        result['recipe']=normalized
    for field in ('variants','addons'):
        if field not in patch:continue
        options=patch[field]
        if not isinstance(options,list) or len(options)>20:raise ValueError('Hasta veinte variantes o adicionales')
        normalized=[];seen=set()
        for option in options:
            if not isinstance(option,dict):raise ValueError('Variante/adicional inválido')
            name=str(option.get('name','')).strip()[:100]
            if not name or name.casefold() in seen:raise ValueError('Variante/adicional requiere nombre único')
            cents=money(option.get('price'))
            normalized.append({'name':name,'portion':str(option.get('portion',''))[:100],
                'price':None if cents is None else cents/100,'price_cents':cents});seen.add(name.casefold())
        result[field]=normalized
    result['is_available']=result['availability']=='available'
    return result


def validate_for_publication(product):
    result=normalize_product(product)
    if not result['name'] or result['price_cents'] is None:raise ValueError('Confirma nombre y precio del producto')
    if not result['ingredients_confirmed'] or not result['allergens_confirmed'] or result['allergens'] is None:
        raise ValueError('Confirma ingredientes y declaración de alérgenos; una foto no los certifica')
    if not result['rights_confirmed']:raise ValueError('Confirma los derechos sobre el contenido')
    if result['menu_type']=='variable' and not result['menu_date']:raise ValueError('El menú variable requiere fecha')
    if any(option['price_cents'] is None for option in result['variants']+result['addons']):raise ValueError('Confirma precio de variantes y adicionales')
    result['image']=result['images'][0] if result['images'] else ''
    return result


def ai_product(proposal,mode='photo',previous=None):
    if not isinstance(proposal,dict):raise ValueError('La IA no produjo un borrador estructurado')
    keys={'name','product_type','category','subcategory','description','portion','ingredients','tags'}
    if mode=='voice':keys|={'price','recipe','variants','addons'}
    filtered={key:value for key,value in proposal.items() if key in keys and (value is not None or key=='price')}
    probable=strings(filtered.pop('ingredients',[]))
    if mode=='voice':filtered['ingredients']=probable
    else:filtered.update(ingredients=[],probable_ingredients=probable,price=None)
    filtered.update(allergens=None,allergens_confirmed=False,ingredients_confirmed=False,rights_confirmed=False)
    return normalize_product(filtered,previous)


def base_quantity(quantity,unit):
    value=Decimal(str(quantity))*(1000 if unit in {'kg','l'} else 1)
    if not value.is_finite() or value!=value.to_integral_value() or value<0:raise ValueError('Convierte la cantidad a gramos, mililitros o unidades enteras')
    return int(value),{'kg':'g','l':'ml'}.get(unit,unit)
