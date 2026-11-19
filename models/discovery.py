"""Borradores auxiliares del radar en app_records; negocios canónicos en sr_*.

No hay publicación automática, copiado de Places ni envíos externos implícitos.
"""
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime,timezone,timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app
from config import Config
from models.base import DataModel
from models.restaurant import RestaurantModel
from models.user import UserModel
from database.repository import document_transaction, PostgresDocumentRepository as Repo
from logic.business_radar import now,clean,duplicate_reason,validate_source_url,claim_transition
from utils.audit import record_event
from utils.discovery_sources import osm_search, official_fetch, OVERPASS, SourceUnavailable


class CandidateModel(DataModel):
    collection='discovery_candidates'
class SourceModel(DataModel):
    collection='discovery_sources'
class RunModel(DataModel):
    collection='discovery_runs'
class InvitationModel(DataModel):
    collection='discovery_invitations'
class ClaimModel(DataModel):
    collection='discovery_claims'


def lock(conn):
    conn.execute('SELECT pg_advisory_xact_lock(731031)')


def event(action,resource_id,actor=None,metadata=None):
    return record_event(action,resource_type='discovery',resource_id=resource_id,
                        actor_user_id=actor,metadata=metadata)


def register_source(data,actor=None):
    kind=data.get('kind','official')
    if kind not in {'official','osm'}:
        raise ValueError('Solo OSM y páginas con permiso pueden alimentar el catálogo')
    source={'name':clean(data.get('name') or ('OpenStreetMap · Trujillo' if kind=='osm' else ''),120),
            'kind':kind,'url':OVERPASS if kind=='osm' else str(data.get('url') or ''),
            'enabled':True,'use_ai':data.get('use_ai') is True,
            'refresh_days':max(1,min(int(data.get('refresh_days',7)),30)),
            'radius_km':max(.2,min(float(data.get('radius_km',3)),10)),
            'created_at':now(),'next_refresh_at':now()}
    if not source['name']:
        raise ValueError('La fuente requiere un nombre')
    validate_source_url(source['url'])
    if kind=='official':
        rights=data.get('rights'); proof=clean(data.get('permission_evidence'),1000)
        if rights not in {'owner_permission','open_license'} or len(proof)<12:
            raise ValueError('Documenta permiso/licencia, alcance exacto de esta URL y responsable')
        expires=data.get('permission_expires_at') or (datetime.now(timezone.utc)+timedelta(days=30)).isoformat()
        try:
            expiry=datetime.fromisoformat(expires)
            if expiry.tzinfo is None or expiry<=datetime.now(timezone.utc):
                raise ValueError()
        except (ValueError,TypeError):
            raise ValueError('El permiso necesita una fecha UTC futura') from None
        source.update(rights=rights,permission_evidence=proof,permission_expires_at=expiry.astimezone(timezone.utc).isoformat(),authorized_by=actor)
    with document_transaction() as conn:
        lock(conn)
        existing=next((s for s in SourceModel.all() if s.get('url')==source['url']),None)
        if existing:
            raise ValueError('Esta fuente ya está registrada')
        row=SourceModel.create(source)
        event('DISCOVERY_SOURCE_REGISTER',row['id'],actor,{'kind':kind})
        return row


def get_default_source(actor=None):
    existing=next((s for s in SourceModel.all() if s.get('kind')=='osm'),None)
    if existing:
        return existing
    return register_source({'kind':'osm'},actor)


def ingest(rows,source_id,actor=None):
    counts={'created':0,'updated':0,'duplicates':0}
    with document_transaction() as conn:
        lock(conn)
        previous=CandidateModel.all()
        catalog=RestaurantModel.all()
        for row in rows[:200]:
            row['source_id']=source_id
            old=next((item for item in previous if item.get('source_key')==row['source_key']),None)
            if old:
                # Retrieval timestamps alone do not require review; provenance does.
                fields=('data','channels','menu_links','media','content_hash','permission_evidence')
                changed=any(old.get(key)!=row.get(key) for key in fields)
                old_evidence={k:{f:v for f,v in evidence.items() if f!='retrieved_at'}
                              for k,evidence in old.get('evidence',{}).items()}
                new_evidence={k:{f:v for f,v in evidence.items() if f!='retrieved_at'}
                              for k,evidence in row.get('evidence',{}).items()}
                if changed or old_evidence!=new_evidence:
                    change={'proposed_update':row,'last_seen_at':now(),'update_pending':True}
                else:
                    change={'last_seen_at':now()}
                CandidateModel.update(old['id'],change)
                counts['updated']+=1
                continue
            match=next((item for item in previous if duplicate_reason(row['data'],item['data'])),None)
            published=next((item for item in catalog if duplicate_reason(row['data'],item)),None)
            if match or published:
                row['duplicate_of']={'kind':'candidate' if match else 'restaurant','id':(match or published)['id']}
                row['duplicate_reason']=duplicate_reason(row['data'],(match or published).get('data',match or published))
                row['status']='duplicate'; counts['duplicates']+=1
            item=CandidateModel.create(row); previous.append(item); counts['created']+=1
        event('DISCOVERY_INGEST',source_id,actor,counts)
    return counts


