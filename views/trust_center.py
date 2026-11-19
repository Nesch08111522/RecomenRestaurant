"""Administrator-only review of security signals, never automatic accusations."""
from collections import defaultdict,Counter
import hashlib,os
from flask import Blueprint,render_template,jsonify,abort,request,redirect,url_for,flash
from utils.security import fresh_session_user
from utils.security_delivery import configured
from models.restaurant import RestaurantModel
from database.repository import PostgresDocumentRepository as Repo,document_transaction
from utils.llm_provider import settings
from logic.market import key

bp=Blueprint('trust_center',__name__)
def overview():
    user=fresh_session_user()
    if not user:abort(401)
    if user['role']!='admin':abort(403)
    shops=RestaurantModel.all();by_name=defaultdict(list);by_image=defaultdict(list)
    for shop in shops:
        name=key(shop.get('name',''))
        if name:by_name[(name,key(shop.get('district','')))].append({'id':shop['id'],'name':shop['name']})
        if shop.get('image'):by_image[hashlib.sha256(str(shop['image']).encode()).hexdigest()].append({'id':shop['id'],'name':shop['name']})
    with document_transaction() as conn:
        counts={r['collection']:r['n'] for r in conn.execute("SELECT collection,count(*) AS n FROM public.app_records WHERE collection=ANY(%s) GROUP BY collection",(['users','dish_models','business_site_media','copilot_actions'],))}
        audit=[r['payload'] for r in conn.execute("SELECT payload FROM public.app_records WHERE collection='audit_events' ORDER BY created_at DESC,id DESC LIMIT 30")]
        models=[r['payload'] for r in conn.execute("SELECT payload - 'data' AS payload FROM public.app_records WHERE collection='dish_models' ORDER BY created_at DESC LIMIT 100")]
        offers=[r['payload'] for r in conn.execute("SELECT payload - 'photo' AS payload FROM public.app_records WHERE collection='market_offers' AND COALESCE(payload->>'review_state','approved')='pending' ORDER BY created_at DESC LIMIT 100")]
        payments=[r['payload'] for r in conn.execute("SELECT payload - 'destination' - 'checkout' AS payload FROM public.app_records WHERE collection='market_orders' AND payload->>'payment_incident' IS NOT NULL ORDER BY created_at DESC LIMIT 50")]
        media=[r['payload'] for r in conn.execute("SELECT payload - 'content' - 'data' AS payload FROM public.app_records WHERE collection='business_site_media' ORDER BY created_at DESC LIMIT 100")]
    try:
        provider=settings();ai={'configured':True,'model':provider.model}
    except Exception:ai={'configured':False,'model':None}
    sites=[{k:r.get(k) for k in ('id','restaurant_id','draft','published','content_review_state')} for r in Repo.all('business_sites')]
    return {'sites':sites,'media':[{'id':m.get('id'),'restaurant_id':m.get('restaurant_id'),'review_state':m.get('review_state')} for m in media],'counts':counts,'audit':[{k:r.get(k) for k in ('action','resource_type','resource_id','created_at')} for r in audit],
      'duplicate_names':[x for x in by_name.values() if len(x)>1],'shared_images':[x for x in by_image.values() if len(x)>1],
      'models':[{k:r.get(k) for k in ('id','rid','description','scale_verified','width_cm','height_cm','depth_cm')} for r in models],
      'pending_offers':[{k:r.get(k) for k in ('id','rid','name','model_id')} for r in offers],
      'payment_incidents':[{'id':r.get('id'),'rid':r.get('rid'),'state':r.get('state')} for r in payments],
      'media_count':len(media),'integrations':{'ai':ai,'email':bool(configured('email')),'sms':bool(configured('sms'))}}
@bp.get('/admin/confianza')
def dashboard():return render_template('admin/trust_center.html',data=overview())
@bp.get('/admin/api/confianza')
def api():
    response=jsonify(success=True,report=overview());response.headers['Cache-Control']='private, no-store';return response


@bp.post('/admin/confianza/revisar/<kind>/<int:identifier>')
def review_content(kind,identifier):
    user=fresh_session_user()
    if not user:abort(401)
    if user['role']!='admin':abort(403)
    if kind not in ('site','media'):abort(404)
    decision=request.form.get('decision');note=str(request.form.get('note') or '').strip()
    if decision not in ('approved','rejected') or not 5<=len(note)<=500:abort(400)
    from utils.audit import record_event
    from logic.market import now
    collection='business_sites' if kind=='site' else 'business_site_media'
    with document_transaction():
        row=Repo.get_by_id(collection,identifier,for_update=True)
        if not row:abort(404)
        fields={'content_review_state' if kind=='site' else 'review_state':decision,'review_note':note,'reviewed_by':user['id'],'reviewed_at':now().isoformat()}
        if kind=='site' and decision=='rejected':
            fields['published']=None
            fields['revisions']=(row.get('revisions',[])+([{'site':row['published'],'changed_at':now().isoformat()}] if row.get('published') else []))[-20:]
        Repo.update(collection,identifier,fields)
        record_event('SITE_CONTENT_REVIEW' if kind=='site' else 'BRAND_MEDIA_REVIEW',resource_type=collection,resource_id=identifier,metadata={'decision':decision})
    flash('Revisión guardada. El contenido retirado deja de estar disponible públicamente.','success')
    return redirect(url_for('trust_center.dashboard'))


@bp.get('/admin/confianza/sitio/<int:rid>')
def site_preview(rid):
    user=fresh_session_user()
    if not user:abort(401)
    if user['role']!='admin':abort(403)
    from models.business_site import find_site
    from views.business_sites import render_site
    shop=RestaurantModel.get_by_id(rid);row=find_site(rid)
    if not shop or not row:abort(404)
    return render_site(row.get('draft') or row.get('published') or {},shop,True)
