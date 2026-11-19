"""Commercial analytics scoped before querying operations, with no customer PII."""
from flask import Blueprint,request,render_template,jsonify,abort
from utils.security import fresh_session_user
from models.restaurant import RestaurantModel
from analytics.management import reporting_period,scoped_records
from analytics.intelligence import report,service_metrics
from logic.market import now
from database.repository import document_transaction

bp=Blueprint('intelligence',__name__)

def period_records(collection, ids, start, end, fields):
    """Date fields are code-owned; scope and dates are bound before transfer."""
    if not ids:return []
    expression="COALESCE("+','.join("NULLIF(payload->>'"+field+"','')" for field in fields)+",'')"
    with document_transaction() as conn:
        rows=conn.execute("SELECT payload - 'photo' - 'destination' - 'checkout' AS payload FROM public.app_records WHERE collection=%s AND payload->>'rid'=ANY(%s) AND left("+expression+",10) BETWEEN %s AND %s",(collection,[str(i) for i in ids],start.isoformat(),end.isoformat()))
        return [row['payload'] for row in rows]

@bp.after_request
def private_report(response):
    response.headers['Cache-Control']='private, no-store'
    return response

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
    from datetime import date
    with document_transaction() as conn:
        products=[row['payload'] for row in conn.execute("SELECT jsonb_build_object('name',payload->>'name') AS payload FROM public.app_records WHERE collection='dishes' AND payload->>'restaurant_id'=ANY(%s)",([str(i) for i in ids],))] if ids else []
        kitchens=[row['payload'] for row in conn.execute("SELECT jsonb_build_object('id',id,'pantry',payload->'pantry') AS payload FROM public.app_records WHERE collection='market_kitchens' AND id=ANY(%s)",(ids,))] if ids else []
        table_count=conn.execute("SELECT count(*) AS n FROM public.app_records WHERE collection='restaurant_tables' AND payload->>'rid'=ANY(%s) AND COALESCE(payload->>'active','true')='true'",([str(i) for i in ids],)).fetchone()['n'] if ids else 0
    # Lifetime customer cohorts require history, not a silently truncated window.
    result=report(period_records('market_orders',ids,date.min,end,('created','day')),products,start,end)
    result['service']=service_metrics(period_records('table_sessions',ids,start,end,('closed_at',)),period_records('flow_queue',ids,start,end,('created_at',)),table_count,start,end)
    result['missing_metrics']=[m for m in result['missing_metrics'] if not m.startswith('Ocupación')]
    offers=scoped_records('market_offers',ids);views=period_records('site_daily_views',ids,start,end,('day',))
    result.update(start=start.isoformat(),end=end.isoformat(),businesses=len(ids),published_businesses=sum(bool(s.get('verified')) for s in shops if s['id'] in ids),published_offers=sum(o.get('review_state','approved')=='approved' for o in offers),website_views=sum(v.get('views',0) for v in views if start.isoformat()<=v.get('day','')<=end.isoformat()),campaign_deliveries=len([c for c in period_records('campaign_deliveries',ids,start,end,('day','at')) if start.isoformat()<=str(c.get('day') or c.get('at') or '')[:10]<=end.isoformat()]),critical_ingredients=[{'rid':i,'name':name} for stock in kitchens for i in [stock['id']] for name,item in (stock.get('pantry') or {}).items() if item.get('quantity',0)<=0 or item.get('expires','9999')<end.isoformat()])
    movements=[m for m in period_records('market_movements',ids,start,end,('at',)) if m.get('move')=='Merma' and start.isoformat()<=m.get('at','')[:10]<=end.isoformat()]
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
