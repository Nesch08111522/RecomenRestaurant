"""Herramienta heredada de copia. No replica índices ni restricciones.
No ejecutar sobre producción: usar migraciones/respaldos completos de PostgreSQL.
Credenciales exclusivamente en variables de entorno; nunca se ejecuta al importar.
"""
import os

def main():
    if os.environ.get("SMARTRESTO_ALLOW_LEGACY_MIGRATION") != "YES":
        raise SystemExit("Copia heredada deshabilitada: no conserva índices ni restricciones. Revisa CONECTIVIDAD.md antes de autorizarla.")
    import psycopg2
    URI_VIEJA = os.environ['MIGRATION_SOURCE_DATABASE_URL']
    URI_NUEVA = os.environ['MIGRATION_TARGET_DATABASE_URL']
    tablas_ordenadas = ['sr_businesses', 'app_records', 'sr_branches', 'sr_settings', 'sr_memberships', 'ai_decisions', 'sr_audit_events']
    conn_vieja = psycopg2.connect(URI_VIEJA)
    conn_nueva = psycopg2.connect(URI_NUEVA)
    cur_vieja = conn_vieja.cursor()
    cur_nueva = conn_nueva.cursor()
    cur_nueva.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    for tabla in tablas_ordenadas:
        print(f'1. Creando estructura de {tabla}...')
        cur_vieja.execute("\n        SELECT \n            column_name,\n            CASE \n                WHEN data_type = 'USER-DEFINED' THEN udt_name\n                WHEN character_maximum_length IS NOT NULL THEN data_type || '(' || character_maximum_length || ')'\n                WHEN data_type = 'ARRAY' THEN LTRIM(udt_name, '_') || '[]'\n                ELSE data_type\n            END,\n            is_nullable,\n            column_default\n        FROM information_schema.columns\n        WHERE table_schema = 'public' AND table_name = %s\n        ORDER BY ordinal_position;\n    ", (tabla,))
        columnas_sql = []
        for col_name, col_type, is_null, col_def in cur_vieja.fetchall():
            linea = f'"{col_name}" {col_type}'
            if is_null == 'NO':
                linea += ' NOT NULL'
            if col_def and 'nextval' not in col_def:
                linea += f' DEFAULT {col_def}'
            elif col_def and 'nextval' in col_def:
                linea = f'"{col_name}" SERIAL'
            columnas_sql.append(linea)
        sql_create = f'CREATE TABLE IF NOT EXISTS public."{tabla}" (\n  ' + ',\n  '.join(columnas_sql) + '\n);'
        cur_nueva.execute(sql_create)
        conn_nueva.commit()
        print(f'2. Copiando datos de {tabla}...')
        archivo_csv = f'{tabla}.csv'
        with open(archivo_csv, 'w', encoding='utf-8') as f:
            cur_vieja.copy_expert(f'COPY public."{tabla}" TO STDOUT WITH CSV HEADER', f)
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            cur_nueva.copy_expert(f'COPY public."{tabla}" FROM STDIN WITH CSV HEADER', f)
        conn_nueva.commit()
    print('¡Listo! Las 7 tablas se crearon y migraron por completo a São Paulo.')

if __name__ == "__main__":
    main()
