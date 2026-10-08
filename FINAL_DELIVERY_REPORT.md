# SmartResto — Reporte final de evolución técnica

**Autor:** Manus AI  
**Proyecto:** Sistema Inteligente de Recomendación y Gestión de Restaurantes  
**Base:** Código existente Flask/Python/HTML/CSS/JavaScript/JSON  
**Estrategia:** Evolución incremental, reversible y compatible  
**Estado de validación:** 24 pruebas aprobadas; JSON originales preservados

## 1. Resumen ejecutivo

Se completó una evolución incremental sobre la copia de trabajo del sistema existente. No se reconstruyó la plataforma desde cero, no se eliminaron los archivos JSON originales y no se sustituyó de forma abrupta el backend JSON. La arquitectura Flask, los blueprints, las vistas actuales y los contratos principales se conservaron, mientras que se añadieron capas controladas para seguridad, persistencia futura en PostgreSQL, auditoría, aprobación híbrida, recomendaciones, geolocalización, BI, accesibilidad y QA.

La validación final compiló los módulos Python, ejecutó la suite completa y comparó los once archivos JSON de la copia de trabajo contra la evidencia auditada. El resultado fue **24 passed** y **JSON_ORIGINALS_PRESERVED**. Permanece una advertencia externa de `pyDatalog` relacionada con una secuencia de escape; no produjo fallos y no pertenece a código modificado por esta evolución.

> La activación real de PostgreSQL queda preparada, pero no se ejecutó contra un servidor porque el entorno de auditoría no disponía de un servicio PostgreSQL activo. El modo JSON continúa siendo el predeterminado y seguro para conservar compatibilidad.

## 2. Estado anterior frente al estado entregado

| Área | Problema observado | Estado entregado |
|---|---|---|
| Seguridad web | CSRF incompleto, sesiones y cabeceras no centralizadas, validación desigual | CSRF global con helper frontend, cookies endurecidas, cabeceras, validación backend y errores controlados |
| Persistencia JSON | Riesgo de colisiones, truncamiento y escrituras concurrentes | Locks por archivo, IDs bajo lock y escritura atómica |
| Administración | Asignación masiva, controles inconsistentes y escasa trazabilidad | Allowlists, revalidación de identidad, auditoría y estados controlados |
| Aprobación | Flujo manual/heurístico sin separación clara entre IA y decisión | Preevaluación explicable; decisión administrativa reversible y auditada |
| Recomendaciones | Reglas aisladas y muestreo aleatorio en menús | Motor híbrido transparente y generación determinista sustentada en catálogo |
| Geolocalización | Validación incompleta y horarios afirmados sin evidencia | Coordenadas normalizadas, Haversine validado, filtros backend y sin horarios inventados |
| BI | Analíticas aisladas sin contrato estable | Snapshot versionado `bi.v1` y endpoint administrativo protegido |
| UX/UI | Responsive y accesibilidad incompletas | Skip link, foco visible, reduced motion, estados visuales y breakpoints mobile-first |
| QA | Cobertura limitada y contratos parcialmente desalineados | 24 pruebas automatizadas, compilación y validación de preservación JSON |

## 3. Cambios realizados por fase

### Fase 4 — Seguridad crítica y compatibilidad funcional

Se centralizaron controles en `utils/security.py`, `config.py` y `app.py`. Se activaron protección CSRF para formularios y mutaciones, cookies con atributos de seguridad, límites de solicitud, cabeceras defensivas y errores sin trazas internas. La sesión se limpia y reconstruye durante el login, y la redirección `next` solo acepta destinos seguros.

Los formularios HTML recibieron tokens explícitos y `static/js/security.js` adjunta el token a mutaciones same-origin. Las rutas de autenticación dejan de exponer hashes y solo aceptan campos permitidos. Los CRUD de empresario y administración usan allowlists, verifican tipos, rangos, pertenencia, disponibilidad y valores enumerados. La API de búsqueda conserva la respuesta histórica en lista y el frontend tolera tanto la forma heredada como la enriquecida.

La persistencia en `models/base.py` fue endurecida con bloqueo por archivo, IDs generados bajo lock y escritura atómica mediante archivo temporal y reemplazo. Esto reduce truncamientos y colisiones durante la transición a una base relacional.

**Archivos relevantes:** `app.py`, `config.py`, `utils/security.py`, `models/base.py`, `views/auth.py`, `views/main.py`, `views/owner.py`, `views/admin.py`, `templates/base.html`, `templates/login.html`, `templates/register.html`, `templates/auth/profile_content.html`, `static/js/security.js` y `requirements.txt`.

