import sys
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from database.connection import connection, test_schema, transaction_limits
from database.repository import PostgresDocumentRepository as Repo, document_transaction
from core.permissions import _canonical_role
from models.user import UserModel

ROOT = Path(__file__).resolve().parent

def snapshot(conn):
    users = conn.execute("SELECT id, payload FROM public.app_records WHERE collection='users' ORDER BY id").fetchall()
    owners = [r for r in users if r['id'] == 2 and _canonical_role(r['payload'].get('role')) == 'business_owner']
    if len(owners) != 1 or not UserModel.is_active(owners[0]['payload']):
        raise RuntimeError('Ambiguous or inactive business owner; no changes')
    owner = owners[0]
    if owner['payload'].get('id') != owner['id']:
        raise RuntimeError('User identity mismatch; no changes')
    restaurants = conn.execute("SELECT id, payload->'owner_id' AS owner_id, payload ? 'owner_id' AS owner_present, md5(payload::text) AS digest, md5((payload - 'owner_id')::text) AS other_digest FROM public.app_records WHERE collection='restaurants' ORDER BY id").fetchall()
    tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('sr_businesses','sr_branches','sr_memberships') ORDER BY table_name").fetchall()
    collections = conn.execute("SELECT collection,count(*) AS n FROM public.app_records WHERE collection IN ('businesses','branches','branch_memberships','business_memberships') GROUP BY collection ORDER BY collection").fetchall()
    return {'owner': {'id': owner['id'], 'name': (owner['payload'].get('profile') or {}).get('name'), 'role': owner['payload'].get('role'), 'active': True}, 'restaurants': restaurants, 'related_tables': tables, 'related_collections': collections}

def main():
    assert not test_schema(), 'Test runtime forbidden'
    mode = sys.argv[1]
    if mode == 'inspect':
        with connection() as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            transaction_limits(conn)
            state = snapshot(conn)
            conn.rollback()
        path = ROOT / ('ownership_snapshot_' + uuid.uuid4().hex + '.json')
        with path.open('x', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=True)
        assert json.loads(path.read_text(encoding='utf-8')) == state
        print(json.dumps({'owner': state['owner'], 'restaurants': len(state['restaurants']), 'related_tables': state['related_tables'], 'related_collections': state['related_collections'], 'snapshot_path': str(path)}))
        return
    if mode != 'apply':
        raise RuntimeError('Invalid mode')
    expected = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    outputs = ROOT / 'outputs'
    outputs.mkdir(exist_ok=True)
    backup = outputs / ('restaurant_assignments_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex + '.json')
    committed = False
    try:
        with document_transaction() as conn:
            conn.execute("SET LOCAL lock_timeout='8s'")
            conn.execute('LOCK TABLE public.app_records IN SHARE ROW EXCLUSIVE MODE')
            current = snapshot(conn)
            if current != expected:
                raise RuntimeError('Snapshot changed; no updates')
            assignments = [{'restaurant_id': r['id'], 'owner_id': r['owner_id'], 'owner_present': r['owner_present']} for r in current['restaurants']]
            with backup.open('x', encoding='utf-8') as f:
                json.dump(assignments, f, ensure_ascii=True)
                f.flush()
                import os
                os.fsync(f.fileno())
            assert backup.is_file() and json.loads(backup.read_text(encoding='utf-8')) == assignments
            checksum = hashlib.sha256(backup.read_bytes()).hexdigest()
            owner_id = current['owner']['id']
            changed = conn.execute("UPDATE public.app_records SET payload=jsonb_set(payload,'{owner_id}',%s,true), updated_at=CURRENT_TIMESTAMP WHERE collection='restaurants' AND payload->'owner_id' IS DISTINCT FROM %s RETURNING id", (Repo._jsonb(owner_id), Repo._jsonb(owner_id))).fetchall()
            verified = conn.execute("SELECT id, payload->'owner_id' AS owner_id, md5((payload - 'owner_id')::text) AS digest FROM public.app_records WHERE collection='restaurants' ORDER BY id").fetchall()
            assert [r['id'] for r in verified] == [r['id'] for r in current['restaurants']]
            assert all(r['owner_id'] == owner_id for r in verified)
            assert [r['digest'] for r in verified] == [r['other_digest'] for r in current['restaurants']]
            # No authenticated application actor exists in this foreground migration.
            audit_id = conn.execute("SELECT COALESCE(MAX(id),0)+1 AS id FROM public.app_records WHERE collection='audit_events'").fetchone()['id']
            event = Repo.create('audit_events', {'id': audit_id, 'actor_user_id': None, 'action': 'SYSTEM_MIGRATION_REQUESTED', 'resource_type': 'restaurant_ownership', 'resource_id': None, 'created_at': datetime.now(timezone.utc).isoformat(), 'metadata': {'actor_type': 'system', 'request_source': 'explicit user authorization in task conversation; application requester identity unverified', 'scope': 'restaurants.owner_id only', 'owner_id': owner_id, 'restaurant_count': len(verified), 'changed_count': len(changed), 'backup_file': backup.name, 'backup_sha256': checksum}})
            txid = conn.execute('SELECT txid_current() AS id').fetchone()['id']
        committed = True
        with connection() as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            post = conn.execute("SELECT id,payload->'owner_id' AS owner_id, md5((payload - 'owner_id')::text) AS digest FROM public.app_records WHERE collection='restaurants' ORDER BY id").fetchall()
            audit = conn.execute("SELECT payload FROM public.app_records WHERE collection='audit_events' AND id=%s", (event['id'],)).fetchone()
            assert post == verified and audit and audit['payload'] == event
            conn.rollback()
        print(json.dumps({'committed': True, 'transaction_id': txid, 'owner': current['owner'], 'total': len(post), 'changed': len(changed), 'already_owned': len(post)-len(changed), 'verified_inside_transaction': True, 'verified_postcommit': True, 'audit_event_id': event['id'], 'backup_path': str(backup), 'backup_sha256': checksum}))
    except Exception:
        print(json.dumps({'committed': committed, 'postcommit_verified': False, 'backup_path': str(backup) if backup.exists() else None}))
        raise

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'blocker_type': type(error).__name__, 'message': 'Operation stopped; credentials and driver details suppressed.'}))
        sys.exit(1)
