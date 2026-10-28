# Supabase como almacenamiento único

SmartResto lee y escribe los datos operativos exclusivamente en Supabase PostgreSQL. La aplicación no tiene una ruta de persistencia en archivos. Los modelos guardan cada entidad en `public.app_records`: una fila por registro, identificada por `collection` e `id`, con el contenido flexible en `payload JSONB`.

Las colecciones usadas por la aplicación incluyen `users`, `restaurants`, `categories`, `dishes`, `favorites`, `daily_menu`, `reviews`, `notifications`, `moderation`, `audit_events` y `reservations`. Las validaciones de negocio siguen en los modelos y las rutas; JSONB permite añadir campos sin cambiar columnas por cada campo nuevo.

## Activación

1. En Supabase, abre **SQL Editor** y ejecuta [`database/app_records.sql`](database/app_records.sql). Es una migración aditiva. Activa RLS y no da acceso a los roles de navegador `anon` y `authenticated`.
2. Configura `.env` local o los secretos del despliegue con `DATA_BACKEND=postgresql`, la URI de servidor en `DATABASE_URL`, `DATABASE_SSLMODE=require` y una `SECRET_KEY` propia de al menos 32 caracteres. No incluyas la URI en Git ni en el cliente web.
3. Si quieres conservar los datos iniciales locales, importa los documentos una sola vez. Primero revisa el conteo con `python migrations/import_json_documents.py --dry-run`; después ejecuta `python migrations/import_json_documents.py`. El importador conserva IDs, inserta solo filas que faltan y nunca sobrescribe registros que ya existan en Supabase.
4. Inicia la aplicación. `create_app()` valida configuración, conexión y existencia de `public.app_records`; falla al arrancar con una indicación si falta algún requisito.

Si no ejecutas la importación, la app comienza con las colecciones que ya existan en Supabase; los archivos heredados no se consultan en tiempo de ejecución. El importador no elimina ni modifica los archivos fuente.

Si tu proyecto ya tiene datos en tablas relacionales como `usuarios`, `restaurantes` o `platos`, la tabla documental no los incorpora automáticamente. Esas tablas quedan intactas; se requiere un mapeo adicional si esos son los datos que deben mostrarse en la aplicación.

## Conexión

`database/connection.py` usa psycopg, requiere SSL, establece timeout y desactiva consultas preparadas para compatibilidad con el pooler de transacciones. Quita `pgbouncer=true` de la URI antes de pasársela a libpq. Para revisar conectividad sin imprimir secretos, ejecuta:

```bash
python -m database.check_connection
```

La comprobación de conectividad no crea tablas. El esquema se aplica de forma explícita desde SQL Editor para evitar cambios de DDL durante el arranque.

## Esquema relacional anterior

`database/schema.sql` y `migrations/migrate_json.py` pertenecen a una propuesta anterior de migración a tablas relacionales; no son necesarios para el backend actual y no deben ejecutarse como parte de esta configuración. La aplicación usa `app_records` hasta que se diseñe una migración explícita desde documentos hacia tablas relacionales.
