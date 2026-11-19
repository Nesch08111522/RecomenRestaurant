"""Personal y verificación empresarial con controles de alcance en servidor."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from database.repository import PostgresDocumentRepository as Repo, document_transaction
from models.membership import ROLES, assign, authorized
from models.restaurant import RestaurantModel
from utils.security import fresh_session_user
from utils.audit import record_event

bp = Blueprint('business_access', __name__)


def actor():
    user = fresh_session_user()
    if not user:
        abort(401)
    return user


@bp.route('/owner/acceso/<int:rid>', methods=['GET', 'POST'])
def access(rid):
    user = actor()
    if not authorized(user, rid, 'staff.manage'):
        abort(403)
    if request.method == 'POST':
        try:
            assign(user, rid, request.form.get('username', '').strip(), request.form.get('role'), request.form.get('status'))
        except ValueError as error:
            flash(str(error), 'error')
            return redirect(url_for('business_access.access', rid=rid))
        except PermissionError:
            abort(403)
        flash('Permisos del establecimiento actualizados.', 'success')
        return redirect(url_for('business_access.access', rid=rid))
    members = [m for m in Repo.all('branch_memberships') if m.get('rid') == rid]
    return render_template('owner/business_access.html', business=RestaurantModel.get_by_id(rid), members=members, roles=ROLES,
                           verification=next((v for v in reversed(Repo.all('business_verifications')) if v.get('rid') == rid), None))


@bp.post('/owner/acceso/<int:rid>/verificacion')
def submit_verification(rid):
    user = actor()
    if not authorized(user, rid, 'business.manage'):
        abort(403)
    import re
    tax_id = request.form.get('tax_id', '').strip()
    name = request.form.get('legal_name', '').strip()
    evidence = request.form.get('evidence', '').strip()
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(evidence)
    except ValueError:
        abort(400)
    if not re.fullmatch(r'\d{11}', tax_id) or not 2 <= len(name) <= 160 or not 1 <= len(evidence) <= 500 or parsed.scheme != 'https' or not parsed.hostname or parsed.username:
        abort(400)
    with document_transaction():
        Repo.get_by_id('restaurants', rid, for_update=True)
        pending = [v for v in Repo.all('business_verifications') if v.get('rid') == rid and v.get('status') == 'pending']
        if pending:
            abort(409)
        Repo.create('business_verifications', dict(rid=rid, uid=user['id'], tax_id=tax_id, legal_name=name, evidence=evidence, status='pending'))
        record_event('BUSINESS_VERIFICATION_SUBMITTED', resource_type='restaurant', resource_id=rid, actor_user_id=user['id'])
    flash('Solicitud enviada para revisión humana. No implica identidad verificada.', 'success')
    return redirect(url_for('business_access.access', rid=rid))


@bp.route('/admin/verificacion-empresarial', methods=['GET', 'POST'])
def review():
    user = actor()
    if user['role'] != 'admin':
        abort(403)
    if request.method == 'POST':
        status = request.form.get('status')
        note = request.form.get('note', '').strip()
        if status not in ('approved', 'rejected') or not 5 <= len(note) <= 1000:
            abort(400)
        try:
            vid = int(request.form.get('id', ''))
        except ValueError:
            abort(400)
        with document_transaction():
            item = Repo.get_by_id('business_verifications', vid, for_update=True)
            if not item:
                abort(404)
            if item['status'] != 'pending':
                abort(409)
            if item['uid'] == user['id']:
                abort(403)
            Repo.update('business_verifications', vid, dict(status=status, note=note, reviewed_by=user['id']))
            # Identity review does not publish or bypass restaurant moderation.
            RestaurantModel.update(item['rid'], {'identity_verified': status == 'approved'})
            record_event('BUSINESS_VERIFICATION_REVIEWED', resource_type='restaurant', resource_id=item['rid'], actor_user_id=user['id'])
        flash('Revisión empresarial registrada.', 'success')
        return redirect(url_for('business_access.review'))
    return render_template('admin/business_verifications.html', verifications=Repo.all('business_verifications'))
