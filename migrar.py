import psycopg2

URI_VIEJA = "postgresql://postgres.kfapwgyhgiiueodxyvcp:BomID0yJNIlCl6Fz@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
URI_NUEVA = "postgresql://postgres.ycfcgfjizubelqvutcjy:Ecosistema2026@aws-1-sa-east-1.pooler.supabase.com:5432/postgres"

tablas_ordenadas = [
    "sr_businesses",
    "app_records",
    "sr_branches",
    "sr_settings",
    "sr_memberships",
    "ai_decisions",
    "sr_audit_events"
]

conn_vieja = psycopg2.connect(URI_VIEJA)
conn_nueva = psycopg2.connect(URI_NUEVA)
cur_vieja = conn_vieja.cursor()
cur_nueva = conn_nueva.cursor()

# Activar extensión vector por si la usas en ai_decisions
cur_nueva.execute("CREATE EXTENSION IF NOT EXISTS vector;")

for tabla in tablas_ordenadas:
    print(f"1. Creando estructura de {tabla}...")
    
    # Obtener columnas exactas desde el proyecto viejo
    cur_vieja.execute("""
        SELECT 
            column_name,
            CASE 
                WHEN data_type = 'USER-DEFINED' THEN udt_name
                WHEN character_maximum_length IS NOT NULL THEN data_type || '(' || character_maximum_length || ')'
                WHEN data_type = 'ARRAY' THEN LTRIM(udt_name, '_') || '[]'
                ELSE data_type
            END,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
    """, (tabla,))
    
    columnas_sql = []
    for col_name, col_type, is_null, col_def in cur_vieja.fetchall():
        linea = f'"{col_name}" {col_type}'
        if is_null == 'NO':
            linea += " NOT NULL"
        if col_def and "nextval" not in col_def:
            linea += f" DEFAULT {col_def}"
        elif col_def and "nextval" in col_def:
            linea = f'"{col_name}" SERIAL'
        columnas_sql.append(linea)
        
    sql_create = f'CREATE TABLE IF NOT EXISTS public."{tabla}" (\n  ' + ",\n  ".join(columnas_sql) + "\n);"
    cur_nueva.execute(sql_create)
    conn_nueva.commit()
    
    print(f"2. Copiando datos de {tabla}...")
    archivo_csv = f"{tabla}.csv"
    with open(archivo_csv, "w", encoding="utf-8") as f:
        cur_vieja.copy_expert(f'COPY public."{tabla}" TO STDOUT WITH CSV HEADER', f)
    with open(archivo_csv, "r", encoding="utf-8") as f:
        cur_nueva.copy_expert(f'COPY public."{tabla}" FROM STDIN WITH CSV HEADER', f)
    conn_nueva.commit()

print("¡Listo! Las 7 tablas se crearon y migraron por completo a São Paulo.")
