"""Commercial analytics scoped before querying operations, with no customer PII."""
from flask import Blueprint,request,render_template,jsonify,abort
from utils.security import fresh_session_user
from models.restaurant import RestaurantModel
from models.dish import DishModel
from models.market import kitchen
from analytics.management import reporting_period,scoped_records
from analytics.intelligence import report
from logic.market import now
from database.repository import document_transaction

bp=Blueprint('intelligence',__name__)
def snapshot():
    user=fresh_session_user()
    if not user:abort(401)
    if user['role'] not in ('admin','business_owner'):abort(403)
    shops=RestaurantModel.all() if user['role']=='admin' else RestaurantModel.get_by_owner(user['id'])
    rid=request.args.get('rid',type=int)
    if request.args.get('rid') and rid is None:abort(400)
    if rid is not None and rid not in {s['id'] for s in shops}:abort(404)
    ids=[rid] if rid is not None else [s['id'] for s in shops]
    try:start,end=reporting_period(request.args,now().date())
    except ValueError:abort(400,description='Selecciona un período válido de hasta 366 días.')
    products=[p for p in DishModel.all() if p.get('restaurant_id') in ids]
    result=report(scoped_records('market_orders',ids),products,start,end)
    offers=scoped_records('market_offers',ids);views=scoped_records('site_daily_views',ids)
    result.update(start=start.isoformat(),end=end.isoformat(),businesses=len(ids),published_businesses=sum(bool(s.get('verified')) for s in shops if s['id'] in ids),published_offers=sum(o.get('review_state','approved')=='approved' for o in offers),website_views=sum(v.get('views',0) for v in views if start.isoformat()<=v.get('day','')<=end.isoformat()),campaign_deliveries=len([c for c in scoped_records('campaign_deliveries',ids) if start.isoformat()<=str(c.get('day') or c.get('at') or '')[:10]<=end.isoformat()]),critical_ingredients=[{'rid':i,'name':name} for i in ids for name,item in kitchen(i).get('pantry',{}).items() if item.get('quantity',0)<=0 or item.get('expires','9999')<end.isoformat()])
    movements=[m for m in scoped_records('market_movements',ids) if m.get('move')=='Merma' and start.isoformat()<=m.get('at','')[:10]<=end.isoformat()]
    from collections import defaultdict
    waste=defaultdict(float)
    for m in movements:waste[(m['rid'],m.get('name','Ingrediente'),m.get('unit') or 'unidad no registrada')]+=abs(float(m.get('delta',0)))
    result['waste']=[{'rid':rid,'name':name,'unit':unit,'quantity':round(qty,3)} for (rid,name,unit),qty in waste.items()]
    with document_transaction() as conn:
        row=conn.execute("SELECT count(*) AS views,count(*) FILTER(WHERE v.payload->>'clicked'='true') AS clicks,count(*) FILTER(WHERE v.payload->>'ordered'='true') AS orders FROM public.app_records v JOIN public.app_records o ON o.collection='market_offers' AND o.id::text=v.payload->>'offer' WHERE v.collection='market_views' AND o.payload->>'rid'=ANY(%s) AND v.payload->>'day' BETWEEN %s AND %s",([str(i) for i in ids],start.isoformat(),end.isoformat())).fetchone()
        result['recommendation_funnel']=dict(row)
    result['missing_metrics']=[m for m in result['missing_metrics'] if not m.startswith('Merma:')]
    return result,shops,start,end
@bp.get('/inteligencia')
def dashboard():
    data,shops,start,end=snapshot()
    return render_template('intelligence.html',data=data,shops=shops,start=start,end=end)
@bp.get('/api/inteligencia')
def api():
    data,_,_,_=snapshot()
    response=jsonify(success=True,report=data);response.headers['Cache-Control']='private, no-store';return response