### Fase 5 — PostgreSQL y migración conservadora

Se creó `database/schema.sql` con un modelo relacional mínimo y extensible que conserva IDs legacy y cubre usuarios, roles, empresarios, restaurantes, ubicaciones, categorías, platos, ingredientes, recetas, menús, preferencias, favoritos, reseñas, recomendaciones, interacciones, aprobaciones, notificaciones, mensajes, promociones y auditoría.

La conexión es opcional mediante `database/connection.py`, y `database/repository.py` usa una allowlist declarativa para evitar interpolación de nombres SQL provenientes de usuarios. `migrations/migrate_json.py` permite `dry-run`, validación de referencias, manifiesto, transacción e idempotencia. Los JSON se mantienen intactos y la migración todavía no reemplaza el backend activo.

**Ventaja frente al estado anterior:** permite iniciar una migración por modelo, verificar integridad y volver al modo JSON sin una migración destructiva.

### Fase 6 — RBAC, aprobación híbrida y auditoría

`utils/audit.py` implementa eventos append-only lógicos con actor, acción, recurso, petición, metadatos sanitizados y fecha UTC. Las IP no se persisten en claro; se conserva una huella ligada al secreto de aplicación. `models/moderation.py` separa la evaluación preliminar de la decisión humana y mantiene historial de transiciones.

Los estados controlados son `APROBADO_AUTOMATICAMENTE`, `PENDIENTE_REVISION`, `RECHAZADO` y `SUSPENDIDO`. La IA puede sugerir una preevaluación y motivos, pero no ejecutar por sí sola una decisión crítica. El administrador autorizado puede aprobar, rechazar, suspender, devolver a revisión o revertir una decisión anterior, dejando cada operación auditada. También se endureció la administración de usuarios para bloquear autoescalado peligroso y registrar cambios sensibles.

### Fase 7 — Recomendaciones híbridas y menús sustentados

`logic/hybrid_recommender.py` combina señales disponibles de contenido, interacciones colaborativas, reglas, contexto y proximidad. El sistema declara explícitamente el método utilizado, el desglose de score y los motivos. Si no existen suficientes interacciones, aplica un fallback de cold start sin presentar una señal colaborativa inexistente.

La generación de menús empresariales dejó de usar muestreo aleatorio. Las propuestas se construyen únicamente con platos propios, disponibles y con precio registrado. No se inventan ingredientes, precios, nombres ni disponibilidad. El contrato de respuesta existente se conserva para evitar romper el frontend.

### Fase 8 — Geolocalización

`utils/geo.py` normaliza latitud y longitud, rechaza valores no finitos y rangos inválidos, y conserva un cálculo Haversine determinista para radios acotados. `views/main.py` incorpora filtros backend de categoría, precio máximo, valoración mínima y disponibilidad en proximidad. Las coordenadas `0,0` se tratan como válidas cuando son finitas, y el enriquecimiento ya no afirma que un restaurante está abierto si no existe un horario calculado explícito.

PostGIS no se activa todavía porque no hay servidor PostgreSQL desplegado en el entorno de validación y el volumen actual no justifica una dependencia operativa adicional. El esquema relacional deja preparada la normalización para añadir posteriormente una columna `geography(Point, 4326)` e índice espacial cuando las consultas reales lo justifiquen.

### Fase 9 — Business Intelligence

Se creó `analytics/metrics.py` con el agregador puro `build_bi_snapshot`. El endpoint `GET /admin/api/bi/overview`, protegido por `admin_required`, genera un snapshot `bi.v1` a partir de los repositorios existentes. Incluye distribución de roles, usuarios con interacciones, restaurantes por estado y categoría, platos disponibles, menús, favoritos, reseñas, calidad del feedback, auditoría y estado de suficiencia para evaluar recomendaciones.

Los valores sin datos se expresan como `null` o colecciones vacías. El snapshot no incluye contraseñas, hashes, tokens, IP en claro ni contenido privado de conversaciones. Su estructura queda preparada para una extracción futura controlada hacia Power BI sin acoplar el backend a esa herramienta.

### Fase 10 — UX/UI

Se mantuvo el diseño existente y se añadieron mejoras compatibles. `templates/base.html` incorpora un enlace para saltar al contenido principal y un `main` enfocable. `static/css/main.css` añade foco visible, estados de error/carga, controles deshabilitados, soporte `prefers-reduced-motion`, adaptación del encabezado y buscador, columnas de detalle de una sola columna en móvil y tamaños táctiles mínimos.

