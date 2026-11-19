from flask import Blueprint, abort, render_template, request, redirect, url_for, flash
from utils.security import fresh_session_user
from database.repository import document_transaction
from datetime import datetime, timezone
from models.company import companies, change_subscription, PLANS, CAPABILITIES

bp = Blueprint('companies', __name__)


@bp.before_app_request
def presence():
    from models.company import Repo
    from flask import g
    if request.endpoint == 'static':
        return
    user = fresh_session_user()
    if not user:
        return
    account = g.account_record
    now = datetime.now(timezone.utc)
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(%s)', (81000000+account['id'],))
        previous = Repo.get_by_id('company_presence', account['id'])
        if previous and (now-datetime.fromisoformat(previous['at'])).total_seconds() < 60 and previous.get('epoch') == str(account.get('auth_epoch', 0)):
            return
        values = {'at': now.isoformat(), 'epoch': str(account.get('auth_epoch', 0))}
        if previous:
            Repo.update('company_presence', account['id'], values)
        else:
            Repo.create('company_presence', {'id': account['id'], **values})


@bp.get('/admin/usuarios-conectados')
def connected():
    user = fresh_session_user()
    if not user or user['role'] != 'admin':
        abort(403)
    with document_transaction() as conn:
        rows = conn.execute("SELECT u.payload->>'username' AS username,u.payload->>'role' AS role,b.name,b.metadata->'subscription'->>'plan' AS plan FROM public.app_records p JOIN public.app_records u ON u.collection='users' AND u.id=p.id LEFT JOIN public.sr_memberships m ON m.user_id=u.id AND m.status='active' LEFT JOIN public.sr_businesses b ON b.id=m.business_id WHERE p.collection='company_presence' AND (p.payload->>'at')::timestamptz > now()-interval '5 minutes' AND COALESCE(u.payload->>'status','ACTIVE')='ACTIVE' AND COALESCE(u.payload->>'auth_epoch','0')=p.payload->>'epoch'").fetchall()
    return render_template('admin/company_presence.html', users=rows)


@bp.route('/admin/empresas', methods=['GET', 'POST'])
def admin_companies():
    user = fresh_session_user()
    if not user or user['role'] != 'admin':
        abort(403)
    if request.method == 'POST':
        if request.form.get('confirm') != 'yes':
            abort(400)
        try:
            values = {key: request.form.get(key, '') for key in ('plan', 'status', 'starts_on', 'expires_on')}
            values['disabled'] = request.form.getlist('disabled')
            change_subscription(user['id'], int(request.form['id']), values, request.form.get('revision'))
        except (ValueError, KeyError):
            abort(400)
        except LookupError:
            abort(404)
        except RuntimeError as error:
            flash(str(error), 'warning')
        else:
            flash('Suscripcion aplicada y propietario notificado.', 'success')
        return redirect(url_for('companies.admin_companies'))
    rows = companies()
    for key in ('plan', 'status'):
        value = request.args.get(key)
        if value:
            rows = [r for r in rows if (r['metadata'].get('subscription') or {}).get(key) == value]
    name = request.args.get('name', '').casefold()
    rows = [r for r in rows if name in r['name'].casefold()]
    return render_template('admin/companies.html', companies=rows, plans=PLANS, capabilities=CAPABILITIES)


@bp.app_context_processor
def company_template_context():
    from models.user import UserModel
    user = fresh_session_user()
    def company_nav_allowed(endpoint):
        from models.company import permitted
        from models.restaurant import RestaurantModel
        if not user or user.get('role') not in ('owner', 'business_owner'):
            return True
        permission = {'intelligence.dashboard': 'analytics.read.business', 'copilot.page': 'ai.business',
            'salon.manage_default': 'tables.manage', 'sites.editor': 'site.manage'}.get(endpoint)
        if not permission:
            return True
        shops = RestaurantModel.get_by_owner(user['id'])
        return bool(shops) and all(permitted(user, r['id'], permission) for r in shops)
    if not user or user['role'] != 'admin':
        return {'demo_owners': [], 'company_nav_allowed': company_nav_allowed}
    return {'company_nav_allowed': company_nav_allowed, 'demo_owners': [{'id': u['id'], 'username': u['username']} for u in UserModel.all() if u.get('company_demo') and u.get('activation_pending')]}


@bp.get('/owner/suscripciones')
def owner_subscriptions():
    user = fresh_session_user()
    if not user:
        abort(401)
    with document_transaction() as conn:
        rows = conn.execute("SELECT b.* FROM public.sr_businesses b JOIN public.sr_memberships m ON m.business_id=b.id WHERE m.user_id=%s AND m.status IN ('active','invited')", (user['id'],)).fetchall()
    return render_template('owner/subscriptions.html', companies=rows)


@bp.post('/admin/empresas/activacion/<int:uid>')
def activation_link(uid):
    import secrets, time
    from models.user import UserModel
    from models.company import Repo
    from utils.account_security import digest
    from utils.password_codes import contact, COLLECTION
    from utils.audit import record_event
    user = fresh_session_user()
    if not user or user['role'] != 'admin':
        abort(403)
    if request.form.get('confirm') != 'yes':
        abort(400)
    with document_transaction():
        account = Repo.get_by_id('users', uid, for_update=True)
        if not UserModel.is_active(account) or not account.get('activation_pending') or not account.get('company_demo'):
            abort(404)
        token, challenge = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        values = {'challenge': challenge, 'used': False, 'channel': 'email',
            'epoch': account.get('auth_epoch', 0), 'reset_until': time.time()+300,
            'contact_hash': digest('otp-contact', contact(account, 'email')).hex(),
            'reset_hash': digest('password-reset', token).hex(), 'hash': '', 'admin_activation': True}
        if Repo.get_by_id(COLLECTION, uid):
            Repo.update(COLLECTION, uid, values)
        else:
            Repo.create(COLLECTION, {'id': uid, **values})
        record_event('BUSINESS_PLAN_APPLIED', resource_type='activation', resource_id=uid,
                     metadata={'operation': 'admin_secure_link', 'expires_seconds': 300})
    response = render_template('admin/company_activation.html',
        link=url_for('companies.activate')+'#'+token+':'+challenge+':'+account['username'])
    from flask import make_response
    response = make_response(response)
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@bp.route('/activar-empresa', methods=['GET', 'POST'])
def activate():
    if request.method == 'GET':
        return render_template('company_activate.html')
    from models.company import Repo
    from models.user import UserModel
    from utils.password_codes import complete, COLLECTION
    from utils.account_security import allow_attempt
    username = request.form.get('username', '')[:80]
    if not allow_attempt('company-activate', username, request.remote_addr or ''):
        abort(429)
    with document_transaction():
        account = UserModel.get_by_username(username)
        if not account or not account.get('activation_pending') or not account.get('company_demo'):
            abort(400)
        account = Repo.get_by_id('users', account['id'], for_update=True)
        challenge = Repo.get_by_id(COLLECTION, account['id'], for_update=True)
        if not account.get('activation_pending') or not challenge or not challenge.get('admin_activation'):
            abort(400)
        if not complete(username, request.form.get('challenge'), request.form.get('token'), request.form.get('password', '')):
            abort(400)
        Repo.update('users', account['id'], {'activation_pending': False})
    return redirect(url_for('auth.login'))
