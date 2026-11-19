# Auditoría de conectividad de SmartResto

Fecha: 18 de noviembre de 2026. Auditoría inicial realizada **antes de modificar la capa de conexión**. La revisión de responsividad se atendió después de documentar esta auditoría; véase `docs/RESPONSIVIDAD.md`.

## A. Diagnóstico inicial y evidencia

| Hallazgo | Evidencia | Impacto / estado inicial |
|---|---|---|
| No existe pool de conexiones en la aplicación | `database/connection.py` ejecuta `psycopg.connect()` en cada entrada y `close()` al salir. Psycopg 3.2.3 instalado; `psycopg_pool` ausente | Alto: repite DNS/TCP/TLS/autenticación por operación |
| Transacciones de documentos agregan viajes de red | `document_transaction()` envuelve cada lectura en transacción; `all()` descarga la colección completa | Alto: red + BEGIN/SELECT/COMMIT repetidos |
| Lecturas duplicadas y N+1 | Categorías se leen en la vista y en el context processor; configuración web en cada HTML; platos y restaurantes filtran listas completas; varios paneles recorren colecciones | Alto, crece con el volumen |
| Solo timeout de establecimiento | `connect_timeout=10`; no hay límites explícitos de adquisición, sentencia o bloqueo | Esperas largas bajo concurrencia |
| Modalidad real | URI local configurada apunta a pooler Supabase por puerto 6543, TLS `require`, prepared statements desactivados | Compatible con transacciones actuales; no cambiar modalidad automáticamente |
| Autenticación actual correcta | Una conexión de diagnóstico completó la autenticación en **881,10 ms** | No hay evidencia de bloqueo de IP o contraseña incorrecta en esta muestra |
| DNS / red | DNS **12,12 ms**; TCP **154,75 ms**; 3 direcciones IPv4, ninguna IPv6 para el host configurado | No se demuestra un problema IPv6 en esta modalidad |
| TLS | El sondeo independiente con el almacén CA de Python falla con `SSLCertVerificationError`; libpq con `sslmode=require` conecta | Cifrado activo. Verificación de identidad con CA requiere revisar la cadena de confianza; no desactivar TLS ni forzar IPv4 |
| SQL vs red | `SELECT 1`: 455,03 ms primera consulta dentro de transacción y 143,75 / 143,19 ms posteriores; lectura de 20 restaurantes: **288,83 ms** | Diferenciar viajes de red de ejecución del servidor |
| Plan real | `EXPLAIN (ANALYZE,BUFFERS)` de una lectura limitada, en transacción READ ONLY: ejecución del servidor **0,092 ms**, 26 restaurantes entre 376 registros, escaneo secuencial | En esta muestra el servidor SQL no explica cientos de ms. Una tabla pequeña puede preferir escaneo secuencial |
| Índices reales | `pg_indexes` no devuelve índices para `public.app_records` en la conexión actual, aunque el script del repositorio sí los define | Requiere comprobar restricciones/esquema real antes de proponer cambios. No crear índices en producción automáticamente |
| Secretos en script ajeno al arranque | `migrar.py` contiene 2 literales con formato de URI PostgreSQL; importa psycopg2 y conecta al ejecutarse | No se ejecutó. Evitar su difusión; revisar/rotar credenciales manualmente si son reales. No registrar sus valores |
| Servicios externos | OpenRouter tiene `max_retries=0`; la inicialización de Flask no llama al LLM. Geocodificación e importaciones IA tienen operaciones síncronas acotadas | Mantener IA separada de lecturas convencionales; evaluar trabajos largos aparte |

### Alcance de las mediciones

Muestra puntual desde este equipo; no es un p95 ni una prueba de carga. El sondeo DNS dentro del entorno restringido falló y se repitió fuera de esa restricción, donde resolvió correctamente. No se atribuye ese primer fallo a Supabase. TCP y TLS se midieron por separado; autenticación se mide como establecimiento completo del driver (incluye TCP y TLS), no como un tiempo puro de contraseña. El sondeo TLS no permite separar negociación TLS satisfactoria porque falló la verificación CA.

