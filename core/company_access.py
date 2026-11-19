"""Additional subscription boundary; existing endpoint ownership checks remain."""
from flask import request, abort
from models.company import permitted
from models.restaurant import RestaurantModel
from utils.security import fresh_session_user


def enforce_subscription():
    endpoint = request.endpoint or ''
    if endpoint == 'static':
        return
    user = fresh_session_user()
    if not user or user.get('role') == 'admin':
        return
    permission = None
    if endpoint.startswith('owner.'):
        permission = 'catalog.manage'
        if endpoint == 'owner.dashboard':
            permission = 'business.manage'
        if endpoint in ('owner.generate_menu', 'owner.audit_restaurant_menu', 'owner.suggest_menu_dish_correction'):
            permission = 'ai.business'
    elif endpoint.startswith('catalog.') and request.path.startswith('/owner/'):
        permission = 'ai.business' if endpoint in ('catalog.photo', 'catalog.voice') else 'catalog.manage'
    elif endpoint.startswith('sites.') and request.path.startswith('/owner/'):
        permission = 'ai.business' if endpoint == 'sites.ai' else 'site.manage'
    elif endpoint.startswith('intelligence.'):
        permission = 'analytics.read.business'
    elif endpoint.startswith('copilot.') and user.get('role') in ('owner', 'business_owner'):
        permission = 'ai.business'
    elif endpoint.startswith('flow.') and request.path.startswith('/salon/'):
        permission = 'flow.manage'
    elif endpoint == 'loyalty.customers':
        permission = 'loyalty.manage.business'
    elif endpoint.startswith('salon.') and request.path.startswith(('/owner/', '/salon')):
        permission = 'tables.manage' if request.path.startswith('/owner/') else 'tables.service'
    elif endpoint in ('ecosystem.campaign', 'ecosystem.business'):
        permission = 'promotion.manage'
    elif endpoint == 'ecosystem.upload_model':
        permission = 'ai.business'
    elif endpoint in ('market.copilot', 'market.simulate'):
        permission = 'ai.business'
    elif endpoint in ('market.publish', 'market.configure_coupon', 'admin.add_promotion'):
        permission = 'promotion.manage'
    elif endpoint.startswith('business_access.') and request.path.startswith('/owner/'):
        permission = 'business.manage' if endpoint == 'business_access.submit_verification' else 'staff.manage'
    if not permission:
        return
    args = request.view_args or {}
    rid = next((args[k] for k in ('rid', 'restaurant_id') if k in args), None)
    if endpoint == 'admin.add_promotion':
        rid = args.get('id')
    body = request.get_json(silent=True) if request.is_json else request.form
    if rid is None:
        raw = request.args.get('rid') or request.args.get('restaurant_id') or (body or {}).get('restaurant_id') or (body or {}).get('rid')
        if raw is not None:
            try:
                rid = int(raw)
            except (ValueError, TypeError):
                abort(400)
    if rid is None and args.get('dish_id'):
        from models.dish import DishModel
        dish = DishModel.get_by_id(args['dish_id']) or {}
        rid = dish.get('restaurant_id')
    if rid is not None:
        if not permitted(user, rid, permission):
            abort(403, description='Tu rol o suscripcion no permite esta funcionalidad.')
    else:
        shops = RestaurantModel.get_by_owner(user['id'])
        # Aggregate routes cannot leak a higher-tier company's data into a lower tier.
        if shops and not all(permitted(user, r['id'], permission) for r in shops):
            abort(403, description='Selecciona una empresa con permisos para esta funcionalidad.')
