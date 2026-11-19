from flask import Blueprint, jsonify, render_template, request
from views.discovery import api_action, payload
from utils.security import fresh_session_user
from utils.account_security import allow_attempt
from models import commercial_radar as service
from config import Config

bp = Blueprint('commercial_radar', __name__)


@bp.before_request
def secure():
    user = fresh_session_user()
    if not user:
        return jsonify(success=False, error='Inicia sesion'), 401
    if user.get('role') != 'admin':
        return jsonify(success=False, error='Administrador requerido'), 403
    if request.method != 'GET' and not allow_attempt('commercial-radar', str(user['id']), request.remote_addr or ''):
        return jsonify(success=False, error='Limite de operaciones alcanzado'), 429


@bp.get('/admin/radar-comercial')
@api_action
def dashboard():
    return render_template('admin/commercial_radar.html', prospects=[service.presentation(p) for p in service.ProspectModel.all()],
        states=service.STATES, center=Config.COORDENADAS_CENTRO, companies=service.companies())


@bp.get('/admin/api/radar-comercial')
@api_action
def listing():
    rows = service.ProspectModel.all()
    state = request.args.get('state')
    if state and state not in service.STATES:
        raise ValueError('Estado invalido')
    return jsonify(success=True, prospects=[service.presentation(p) for p in rows if not state or p['state'] == state])


@bp.post('/admin/api/radar-comercial/discover')
@api_action
def discover():
    return jsonify(success=True, result=service.discover(fresh_session_user()['id'], payload()))


@bp.post('/admin/api/radar-comercial/<int:pid>/<action>')
@api_action
def action(pid, action):
    values = payload()
    actor = fresh_session_user()['id']
    if action == 'state':
        row = service.update_state(pid, values.get('state'), actor, values.get('notes'), values.get('company_id'))
    elif action == 'analyze':
        row = service.analyze(pid)
    elif action == 'convert':
        if values.get('confirm') is not True:
            raise ValueError('Confirma conversion provisional')
        row = service.convert(pid, actor, values.get('notes'))
    else:
        raise ValueError('Accion invalida')
    return jsonify(success=True, prospect=service.presentation(row))


@bp.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response
