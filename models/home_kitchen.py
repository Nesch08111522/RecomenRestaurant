"""Private home pantry, declared recipes and transactional preparation."""
from datetime import date, timedelta
from uuid import UUID

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import MarketError, integer, key, now
from utils.audit import record_event

UNITS = ('g', 'ml', 'unidad')
MEALS = ('Desayuno', 'Almuerzo', 'Cena')


def rows(collection, uid):
    return [r for r in Repo.all(collection) if r.get('uid') == uid]


def owned(collection, item_id, uid):
    row = Repo.get_by_id(collection, item_id, for_update=True)
    if not row or row.get('uid') != uid:
        raise MarketError('Registro no disponible.')
    return row


def lock(conn, uid):
    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', (f'home:{uid}',))


def save_pantry(uid, data, item_id=None):
    name = key(data.get('name', ''))
    unit = data.get('unit')
    quantity = integer(data.get('quantity'), 0, 10000000)
    try:
        expires = date.fromisoformat(data.get('expires', ''))
    except (TypeError, ValueError):
        raise MarketError('Indica un vencimiento valido.') from None
    if not 1 <= len(name) <= 70 or unit not in UNITS:
        raise MarketError('Revisa el ingrediente y su unidad.')
    with document_transaction() as conn:
        lock(conn, uid)
        if item_id:
            owned('home_pantry', item_id, uid)
        payload = dict(uid=uid, name=name, unit=unit, quantity=quantity, expires=expires.isoformat(), updated=now().isoformat())
        result = Repo.update('home_pantry', item_id, payload) if item_id else Repo.create('home_pantry', payload)
        record_event('HOME_UPDATED', resource_type='home_pantry', resource_id=result['id'], actor_user_id=uid)
        return result


def remove(uid, collection, item_id):
    if collection not in ('home_pantry', 'home_recipes', 'home_plan'):
        raise MarketError('Operacion no permitida.')
    with document_transaction() as conn:
        lock(conn, uid)
        owned(collection, item_id, uid)
        # Recipes used by a plan must remain available until that plan is removed.
        if collection == 'home_recipes' and any(r.get('recipe_id') == item_id for r in rows('home_plan', uid)):
            raise MarketError('Retira primero esta receta del plan.')
        Repo.delete(collection, item_id)
        record_event('HOME_UPDATED', resource_type=collection, resource_id=item_id, actor_user_id=uid)


def save_recipe(uid, data, item_id=None):
    name = str(data.get('name', '')).strip()
    ingredients = data.get('ingredients')
    steps = data.get('steps')
    if not 1 <= len(name) <= 120 or not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 30:
        raise MarketError('Declara nombre e ingredientes de la receta.')
    if not isinstance(steps, list) or not 1 <= len(steps) <= 30 or any(not isinstance(s, str) or not 1 <= len(s.strip()) <= 1000 for s in steps):
        raise MarketError('Declara entre uno y treinta pasos de preparacion.')
    clean, seen = [], set()
    for entry in ingredients:
        if not isinstance(entry, dict):
            raise MarketError('Ingrediente invalido.')
        ingredient = key(entry.get('name', ''))
        unit = entry.get('unit')
        if not 1 <= len(ingredient) <= 70 or unit not in UNITS or (ingredient, unit) in seen:
            raise MarketError('Revisa ingredientes duplicados y unidades.')
        seen.add((ingredient, unit))
        clean.append(dict(name=ingredient, unit=unit, quantity=integer(entry.get('quantity'), 1, 10000000)))
    confirmed = data.get('confirmed') is True
    payload = dict(uid=uid, name=name, ingredients=clean, steps=[s.strip() for s in steps],
                   servings=integer(data.get('servings', 1), 1, 20), minutes=integer(data.get('minutes', 0), 0, 1440),
                   status='confirmed' if confirmed else 'draft', source='user_declared', updated=now().isoformat())
    with document_transaction() as conn:
        lock(conn, uid)
        if item_id:
            owned('home_recipes', item_id, uid)
        result = Repo.update('home_recipes', item_id, payload) if item_id else Repo.create('home_recipes', payload)
        record_event('HOME_UPDATED', resource_type='home_recipe', resource_id=result['id'], actor_user_id=uid)
        return result


