# SmartResto

## Supabase como almacenamiento

La aplicaciÃ³n guarda todos sus datos operativos en Supabase PostgreSQL, en la tabla flexible `public.app_records` (JSONB). No hay respaldo ni lectura en archivos JSON durante la ejecuciÃ³n. Para configurar la base, ejecuta [`database/app_records.sql`](database/app_records.sql) en Supabase, define `DATABASE_URL`, `DATABASE_SSLMODE=require` y `DATA_BACKEND=postgresql` en `.env`, y luego inicia Flask. El arranque valida la conexiÃ³n y la tabla.

Para pasar los datos iniciales locales a Supabase, usa `python migrations/import_json_documents.py --dry-run` para ver el conteo y luego ejecuta `python migrations/import_json_documents.py`. El importador conserva IDs y archivos fuente; las filas que ya existan en la base no se sobrescriben. Consulta [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md) para los detalles.

Aplicación web de recomendaciones y gestión de restaurantes construida con Flask.

## Crear una carta con Qwen

El empresario puede descargar una plantilla Excel o Word, completarla y subirla desde la gestión de su restaurante. SmartResto extrae las filas de platos, las envía a Qwen mediante Groq y presenta una carta editable. El empresario revisa y aprueba el borrador antes de que se agreguen los platos a la carta pública; los nombres y precios se conservan desde la plantilla.

La integración usa la API compatible con OpenAI de [Groq](https://console.groq.com/docs/openai). Para configurar el desarrollo local, copia `.env.example` como `.env` si todavía no existe y agrega una clave nueva de Groq en `QWEN_API_KEY`. El archivo `.env` está ignorado por Git. En producción, guarda la clave en el administrador de secretos del servidor:

- `QWEN_API_KEY`: clave de Groq. También se acepta `GROQ_API_KEY`.
- `QWEN_BASE_URL`: por defecto `https://api.groq.com/openai/v1`.
- `QWEN_MODEL`: por defecto `qwen/qwen3.8-27b`.

Puedes crear una clave en [Groq Console](https://console.groq.com/keys). Instala las dependencias con `pip install -r requirements.txt` y reinicia Flask después de configurar `.env`. El plan gratuito tiene límites por organización/modelo; al excederlos, Groq devuelve un error de cuota. Consulta los [límites vigentes](https://console.groq.com/docs/rate-limits).

No incluyas claves reales en `.env.example`, el código, las plantillas ni el navegador. Para Word, se envían a Groq únicamente los datos extraídos de la tabla; el archivo cargado se procesa en memoria y no se guarda.
