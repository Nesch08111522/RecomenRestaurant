"""Company subscriptions use canonical businesses, never account plan fields."""
from datetime import date, datetime, timezone
from database.repository import document_transaction, PostgresDocumentRepository as Repo
from core.permissions import can

PLANS = ('basic', 'decente', 'premium')
LEVELS = dict(zip(PLANS, range(3)))
CAPABILITIES = {
    'business.manage': 0, 'branch.manage': 0, 'catalog.manage': 0,
    'orders.read.business': 0, 'notifications.manage.business': 0,
    'tables.service': 0, 'tables.manage': 1, 'staff.manage': 1,
    'staff.invite': 1, 'analytics.read.business': 1, 'promotion.manage': 1,
    'site.manage': 1, 'flow.manage': 2, 'loyalty.manage.business': 2,
    'rewards.manage.business': 2, 'audit.read.business': 2, 'ai.business': 2,
}


def companies():
    with document_transaction() as conn:
        return conn.execute('SELECT * FROM public.sr_businesses ORDER BY id').fetchall()


def company_for_restaurant(rid):
    with document_transaction() as conn:
        row = conn.execute("SELECT b.* FROM public.sr_businesses b JOIN public.app_records r "
            "ON r.collection='restaurants' AND r.id=%s AND "
            "r.payload->>'business_id'=b.id::text", (rid,)).fetchone()
        return row


def subscription_allows(company, permission):
    if not company:
        return False
    sub = (company.get('metadata') or {}).get('subscription') or {}
    if company['status'] != 'active' or sub.get('status') != 'active':
        return False
    try:
        if sub.get('expires_on') and date.fromisoformat(sub['expires_on']) < date.today():
            return False
    except (ValueError, TypeError):
        return False
    return (permission not in sub.get('disabled', []) and
            LEVELS.get(sub.get('plan'), -1) >= CAPABILITIES.get(permission, 99))


def permitted(user, rid, permission):
    from models.user import UserModel
    from models.restaurant import RestaurantModel
    account = UserModel.get_by_id(user['id']) if user else None
    if not UserModel.is_active(account):
        return False
    restaurant = RestaurantModel.get_by_id(rid)
    if not restaurant:
        return False
    if account.get('role') == 'admin':
        return True
    company = company_for_restaurant(rid)
    if not subscription_allows(company, permission):
        return False
    role_permission = {'ai.business': 'catalog.manage', 'site.manage': 'business.manage',
                       'promotion.manage': 'business.manage'}.get(permission, permission)
    if restaurant.get('owner_id') == account['id'] and account.get('role') in ('owner', 'business_owner'):
        return can('business_owner', role_permission)
    with document_transaction() as conn:
        roles = conn.execute("SELECT role FROM public.sr_memberships WHERE business_id=%s "
            "AND user_id=%s AND status='active'", (company['id'], account['id'])).fetchall()
    branch_roles = [m for m in Repo.all('branch_memberships') if m.get('rid') == rid
                    and m.get('uid') == account['id'] and m.get('status') == 'active']
    return any(can(m['role'], role_permission) for m in roles + branch_roles)


def change_subscription(actor, bid, values, expected):
    from models.user import UserModel
    from models.communication import notify
    from utils.audit import record_event
    if not UserModel.is_admin(actor):
        raise PermissionError('Administrador requerido.')
    if values.get('plan') not in PLANS or values.get('status') not in ('active', 'suspended'):
        raise ValueError('Plan o estado invalido.')
    for field in ('starts_on', 'expires_on'):
        if values.get(field):
            date.fromisoformat(values[field])
    if values.get('expires_on') and values.get('starts_on') and values['expires_on'] < values['starts_on']:
        raise ValueError('Vencimiento anterior a contratacion.')
    if not isinstance(values.get('disabled', []), list) or set(values.get('disabled', [])) - CAPABILITIES.keys():
        raise ValueError('Capacidad desconocida.')
    with document_transaction() as conn:
        row = conn.execute('SELECT * FROM public.sr_businesses WHERE id=%s FOR UPDATE', (bid,)).fetchone()
        if not row:
            raise LookupError('Empresa no encontrada.')
        old = (row['metadata'] or {}).get('subscription') or {}
        if str(old.get('revision', 0)) != str(expected):
            raise RuntimeError('La suscripcion cambio; recarga antes de confirmar.')
        sub = {**values, 'revision': old.get('revision', 0) + 1, 'updated_by': actor,
               'updated_at': datetime.now(timezone.utc).isoformat()}
        conn.execute('UPDATE public.sr_businesses SET metadata=%s, updated_at=now() WHERE id=%s',
                     (Repo._jsonb({**row['metadata'], 'subscription': sub}), bid))
        record_event('BUSINESS_PLAN_APPLIED', resource_type='company', resource_id=bid,
                     actor_user_id=actor, metadata={'previous_plan': old.get('plan'), 'plan': sub['plan'], 'status': sub['status']})
        owners = conn.execute("SELECT user_id FROM public.sr_memberships WHERE business_id=%s AND role='business_owner' AND status IN ('active','invited')", (bid,)).fetchall()
        notify([o['user_id'] for o in owners], 'Suscripcion actualizada',
               f"{row['name']}: {sub['plan']} / {sub['status']}", '/owner/suscripciones')