def plan(uid, recipe_id, day, meal, batches=1):
    try:
        target = date.fromisoformat(day)
    except (TypeError, ValueError):
        raise MarketError('Dia de plan invalido.') from None
    if not now().date() <= target <= now().date() + timedelta(days=90) or meal not in MEALS:
        raise MarketError('Elige una comida y un dia dentro de los proximos 90 dias.')
    batches = integer(batches, 1, 20)
    with document_transaction() as conn:
        lock(conn, uid)
        recipe = owned('home_recipes', recipe_id, uid)
        if recipe['status'] != 'confirmed':
            raise MarketError('Confirma la receta antes de planificar.')
        existing = next((r for r in rows('home_plan', uid) if r['day'] == day and r['meal'] == meal), None)
        if existing and existing.get('prepared'):
            raise MarketError('La comida ya preparada no puede reemplazarse.')
        payload = dict(uid=uid, recipe_id=recipe_id, day=day, meal=meal, batches=batches, prepared=False)
        result = Repo.update('home_plan', existing['id'], payload) if existing else Repo.create('home_plan', payload)
        record_event('HOME_UPDATED', resource_type='home_plan', resource_id=result['id'], actor_user_id=uid)
        return result


def shopping(uid, start):
    end = start + timedelta(days=6)
    pantry = [dict(r) for r in rows('home_pantry', uid)]
    recipes = {r['id']: r for r in rows('home_recipes', uid)}
    missing = {}
    for item in sorted(rows('home_plan', uid), key=lambda r: (r['day'], r['id'])):
        if item.get('prepared') or not start.isoformat() <= item['day'] <= end.isoformat():
            continue
        recipe = recipes.get(item['recipe_id'])
        if not recipe:
            continue
        for ingredient in recipe['ingredients']:
            need = ingredient['quantity'] * item['batches']
            for lot in sorted(pantry, key=lambda r: (r['expires'], r['id'])):
                if (lot['name'], lot['unit']) != (ingredient['name'], ingredient['unit']) or lot['expires'] < item['day']:
                    continue
                used = min(need, lot['quantity'])
                lot['quantity'] -= used
                need -= used
            signature = (ingredient['name'], ingredient['unit'])
            missing[signature] = missing.get(signature, 0) + need
    return [dict(name=n, unit=u, quantity=q) for (n, u), q in sorted(missing.items()) if q]


def prepare(uid, recipe_id, batches, request_key, plan_id=None):
    try:
        request_key = str(UUID(request_key))
    except (TypeError, ValueError, AttributeError):
        raise MarketError('Actualiza la solicitud de preparacion.') from None
    batches = integer(batches, 1, 20)
    with document_transaction() as conn:
        lock(conn, uid)
        existing = next((r for r in rows('home_preparations', uid) if r['request_key'] == request_key), None)
        if existing:
            if existing['recipe_id'] != recipe_id or existing['batches'] != batches or existing.get('plan_id') != plan_id:
                raise MarketError('La solicitud ya corresponde a otra preparacion.')
            return existing
        recipe = owned('home_recipes', recipe_id, uid)
        if recipe['status'] != 'confirmed':
            raise MarketError('Confirma los ingredientes y pasos antes de preparar.')
        planned = owned('home_plan', plan_id, uid) if plan_id else None
        if planned and (planned.get('prepared') or planned['recipe_id'] != recipe_id or planned['batches'] != batches):
            raise MarketError('El plan ya se preparo o cambio.')
        pantry = rows('home_pantry', uid)
        usage = []
        for ingredient in recipe['ingredients']:
            need = ingredient['quantity'] * batches
            for lot in sorted(pantry, key=lambda r: (r['expires'], r['id'])):
                if (lot['name'], lot['unit']) != (ingredient['name'], ingredient['unit']) or lot['expires'] < now().date().isoformat():
                    continue
                used = min(need, lot['quantity'])
                if used:
                    lot['quantity'] -= used
                    need -= used
                    Repo.update('home_pantry', lot['id'], {'quantity': lot['quantity']})
                    usage.append(dict(pantry_id=lot['id'], name=lot['name'], quantity=used, unit=lot['unit']))
            if need:
                raise MarketError(f"Stock vigente insuficiente: {ingredient['name']}.")
        result = Repo.create('home_preparations', dict(uid=uid, recipe_id=recipe_id, name=recipe['name'], batches=batches,
                            servings=recipe['servings'] * batches, request_key=request_key, plan_id=plan_id, usage=usage, at=now().isoformat()))
        if planned:
            Repo.update('home_plan', plan_id, {'prepared': True, 'preparation_id': result['id']})
        record_event('HOME_PREPARED', resource_type='home_preparation', resource_id=result['id'], actor_user_id=uid)
        return result