No se probaron URI alternativas inventando host o usuario. Las conexiones directa y Session Pooler requieren sus valores reales del panel de Supabase. Los puertos por sí solos no identifican toda la configuración.

## Revisión de arquitectura

- Punto central de conexión de la aplicación: `database/connection.py`; 13 bloques consumidores directos en database/models/views/utils. Los modelos de documentos comparten `document_transaction()` mediante ContextVar y conservan atomicidad de operaciones y auditoría.
- Puntos independientes: `migrations/migrate_json.py` (migración explícita), `migrar.py` (script suelto no ejecutado). No forman parte del arranque normal.
- `app.py` verifica el esquema al crear la aplicación; el reloader de depuración puede inicializar dos procesos. `FLASK_DEBUG=0` evita esa duplicación en uso normal.
- El almacenamiento es PostgreSQL JSONB; muchos `.all()` son búsquedas y agregaciones en Python. No corresponde sustituir toda la arquitectura durante este mantenimiento.
- Se conservan roles, revalidación de sesión en BD, CSRF, OpenRouter, pyDatalog y las interfaces de anclaje/blockchain.

## Plan seguro de mantenimiento

1. Respaldar los archivos antes de editarlos, sin copiar `.env` ni credenciales incrustadas.
2. Implementar reutilización acotada por proceso, adquisición con límite, descarte de conexiones inválidas, liberación y rollback seguros. Evaluar Psycopg Pool frente a un pool síncrono pequeño sin reintentos de fondo, considerando el antecedente de bloqueo por autenticaciones fallidas.
3. Añadir límites transaccionales de sentencia/bloqueo compatibles con Transaction Pooler, sin `SET` de sesión persistente ni prepared statements.
4. Reducir consultas duplicadas dentro de la misma solicitud sin cachear permisos entre solicitudes; optimizar lecturas puntuales con SQL parametrizado donde conserve semántica.
5. Incorporar métricas agregadas sin URI, parámetros, cuerpos, usuarios ni claves. Añadir diagnóstico reutilizable de solo lectura.
6. Ejecutar pruebas locales antes/después, rollback, concurrencia y fallo de autenticación; escritura únicamente en BD temporal local. Repetir una muestra de lectura de Supabase si autentica; detenerse ante fallo, sin bucles de reintento.
7. Documentar resultados y pendientes. Ningún índice ni cambio de credenciales/red se aplicará automáticamente a producción.

## Fuentes verificadas

