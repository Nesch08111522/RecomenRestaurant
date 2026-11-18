from dotenv import load_dotenv
load_dotenv(".env", override=False)

from database.connection import connection

with connection() as c:
    cur = c.cursor()
    cur.execute("select count(*) from public.app_records")
    print("app_records rows:", cur.fetchone())