"""Read-only API for food photography/GLB selection; never generates models on login."""
from flask import Blueprint, jsonify, session, g, current_app, request, url_for
from core.food_experience import select_food_scene
from utils.security import fresh_session_user
from models.favorite import FavoriteModel
from models.dish import DishModel
from models.restaurant import RestaurantModel

bp=Blueprint('food_experience',__name__)

@bp.get('/api/food-experience')
def food_experience():
    view=request.args.get('view','home')
    if view not in ('home','login','register','recover','business'):return jsonify(error='Vista no válida'),400
    profile={};favorites=set();favorite_dishes=set();dishes=[];personalized=False;degraded=False
    # No identity from query parameters. Guests do not trigger private DB queries.
    user=fresh_session_user() if session.get('user_id') else None
    if user:
        account=getattr(g,'account_record',{}) or {}
        profile=account.get('profile') or {};personalized=True
        try:
            favorites={f.get('restaurant_id') for f in FavoriteModel.get_by_user(user['id'])}
            favorite_dishes={i for i in profile.get('favorite_dishes',[]) if isinstance(i,int) and i>0}
            approved={r['id']:r for r in RestaurantModel.get_approved()}
            from models.market import records
            published={o['dish_id']:o['id'] for o in records('market_offers') if o.get('model_id') and o.get('review_state','approved')=='approved' and approved.get(o.get('rid'),{}).get('verified')}
            for dish in DishModel.all()[:1000]:
                if dish.get('restaurant_id') not in approved:continue
                row={**dish,'business':approved[dish['restaurant_id']]['name']}
                if dish['id'] in published:row['model_url']=url_for('ecosystem.dish_model',oid=published[dish['id']])
                dishes.append(row)
        except Exception as error:
            current_app.logger.warning('Visual catalog unavailable: %s',type(error).__name__);degraded=True
    items=select_food_scene(view,profile,dishes,favorites,favorite_dishes)
    if not user and view == 'business':
        from pathlib import Path
        if (Path(current_app.static_folder) / 'images/editorial/business.webp').is_file():
            items[0] = {**items[0], 'image':'/static/images/editorial/business.webp', 'name':'Trucha andina de autor', 'caption':'Imagen editorial generada con IA · presentación ilustrativa'}
    response=jsonify(items=items,personalized=personalized,selection='preferences' if personalized else 'editorial',degraded=degraded,
                     notice='Confirma ingredientes y alérgenos con el negocio.' if profile.get('restrictions') else None)
    response.headers['Cache-Control']='private, no-store'
    response.headers['Vary']='Cookie'
    return response