- [Psycopg: gestión de pools, comprobaciones y reconexión](https://www.psycopg.org/psycopg3/docs/advanced/pool.html).
- [Supabase: modalidades de conexión y compatibilidad](https://supabase.com/docs/guides/database/connecting-to-postgres).
- [Supabase: prepared statements y Transaction Pooler](https://supabase.com/kb/troubleshooting/disabling-prepared-statements-qL8lEL).

## B. Modificaciones aplicadas

| Archivo | Cambio y justificación |
|---|---|
| `database/pool.py` | Pool síncrono por proceso, máximo 4 conexiones por defecto, creación serializada, espera acotada, cierre de conexiones rotas/ociosas, rollback y cierre al terminar el proceso. Cero conexiones precargadas y cero reintentos en segundo plano. Pausa de 30–300 s con backoff y jitter tras fallar el establecimiento; solo una nueva solicitud posterior puede reintentar |
| `database/connection.py` | Reutilización con el mismo host/puerto/TLS y `prepare_threshold=None`; métricas de adquisición/establecimiento y clasificación segura de autenticación; helper de límites locales de transacción |
| `database/repository.py` | Lecturas repetidas `.all()` se reutilizan solo dentro de una petición GET/HEAD, con copias defensivas e invalidación en escrituras. No se reutilizan dentro de una transacción activa; `FOR UPDATE` conserva su bloqueo y no consulta caché. Máximo 16 colecciones de hasta 1000 registros en esa caché |
| `models/ai_decision.py`, `models/favorite.py` | Límites locales de sentencia/bloqueo en sus transacciones SQL directas, conservando commits, cuotas y bloqueos atómicos |
| `database/metrics.py` | Agregados acotados a 128 entradas por proceso; duración SQL con huella, sin texto/valores de consultas; contadores de errores y consultas lentas |
| `app.py` | Tiempo/errores por endpoint conocido, sin parámetros ni URL completa; fallo operativo del driver devuelve respuesta segura 503 |
| `views/admin.py` | `GET /admin/api/performance`, exclusivo del administrador revalidado, sin caché HTTP; tiempos medios/máximos, pool y errores del proceso actual. El context processor de restaurantes se limita a páginas internas y tolera una caída de BD; las páginas públicas y de error no repiten esa consulta |
| `config.py`, `.env.example` | Parámetros de capacidad/espera/timeout documentados. `.env` no se editó |
| `database/diagnose.py` | Diagnóstico reutilizable de solo lectura, tres consultas de prueba, plan de lectura limitado, sin reintentos de autenticación ni exposición de URI |
| `database/connectivity_schema_review.sql` | Diagnóstico SQL de solo lectura y propuesta de PK/RLS deliberadamente comentada para revisión manual; no se ejecutó DDL en producción |
| `migrar.py` | Eliminadas las dos URI incrustadas. Lee origen/destino del entorno, no conecta al importarse y exige autorización explícita mediante variable para ejecutar la copia heredada |
| `test/test_connection_pool.py`, `test/test_connection_integration.py`, `test/test_migration_secrets.py` | Regresiones de concurrencia, presupuesto, cooldown, rollback, atomicidad, timeout/recuperación, caché por petición, autorización de métricas y ausencia de URI incrustadas |
| `static/css/adaptive-experience.css`, `public-navigation.css`, `business-sites.css`, `theme-tokens.css` | La suite detectó colores literales fuera del contrato del tema. Sustituidos por tokens, manteniendo el contraste fijo necesario sobre fotografías |

Se conservaron las transacciones, CSRF, revalidación de sesión por petición, roles, reglas comerciales y auditoría. Ninguna transacción se mantiene abierta deliberadamente para llamar a OpenRouter. Las lecturas siguen usando transacciones con límites locales: no se hicieron cambios de sesión incompatibles con el pooler transaccional para ahorrar viajes de red.

### Decisión sobre el pool

Se evaluó `psycopg_pool`: es la opción estándar con capacidad y comprobaciones, pero su reconexión en segundo plano requiere una política adicional para el antecedente de autenticaciones fallidas. Se eligió aquí un pool síncrono pequeño, probado y sin dependencias nuevas, que no genera tráfico sin solicitudes. El coste es mantener esta implementación y sus pruebas. En despliegues con más procesos o mayor carga debe revisarse frente a `psycopg_pool` y métricas reales; no se afirma que sea una solución universal.

Las conexiones ociosas de más de 60 s o de vida superior a 300 s se descartan al reutilizarlas. Las conocidas como cerradas/rotas se descartan; una caída remota silenciosa puede producir un primer 503 al ejecutar SQL. No se repite una operación automáticamente: se evita duplicar cobros o escrituras.

### Respaldos

Archivos respaldados en `C:/Users/Nancy Sandoval/.codex/visualizations/2026/11/17/01a1e7c2-906d-78e2-bc7d-0d4f3be2d440/connectivity-backup-20261118/`. El original de `migrar.py` se conserva cifrado con DPAPI de Windows para este usuario (`migrar.py.dpapi`), en lugar de duplicar sus credenciales en texto plano. No se copió `.env`.

## C. Dependencias

No se agregaron, eliminaron ni actualizaron librerías. Se mantiene Psycopg 3.2.3 y compatibilidad con Python 3.12/Windows. El script heredado aún depende de psycopg2 y **no es una herramienta de migración completa**; su ejecución está deshabilitada por defecto y no se instaló esa dependencia para ejecutarlo.

## D. Rendimiento medido

Lectura controlada idéntica en Supabase: abrir/adquirir conexión, iniciar transacción READ ONLY, contar restaurantes, finalizar/liberar. Tres muestras secuenciales por modalidad, comparando la función respaldada anterior con la nueva. No es una prueba de carga ni un promedio de todo el sitio.

| Medición | Antes (ms) | Después (ms) |
|---|---:|---:|
| Primera muestra | 1661,45 | 1438,40 |
| Segunda muestra | 1630,61 | 567,79 |
| Tercera muestra | 1306,59 | 568,59 |
| Media de las tres | **1532,88** | **858,26** |
| Conexiones físicas para las tres lecturas | 3 | 1 |

**Reducción observada del 44,0 %** incluyendo la conexión fría. Media de las dos reutilizaciones: 568,19 ms. La consulta sigue cruzando la red y mantiene transacciones; no se promete ese porcentaje para todos los endpoints. Muestra pequeña y secuencial, susceptible a variaciones de la red.

El diagnóstico final volvió a autenticar en 891,98 ms; `SELECT 1` registró 141,99 / 142,36 / 143,07 ms. La ejecución del plan de lectura en PostgreSQL fue 0,084 ms. Esto respalda reducir conexiones y viajes repetidos antes de atribuir el problema a consultas SQL costosas. No identifica el tiempo puro de autenticación separado del establecimiento TCP/TLS.

Evidencia: [comparación](docs/connectivity/comparison.json), [inicio y HTTP local](docs/connectivity/local-smoke.json), [resumen de pruebas](docs/connectivity/tests-summary.json).

## E. Seguridad y esquema real

La revisión posterior confirma: tabla ordinaria `app_records`, **sin clave primaria**, RLS desactivado y un único índice válido (`trust_anchors_review_kind`), limitado a la colección de anclajes. No sustituye un índice general por `(collection,id)`. La primera observación de `pg_indexes` devolvió cero índices; la verificación posterior detallada es la referencia final.

No se encontraron grupos duplicados `(collection,id)` en la muestra consultada. No se crearon restricciones o índices automáticamente. El script `migrar.py` reconstruye columnas y copia CSV, pero omite claves, índices, RLS y otros elementos del esquema; **puede explicar ese resultado**, aunque no se dispone del historial DDL para afirmar que fue su causa histórica.

Los privilegios comprobados para `anon` y `authenticated` son **false** para SELECT y escritura. Por tanto, RLS desactivado no demuestra por sí solo exposición pública de esta tabla en el estado revisado. La PK sigue siendo un pendiente de integridad y RLS aporta defensa adicional. Revisar también todas las demás tablas tras cualquier migración heredada.

Procedimiento manual: respaldo completo válido, comprobar duplicados/nulos/restricciones y rol del backend, revisar la propuesta comentada en `database/connectivity_schema_review.sql`, probar en staging y programar el cambio. No ejecutar el copiado heredado para corregir este problema. Un índice GIN o índices parciales adicionales requieren planes representativos y datos suficientes; no se recomiendan indiscriminadamente para la tabla pequeña observada.

TLS continúa en `require`: cifra, pero no equivale a verificar identidad como `verify-full`. El fallo del sondeo con CA del almacén de Python queda pendiente de revisión de cadena/certificados. Obtener el certificado correcto por canal oficial y probar `verify-full` en el entorno antes de adoptarlo; no se deshabilitó TLS ni la restricción de red.

Revisar si las credenciales incrustadas en el script fueron compartidas o versionadas. Si lo fueron, revocarlas/rotarlas desde Supabase con el responsable; no se cambiaron contraseñas automáticamente ni se reprodujeron los valores en el informe.

Evidencia: [índice y privilegios](docs/connectivity/schema-review.json).

## F. Pruebas y límites de validación

- Suite completa final en PostgreSQL local desechable con TLS: **441 aprobadas, 0 fallos, 0 omitidas**, 114,42 s.
- La primera ejecución completa tuvo 433 aprobadas y un fallo del contrato de colores; corregido y repetido. La prueba de ausencia de URI incrustadas y la de 503 seguro reprodujeron el problema antes de sus respectivas correcciones.
- Pruebas específicas: límite del pool, ocho trabajadores, ausencia de reintentos de fondo, espera agotada, conexiones rotas, rollback y atomicidad de escritura, timeout SQL y recuperación, caché aislada y bloqueo `FOR UPDATE`, métricas solo para admin.
- Inicio normal de `create_app()` contra la base local con validación de esquema: 186,97 ms **después de importar módulos**, no mide el proceso Python completo. GET de inicio, login, registro, ofertas, planes y health devolvieron 200. POST de login sin CSRF devolvió 400.
- Ocho lecturas simultáneas reales contra PostgreSQL local: presupuesto respetado, dos conexiones creadas durante esa muestra, cero conexiones prestadas al finalizar. La prueba unitaria comprueba además saturación con máximo 2.
- Supabase: solo lecturas, diagnóstico y EXPLAIN ANALYZE de SELECT acotado. No se enviaron correos, SMS, pagos ni solicitudes facturables a OpenRouter durante estas pruebas.
- Suite final completa: **443 pruebas aprobadas**, 0 fallos, 0 errores, 0 omitidas, en 116,30 s. La primera pasada detectó un fallo del contrato de colores; se corrigió. La comprobación visual adicional con BD deliberadamente inaccesible reveló la consulta privada global que impedía renderizar páginas públicas/de error: se añadieron dos regresiones, se corrigió y se repitió toda la suite.
- No se simularon escrituras ni caída de producción. No se reproduce un bloqueo de IP intencionadamente. No se verificó un despliegue multiproceso real ni se compararon modalidades sin sus URI oficiales.

## G. Configuración que debe revisarse

| Variable | Valor inicial propuesto / efecto |
|---|---|
| `DATABASE_URL` | Mantener la URI real de la modalidad seleccionada. Contraseña codificada correctamente en URI; no mezclar usuarios de modalidades |
| `DATABASE_SSLMODE` | `require` actual. Revisar CA y probar `verify-full`; no usar `disable` |
| `DATABASE_POOL_MAX` | `4` por proceso (rango efectivo 1–16) |
| `DATABASE_POOL_TIMEOUT` | `5` s para esperar capacidad; el establecimiento tiene su propio límite |
| `DATABASE_CONNECT_TIMEOUT` | `5` s por establecimiento (efectivo 2–30) |
| `DATABASE_STATEMENT_TIMEOUT_MS` | `8000` ms por sentencia dentro de las transacciones configuradas |
| `DATABASE_LOCK_TIMEOUT_MS` | `2000` ms esperando bloqueo |
| `FLASK_DEBUG` | `0` para evitar el reloader y procesos duplicados durante uso normal |
| `AI_TIMEOUT`, `ADMIN_AI_TIMEOUT` | Solo operaciones explícitas de IA; el SDK compartido mantiene `max_retries=0`. La reparación única de JSON inválido en moderación es distinta de un reintento de autenticación |
| `SMARTRESTO_TEST_DATABASE_URL` | Exclusivamente BD desechable. No usar el DSN de producción para pruebas de escritura |

El script heredado lee `MIGRATION_SOURCE_DATABASE_URL` y `MIGRATION_TARGET_DATABASE_URL`; no deben incrustarse URI en el código. Su bandera `SMARTRESTO_ALLOW_LEGACY_MIGRATION` permanece sin configurar. No se recomienda usar esa copia como sustituto de una migración PostgreSQL completa.

Capacidad total estimada: procesos web × `DATABASE_POOL_MAX` + procesos de tareas/diagnóstico. Ajustarla al límite real del plan de Supabase; no aumentar a ciegas. La tarea de descubrimiento y el servidor son procesos independientes.

## H. Estado final

| Componente | Estado | Alcance / pendiente |
|---|---|---|
| Conectividad de la URI actual | VERIFICADO | DNS, TCP y autenticación de lectura correctos en la muestra |
| Reutilización y límite de conexiones | OPTIMIZADO | Menos establecimientos medidos; límite por proceso y liberación comprobados |
| Fallos, pausas y timeouts | CORREGIDO | Sin tormenta de reintentos; 503 seguro; límites locales de transacción |
| Lecturas duplicadas por solicitud | OPTIMIZADO | Caché GET/HEAD aislada; no caché de autorización entre solicitudes |
| SQL de lectura medido | VERIFICADO | Servidor < 0,1 ms en el plan limitado; no todos los endpoints tienen planes revisados |
| PK/índices generales de `app_records` | REQUIERE INTERVENCIÓN MANUAL | No se aplicó DDL en producción; revisar integridad antes de añadir PK |
| RLS tras la migración | REQUIERE INTERVENCIÓN MANUAL | Desactivado; permisos públicos revisados sin acceso |
| Cadena CA / `verify-full` | REQUIERE INTERVENCIÓN MANUAL | Cifrado actual conservado; verificación estricta pendiente |
| Credenciales del script heredado | CORREGIDO / REQUIERE INTERVENCIÓN MANUAL | Quitadas del código; valorar rotación si hubo exposición |
| Métricas internas | VERIFICADO | SQL/pool/HTTP por proceso; endpoint exclusivo de admin |
| Paginación y agregación SQL de todo el catálogo/BI | PENDIENTE | Persisten `.all()` y filtros/agregaciones en Python. No imponer límites silenciosos que omitan datos; requiere sustituir consultas por casos y validar reglas |
| OpenRouter y pyDatalog | VERIFICADO | Integraciones conservadas; salud convencional no llama al proveedor. No es un benchmark del proveedor externo |
| Blockchain/anclajes | VERIFICADO | Interfaces conservadas; no se ejecutaron transacciones externas |
| Comparación Direct/Session/Transaction | PENDIENTE | Solo se midió la URI habilitada; no se inventaron credenciales |
| Responsividad | VERIFICADO | 1500 combinaciones de tamaños/temas y 30 escenarios de interacción; alcance y límites en `docs/RESPONSIVIDAD.md` |

## I. Ejecución en PowerShell

```powershell
Set-Location 'C:\Users\Nancy Sandoval\Downloads\SISRESTAURANTE\RecomenRestaurant'
.\.venv\Scripts\Activate.ps1
$env:FLASK_DEBUG = '0'
python -m database.diagnose --network --output conectividad-diagnostico.json
python app.py
```

En otra terminal, con el servidor iniciado:

```powershell
Invoke-RestMethod 'http://127.0.0.1:5000/api/platform/health'
```

Con sesión de administrador, abrir `/admin/api/performance` para consultar métricas del proceso. No exponerlo mediante una ruta pública alternativa. Si falla la autenticación, detener los intentos, verificar modalidad/usuario/contraseña en el panel oficial y revisar bloqueos de red con el responsable. No ejecutar `migrar.py` para diagnosticar ni usar el pooler como excusa para cambiar credenciales automáticamente.

Las pruebas de escritura requieren `SMARTRESTO_TEST_DATABASE_URL` y el esquema instalado **en una base local/desechable explícita**. Nunca apuntar esa variable a la base operativa. No es necesario reinstalar dependencias para estos cambios.

