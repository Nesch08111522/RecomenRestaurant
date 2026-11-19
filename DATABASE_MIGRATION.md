# Supabase como almacenamiento único

SmartResto lee y escribe los datos operativos exclusivamente en Supabase PostgreSQL. La aplicación no tiene una ruta de persistencia en archivos. Los modelos guardan cada entidad en `public.app_records`: una fila por registro, identificada por `collection` e `id`, con el contenido flexible en `payload JSONB`.

Las colecciones usadas por la aplicación incluyen `users`, `restaurants`, `categories`, `dishes`, `favorites`, `daily_menu`, `reviews`, `notifications`, `moderation`, `audit_events` y `reservations`. Las validaciones de negocio siguen en los modelos y las rutas; JSONB permite añadir campos sin cambiar columnas por cada campo nuevo.

## Activación

1. En Supabase, abre **SQL Editor** y ejecuta [`database/app_records.sql`](database/app_records.sql). Es una migración aditiva. Activa RLS y no da acceso a los roles de navegador `anon` y `authenticated`.
2. Configura `.env` local o los secretos del despliegue con `DATA_BACKEND=postgresql`, la URI de servidor en `DATABASE_URL`, `DATABASE_SSLMODE=require` y una `SECRET_KEY` propia de al menos 32 caracteres. No incluyas la URI en Git ni en el cliente web.
3. Si quieres conservar los datos iniciales locales, importa los documentos una sola vez. Primero revisa el conteo con `python -m migrations.import_json_documents --dry-run`; después ejecuta `python -m migrations.import_json_documents`. El importador conserva IDs, inserta solo filas que faltan y nunca sobrescribe registros que ya existan en Supabase.
4. Inicia la aplicación. `create_app()` valida configuración, conexión y existencia de `public.app_records`; falla al arrancar con una indicación si falta algún requisito.

Si no ejecutas la importación, la app comienza con las colecciones que ya existan en Supabase; los archivos heredados no se consultan en tiempo de ejecución. El importador no elimina ni modifica los archivos fuente.

Si tu proyecto ya tiene datos en tablas relacionales como `usuarios`, `restaurantes` o `platos`, la tabla documental no los incorpora automáticamente. Esas tablas quedan intactas; se requiere un mapeo adicional si esos son los datos que deben mostrarse en la aplicación.

## Integridad de auditoría y decisiones de IA

Después de instalar `app_records` y `ai_decisions`, ejecuta [`database/integrity_audit.sql`](database/integrity_audit.sql) en Supabase SQL Editor. La migración agrega metadatos de cadena a `audit_events` y `ai_decisions`, y crea `integrity_roots`; los registros históricos previos a esta migración permanecen consultables, pero no se incorporan retroactivamente a las cadenas.

Configura `AUDIT_SIGNING_KEY` solo en el entorno secreto del servidor. Usa al menos 32 bytes aleatorios; es independiente de `ANCHOR_PRIVATE_KEY`, `SECRET_KEY` y de cualquier clave de Polygon. Para generar una clave hexadecimal en PowerShell:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

La aplicación encadena los eventos sensibles en la misma transacción PostgreSQL; las decisiones de IA se encadenan al completar su reserva. El worker de verificación/firma se ejecuta por lotes y no publica eventos en redes externas:

```powershell
python -m scripts.integrity_audit verify
python -m scripts.integrity_audit sign --batch-size 500
python -m scripts.integrity_audit verify
```

`sign` se niega a crear raíces si detecta una cadena rota. `verify` valida las cadenas completas y las firmas HMAC-SHA256 guardadas en `integrity_roots`.

## Conexión

`database/connection.py` usa psycopg, requiere SSL, establece timeout y desactiva consultas preparadas para compatibilidad con el pooler de transacciones. Quita `pgbouncer=true` de la URI antes de pasársela a libpq. Para revisar conectividad sin imprimir secretos, ejecuta:

```bash
python -m database.check_connection
```

La comprobación de conectividad no crea tablas. El esquema se aplica de forma explícita desde SQL Editor para evitar cambios de DDL durante el arranque.

## Esquema relacional anterior

`database/schema.sql` y `migrations/migrate_json.py` pertenecen a una propuesta anterior de migración a tablas relacionales; no son necesarios para el backend actual y no deben ejecutarse como parte de esta configuración. La aplicación usa `app_records` hasta que se diseñe una migración explícita desde documentos hacia tablas relacionales.