def run_source(source_id,actor=None):
    source=get_default_source(actor) if str(source_id)=='osm' else SourceModel.get_by_id(int(source_id))
    if not source or not source.get('enabled'):
        raise ValueError('La fuente no existe o está desactivada')
    with document_transaction() as conn:
        lock(conn)
        active=[r for r in RunModel.all() if r.get('source_id')==source['id'] and r.get('status')=='running']
        recent=datetime.now(timezone.utc)-timedelta(minutes=2)
        if any(datetime.fromisoformat(r['started_at'])>datetime.now(timezone.utc)-timedelta(minutes=5) for r in active):
            raise ValueError('Ya hay una búsqueda de esta fuente en ejecución')
        if source.get('last_started_at') and datetime.fromisoformat(source['last_started_at'])>recent:
            raise ValueError('Espera dos minutos entre consultas para respetar la cuota de la fuente')
        run=RunModel.create({'source_id':source['id'],'source_name':source['name'],'status':'running','started_at':now(),'actor_id':actor})
        SourceModel.update(source['id'],{'last_started_at':now()})
    try:
        rows=osm_search(source.get('radius_km',3)) if source['kind']=='osm' else official_fetch(source,source.get('use_ai',False))
        counts=ingest(rows,source['id'],actor)
        with document_transaction():
            RunModel.update(run['id'],{'status':'completed','finished_at':now(),**counts})
            SourceModel.update(source['id'],{'last_success_at':now(),'next_refresh_at':(datetime.now(timezone.utc)+timedelta(days=source['refresh_days'])).isoformat(),'last_error':None})
        return {**run,**counts,'status':'completed'}
    except Exception as error:
        safe=clean(error,250) if isinstance(error,(ValueError,SourceUnavailable)) else 'La fuente o proveedor no respondió; se conservaron los datos anteriores'
        with document_transaction():
            RunModel.update(run['id'],{'status':'failed','finished_at':now(),'error':safe,'error_type':type(error).__name__})
            SourceModel.update(source['id'],{'last_error':safe,'next_refresh_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
        raise RuntimeError(safe) from None


def review(candidate_id,action,actor,notes=''):
    if action not in {'approve','reject','accept_update','mark_distinct'} or not clean(notes):
        raise ValueError('Selecciona una decisión y documenta el motivo')
    with document_transaction() as conn:
        lock(conn)
        row=Repo.get_by_id(CandidateModel.collection,candidate_id,for_update=True)
        if not row:
            raise ValueError('Ficha no encontrada')
        if action=='accept_update':
            if not row.get('proposed_update'):
                raise ValueError('No hay actualización pendiente')
            proposed=row['proposed_update']
            CandidateModel.update(candidate_id,{'data':proposed['data'],'evidence':proposed['evidence'],
                'channels':proposed['channels'],'menu_links':proposed['menu_links'],'media':proposed['media'],
                'confidence':proposed.get('confidence',row.get('confidence',0)),
                'confidence_level':proposed.get('confidence_level',row.get('confidence_level','low')),
                'missing_fields':proposed.get('missing_fields',row.get('missing_fields',[])),
                'revision_history':(row.get('revision_history',[])+[{'data':row['data'],'evidence':row.get('evidence',{}),'replaced_at':now(),'reviewed_by':actor}])[-30:],
                'proposed_update':None,'update_pending':False,'source_fields_verified':False,'status':'pending_review'})
        elif action=='mark_distinct':
            if row['status']!='duplicate':
                raise ValueError('Esta ficha no está marcada como duplicada')
            CandidateModel.update(candidate_id,{'status':'pending_review','duplicate_of':None,
                'duplicate_reason':None,'duplicate_reviewed_by':actor,'duplicate_review_notes':clean(notes,500)})
        elif action=='reject':
            if row['status'] in {'claimed','claim_pending'}:
                raise ValueError('La reclamación debe resolverse por su flujo específico')
            CandidateModel.update(candidate_id,{'status':'rejected','invitation_revoked':True})
        else:
            if row['status'] not in {'pending_review'} or row.get('duplicate_of'):
                raise ValueError('No se puede aprobar una ficha duplicada, ya resuelta o pendiente de otra operación')
            data=row['data']
            if not data.get('name') or not data.get('business_type') or not data.get('address'):
                raise ValueError('Nombre, tipo y dirección requieren evidencia antes de aprobar la ficha')
            if row.get('business_id') and row.get('branch_id'):
                business={'id':row['business_id']}; branch={'id':row['branch_id']}
                conn.execute("UPDATE public.sr_businesses SET name=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (data['name'],business['id']))
                conn.execute("UPDATE public.sr_branches SET address=%s,district=%s,latitude=%s,longitude=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (data['address'],data.get('district'),data.get('lat'),data.get('lng'),branch['id']))
            else:
                business=conn.execute("INSERT INTO public.sr_businesses(slug,name,status,metadata) VALUES(%s,%s,'draft',%s) RETURNING id",
                    (f"radar-{candidate_id}",data['name'],Repo._jsonb({'discovery_candidate_id':candidate_id,'source':row['source_url']}))).fetchone()
                branch=conn.execute("INSERT INTO public.sr_branches(business_id,name,address,district,latitude,longitude,status) VALUES(%s,'Principal',%s,%s,%s,%s,'draft') RETURNING id",
                    (business['id'],data['address'],data.get('district'),data.get('lat'),data.get('lng'))).fetchone()
            state='claimed' if row.get('owner_verified') and row.get('owner_id') else 'approved'
            CandidateModel.update(candidate_id,{'status':state,'business_id':business['id'],'branch_id':branch['id']})
        event('DISCOVERY_REVIEW',candidate_id,actor,{'action':action,'notes':clean(notes,300)})
        return CandidateModel.get_by_id(candidate_id)


def serializer():
    key=current_app.secret_key
    return URLSafeTimedSerializer(key,salt='smartresto-discovery-claim-v1')


def invite(candidate_id,actor):
    with document_transaction() as conn:
        lock(conn)
        row=Repo.get_by_id(CandidateModel.collection,candidate_id,for_update=True)
        if not row or row['status'] not in {'approved','invited'}:
            raise ValueError('La ficha debe estar aprobada antes de generar una invitación')
        nonce=secrets.token_urlsafe(32)
        token=serializer().dumps({'candidate_id':candidate_id,'nonce':nonce})
        digest=hashlib.sha256(token.encode()).hexdigest()
        item=InvitationModel.create({'candidate_id':candidate_id,'token_hash':digest,'used':False,
             'created_at':now(),'expires_at':(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()})
        CandidateModel.update(candidate_id,{'status':'invited','active_invitation_id':item['id'],'invitation_revoked':False})
        event('DISCOVERY_INVITATION',candidate_id,actor,{'invitation_id':item['id'],'delivery':'generated_not_sent'})
        return {'token':token,'expires_at':item['expires_at'],'delivery':'generated_not_sent'}


def invitation_record(token):
    try:
        payload=serializer().loads(token,max_age=7*86400)
    except (BadSignature,SignatureExpired):
        raise ValueError('Invitación inválida o vencida') from None
    digest=hashlib.sha256(str(token).encode()).hexdigest()
    row=next((r for r in InvitationModel.all() if secrets.compare_digest(r.get('token_hash',''),digest)),None)
    candidate_row=CandidateModel.get_by_id(payload.get('candidate_id')) if row else None
    if not row or row.get('used') or row['expires_at']<=now() or not candidate_row or candidate_row.get('invitation_revoked') or candidate_row.get('active_invitation_id')!=row['id']:
        raise ValueError('Invitación revocada, usada o vencida')
    return row,candidate_row


def request_claim(token,user_id,proof):
    if len(clean(proof,1500))<20:
        raise ValueError('Describe una prueba de titularidad verificable (mínimo 20 caracteres)')
    user=UserModel.get_by_id(user_id)
    if not UserModel.is_active(user) or user.get('role')!='business_owner':
        raise ValueError('Solo un empresario activo puede solicitar un establecimiento')
    with document_transaction() as conn:
        lock(conn)
        invitation,row=invitation_record(token)
        state=claim_transition(row['status'],'request')
        claim=ClaimModel.create({'candidate_id':row['id'],'user_id':user_id,'proof':clean(proof,1500),'status':'pending','created_at':now()})
        InvitationModel.update(invitation['id'],{'used':True,'used_at':now()})
        CandidateModel.update(row['id'],{'status':state,'claim_id':claim['id']})
        event('DISCOVERY_CLAIM_REQUEST',row['id'],user_id,{'claim_id':claim['id']})
        return claim


def decide_claim(claim_id,action,actor,notes):
    if action not in {'approve','reject'} or len(clean(notes))<12:
        raise ValueError('Documenta la revisión independiente de titularidad')
    with document_transaction() as conn:
        lock(conn)
        claim=Repo.get_by_id(ClaimModel.collection,claim_id,for_update=True)
        if not claim or claim['status']!='pending':
            raise ValueError('La solicitud no está pendiente')
        row=CandidateModel.get_by_id(claim['candidate_id'])
        state=claim_transition(row['status'],action)
        if action=='approve':
            user=UserModel.get_by_id(claim['user_id'])
            if not UserModel.is_active(user) or user.get('role')!='business_owner':
                raise ValueError('El solicitante ya no es un empresario activo')
            conn.execute("INSERT INTO public.sr_memberships(user_id,business_id,role,status) VALUES(%s,%s,'business_owner','active')",
                (claim['user_id'],row['business_id']))
        ClaimModel.update(claim_id,{'status':'approved' if action=='approve' else 'rejected','reviewed_by':actor,'reviewed_at':now(),'notes':clean(notes,500)})
        CandidateModel.update(row['id'],{'status':state,'owner_verified':action=='approve','owner_id':claim['user_id'] if action=='approve' else None})
        event('DISCOVERY_CLAIM_REVIEW',row['id'],actor,{'claim_id':claim_id,'action':action,'notes':clean(notes,300)})
        return CandidateModel.get_by_id(row['id'])
