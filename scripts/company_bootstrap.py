"""Explicit, atomic bootstrap. No emails, known passwords or public reset tokens."""
import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from database.connection import check_application_schema
from database.repository import document_transaction, PostgresDocumentRepository as Repo
from models.user import UserModel
from utils.account_security import cipher
from utils.audit import record_event
from werkzeug.security import generate_password_hash

DEMOS = (
    ('sakura-nori', 'Sakura Nori', 'japonesa', 'basic'),
    ('dragon-de-jade', 'Drag\u00f3n de Jade', 'china', 'decente'),
    ('trattoria-bellavista', 'Trattoria Bellavista', 'italiana', 'premium'),
)


def bootstrap(apply=False):
    root = Path(__file__).resolve().parents[1]
    backup_dir = root / '.work'
    report_dir = root / 'outputs'
    if not backup_dir.is_dir() or not report_dir.is_dir():
        raise RuntimeError('Missing existing backup/report directories.')
    check_application_schema()
    run = uuid4().hex
    report = {'run': run, 'applied': False, 'created_companies': [], 'created_memberships': [],
              'created_users': [], 'created_restaurants': [], 'linked_restaurants': [],
              'premium_company_ids': [], 'activation': 'Pending confirmed recipient; no email sent.'}
    before = {'businesses': [], 'restaurants': [], 'created': []}
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(731904112)')
        for table in ('sr_businesses', 'sr_memberships', 'sr_branches'):
            if not conn.execute('SELECT to_regclass(%s) AS t', ('public.'+table,)).fetchone()['t']:
                raise RuntimeError('Canonical schema missing; nothing changed.')
        owners = [u for u in UserModel.all() if u.get('role') in ('owner', 'business_owner') and not u.get('company_demo')]
        shops = Repo.all('restaurants')
        conn.execute('LOCK TABLE public.sr_businesses, public.sr_memberships IN SHARE ROW EXCLUSIVE MODE')
        if not apply:
            return {'applied': False, 'existing_owner_ids': [u['id'] for u in owners],
                    'restaurants': len(shops), 'authorized_demos': [d[1] for d in DEMOS]}

        def company(slug, name, owner_id, plan, demo=False):
            row = conn.execute('SELECT * FROM public.sr_businesses WHERE slug=%s FOR UPDATE', (slug,)).fetchone()
            if row and demo and not row['metadata'].get('demo'):
                raise RuntimeError('Demo slug collision; transaction aborted.')
            if not row:
                metadata = {'demo': demo, 'bootstrap': 'companies-v1', 'subscription': {
                    'plan': plan, 'status': 'active', 'starts_on': '', 'expires_on': '',
                    'disabled': [], 'revision': 1, 'provisioned_at': datetime.now(timezone.utc).isoformat()}}
                bid = conn.execute('SELECT COALESCE(max(id),0)+1 AS id FROM public.sr_businesses').fetchone()['id']
                row = conn.execute('INSERT INTO public.sr_businesses(id,slug,name,status,metadata) VALUES (%s,%s,%s,%s,%s) RETURNING *',
                    (bid, slug, name, 'active', Repo._jsonb(metadata))).fetchone()
                report['created_companies'].append({'id': row['id'], 'name': name, 'plan': plan, 'demo': demo})
                before['created'].append(['sr_businesses', row['id']])
            elif not demo and (row['metadata'].get('subscription') or {}).get('plan') != 'premium':
                before['businesses'].append(row)
                metadata = {**row['metadata'], 'subscription': {**row['metadata'].get('subscription', {}),
                    'plan': 'premium', 'status': 'active', 'revision': row['metadata'].get('subscription', {}).get('revision', 0)+1}}
                conn.execute('UPDATE public.sr_businesses SET metadata=%s,updated_at=now() WHERE id=%s', (Repo._jsonb(metadata), row['id']))
            membership = conn.execute('SELECT * FROM public.sr_memberships WHERE user_id=%s AND business_id=%s', (owner_id, row['id'])).fetchone()
            if not membership:
                mid = conn.execute('SELECT COALESCE(max(id),0)+1 AS id FROM public.sr_memberships').fetchone()['id']
                membership = conn.execute("INSERT INTO public.sr_memberships(id,user_id,business_id,role,status) VALUES (%s,%s,%s,'business_owner','active') RETURNING id", (mid, owner_id, row['id'])).fetchone()
                report['created_memberships'].append(membership['id'])
                before['created'].append(['sr_memberships', membership['id']])
            return row['id']

        for owner in owners:
            assigned = conn.execute("SELECT b.* FROM public.sr_businesses b JOIN public.sr_memberships m ON m.business_id=b.id WHERE m.user_id=%s AND m.role='business_owner' AND m.status='active'", (owner['id'],)).fetchall()
            if assigned:
                bids = [company(b['slug'], b['name'], owner['id'], 'premium') for b in assigned]
            else:
                bids = [company('existing-owner-'+str(owner['id']), 'Empresa de '+owner['username'], owner['id'], 'premium')]
            report['premium_company_ids'].extend(bids)
            for shop in shops:
                if shop.get('owner_id') != owner['id'] or shop.get('business_id'):
                    continue
                if len(bids) != 1:
                    raise RuntimeError('Ambiguous company mapping; transaction aborted.')
                current = Repo.get_by_id('restaurants', shop['id'], for_update=True)
                if current.get('owner_id') != owner['id'] or current.get('business_id'):
                    raise RuntimeError('Concurrent ownership change; transaction aborted.')
                before['restaurants'].append(current)
                Repo.update('restaurants', shop['id'], {'business_id': bids[0]})
                report['linked_restaurants'].append({'id': shop['id'], 'business_id': bids[0], 'owner_id': owner['id']})
        for slug, name, cuisine, plan in DEMOS:
            username = 'demo-'+slug
            owner = UserModel.get_by_username(username)
            if owner and owner.get('company_demo') != slug:
                raise RuntimeError('Demo username collision; transaction aborted.')
            if not owner:
                owner = Repo.create('users', {'username': username, 'password': generate_password_hash(secrets.token_urlsafe(64)),
                    'role': 'business_owner', 'status': 'ACTIVE', 'company_demo': slug,
                    'activation_pending': True, 'profile': {'name': 'Propietario demo '+name, 'email': ''}})
                report['created_users'].append({'id': owner['id'], 'username': username})
                before['created'].append(['users', owner['id']])
            bid = company('demo-'+slug, name, owner['id'], plan, True)
            demo_shops = [r for r in Repo.all('restaurants') if r.get('company_demo') == slug]
            if demo_shops and (len(demo_shops) != 1 or demo_shops[0].get('owner_id') != owner['id'] or demo_shops[0].get('business_id') != bid):
                raise RuntimeError('Demo ownership mismatch; transaction aborted.')
            if not demo_shops:
                restaurant = Repo.create('restaurants', {'name': name, 'owner_id': owner['id'], 'business_id': bid,
                    'company_demo': slug, 'is_demo': True, 'cuisine': cuisine, 'verified': False, 'status': 'draft',
                    'description': 'Demostracion autorizada; no representa un negocio comercial real.'})
                report['created_restaurants'].append({'id': restaurant['id'], 'company_id': bid, 'name': name, 'owner_id': owner['id']})
                before['created'].append(['restaurants', restaurant['id']])
        changed = bool(before['created'] or before['businesses'] or before['restaurants'])
        if changed:
            event = record_event('BUSINESS_PLAN_APPLIED', resource_type='company_bootstrap', metadata={'run': run, 'demo_count': 3})
            before['created'].append(['audit_events', event['id']])
        # Exclusive, encrypted backup is durable before the transaction commits.
        backup = backup_dir / ('companies-before-'+run+'.fernet')
        with backup.open('xb') as handle:
            handle.write(cipher().encrypt(json.dumps(before, default=str).encode()))
            handle.flush()
            import os
            os.fsync(handle.fileno())
        report['backup'] = str(backup)
    report['applied'] = True
    report['changed'] = changed
    destination = report_dir / ('companies-evidence-'+run+'.json')
    destination.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding='utf-8')
    report['evidence'] = str(destination)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    application = create_app({'TESTING': True})
    try:
        with application.app_context():
            print(json.dumps(bootstrap(args.apply), ensure_ascii=True))
    except Exception as error:
        print(json.dumps({'applied': False, 'error_type': type(error).__name__, 'message': 'Transaction aborted; no credentials disclosed.'}))
        raise SystemExit(1) from None
