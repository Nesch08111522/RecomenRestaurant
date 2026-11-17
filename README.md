# SmartResto

**Mercado de barrio** conecta la carta con compras programadas, stock por receta y seguimiento de pedidos. Abre **Mercado** en la cabecera. [Ver el recorrido por rol, las 17 capacidades y la configuración de pagos](MERCADO.md).

Aplicación Flask de descubrimiento y gestión de restaurantes en Trujillo. Supabase PostgreSQL es el único almacenamiento operativo. Los modelos guardan documentos JSONB en `public.app_records`. El copiloto administrativo registra sus consultas en `public.ai_decisions`.

## Configuración y arranque

Desde la raíz del proyecto, en PowerShell con Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m scripts.secret_key
```

Copia el valor generado a `SECRET_KEY` y completa la URI PostgreSQL del proyecto en `DATABASE_URL`. Conserva `DATABASE_SSLMODE=require`. Usa el gestor de secretos del servidor para producción y activa `SESSION_COOKIE_SECURE=1` si sirves por HTTPS.

Ejecuta [app_records.sql](database/app_records.sql) y [ai_decisions.sql](database/ai_decisions.sql) en el editor SQL de Supabase. La aplicación comprueba el esquema de documentos al arrancar.

```powershell
python -m scripts.create_user
python app.py
```

Abre `http://127.0.0.1:5000`. El alta pública admite comensales y empresarios. El script crea al administrador de manera interactiva. Para comprobar credenciales, usa `python -m scripts.test_auth`.

## Flujos de negocio

- **Comensal**. Explora locales aprobados, filtra por ubicación o categoría y consulta su carta. Con sesión iniciada puede guardar favoritos, calificar y reservar para una fecha y hora de Lima.
- **Empresario**. Registra su restaurante, administra los platos y el menú por fecha. Puede revisar un borrador extraído de Excel, Word o fotografías antes de publicarlo.
- **Administrador**. Revisa locales, aprueba o revierte decisiones, consulta el historial, gestiona categorías y accede a los indicadores de negocio.

## Inteligencia artificial

Configura la clave de Groq en `QWEN_API_KEY` y el identificador habilitado para tu cuenta en `QWEN_MODEL`. Búsqueda, chat y extracción de texto comparten configuración. El copiloto administrativo admite `ADMIN_QWEN_MODEL` y exige el endpoint de Groq. La lectura de fotos utiliza `GEMINI_API_KEY` y `GEMINI_MODEL=gemini-2.5-flash`.

Los formularios POST utilizan `csrf_token`. Los clientes JSON del sitio envían el token de la página en `X-CSRFToken`. El cierre de sesión también requiere POST.

## Datos históricos y pruebas

Los archivos de `data/` sirven de origen para una migración manual. Comprueba primero una copia con `python -m migrations.import_json_documents --dry-run --source-dir RUTA`. La importación de moderación conserva todas las filas y su archivo de origen. Cuando se repite un ID, mantiene la referencia utilizada en auditoría y asigna IDs nuevos con el campo legacy_id a los registros restantes. Una referencia ambigua detiene la importación. Consulta [la guía de migración](DATABASE_MIGRATION.md).

Para las pruebas de integración, usa una **base PostgreSQL desechable** con TLS, los dos esquemas instalados y los roles `anon` y `authenticated` que referencian los scripts. La suite crea cuentas, restaurantes y decisiones de prueba.

```powershell
$env:DATABASE_URL = '<URI de la base de pruebas>'
$env:SMARTRESTO_TEST_DATABASE_URL = $env:DATABASE_URL
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
$env:FLASK_DEBUG = '0'
python -m pytest -q test
```

El informe de transformación y las rutas para cada perfil están en [PLATAFORMA.md](PLATAFORMA.md).
