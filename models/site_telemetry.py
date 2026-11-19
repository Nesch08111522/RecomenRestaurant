from hashlib import blake2s
from database.repository import PostgresDocumentRepository as Repo,document_transaction
from logic.market import now

def view(rid):
    day=now().date().isoformat();identifier=int.from_bytes(blake2s(f'{rid}:{day}'.encode(),digest_size=7).digest(),'big')
    with document_transaction() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(%s)',(identifier,))
        row=Repo.get_by_id('site_daily_views',identifier)
        if row:Repo.update('site_daily_views',identifier,{'views':row.get('views',0)+1})
        else:Repo.create('site_daily_views',{'id':identifier,'rid':rid,'day':day,'views':1})
