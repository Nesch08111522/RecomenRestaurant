"""HTTP del radar: lectura de borradores solo administrativa y claim supervisado."""
from functools import wraps
from flask import Blueprint,request,jsonify,render_template,session,current_app
from core.permissions import can
from utils.security import fresh_session_user
from models import discovery as service
from utils.discovery_sources import google_lookup,SourceUnavailable

bp=Blueprint('discovery',__name__)


def admin_only(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        user=fresh_session_user()
        if not user:
            return jsonify(success=False,error='Inicia sesión como administrador',code='unauthenticated'),401
        if not can(user.get('role'),'platform.verification.manage'):
            return jsonify(success=False,error='Este módulo es exclusivo del administrador',code='forbidden'),403
        return view(*args,**kwargs)
    return wrapped


def api_action(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        try:
            return view(*args,**kwargs)
        except ValueError as error:
            return jsonify(success=False,error=str(error),code='validation_error'),400
        except SourceUnavailable as error:
            return jsonify(success=False,error=str(error),code='source_unavailable'),502
        except Exception as error:
            current_app.logger.error('Radar no completó operación: %s',type(error).__name__)
            return jsonify(success=False,error='La operación no pudo completarse. Revisa el estado de la fuente y la conexión.',code='discovery_unavailable'),503
    return wrapped


def payload():
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        raise ValueError('Se requiere un objeto JSON')
    return data


@bp.get('/admin/discovery')
@admin_only
@api_action
def dashboard():
    return render_template('discovery/dashboard.html',candidates=service.CandidateModel.all(),
        sources=service.SourceModel.all(),runs=service.RunModel.all()[-10:][::-1],claims=service.ClaimModel.all())


@bp.get('/admin/discovery/google-lookup')
@admin_only
def google_page():
    return render_template('discovery/google.html')


@bp.get('/admin/api/discovery/export/osm')
@admin_only
@api_action
def export_osm():
    rows=[{'source_key':row['source_key'],'data':row['data'],'evidence':row['evidence']}
          for row in service.CandidateModel.all() if row['source_key'].startswith('osm:')]
    response=jsonify(attribution='Map data from OpenStreetMap',
        license='ODbL-1.0',license_url='https://opendatacommons.org/licenses/odbl/1-0/',
        attribution_url='https://www.openstreetmap.org/copyright',records=rows)
    response.headers['Content-Disposition']='attachment; filename="smartresto-osm-provisional.json"'
    return response


@bp.get('/admin/api/discovery/candidates')
@admin_only
@api_action
def candidates():
    rows=service.CandidateModel.all()
    state=request.args.get('status'); query=request.args.get('q','').casefold()
    rows=[r for r in rows if (not state or r['status']==state) and (not query or query in r['data'].get('name','').casefold())]
    return jsonify(success=True,candidates=rows[-500:][::-1],total=len(rows))


@bp.get('/admin/api/discovery/sources')
@admin_only
@api_action
def sources():
    return jsonify(success=True,sources=service.SourceModel.all())


@bp.post('/admin/api/discovery/sources')
@admin_only
@api_action
def add_source():
    return jsonify(success=True,source=service.register_source(payload(),session['user_id'])),201


@bp.patch('/admin/api/discovery/sources/<int:source_id>')
@admin_only
@api_action
def pause_source(source_id):
    data=payload()
    if not isinstance(data.get('enabled'),bool):
        raise ValueError('enabled debe ser booleano')
    with service.document_transaction() as conn:
        service.lock(conn)
        source=service.SourceModel.get_by_id(source_id)
        if not source:
            raise ValueError('Fuente no encontrada')
        updated=service.SourceModel.update(source_id,{'enabled':data['enabled']})
        service.event('DISCOVERY_SOURCE_REGISTER',source_id,session['user_id'],{'enabled':data['enabled']})
    return jsonify(success=True,source=updated)


@bp.post('/admin/api/discovery/runs')
@admin_only
@api_action
def start_run():
    data=payload()
    result=service.run_source(data.get('source','osm'),session['user_id'])
    return jsonify(success=True,run=result)


@bp.post('/admin/api/discovery/candidates/<int:candidate_id>/review')
@admin_only
@api_action
def review(candidate_id):
    data=payload()
    result=service.review(candidate_id,data.get('action'),session['user_id'],data.get('notes',''))
    return jsonify(success=True,candidate=result)


@bp.post('/admin/api/discovery/candidates/<int:candidate_id>/invite')
@admin_only
@api_action
def invite(candidate_id):
    result=service.invite(candidate_id,session['user_id'])
    # Fragment: token never appears in HTTP access logs or Referer.
    result['path']='/reclamar#token='+result.pop('token')
    return jsonify(success=True,invitation=result)


@bp.post('/admin/api/discovery/claims/<int:claim_id>/review')
@admin_only
@api_action
def review_claim(claim_id):
    data=payload()
    return jsonify(success=True,candidate=service.decide_claim(claim_id,data.get('action'),session['user_id'],data.get('notes','')))


@bp.post('/admin/api/discovery/google')
@admin_only
@api_action
def google():
    response=jsonify(success=True,**google_lookup(payload().get('q')))
    response.headers['Cache-Control']='no-store'
    return response


@bp.get('/reclamar')
def claim_page():
    return render_template('discovery/claim.html')


@bp.post('/api/discovery/invitations/preview')
@api_action
def preview():
    _,row=service.invitation_record(payload().get('token',''))
    return jsonify(success=True,business={k:row['data'].get(k) for k in ('name','address','business_type')},status='Ficha provisional, no publicación verificada')


@bp.post('/api/discovery/claims')
@api_action
def claim():
    user=fresh_session_user()
    if not user:
        return jsonify(success=False,error='Inicia sesión como empresario',code='unauthenticated'),401
    if user.get('role')!='business_owner':
        return jsonify(success=False,error='Solo el empresario puede solicitar titularidad',code='forbidden'),403
    data=payload()
    row=service.request_claim(data.get('token',''),user['id'],data.get('proof',''))
    return jsonify(success=True,claim_id=row['id'],status='Pendiente de revisión administrativa'),201


@bp.get('/owner/discovery')
@api_action
def owner_space():
    user=fresh_session_user()
    if not user:
        return jsonify(success=False,error='Inicia sesión como empresario'),401
    if user.get('role')!='business_owner':
        return jsonify(success=False,error='Este espacio es exclusivo del empresario'),403
    owned=[row for row in service.CandidateModel.all() if row.get('owner_id')==user['id']]
    requests=[row for row in service.ClaimModel.all() if row.get('user_id')==user['id']]
    return render_template('discovery/owner.html',businesses=owned,claims=requests)


@bp.after_request
def protect_discovery_response(response):
    response.headers['Cache-Control']='no-store'
    if request.path=='/reclamar' or request.path.startswith('/api/discovery/'):
        response.headers['Referrer-Policy']='no-referrer'
    return response
