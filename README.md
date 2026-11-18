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

Ejecuta [app_records.sql](database/app_records.sql), [ai_decisions.sql](database/ai_decisions.sql) y, para la Fase 1, [platform_foundation.sql](database/platform_foundation.sql) en el editor SQL de Supabase. La aplicación comprueba el esquema de documentos al arrancar.

La arquitectura transversal está documentada en [ARQUITECTURA_FASE_1.md](ARQUITECTURA_FASE_1.md). El contrato de plataforma está disponible sin exponer secretos en `GET /api/platform/manifest` y su estado no sensible en `GET /api/platform/health`.

La gestión de usuarios, roles, permisos y perfiles de la Fase 2 está documentada en [FASE_2_USUARIOS_PERFILES.md](FASE_2_USUARIOS_PERFILES.md). El perfil autenticado se consulta en `GET /api/platform/me` y se actualiza mediante `PATCH /api/platform/me/profile` con CSRF.

```powershell
python -m scripts.create_user
python app.py
```

Abre `http://127.0.0.1:5000`. El alta pública admite comensales y empresarios. El script crea al administrador de manera interactiva. Para comprobar credenciales, usa `python -m scripts.test_auth`.

### Conexión de red sin modificar `.env`

La conexión directa de Supabase puede requerir IPv6. Si aparece `getaddrinfo failed`, comprueba la conectividad de la red antes de atribuir el fallo a las tablas. El pooler de sesión permite conectar desde redes IPv4, pero su host y usuario deben copiarse del diálogo **Connect → Session pooler**; no uses literalmente `HOST_POOLER` ni inventes la región.

Las variables del proceso tienen prioridad sobre `.env`. Si pegaste una URL de ejemplo en PowerShell, quita únicamente ese override temporal y usa la configuración original:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
python -m database.check_connection
python app.py
```

Estos comandos no escriben en `.env`. Las APIs de IA y perfil requieren CSRF; el frontend lo envía con el helper global. `GET /api/platform/health` comprueba la base real y distingue la configuración de IA de una llamada efectiva al proveedor.

## Flujos de negocio

- **Comensal**. Explora locales aprobados, filtra por ubicación o categoría y consulta su carta. Con sesión iniciada puede guardar favoritos, calificar y reservar para una fecha y hora de Lima.
- **Empresario**. Registra su restaurante, administra los platos y el menú por fecha. Puede revisar un borrador extraído de Excel, Word o fotografías antes de publicarlo.
- **Administrador**. Revisa locales, aprueba o revierte decisiones, consulta el historial, gestiona categorías y accede a los indicadores de negocio.

## Inteligencia artificial

Pega tu clave de OpenRouter en `OPENROUTER_API_KEY` dentro de `.env`. Búsqueda, chat y copiloto administrativo comparten `AI_BASE_URL=https://openrouter.ai/api/v1` y `AI_MODEL=openai/gpt-4o-mini`. Para contratar un modelo cambia `AI_MODEL` por su identificador en OpenRouter. `ADMIN_AI_MODEL` permite escoger uno diferente para administración.

El análisis de platos utiliza `AI_VISION_MODEL`, cuyo modelo debe admitir imágenes. Se configuró inicialmente `openai/gpt-4o-mini`, con disponibilidad y selección dependientes del proveedor. La extracción de cartas que usa Gemini conserva `GEMINI_API_KEY` y `GEMINI_MODEL=gemini-2.5-flash`. Guarda las claves únicamente en `.env` privado y conserva `.env.example` sin credenciales.

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

## Fase 3 — Radar gastronómico

El radar administrativo está en `/admin/discovery` y el espacio empresarial de reclamación en `/owner/discovery`. Consulta [la guía de implementación y límites de Fase 3](FASE_3_RADAR_GASTRONOMICO.md). Conserva el stack Flask/PostgreSQL/Supabase y el proveedor IA compartido; no requiere modificar `.env` ni ejecutar nuevas migraciones.

El flujo es fuente autorizada → evidencia → ficha provisional → revisión → invitación → reclamación supervisada → registro comercial con los mismos IDs de negocio/sucursal. No se copian datos Google Places al catálogo ni se publican precios, menús o disponibilidad inventados. Las imágenes y videos detectados quedan como referencias con permiso de reutilización pendiente.

Para actualización periódica: `python -m scripts.refresh_discovery`. El instalador Windows `scripts/install_discovery_task.ps1` prepara una tarea diaria bajo el usuario que lo ejecute; **la tarea no fue registrada automáticamente durante esta implementación**. Requiere usuario conectado, equipo encendido y red. La consulta OSM real desde este entorno agotó timeout: comprobar conectividad del proveedor antes de considerar validada una corrida real.

## Fase 4 — Portal empresarial y sitios de marca

Entra como empresario a `/owner/sites` o usa **Mi sitio y marca**. Edita borradores, sube tu logo, pide propuestas con el proveedor IA ya configurado y publica una copia revisada en `/negocio/<slug>`; las sucursales relacionadas tienen rutas propias. No se modifica `.env` ni se duplican la carta y el mercado. La IA pagada se comprobó con texto e imagen, ambas con HTTP 200.

Consulta [la guía completa de Fase 4](FASE_4_PORTAL_EMPRESARIAL.md) para cobertura de los 18 requisitos, publicación, cuota de IA, formatos de contenido y requisitos de despliegue. Publicar dentro del proyecto local no equivale a desplegarlo en Internet. Reinicia `python app.py` para cargar el nuevo blueprint.