No se añadieron elementos innecesarios, dependencias visuales nuevas ni cambios que alteren los contratos JavaScript.

### Fase 11 — QA y regresión

Se agregó `test/test_phase11_qa.py` para comprobar páginas públicas, contratos de búsqueda, cabeceras `X-Content-Type-Options` y `X-Frame-Options`, aislamiento administrativo, entradas inválidas, unicidad de endpoints y ausencia de debug. Durante la primera ejecución se detectó que dos rutas del test no incluían el prefijo real `/auth`; se corrigió la prueba, no el sistema. La segunda ejecución fue satisfactoria.

## 4. Matriz de archivos de trazabilidad

| Documento | Contenido |
|---|---|
| `DIAGNOSTICO_PREVIO_SMARTRESTO.md` | Diagnóstico aprobado y hallazgos iniciales |
| `PRIORITY_MATRIX.md` | Priorización y baseline |
| `CHANGELOG_PHASE4_SECURITY.md` | Seguridad, validación y compatibilidad |
| `DATABASE_MIGRATION.md` | Esquema y migración JSON→PostgreSQL |
| `CHANGELOG_PHASE5_DATABASE.md` | Decisiones de base de datos y pruebas |
| `CHANGELOG_PHASE6_RBAC_APPROVAL.md` | RBAC, auditoría y aprobación híbrida |
| `CHANGELOG_PHASE7_ML_RECOMMENDATIONS.md` | Recomendaciones híbridas y menús sustentados |
| `CHANGELOG_PHASE8_GEOLOCATION.md` | Geolocalización y decisión sobre PostGIS |
| `CHANGELOG_PHASE9_BI.md` | Métricas y snapshot BI |
| `CHANGELOG_PHASE10_UX_UI.md` | Responsive y accesibilidad |
| `CHANGELOG_PHASE11_QA.md` | QA, regresión y corrección del test |
| `FINAL_TEST_REPORT.txt` | Evidencia final de ejecución |

## 5. Validación final

| Verificación | Resultado |
|---|---:|
| Compilación Python | Correcta |
| Suite automatizada | **24 passed** |
| Advertencias | 1 warning externo de `pyDatalog` |
| JSON originales comparados | 11/11 sin cambios |
| Migración PostgreSQL ejecutada | No; preparada en `dry-run`, sin servidor disponible |
| Backend JSON activo | Conservado como predeterminado |
| Código debug intencional | No habilitado en la configuración de producción |

## 6. Ejecución local

Antes de iniciar se debe definir una clave fuerte mediante `SECRET_KEY`; la aplicación ahora falla de forma explícita si se intenta arrancar sin ella. La instalación se realiza con el archivo `requirements.txt`.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY='reemplazar-por-un-secreto-largo-y-aleatorio'
python3 app.py
```

La ejecución de pruebas se realiza con:

```bash
SECRET_KEY='test-secret-key-123456789012345678901234' FLASK_TESTING=1 python3 -m pytest -q
```

Para inspeccionar la migración sin tocar PostgreSQL ni los JSON:

```bash
python3 migrations/migrate_json.py --dry-run
```

La activación de PostgreSQL debe hacerse únicamente después de provisionar el servicio, configurar `DATABASE_URL`, ejecutar el esquema, realizar el `dry-run`, revisar el manifiesto y validar conteos, referencias, restricciones y reversibilidad.

## 7. Riesgos residuales y siguiente control recomendado

La migración real a PostgreSQL no puede considerarse cerrada hasta ejecutarse contra una instancia PostgreSQL controlada. Tampoco se activa PostGIS hasta disponer de consultas espaciales y un volumen que justifique el índice. El sistema dispone de auditoría de eventos administrativos, pero la mensajería entre roles todavía debe desarrollarse como un módulo independiente con reglas de privacidad, retención, moderación y notificaciones; el esquema PostgreSQL ya reserva las estructuras necesarias.

La evaluación estadística de calidad de recomendaciones permanece limitada por el volumen real disponible. El snapshot lo declara de forma explícita y no fabrica una métrica de precisión. Para activar Collaborative Filtering con confianza deberán acumularse interacciones suficientes, definir un conjunto de evaluación temporal y medir cobertura, precisión@k, recall@k, diversidad y tasa de aceptación sin contaminar el entrenamiento con eventos futuros.

## References

[1]: https://owasp.org/www-project-web-security-testing-guide/ "OWASP Web Security Testing Guide"
[2]: https://flask.palletsprojects.com/en/stable/web-security/ "Flask Security Considerations"
[3]: https://postgis.net/ "PostGIS — Spatial database extender for PostgreSQL"
