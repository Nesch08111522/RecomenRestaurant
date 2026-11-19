"""Read-only post-commit evidence, comparing encrypted affected records."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from utils.account_security import cipher
from database.repository import PostgresDocumentRepository as Repo, document_transaction


def verify(evidence):
    report = json.loads(Path(evidence).read_text(encoding='utf-8'))
    before = json.loads(cipher().decrypt(Path(report['backup']).read_bytes()))
    unchanged = []
    with document_transaction() as conn:
        for old in before['restaurants']:
            current = Repo.get_by_id('restaurants', old['id'])
            current.pop('business_id', None)
            original = dict(old)
            original.pop('business_id', None)
            if current != original:
                raise RuntimeError('Existing restaurant changed beyond company link.')
            unchanged.append(old['id'])
        companies = conn.execute("SELECT b.id,b.name,b.metadata->'subscription'->>'plan' AS plan,m.user_id FROM public.sr_businesses b JOIN public.sr_memberships m ON m.business_id=b.id AND m.role='business_owner' ORDER BY b.id").fetchall()
        demos = [r for r in Repo.all('restaurants') if r.get('company_demo')]
        owners = [Repo.get_by_id('users', r['owner_id']) for r in demos]
        assert len(demos) == 3 and len({r['owner_id'] for r in demos}) == 3
        assert all(u.get('activation_pending') and not u['profile'].get('email') for u in owners)
        result = {'verified': True, 'run': report['run'], 'companies': companies,
                  'preserved_restaurant_ids': unchanged, 'demo_restaurant_ids': [r['id'] for r in demos],
                  'activation_pending': True, 'emails_sent': 0}
    destination = Path(evidence).with_name('companies-verified-'+report['run']+'.json')
    destination.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    application = create_app({'TESTING': True})
    try:
        with application.app_context():
            print(json.dumps(verify(sys.argv[1]), ensure_ascii=True))
    except Exception as error:
        print(json.dumps({'verified': False, 'error_type': type(error).__name__}))
        raise SystemExit(1) from None
