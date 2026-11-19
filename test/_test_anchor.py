"""Script temporal para validar el ancla contra la base de test.

Uso:
    python _test_anchor.py

Requiere que las variables estén en .env.test (no en .env). No toca producción.
Borra este archivo cuando termines la validación.
"""
import os
import sys

# 1. Cargar .env.test si existe; si no, abortar (no queremos tocar .env de producción)
from dotenv import load_dotenv
if not os.path.exists(".env.test"):
    print("ERROR: falta .env.test. Crea el archivo con DATABASE_URL de test y vuelve a correr.")
    sys.exit(1)

load_dotenv(".env.test", override=True)

# 2. Verificar que apunta a test, no a producción
db_url = os.environ.get("DATABASE_URL", "")
if "db.ofjeabwbowfcjdokogvz" not in db_url:
    print(f"ERROR: DATABASE_URL no apunta a test. Host actual: {db_url.split('@')[-1].split('/')[0] if '@' in db_url else 'NO SET'}")
    sys.exit(1)

print("== Entorno ==")
print("DB host:", db_url.split("@")[-1].split("/")[0])
print("ANCHOR_STORE:", os.environ.get("ANCHOR_STORE"))
print("ANCHOR_MODE:", os.environ.get("ANCHOR_MODE"))

# 3. Verificar conexión
print("\n== Conexión ==")
try:
    from database.connection import connection
    with connection() as c:
        cur = c.cursor()
        cur.execute("select count(*) from public.app_records")
        print("app_records rows:", cur.fetchone())
except Exception as e:
    print("ERROR de conexión:", type(e).__name__, str(e)[:200])
    sys.exit(1)

# 4. Verificar trust_anchors
print("\n== trust_anchors ==")
try:
    from database.repository import PostgresDocumentRepository as R
    rows = R.all("trust_anchors")
    print("trust_anchors rows:", len(rows))
    for r in rows[:10]:
        print(" ", r.get("review_id"), r.get("kind"), r.get("status"))
except Exception as e:
    print("ERROR leyendo trust_anchors:", type(e).__name__, str(e)[:200])
    sys.exit(1)

# 5. Verificar selector del store
print("\n== Selector del store ==")
from utils.anchor_store import get_anchor_store
store = get_anchor_store()
print("Store:", type(store).__name__)

# 6. Validación end-to-end (insertar fila de prueba, job dry_run, verificar, borrar)
print("\n== Validación end-to-end ==")
try:
    r = {"id": 9999, "restaurant_id": 1, "user_id": 1, "rating": 5,
         "comment": "test", "created_at": "2026-11-18T10:00:00", "order_id": 1}
    o = {"id": 1, "state": "Entregado", "paid": True}
    row = store.add_pending(r, o, "hash_test_9999")
    print("add_pending OK:", row.get("review_id"), row.get("status"))

    from utils.anchor_job import anchor_pending
    result = anchor_pending(store, mode="dry_run")
    print("job dry_run:", result)

    again = anchor_pending(store, mode="dry_run")
    print("job dry_run (idempotente):", again)

    row = store.get_by_review(9999)
    print("estado final:", row.get("status") if row else "NO ENCONTRADO")

    # Borrar la fila de prueba (directo en app_records, sin modelo)
    from database.repository import document_transaction
    with document_transaction() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM public.app_records WHERE collection='trust_anchors' AND payload->>'review_id' = '9999'"
        )
        print("limpieza: fila borrada")
except Exception as e:
    print("ERROR en validación end-to-end:", type(e).__name__, str(e)[:300])

print("\n== Fin ==")