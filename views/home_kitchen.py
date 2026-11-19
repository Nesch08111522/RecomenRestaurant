"""Authenticated home kitchen, using the existing private application shell."""
from datetime import date, timedelta
from uuid import uuid4

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from logic.market import MarketError, integer, now
from models import home_kitchen as home
from utils.security import fresh_session_user

bp = Blueprint('home_kitchen', __name__, url_prefix='/home')


def actor():
    user = fresh_session_user()
    if not user:
        abort(401)
    return user['id']


@bp.before_request
def validate_body():
    if request.is_json and not isinstance(request.get_json(silent=True), dict):
        return jsonify(success=False, error='Se requiere un objeto JSON.'), 400


@bp.errorhandler(MarketError)
def invalid(error):
    if request.is_json:
        return jsonify(success=False, error=str(error)), 400
    flash(str(error), 'warning')
    return redirect(url_for('home_kitchen.index'))


@bp.get('/')
def index():
    uid = actor()
    try:
        start = date.fromisoformat(request.args.get('week', now().date().isoformat()))
    except ValueError:
        raise MarketError('Semana invalida.') from None
    start -= timedelta(days=start.weekday())
    recipes = home.rows('home_recipes', uid)
    return render_template('home_kitchen.html', pantry=home.rows('home_pantry', uid), recipes=recipes,
                           recipe_map={r['id']: r for r in recipes},
                           plans=[r for r in home.rows('home_plan', uid) if start.isoformat() <= r['day'] <= (start + timedelta(days=6)).isoformat()],
                           shopping=home.shopping(uid, start), preparations=home.rows('home_preparations', uid)[-30:][::-1],
                           week=start.isoformat(), today=now().date().isoformat(), meals=home.MEALS, request_key=str(uuid4()))


@bp.post('/pantry')
def pantry_save():
    data = request.get_json() if request.is_json else request.form
    uid = actor()
    item_id = integer(data['id'], 1) if data.get('id') else None
    row = home.save_pantry(uid, data, item_id)
    if request.is_json:
        return jsonify(success=True, item=row)
    return redirect(url_for('home_kitchen.index'))


@bp.post('/recipes')
def recipe_save():
    uid = actor()
    if request.is_json:
        data = request.get_json()
    else:
        data = dict(request.form)
        ingredients = []
        for line in data.get('ingredients', '').splitlines():
            parts = line.split('=')
            if len(parts) != 3:
                raise MarketError('Usa ingrediente=cantidad=unidad en cada linea.')
            ingredients.append(dict(name=parts[0], quantity=parts[1], unit=parts[2].strip()))
        data.update(ingredients=ingredients, steps=data.get('steps', '').splitlines(), confirmed=data.get('confirmed') == 'on')
    row = home.save_recipe(uid, data, integer(data['id'], 1) if data.get('id') else None)
    if request.is_json:
        return jsonify(success=True, item=row)
    return redirect(url_for('home_kitchen.index', _anchor='recetas'))


@bp.post('/<collection>/<int:item_id>/remove')
def remove(collection, item_id):
    home.remove(actor(), 'home_' + collection, item_id)
    return redirect(url_for('home_kitchen.index'))


@bp.post('/plan')
def plan_save():
    uid = actor()
    data = request.get_json() if request.is_json else request.form
    row = home.plan(uid, integer(data.get('recipe_id'), 1), data.get('day'), data.get('meal'), data.get('batches', 1))
    if request.is_json:
        return jsonify(success=True, item=row)
    return redirect(url_for('home_kitchen.index', week=row['day'], _anchor='plan'))


@bp.post('/prepare')
def prepare():
    uid = actor()
    data = request.get_json() if request.is_json else request.form
    row = home.prepare(uid, integer(data.get('recipe_id'), 1), data.get('batches', 1), data.get('request_key'),
                       integer(data['plan_id'], 1) if data.get('plan_id') else None)
    if request.is_json:
        return jsonify(success=True, item=row)
    flash('Preparacion registrada y stock descontado.', 'success')
    return redirect(url_for('home_kitchen.index'))
