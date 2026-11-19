"""Permisos por establecimiento; las asignaciones se revalidan en servidor."""
from core.permissions import can
from database.repository import PostgresDocumentRepository as Repo, document_transaction
from models.restaurant import RestaurantModel
from models.user import UserModel

ROLES = ('manager', 'cashier', 'waiter', 'kitchen')


def authorized(user, rid, permission):
    account = UserModel.get_by_id(user.get('id')) if user else None
    if not UserModel.is_active(account):
        return False
    user = account
    restaurant = RestaurantModel.get_by_id(rid)
    if not restaurant:
        return False
    if user.get('role') == 'admin':
        return True
    if restaurant.get('owner_id') == user['id'] and user.get('role') in ('owner', 'business_owner'):
        return can('business_owner', permission)
    assignments = [m for m in Repo.all('branch_memberships') if m.get('rid') == rid and m.get('uid') == user['id']]
    if assignments:
        return any(m.get('status') == 'active' and can(m.get('role'), permission) for m in assignments)
    # Existing kitchen teams remain supported until explicitly migrated/revoked.
    from models.market import kitchen
    return permission == 'tables.service' and user['id'] in ((kitchen(rid) or {}).get('team') or [])


def assign(actor, rid, username, role, status):
    if role not in ROLES or status not in ('active', 'revoked'):
        raise ValueError('Rol o estado no permitido.')
    with document_transaction():
        Repo.get_by_id('restaurants', rid, for_update=True)
        if not authorized(actor, rid, 'staff.manage'):
            raise PermissionError('No autorizado para administrar personal.')
        employee = UserModel.get_by_username(username)
        if not employee or not UserModel.is_active(employee):
            raise ValueError('Selecciona una cuenta activa.')
        if employee['id'] == actor['id'] or employee.get('role') == 'admin':
            raise ValueError('No se puede asignar esta cuenta como personal.')
        existing = next((m for m in Repo.all('branch_memberships') if m.get('uid') == employee['id'] and m.get('rid') == rid), None)
        values = dict(uid=employee['id'], rid=rid, role=role, status=status, updated_by=actor['id'])
        result = Repo.update('branch_memberships', existing['id'], values) if existing else Repo.create('branch_memberships', values)
        from utils.audit import record_event
        record_event('BRANCH_MEMBERSHIP_UPDATED', resource_type='restaurant', resource_id=rid, actor_user_id=actor['id'])
        return result
