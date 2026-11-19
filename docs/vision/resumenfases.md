# SmartResto — Resumen de auditoría de las 18 fases

**Fecha de corte:** 19 de noviembre de 2026
**Fuente de requisitos:** plan maestro de 18 fases adjunto por la usuaria.
**Alcance:** contraste estático del repositorio, sus rutas, plantillas, pruebas y documentación disponible. Este archivo no reemplaza las especificaciones de cada fase.

## Estilo interno: Minimalismo SaaS de Alta Precisión

Evidencia del 19 de noviembre de 2026. Especificación adjunta leída completa (79 líneas). Cambios de presentación, no cierre funcional de fases ni certificación visual exhaustiva.

### Implementación y alcance

- `templates/base.html`: frontera explícita para endpoints internos de blueprints mixtos; incorpora empresas, radar comercial y Google administrativo. `sr-workspace` incluye usuario, administrador y empresario; reutiliza header/sidebar y `internal_workspace_header.html`. CSS interno cargado al final, exclusivamente en sistema autenticado.
- `static/css/internal-workspace.css`: superficies planas, bordes 1px, radios 8px/controles 6px, títulos 22px, números tabulares, header 54px, sidebar expandida 232px y contenido máximo 1280px. Corrección dentro de la capa existente `visualContract`: sus declaraciones importantes prevalecían sobre CSS sin capa. Formularios de personal, verificación y suscripciones agrupados con divisores; rejillas responsivas y tablas desplazables por teclado.
- `saas-private.css` y `admin-precision.css`: sustituidos resets universales de background-image por listas de superficies concretas. No se borran fondos de fotografías, canvas, mapas o visores 3D. No nuevos colores ni fuentes/dependencias runtime. Se conservan las fuentes y tokens existentes.
- `private-shell.js`: envolturas de presentación para tablas que aún no tienen contenedor desplazable; no intercepta formularios/endpoints. `notification-feed.js`: controles de sonido y estado pasan al footer de sidebar solo en workspace, evitando overflow del header móvil. IDs, payloads, permisos y lógica de negocio no cambiados por esta intervención.
- Se añadieron únicamente clases de formulario en `owner/business_access.html`, `admin/business_verifications.html`, `admin/companies.html` y `admin/commercial_radar.html`. Se preservaron cambios concurrentes incluso cuando otro proceso dejó archivos en staging; esta intervención no ejecutó git add, commit ni borrados.

### Inventario de plantillas

| Grupo interno | Plantillas alcanzadas por shell/átomos compartidos | Evidencia visual nueva |
|---|---|---|
| Administración | `admin/dashboard`, `analytics`, `users`, `restaurants`, `restaurant_form`, `restaurant_import_preview`, `categories`, `moderation`, `operations`, `operation_detail`, `controls`, `website_settings`, `trust_center`, `business_verifications`, `companies`, `company_presence`, `company_activation` | users y companies; otras heredan CSS, no todas recorridas |
| Empresario | `owner/dashboard`, `restaurants`, `menu_management`, `menu_import_preview`, `business_access`, `subscriptions` | business_access y subscriptions |
| Operación | `market/kitchen`, `salon/manage`, `salon/desk`, `flow/desk`, `loyalty/customers`, `ecosystem/business` | salon/desk y flow/desk |
| Catálogo y marca | `catalog/dashboard`, `sites/editor` | ambos; catálogo sin restaurante seleccionado |
| Inteligencia y radar | `intelligence`, `discovery/dashboard`, `discovery/google`, `discovery/owner`, `admin/commercial_radar` | inteligencia, discovery/dashboard y radar comercial |
| Usuario | `auth/profile`, `auth/profile_owner`, `auth/security`, `favorites`, `home_kitchen`, `market/orders`, `market/cart`, `market/trust`, `loyalty/wallet`, `ecosystem/groups`, `group`, `scan`, `rewards`, `city`, `publications`, `copilot` | seguridad, favoritos, Home, pedidos, reservas y Copilot |
| Comunicación | `communication/inbox`, `thread`, `cases`, `case`, `notifications`; parciales conversation_list/message_fields | inbox |

Son nombres relativos a templates, con extensión .html. Parciales/base no son rutas independientes. Inventario de alcance por herencia no prueba conformidad de cada selector propio ni de todos los estados pendientes.

Excluidas: index/landing, detail/negocio público, offers, recommendations, information, business_plans, catalog/explore, market/browse y dish, ecosystem/home, sites/public (incluye previews públicos), flow/public, salon/menu/cart/session y mensajes QR públicos, login/register/recovery, company_activate y discovery/claim. Ninguna de sus plantillas fue editada por este rediseño. Contrato comprueba ausencia de CSS interno incluso con sesión admin en endpoints públicos seleccionados.

### Matriz Edge reproducible

`test/test_internal_style.py`: harness Flask independiente con Jinja/assets reales y datos simulados, sin ejecutar hooks/rutas backend productivos. Servidor propio 127.0.0.1 con puerto 0 asignado por SO, cerrado en finally; ninguna petición a :5000. Salida externa bloqueada (fuentes, mapas/proveedores incluidos). No conexiones ni escrituras DB en esta selección; no se modificó .env.

Cada fila siguiente pasó seis combinaciones: 360/768/1280 por dark/light. scrollWidth exacto 360/768/1280; header 54px, sidebar escritorio 232px, h1 22px. Drawer abierto/cerrado con Escape en 360 y 768 para cada fila. Rutas son las del harness, no evidencia HTTP de permisos productivos.

| Endpoint | Ruta harness | Template |
|---|---|---|
| admin.users | /admin/users | admin/users.html (una cuenta QA) |
| commercial_radar.dashboard | /admin/radar-comercial | admin/commercial_radar.html |
| companies.admin_companies | /admin/empresas | admin/companies.html (una empresa QA) |
| salon.desk | /salon/1 | salon/desk.html (sin mesas) |
| intelligence.dashboard | /inteligencia | intelligence.html (sin historial) |
| companies.owner_subscriptions | /owner/suscripciones | owner/subscriptions.html |
| business_access.access | /owner/acceso/1 | owner/business_access.html |
| flow.desk | /salon/1/cola | flow/desk.html (fila de aforo QA) |
| sites.editor | /owner/sites | sites/editor.html (borrador QA seleccionado) |
| catalog.dashboard | /owner/catalog | catalog/dashboard.html (sin selección) |
| copilot.page | /copilot | copilot.html |
| auth.account_security | /auth/seguridad | auth/security.html |
| auth.favorites | /auth/favorites | favorites.html (vacío) |
| home_kitchen.index | /home/ | home_kitchen.html (vacío) |
| comunicacion.inbox | /mensajes | communication/inbox.html (vacío) |
| loyalty.reservations | /mis-reservas | loyalty/wallet.html (reservas vacías) |
| market.orders | /mercado/pedidos | market/orders.html (vacío) |
| discovery.dashboard | /admin/discovery | discovery/dashboard.html (vacío) |

108 mediciones, no 108 pruebas independientes. Modal de edición users abierto con botón real y cerrado con Cancelar; dialog de discovery abierto por showModal y cerrado con Escape, ambos al final en 1280 light. Tablas de Flow comprobaron contenedor role=region/tabindex=0 y overflow-x auto. No screenshots ni inspección visual humana; mediciones DOM/browser no demuestran contraste completo ni todas las interacciones. No se probaron modals en seis combinaciones, catálogo poblado, plano con mesas, todos los gráficos con datos, ni todas las vistas de inventario.

### Pruebas y límites

| Comando | Resultado | Timeout |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest test/test_internal_style.py -q -s --tb=short` | 2 aprobadas, 119,52 s; matriz anterior | 300 s |
| `.venv/Scripts/python.exe -m pytest test/test_theme_contract.py test/test_phase4_public_site_contracts.py test/test_request_outage.py -q --tb=short` | 17 aprobadas, 8,05 s | 120 s |
| `node --check static/js/private-shell.js` y `node --check static/js/notification-feed.js` | sin errores | 120 s |

Selección anterior de theme/admin_user_editor/runtime/public_site: 10 aprobadas y 3 fallos, 7,51 s. Fallaron update administrativo, login con outage y API favoritos por respuesta 503; hooks de presencia/contexto ahora requieren datos adicionales respecto a mocks antiguos. Cambios concurrentes en app/context/company_access observados; no se alteraron pruebas existentes ni backend para ocultarlos. La selección posterior outage pasó, pero no reemplaza estos tres contratos fallidos: permanecen como límite de verificación de esta intervención.

Fallos responsive iniciales corregidos: status de notificaciones fuera del header 360; capa visualContract imponía 36,096px al h1 en 768; especificidad del shell mantenía rail 64px. Todos los assertions de ancho/altura/título/rail se mantuvieron. El wrapper existente responsive-layout crea table-responsive antes que private-shell; la prueba exige comportamiento accesible/overflow, no un nombre de clase artificial.

`git diff --check` comprobado sin errores de espacios, con avisos CRLF antes de actualizar esta sección; revalidación final al terminar. MCP discovery no expuso browser/subagentes; Edge local con Playwright ya instalado. Ningún commit, proveedor real, despliegue o certificación 100%. La base compartida cubre los grupos anteriores, pero la verificación exhaustiva de todas las vistas/estados solicitada queda pendiente; no se declara terminado ese alcance.

## Continuación funcional: Home, lotes y adicionales

Evidencia nueva del 19 de noviembre de 2026. Se implementaron tres áreas, sin certificar el 100% del plan maestro.

### Fase 13: Home integrado

- Nuevos `models/home_kitchen.py`, `views/home_kitchen.py`, `templates/home_kitchen.html`; registro en `app.py`, reconocimiento del blueprint privado en `templates/base.html` y enlace de navegación en `templates/partials/header.html`.
- `/home/`: despensa personal CRUD de lotes, cantidad entera, unidad base y vencimiento; consultas SQL filtradas por titular. Ediciones/eliminaciones comprueban propietario en servidor; no hay acceso administrador implícito a despensas ajenas.
- Recetas privadas con ingredientes/cantidades/unidades, porciones, minutos declarados y pasos editables. Fuente `user_declared`; borrador hasta confirmación explícita. No se generaron recetas con proveedor IA ni se atribuye verificación nutricional. Receta en plan pendiente no cambia silenciosamente: debe retirarse del plan antes de editar.
- Plan semanal con días/comidas y multiplicador de receta; lista de compras calculada desde ingredientes reales, asignando cada lote una sola vez y respetando vencimiento del día planificado. Enlaces al buscador existente del mercado, sin garantizar que comercialice ese ingrediente.
- Preparación confirmada descuenta lotes domésticos FEFO con lock por titular y transacción única; stock insuficiente y fallo de auditoría revierten todo. UUID idempotente, plan preparado una sola vez, historial con snapshot de receta y trazabilidad por lote. No permite preparar borradores.
- UI hereda `market/base.html` y shell privado con sidebar/nav; reutiliza clases de mercado. Ajuste de flex-wrap limitado a `.sr-home-kitchen` en tablet, sin colores ni cambios globales.
- Alcance pendiente Home: cámara/OCR y borradores IA de proveedor, sustituciones verificadas, sugerencias automáticas por restricciones y optimización de presupuesto. El registro de pasos del usuario es funcional, no un motor nutricional validado.

### Fases 8–10: lotes y adicionales

- `logic/inventory_lots.py`: múltiples lotes bajo el mismo ingrediente, rotación FEFO o FIFO y exclusión de vencidos; soporte necesario de registros de un lote ya persistidos. Entradas independientes con costo, vencimiento, fecha de recepción y UUID. Merma/conteo requieren lote específico; unidades incompatibles y merma excesiva rechazadas.
- Integración en `logic/market.py`, `models/market.py`, `views/market_kitchen.py`, `templates/market/kitchen.html`: disponibilidad suma lotes vigentes, venta reparte consumo entre lotes y registra asignaciones/costo real; cancelación restaura cada lote original, no un sustituto. Cotización, alertas y simulación consideran cantidad vigente; alerta individual de cada lote y compras/producción avanzadas siguen pendientes.
- `logic/order_addons.py`: nombres seleccionados se resuelven desde el catálogo servidor; precios en céntimos y stock entero obligatorio. Nombres inventados, duplicados, objetos con precios cliente y stock insuficiente rechazados. Sin declaraciones verificadas, los adicionales se bloquean para perfiles con restricciones, no se asumen seguros.
- Gestión de precio/stock por propietario en `/mercado/cocina/<rid>/adicional`, con validación de producto del negocio y auditoría. `logic/product_catalog.py` conserva stock declarado de adicionales.
- Carta QR permite seleccionar adicionales por porción; carrito muestra suma y nombres; `place_order` recalcula precios/stock, persiste desglose y revierte stock al cancelar. Precio esperado obsoleto revierte todos los descuentos. Costo de adicionales desconocido se representa como `None`, evitando margen ficticio. UI en `templates/salon/menu.html`, backend en `views/salon.py`.
- El mismo lock de negocio serializa ventas/configuración. Contención que alcanza lock_timeout se convierte en `MarketError` seguro y reintentable, sin ampliar timeout ni quitar exclusión concurrente.
- Pendiente: selección de adicionales fuera del carrito QR, declaraciones alimentarias detalladas/costos de complementos, pagos externos, gestión avanzada de compras y producción. No se hicieron cobros reales.

### Fases 17–18: evidencia exacta

Todas las selecciones DB usaron `SMARTRESTO_RUN_ISOLATED_DB=1` y fixtures actuales inspeccionadas: esquema QA UUID nuevo, tablas y secuencias exclusivas, comprobación FK interna y cursor protegido; `.env` solo cargado en memoria por fixture, nunca impreso/editado. No se ejecutaron scripts DB independientes.

| Comando `python -m pytest`, sufijo `-q --tb=short` salvo browser `-q -s --tb=short` | Resultado | Límite |
|---|---|---|
| `test/test_home_kitchen.py` última ejecución | 13 aprobadas, 85,66 s | 300 s |
| `test/test_home_kitchen.py test/test_order_addons.py` antes del último guard/snapshot Home | 20 aprobadas, 226,00 s | 300 s |
| `test/test_home_kitchen.py test/test_inventory_lots.py test/test_order_addons.py` previo a dos regresiones nuevas | 22 aprobadas, 156,70 s | 300 s |
| `test/test_market_transactions.py test/test_phase10_kitchen.py` tras corregir contención | 5 aprobadas, 75,73 s | 300 s |
| `test/test_inventory_lots.py test/test_phase10_kitchen.py` inicial | 7 aprobadas, 91,18 s | 300 s |
| `test/test_phase5_catalog.py test/test_phase7_personalization.py test/test_theme_contract.py` sin DB | 46 aprobadas, 7,19 s | 120 s |
| `test/test_home_browser.py` | 1 aprobada, 54,92 s | 120 s |

Los grupos repiten pruebas y no son un total único ni suite integral. Fallos intermedios corregidos: claves str/int del carrito de adicionales; contención de lock de la última plaza; overflow de cabecera Home en 768px (788px antes, 768px después). No se relajaron expectativas de stock, permisos, CSRF ni overflow.

Navegador real: MCP browser no disponible; Playwright Python instalado, Chromium administrado ausente, Edge local disponible sin instalar dependencias. `test/test_home_browser.py` inició servidor propio 127.0.0.1 en puerto libre asignado por SO, únicamente con fixture QA y cookie firmada de test; bloqueó toda salida HTTP externa. Verificó Home 360/768/1280, dark/light, sidebar, ancho sin overflow (360/768/1280 respectivos) y alta de avena con formulario CSRF real. Servidor propio cerrado en finally; no se tocó :5000. Sin screenshots, ni validación visual de todas las otras vistas ni contraste/accesibilidad integral. La verificación Home fue anterior al guard/snapshot backend final, que pasó pruebas DB posteriores.

### Estado de las demás fases

Fases 3, 4, 6, 7, 11, 12, 14 y 15: sin implementación nueva atribuible a esta continuación; estados históricos no equivalen a cierre. Fase 5 recibe stock de adicionales; no se completó multimedia/categorías. Fase 9 recibe consumo/restauración y precios del QR; multivendedor/pagos siguen pendientes. Fase 16: no se añadió historial persistente Copilot en esta continuación. Fase 17: permisos titular Home y propietario/producto en adicionales, auditoría transaccional; no certifica tenancy transversal. Fase 18: pruebas anteriores, no release, deploy, backup, AR ni suite integral.

Se preservaron modificaciones previas/concurrentes. No commits, cambios `.env`, escrituras public, proveedores ni pagos reales. `git diff --check` sin errores de espacios en la comprobación realizada, únicamente avisos CRLF. Archivos nuevos son módulos/tests solicitados, sin dependencias runtime nuevas.

## Implementación de esta sesión: fases 7, 9, 11 y 12

Esta sección es la evidencia más reciente. No certifica el cierre de fases 3–18 ni sustituye las brechas históricas.

### Cambios implementados

- Fase 7: el feed `for_you` admite coincidencias con preferencias declaradas en cold-start, identificadas como `personalization_basis=declared_preferences`. No inventa compras ni visitas; mantiene descubrimiento y filtros existentes. La vista menciona preferencias como fuente de selección.
- Fase 9: nueva pantalla `/mis-reservas` con estilos `sr-service`, `sr-list` y botones existentes, enlace desde puntos y cancelación POST con CSRF. Cancelación exclusiva del titular, lock de fila, estados/futuro validados, retry idempotente y auditoría atómica. La creación valida grupos enteros 1–20, fecha futura hasta 30 días y negocios suspendidos. La ruta de creación revalida la cuenta mediante `fresh_session_user`, no confía solo en el objeto de sesión legado.
- Fase 11: altas y configuración serializadas por negocio mediante advisory lock transaccional PostgreSQL; aceptación revalidada tras el lock. Lectura de turno con lock de fila para transiciones. Prueba concurrente de dos altas con códigos distintos y dos solicitudes del mismo usuario con un único turno activo. Vista pública consulta estado cada 15 segundos, evita requests solapados y pestañas ocultas, repinta mediante textContent y conserva estado ante errores de red. No demuestra comportamiento visual en navegador.
- Fase 12: cumpleaños serializado por usuario/año con comprobación de unicidad dentro de la transacción y auditoría sin fecha personal; opt-out explícito bloquea el beneficio. Visitas sin consumo pagado vigente dejan de aportar historial/insignias; reembolsos descuentan puntos históricos usados para nivel. Segmentos del negocio omiten usuarios con visitas privadas y exponen autorización de marketing explícita. No es todavía una política transversal de todos los consumidores de datos.
- Fases 17–18: regresiones cross-user/cross-business, rollback cuando falla auditoría, controles de grupo/fecha/suspensión y contratos HTTP. Fixture QA de fase 11 ahora configura secreto efímero de prueba sin relajar validación productiva.

### Pruebas recientes exactas

Todos los grupos DB usaron `SMARTRESTO_RUN_ISOLATED_DB=1`, el fixture inspeccionado que crea esquema aleatorio con tablas/secuencias exclusivas y cursor protegido. No se leyó/imprimió `.env`, no se corrieron scripts DB directos, servidores propios, proveedores, pagos o despliegue.

| Selección con `python -m pytest`, sufijo `-q --tb=short` | Resultado | Límite |
|---|---|---|
| `test/test_phase11_flow.py test/test_phase12_loyalty.py` inicial | 22 aprobadas, 233,87 s | 300 s |
| `test/test_phase11_flow.py` con nueva regresión HTTP | 11 aprobadas, 150,16 s | 300 s |
| `test/test_phase11_qa.py` tras secreto efímero | 5 aprobadas, 19,93 s | 120 s |
| `test/test_phase12_loyalty.py` última ejecución, incluye reservas y validaciones | 15 aprobadas, 162,53 s | 300 s |
| `test/test_phase7_personalization.py test/test_phase7_recommender.py test/test_theme_contract.py test/test_copilot_backend.py` | 91 aprobadas, 4,93 s; sin fixture DB | 120 s |

Son selecciones con pruebas repetidas, no un total único ni suite integral. Fallos intermedios: contrato cold-start anterior esperaba feed vacío (actualizado al nuevo requisito); test de reservas sin SECRET_KEY efímero (corregido); cinco tests QA usaban create_app sin secreto (corregidos en fixture local). Se ejecutaron nuevamente las selecciones afectadas con resultados anteriores. `git diff --check` se verificó durante la sesión sin errores de espacios, con avisos CRLF; no acredita cambios posteriores concurrentes.

### Estado por fase al terminar esta implementación

| Fase | Resultado de esta sesión / brecha pendiente |
|---|---|
| 3 | Requisitos y reporte leídos; sin implementación nueva atribuible. Fuentes externas y scheduler pendientes. |
| 4 | Sin implementación nueva; configuración independiente de sucursal y recorrido visual pendientes. |
| 5 | Sin implementación nueva; categorías/multimedia completas pendientes. |
| 6 | Sin implementación nueva; promociones por producto y rutas viales pendientes. |
| 7 | Cold-start implementado y probado; evaluación del ranking y desglose completo por factor pendientes. |
| 8 | Sin implementación nueva; adicionales cobrables y pagos separados pendientes. |
| 9 | Espacio cliente de reservas implementado/probado; carrito multivendedor y cobros externos pendientes. |
| 10 | Sin implementación nueva; lotes múltiples FEFO/FIFO y producción/compras pendientes. |
| 11 | Concurrencia de altas y transiciones, repintado público implementados; reserva física y carga sostenida pendientes. |
| 12 | Unicidad, opt-out, segmentos privados y reembolsos corregidos/probados; consentimientos transversales y reseña multidimensional pendientes. |
| 13 | Sin implementación doméstica nueva; despensa/recetas/planificador/lista pendientes. |
| 14 | Sin implementación nueva; GLB real y AR físico no probados. |
| 15 | Sin implementación BI nueva; alcance global y predicción validada pendientes. |
| 16 | 54 pruebas backend incluidas en selección de 91; sin historial persistente ni acciones nuevas. |
| 17 | Cuenta fresca en reservas y auditoría de cancelación/cumpleaños; tenancy transversal no certificada. |
| 18 | Selecciones modulares anteriores; sin suite integral, browser responsive 360/768/1280, dark/light, backup o deploy. |

El catálogo MCP consultado no expuso herramientas de subagentes ni navegador. No se ejecutaron ni tocaron los procesos Flask existentes de :5000. Estado inicial Git limpio; aparecieron cambios concurrentes ajenos en arquitectura, perfiles, empresas, radar, shell y Copilot durante el trabajo: se preservaron, no se ejecutaron sus scripts ni se atribuyen a esta sesión. Sin commits, borrados ni dependencias runtime nuevas. Ninguna fase se declara completa.

## Verificación modular posterior: fases 4–18

Esta sección sustituye el estado de «no atendidas» de la continuación anterior para los módulos aquí comprobados. Las pruebas verdes no equivalen al cumplimiento completo del plan.

### Seguridad y procesos

- Inspección inicial mediante `Get-CimInstance Win32_Process`: solo dos procesos Python de Flask en :5000, ningún pytest previo visible. No se terminó ningún proceso. Inspección posterior a la última prueba: solo Flask, ningún pytest visible. No acredita procesos no Python ni una finalización retrospectiva del intento anterior.
- Se releyeron `test/conftest.py`, `database/connection.py` y `database/metrics.py`. Se mantuvo la política existente: `.env` cargado por fixture en memoria; esquema QA aleatorio nuevo por sesión de pytest, seis secuencias propias y FK internas verificadas. No se reutilizó un identificador de esquema anterior porque la fixture lo genera por sesión; no se cambió la política para conectarse a public.
- Sin escrituras en public, DROP, scripts DB independientes, proveedores reales, pagos, invitaciones, scheduler o acceso a :5000. Los clientes HTTP utilizados son clientes Flask en proceso. No hubo validación visual con navegador ni dependencias runtime nuevas.

### Comandos y resultados

Todos los comandos usan `SMARTRESTO_RUN_ISOLATED_DB=1`, `python -m pytest`, prefijo `test/` para cada archivo y sufijo `-q --tb=short`. Los grupos son selecciones dirigidas, no suite completa; algunos repiten pruebas.

| Grupo | Archivos exactos | Límite | Resultado |
|---|---|---:|---|
| A: 4–5 | `test_phase4_sites.py test_phase4_publication.py test_phase4_public_site_contracts.py test_phase4_ai_quota.py test_phase5_catalog.py test_phase5_ai_nullable.py test_phase5_workbook.py test_phase5_flow.py` | 300 s | 51 aprobadas, 6,63 s |
| B: 6–8 | `test_phase6_catalog.py test_phase6_rbac.py test_phase7_recommender.py test_phase7_personalization.py test_phase8_salon_rules.py test_phase8_salon_db.py test_phase8_geo.py` | 300 s | 77 aprobadas, 100,42 s |
| C: 9–11 | `test_market_transactions.py test_commerce_extensions.py test_phase10_kitchen.py test_phase11_flow.py test_phase11_qa.py` | 300 s | 20 aprobadas, 237,97 s |
| D: 12, 14–17 | `test_phase12_loyalty.py test_advanced_phases.py test_intelligence_unit.py` | 300 s | 31 aprobadas, 231,15 s |
| E: regresiones y 16–18 | `test_phase4_public_site_contracts.py test_phase6_catalog.py test_copilot_backend.py test_content_filter.py test_moderation_explain.py test_theme_contract.py test_connection_pool.py` | 120 s | 135 aprobadas, 9,44 s |
| F: 3, 17–18 | `test_phase3_discovery.py test_phase3_worker.py test_phase3_sources_claims.py test_phase3_review_update.py test_account_security.py test_profile_recovery_unit.py test_runtime_contracts.py test_platform_health.py` | 300 s | 49 aprobadas, 1 fallo, 108,68 s |
| G: confirmación posterior y 9/15 | `test_account_security.py test_phase4_public_site_contracts.py test_phase6_catalog.py test_phase9_bi.py test_market.py` | 300 s | 38 aprobadas, 103,17 s |

El fallo F fue `test_account_recovery_and_second_factor`: esperaba 200 en el replay del código guardado. `views/auth.py::recover` usa POST/Redirect/GET y devuelve 302 tanto al rechazar como al aceptar, pero con destinos distintos. Se actualizó `test/test_account_security.py` para exigir redirección a recuperación en el rechazo y comprobar criptográficamente que la contraseña nueva permanece y la anterior no se restaura. No se relajó el control de código de un solo uso. Grupo G confirma la prueba reparada. El fallo histórico de colores no se reprodujo: `test_theme_contract.py` pasó en E; no se atribuyen cambios de estilos concurrentes a esta ejecución.

### Matriz actual por fase

| Fase | Evidencia nueva | Corrección / cobertura | Pendiente frente al plan |
|---|---|---|---|
| 3 Discovery | F; 18 pruebas dirigidas de la ejecución anterior | Recuperación de cambios en referencias/procedencia; worker con fuentes vencidas y fallos simulados, invitaciones y revisión simuladas | Consulta externa y entrega real no probadas; tarea periódica no activada |
| 4 Sites | A, E, G; lectura `views/business_sites.py` | Se corrigió exposición pública de `/portal-media/<id>` de negocios suspendidos: ahora usa `visible_restaurant`. Nueva regresión HTTP de suspensión y reactivación. Borradores, publicación simulada, slugs, logos y cuotas | Configuración independiente completa de sucursal, horarios semanales, despliegue y recorrido visual |
| 5 Catalog | A; lectura `test_phase5_flow.py` | Normalización, alérgenos, disponibilidad, confirmación idempotente e importación Excel con repositorio simulado | CRUD categorías completo, vídeo, audio servidor y proveedor multimodal real; persistencia real de importación no acreditada por A |
| 6 Search | B, E, G; lectura `views/main.py` y `utils/functional.py` | Corrección de `matching_dishes`: aplica presupuesto por producto y restricciones al mismo plato. Antes platos distintos podían satisfacer condiciones separadas. Nueva regresión HTTP comprueba presupuesto y combinación de restricciones | Precio promedio del negocio sigue filtrándose además del producto; promociones individuales y rutas viales completas |
| 7 Recommender | B; lectura `logic/phase7_recommender.py` | Preferencias, ranking, restricciones y personalización existentes comprobadas por pruebas | Feed cold-start, explicación exhaustiva reproducible, clima/proveedor real y evaluación de calidad |
| 8 Salon | B | Reglas, geolocalización y persistencia de mesas/sesiones sobre QA | Adicionales cobrables, pagos separados y recorrido QR responsive real |
| 9 Orders | C, G; lectura `test_market_transactions.py` | Último turno concurrente, retry idempotente, cancelación/restauración de stock, webhook con proveedor simulado y recompensa | Carrito multivendedor, espacio completo de reservas y cobro/reembolso externo real |
| 10 Inventory | C; lectura `models/market.py` y `test_phase10_kitchen.py` | Insumos por venta, alertas/lotes existentes y métricas de producción; aislamiento PostgreSQL | Múltiples lotes por ingrediente, FEFO/FIFO y órdenes de producción/compras proveedor |
| 11 Flow | C; lectura `models/flow.py` | Cola, espera y asignación existentes; aforo y contratos de seguridad | `join` consulta cola antes de crear sin lock específico: riesgo concurrente de códigos/turnos duplicados no corregido ni probado aquí. Repintado público automático y reservas físicas pendientes |
| 12 Loyalty | D; lectura `models/loyalty.py` | Puntos por pagos/visitas, reembolso, cumpleaños, reseñas y segmentación PostgreSQL | Preferencias de privacidad no aplicadas transversalmente; criterios de badges/visitas tras reembolsos requieren unificación; cumpleaños consulta unicidad antes de transacción, riesgo concurrente pendiente |
| 13 Home | Búsqueda en `views/`, glob `**/*home*.py`, manifiesto | No se encontró backend de despensa doméstica; `home_kitchen` es declaración del manifiesto y `ecosystem/home.html` no es despensa | Sin pruebas de fase 13 ni implementación nueva: despensa, recetas domésticas, planificación y lista de compras no integradas |
| 14 Immersive | D; lectura `logic/immersive.py` | Dimensiones finitas, propietario no auto-verifica escala, moderación y visibilidad por estado | La prueba usa bytes sintéticos, no valida GLB real ni AR físico; generación IA, variantes y versiones pendientes |
| 15 Analytics | D, G | Datos privados por negocio, ingresos/margen, reembolsos, pronóstico condicionado a historial; métricas de servicio | BI global completo, predicción validada, visitantes únicos y causalidad de campañas |
| 16 Copilot | D, E; lectura pruebas backend | Historial validado en request, contexto servidor, confirmación, replay y promoción obsoleta | Operaciones completas por rol e historial persistente; IA externa no probada |
| 17 Security | D, E, F, G | OTP, revocación, permisos, CSRF, moderación y recuperación single-use; prueba de recuperación reforzada | Tenancy transversal, cuotas/proveedores completos, auditoría histórica y revisión documental oficial |
| 18 QA | C, E, F, G | Todos los comandos terminaron dentro de 120/300 s; prueba de concurrencia acotada, seguridad y tokens de tema. `git diff --check` sin errores | No suite completa nueva, carga sostenida, pruebas visuales/responsive reales, backup/restore, pentest ni deploy |

Cambios propios: `views/business_sites.py`, `views/main.py`, `test/test_phase4_public_site_contracts.py`, `test/test_phase6_catalog.py`, `test/test_account_security.py` y este reporte. Se preservaron cambios concurrentes observados durante la ejecución. Ninguna fase se certifica completa. No hay fallos pendientes en los últimos grupos ejecutados; eso no borra las brechas ni acredita pruebas no seleccionadas.

## Continuación solicitada desde Fase 3 (ejecución acotada)

- Fuente nueva leída completa: `pasted_1795096047303_dl2pe69.txt` (919 líneas). Se inspeccionaron estado Git, fixture y protección SQL antes de ejecutar pruebas; se preservaron modificaciones previas y concurrentes. No se leyó ni imprimió el contenido de `.env`.
- Fase 3: corrección funcional en `models/discovery.py::ingest`. Antes solo se comparaba `data`: una carta nueva, medios, canales o procedencia modificados podían perderse silenciosamente. Ahora se comparan esos campos y las evidencias sin su timestamp de recuperación; los cambios quedan en `proposed_update` sin publicación automática. La regresión nueva `test/test_phase3_discovery.py::test_refresh_tracks_menu_changes_without_publishing` comprueba persistencia PostgreSQL, recuperación idéntica, carta modificada y aceptación administrativa como borrador.
- Evidencia ejecutada: `SMARTRESTO_RUN_ISOLATED_DB=1`, `python -m pytest test/test_phase3_discovery.py -q --tb=short`: **18 aprobadas en 16,01 s**. La fixture crea esquema QA aleatorio con secuencias propias y verifica ausencia de FK externas. No se ejecutaron scripts independientes de DB ni limpieza de public.
- Fase 3 pendiente: no se ejecutó consulta externa, envío de invitaciones ni scheduler real. Se inspeccionaron generación de invitaciones, deduplicación y worker; inspección no equivale a prueba funcional de todos esos flujos.
- Fase 4: inspección de `models/business_site.py`; sin implementación ni verificación nueva. Fases 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 y 17: **no atendidas funcionalmente en esta continuación**. Sus estados históricos permanecen como evidencia anterior, no certificación actual.
- Fase 18: intento de suite completa `python -m pytest test -q --tb=short` con aislamiento autorizado. El proceso excedió 1800 s después del indicador 54%, con dos marcadores de fallo; no produjo resumen ni diagnósticos finales. La herramienta indicó además que la limpieza del proceso no terminó antes de su límite de seguridad: no se acredita que todo proceso hijo haya finalizado. No se certifica suite verde, ni se relajan tests.
- Limitaciones: catálogo MCP sin herramientas de creación/delegación de subagentes (búsquedas task/agent vacías); no fue posible cumplir auditorías delegadas. No hubo validación visual, AR, cobros, despliegue ni pruebas externas. No se hicieron commits ni borrados. Las fases 3–18 **no están completadas**.

## Continuación: implementación y pruebas reales

- Fase 1: se bloqueó autocommit en `database.connection.connection` durante aislamiento. La fixture `test_database` también bloquea nuevas llamadas directas a `psycopg.connect` que no utilicen el cursor protegido y el search_path exclusivo. No cubre conexiones previamente abiertas, alias importados previamente, `Connection.connect`, cursores alternativos ni SQL arbitrario; no constituye aislamiento global de privilegios.
- Fase 2: se implementaron `models/membership.py`, `views/business_access.py`, formularios de personal y verificación empresarial y pruebas PostgreSQL. Ruta `/owner/acceso/<rid>` permite asignar/revocar funciones por establecimiento sin alterar el rol global. El salón revalida estas asignaciones y la cuenta activa en servidor; una revocación explícita prevalece sobre equipos legados. No se aplicó todavía esta política a todos los módulos ni se unificó con sr_memberships.
- Fase 2: solicitud documental con RUC y referencia HTTPS, revisión exclusiva de administrador con justificación, bloqueo de duplicados pendientes/revisión repetida y auditoría transaccional. Aprobar identidad no publica el restaurante. Son revisión manual y referencia documental, no verificación oficial ni almacenamiento seguro de documentos acreditado.
- Copilot: el fallo 400/403 era una prueba desactualizada frente al contrato explícito `mode=full`, confirmado por backend, frontend y pruebas dirigidas. Se actualizaron solamente los payloads de integración; se conservaron los controles y las expectativas 403/404/409 y de confirmación.
- Fase 5: las pruebas unitarias de importación ahora usan contexto Flask para tokens firmados; la expectativa de hojas incorpora Restaurantes y Ejemplos, agregados por cambios concurrentes. No se quitaron comprobaciones de plantilla vacía o importación idempotente.
- Primera suite completa: **533 aprobadas, 1 fallo**, 1437,59 s. Se corrigieron colores literales de ofertas usando tokens existentes.
- Segunda suite completa: **559 aprobadas, 7 fallos y 4 subtests aprobados**, 1349,38 s. Fallos diagnosticados: endpoints de plantilla desalineados durante cambios concurrentes (perfil y análisis), contexto Flask ausente en dos pruebas Excel y expectativa de hojas desactualizada. Los endpoints ya estaban corregidos por cambios simultáneos al volver a leerlos; no se sobrescribieron.
- Verificación dirigida posterior: **44 aprobadas**, 229,06 s, con `python -m pytest test/test_phase5_flow.py test/test_phase5_workbook.py test/test_detail_personalization.py test/test_business_access.py test/test_advanced_phases.py -q --tb=short` y `SMARTRESTO_RUN_ISOLATED_DB=1`.
- Última suite completa: **604 aprobadas, 2 fallos y 4 subtests aprobados**, 1375,46 s, comando `python -m pytest test -q --tb=short`, `SMARTRESTO_RUN_ISOLATED_DB=1`. Fallos actuales: recuperación devuelve redirección 302 frente a expectativa 200 tras cambios simultáneos; nuevo `static/css/copilot-wake.css` contiene colores literales. No se certifica suite verde ni se atribuyen cambios concurrentes a esta ejecución.
- Se instaló Playwright como dependencia de pruebas del entorno, sin modificar requirements ni dependencias runtime. No se abrió ni modificó :5000, .env o datos vivos. Los esquemas QA se conservaron.
- Fases 1 y 2 siguen parciales: falta tenancy transversal canónica, cierre UI responsive de formularios nuevos y verificación oficial. Fases 3–18 no se completaron; solamente se repararon contratos de pruebas y estilos relacionados con fallos de suite.

## Ejecución actual: aislamiento y verificación

Esta ejecución implementó el primer prerrequisito de Fase 1, no las 18 fases completas. `docs/vision/fases.md` contiene solamente dos líneas de avance; los requisitos completos se leyeron del adjunto `pasted_1795088036226_vn12mmu.txt`.

### Fase 1: en progreso

- `test/conftest.py` requiere `SMARTRESTO_RUN_ISOLATED_DB=1`, obtiene la conexión del `.env` raíz en memoria y crea un esquema aleatorio exclusivo `smartresto_qa_<UUID>` por sesión. No modifica `.env`.
- Se crean tablas mediante DDL original transformado al esquema exclusivo, nunca mediante copias de tablas ni defaults heredados. Se comprobaron las seis secuencias identity de app_records, negocios, sucursales, membresías, auditoría y decisiones IA; todas pertenecen al esquema aislado. Las claves foráneas no apuntan fuera de ese esquema.
- `database/connection.py` y `database/metrics.py` interceptan las consultas del cursor de aplicación: redirigen referencias legadas conocidas `public.app_records`, `public.sr_*` y `public.ai_decisions` al esquema autorizado y bloquean referencias públicas restantes, DROP, TRUNCATE y COPY. El search_path no incluye public. Esto cubre el cursor compartido, no scripts independientes con conexiones directas; esos scripts no se ejecutaron.
- `service_db` ya no permite limpieza basada solamente en el nombre de la base. Exige el esquema aislado y su DELETE pasa por el cursor protegido. Los esquemas de pruebas se conservan; no se ejecutó DROP ni limpieza de public.
- Se corrigió una expectativa incorrecta de la prueba del pool: PostgreSQL tiene un timeout predeterminado de 2 minutos, no necesariamente cero. La prueba verifica ahora que el valor previo se restaura tras la transacción.
- Pendiente: tenancy central por membresías aplicada a todas las rutas, gestión canónica transversal de sucursales, comprobación visual responsive y seguridad del aislamiento frente a SQL arbitrario. La transformación SQL no sustituye un usuario PostgreSQL de privilegios restringidos.

### Fase 2: verificación parcial, sin nuevas funciones de personal

- Las pruebas dirigidas existentes de recuperación, segundo factor y edición administrativa parcial se ejecutaron junto con las de plataforma sobre PostgreSQL aislado.
- Pendiente implementar y comprobar gestión integral de personal por sucursal, permisos efectivos y verificación empresarial/documental. No se certifica Fase 2 completa.

### Evidencia actual

- Comando dirigido: `python -m pytest test/test_connection_integration.py test/test_account_security.py test/test_phase1_audit_context.py test/test_phase1_readiness_contract.py test/test_phase2_admin_profile_integrity.py test/test_platform_foundation.py -q --tb=short`, con `SMARTRESTO_RUN_ISOLATED_DB=1` y `DATABASE_URL` vacío en el proceso: **19 aprobadas en 103,10 segundos**.
- La suite completa no terminó: faltan Playwright en el entorno para dos archivos de navegador. Excluyéndolos y usando `-x`, terminó con **30 aprobadas y 1 fallo** en `test_advanced_phases.py::test_copilot_confirmation_actor_scope_and_replay`: la petición del comensal devolvió 400 cuando se esperaba 403. No se corrigió ese fallo de Fase 16 en esta ejecución.
- Un intento anterior de suite ampliada fue interrumpido por timeout; no cuenta como suite aprobada. Se instaló `qrcode==8.2`, ya declarado en requirements.txt; no se añadieron dependencias al proyecto.
- No se tocó el servidor :5000 ni se ejecutaron pagos, proveedores externos, pruebas AR o despliegue. No se modificaron datos/tablas/secuencias de public mediante los comandos de esta ejecución.
- Fases **3–18 no trabajadas funcionalmente en esta ejecución**. Sus estados históricos de la tabla siguiente no son nuevas verificaciones.

## Dictamen ejecutivo

El sistema contiene una base Flask integrada y varios módulos funcionales, pero **ninguna de las 18 fases puede certificarse como terminada** con el criterio del plan maestro: interfaz, backend, persistencia/migraciones, integraciones aplicables y pruebas. La clasificación de esta auditoría es **17 fases parciales y la fase 13 sin integración doméstica**. “Parcial” no significa que nada funcione: significa que hay código conectado, pero faltan entregables, validación de extremo a extremo o partes del alcance.

El archivo `resumenfases.md` no existía en el repositorio al iniciar esta revisión. Este documento se creó en `docs/vision/` para dejar el resultado solicitado.

| Fase | Estado | Dónde localizarla / qué se ve | Resultado y brecha principal |
|---|---|---|---|
| **1. Arquitectura general** | Parcial | `app.py`; `core/`; `database/`; `/api/platform/manifest`, `/api/platform/health`, `/api/platform/me`; `templates/base.html` | Flask modular y PostgreSQL están presentes. Se agregaron contexto de plataforma por solicitud, scopes de roles legados y un health check de auditoría ligado a la base; los eventos ahora usan el request ID del servidor y guardan el business ID del contexto. La persistencia sigue siendo híbrida en `app_records`; el esquema `sr_*` y la validación central de membresías/tenancy aún no están verificados transversalmente. |
| **2. Usuarios, roles y perfiles** | Parcial | `/auth/register`, `/auth/profile`, `/admin/users`; `views/auth.py`, `views/admin.py`, `core/profile.py`, `templates/auth/profile_content.html`, `templates/admin/users.html` | Hay autenticación, preferencias, consentimientos, edición administrativa y suspensión en backend. El formulario ya respeta el contrato de perfil/rol/estado; la edición parcial del perfil ahora preserva preferencias, restricciones, presupuestos y consentimientos existentes, y la API rechaza correos inválidos. Siguen pendientes la asignación integral de personal y roles por sucursal, la verificación documentada de identidad empresarial y una política central aplicada uniformemente. |
| **3. Descubrimiento automático** | Parcial | `/admin/discovery`, APIs `/admin/api/discovery/*`; `views/discovery.py`, `logic/business_radar.py`, `utils/discovery_sources.py`, `templates/discovery/dashboard.html` | Hay fuentes configurables, evidencias/procedencia, revisión, duplicados, reclamos e invitaciones. No se verificó una consulta externa completa ni la activación efectiva del trabajo periódico. La documentación local discrepa sobre si la tarea diaria está registrada; debe comprobarse en el Programador de tareas de Windows. |
| **4. Portal empresarial** | Parcial | `/owner/sites`, `/negocio/<slug>`, `/negocio/<slug>/sucursal/<id>`; `views/business_sites.py`, `templates/sites/editor.html`, `templates/sites/public.html` | Editor, borrador/publicación, SEO, medios, carta, promociones y propuestas IA están conectados en código. Se corrigieron tres discrepancias visibles: WhatsApp se conserva y aparece como enlace público, el editor ya no ofrece SVG no soportado y el vídeo de portada requiere controles del usuario y no usa autoplay. Quedan pendientes contenido/configuración independiente por sucursal, horarios semanales, publicación/despliegue público y validación visual completa. |
| **5. Catálogo y registro inteligente** | Parcial | `/owner/catalog`, `/owner/api/catalog/<rid>`; `views/catalog.py`, `models/catalog.py`, `utils/catalog_workbook.py`, `templates/catalog/dashboard.html` | Hay borradores revisables, productos, recetas por oferta, importación Excel, foto y dictado de voz en navegador. No se encontró gestión CRUD de categorías desde el editor; la voz envía transcripción del navegador (no audio al servidor), no hay carga de video y faltan pruebas de extremo a extremo de los flujos de foto/voz/Excel y proveedor real. |
| **6. Marketplace y búsqueda** | Parcial | `/explorar`, `/api/search`, `/api/ai/interpret`, `/mercado/`; `views/main.py`, `views/market.py`, `utils/functional.py`, `templates/catalog/explore.html`, `templates/market/browse.html` | Búsqueda, filtros, comparación, favoritos, mapa y ofertas están conectados. En búsqueda general, el presupuesto se aplica al precio promedio del negocio; no necesariamente elimina de `matching_dishes` un plato cuyo precio exceda el límite. El filtro de promociones no busca condiciones de ofertas individuales; mapas no calculan ruta/tiempo vial. |
| **7. Recomendador** | Parcial | `/recomendaciones`, `/api/recomendaciones`, `/api/recomendaciones/contexto`; `logic/phase7_recommender.py`, `views/recommendations.py`, `templates/recommendations.html` | El ranking usa preferencias y señales disponibles y presenta motivos. El feed “Para ti” necesita evidencia de compras o búsquedas; una persona nueva con preferencias guardadas puede ver descubrimiento, pero no recomendaciones personalizadas en ese feed. La explicación no presenta desglose reproducible por factor. |
| **8. Carta QR y mesas** | Parcial | `/mesa/<token>`, `/owner/salon/<rid>`, `/salon/<rid>`; `views/salon.py`, `models/salon.py`, `logic/salon.py`, `templates/salon/` | QR por mesa, carta, sesión, solicitudes, división, estados y limpieza existen. Se corrigió un defecto del plano: coordenadas válidas `0%` ya no se confunden con “sin posición”. Los adicionales se muestran pero no se agregan/cobran en el carrito; el QR es por mesa y la jerarquía no es relacional específica. |
| **9. Pedidos, reservas y pagos** | Parcial | `/mercado/`, `/mercado/carrito`, `/mercado/pedidos`, `/mesa/<token>/pedido`, rutas de pago y cocina; `models/market.py`, `utils/market_payments.py` | Compra, estados, reservas, cupones, stock, reembolsos y webhook están implementados. Un carrito no permite combinar negocios; la reserva no tiene un espacio completo del cliente para revisar/cancelar; la división de mesa no acredita cobros separados. No se realizó un cobro real con Mercado Pago. |
| **10. Cocina e inventario** | Parcial | `/mercado/cocina/<rid>`; `views/market_kitchen.py`, `models/market.py`, `logic/market.py`, `templates/market/kitchen.html` | Inventario, recetas por oferta, descuento de insumos por venta, merma, simulador y alertas están conectados. Se maneja un lote vigente por insumo, no varios lotes ni FEFO/FIFO; producción es principalmente un registro al publicar oferta, sin orden de producción real. No hay compras a proveedor ni predicción de reposición por ingredientes. |
| **11. SmartResto Flow** | Parcial | `/cola/<rid>`, `/salon/<rid>/cola`, `/salon/<rid>/aforo.json`; `views/flow.py`, `models/flow.py`, `templates/flow/` | Cola, estimación, aforo y asignación a sesión real existen. El estado JSON no actualiza/repinta automáticamente la cola pública; falta estado de reserva física en el aforo y las notificaciones no cubren de forma proactiva a todos los turnos. |
| **12. Fidelización y reputación** | Parcial | `/puntos`, `/owner/puntos/<rid>`, `templates/loyalty/`; `models/loyalty.py`, `views/loyalty.py` | Puntos por compras/visitas verificadas, niveles, insignias, reseña y segmentos están conectados. Algunos controles de privacidad de fidelización se guardan pero no gobiernan las funciones asociadas; la reseña no separa plato/atención/ambiente y no ofrece carga de fotos en la pantalla. |
| **13. SmartResto Home** | **No integrada** | `core/platform_manifest.py` solo declara el nombre/capacidad; no se halló ruta, modelo o plantilla de despensa doméstica | La cocina empresarial y el plan semanal de ofertas del marketplace no equivalen a despensa personal ni a recetas para preparar en casa. No se halló captura de alimentos, alertas domésticas, planificador de comidas, lista de compras ni conexión de ingredientes faltantes con delivery. |
| **14. 3D y realidad aumentada** | Parcial | `/experiencias/negocio/<rid>/modelo`, `/mercado/oferta/<id>`, `/experiencias/modelos/<id>`; `utils/dish_model.py`, `logic/immersive.py`, `templates/market/dish.html`, `static/js/dish-model.js` | Carga/validación GLB, revisión administrativa, visor y soporte condicionado de AR existen. No se probó colocación física en dispositivo AR; no se halló generación de modelos GLB por IA a partir de fotos, gestión avanzada/versiones de modelos ni ajuste paramétrico de porciones. |
| **15. Analítica y predicción** | Parcial | `/inteligencia`, `/api/inteligencia`, `/admin/api/bi/overview`; `analytics/intelligence.py`, `analytics/metrics.py`, `templates/intelligence.html` | Métricas privadas por negocio y algunas previsiones están conectadas. El panel administrador no reúne todos los indicadores del plan; las previsiones son medias históricas descriptivas, no IA entrenada ni alertas fiables de agotamiento. No se acreditan visitantes únicos ni causalidad de campañas. |
| **16. SmartResto Copilot** | Parcial | `/copilot`, `/api/copilot/chat`, `/api/copilot/actions`; `views/copilot.py`, `templates/copilot.html`, `static/js/copilot.js` | El contexto se decide en servidor y una actualización promocional exige confirmación y auditoría. El chat no conserva conversación y la única acción confirmable principal es el texto promocional; no ejecuta el conjunto de operaciones por rol del plan. No se atribuyen al Copilot funciones que pertenecen a rutas separadas de IA. |
| **17. Administración y seguridad** | Parcial | `/admin/users`, `/admin/moderation`, `/admin/confianza`, rutas de reclamaciones; `views/admin.py`, `views/trust_center.py`, `utils/audit.py` | Hay gestión de usuarios, moderación, incidencias, duplicados, auditoría y controles de sesión. Se corrigió el contrato roto del editor de usuarios; ahora la interfaz permite perfil, rol y estado y ya no presenta un cambio de contraseña que el endpoint rechazaba. Faltan consola de proveedores/cuotas, verificación documental completa, búsqueda histórica amplia de auditoría y cobertura uniforme de permisos/moderación. |
| **18. Pruebas, optimización y despliegue** | Parcial | `test/`, `/api/platform/health`, `/admin/api/performance`, `README.md` | Existen pruebas de rutas, reglas, concurrencia acotada, seguridad y responsive; health check y métricas en memoria no son un sistema de monitoreo productivo. No se halló un proceso de release/CI-CD, backup/restore probado, carga sostenida, prueba de penetración completa ni manual operativo/despliegue. |

## Correcciones realizadas y comprobadas

1. **Edición de usuarios:** `templates/admin/users.html` enviaba `name`, `email` y `password` en la raíz, mientras `views/admin.py` acepta `profile`, `role` y `status`. El modal ahora usa el contrato del backend, permite cambiar el estado y no ofrece un campo de contraseña que la ruta no implementa. La API se probó con datos simulados, sin base de datos.
2. **Plano de mesas:** `templates/salon/desk.html` usaba filtros Jinja que trataban `0` como falso. Ahora acepta X/Y igual a cero y excluye coordenadas ausentes.
3. **Portal de marca:** `models/business_site.py` permite `wa.me`; `templates/sites/public.html` muestra enlaces sociales seguros; el editor anuncia solo PNG/JPG/WebP, que son los formatos que valida el servidor; el vídeo inmersivo tiene controles, no se reproduce automáticamente y no queda en bucle. Se añadieron estilos de enlaces con foco visible.
4. **Fundación de plataforma:** `core/platform_context.py` reconoce scopes de `user` y `owner`; `app.py` expone el contexto en `g` para cada petición; `/api/platform/health` ya no informa auditoría disponible si la base está caída; `utils/audit.py` usa el request ID generado por servidor y registra el business ID disponible en el contexto.
5. **Perfil administrativo de Fase 2:** `views/admin.py` fusiona los cambios permitidos con el perfil existente y valida los mismos campos con `core/profile.py`, evitando borrar preferencias y guardar emails mal formados. Dos regresiones se observaron fallar antes del cambio.

## Gantt del documento APF3

**No: el Gantt existente no cubre todas las fases restantes.** El capítulo `04_plan_trabajo.typ` agenda nueve semanas relativas (semanas 10–18) con hitos M0–M7 para el MVP de descubrimiento/recomendación, autenticación y catálogo. No contiene una fila por cada fase 1–18 ni estima el trabajo pendiente de todos los módulos. El texto del propio capítulo lo presenta como alcance MVP, no como cronograma de ejecución de los 18 dominios.

El plan maestro propone estas olas de secuencia, que sirven como cobertura de alcance pero **no son fechas ni duraciones estimadas**:

| Ola sugerida | Fases | Énfasis |
|---|---:|---|
| 1 | 1–6 | Plataforma, perfiles, descubrimiento, portal, catálogo y marketplace |
| 2 | 7–11 | Recomendación y operación presencial/comercial |
| 3 | 12–16 | Fidelización, cocina en casa, 3D, analítica y Copilot |
| 4 | 17–18 | Seguridad global, QA integral y despliegue |

No se debe representar esta secuencia como un Gantt temporal definitivo hasta que el equipo confirme responsables, disponibilidad, esfuerzo, dependencias, costos y fecha objetivo. Para terminar un Gantt real de fases restantes, primero hay que estimar esos datos; el Gantt actual puede conservarse como cronograma del MVP, claramente separado del plan maestro.

## Verificación y límites de esta auditoría

- Las regresiones se añadieron primero y se observaron fallar: dos casos iniciales para edición/posición y cuatro para los contratos del portal. Después de los cambios, las pruebas focalizadas de edición, plano, portal y publicaciones terminaron con **22 aprobadas**.
- Las pruebas focalizadas nuevas/existentes de plataforma, permisos, perfil y auditoría terminaron con **17 aprobadas**; sus regresiones se observaron fallar antes de corregir.
- Los contratos dirigidos de edición administrativa parcial y correo de Fase 2, junto con edición de usuario, permisos y perfil, terminaron con **11 aprobadas**; las dos regresiones nuevas fallaron antes de la corrección.
- La suite completa más reciente, ejecutada con `DATABASE_URL`, `SMARTRESTO_TEST_DATABASE_URL` y claves de proveedores vacías antes de importar la aplicación, terminó con **430 aprobadas y 70 omitidas**. No se conectó a Supabase, al servidor local ni a proveedores externos; las pruebas PostgreSQL que necesitan una base desechable no quedaron verificadas en esta ejecución.
- Se compilaron con Jinja las plantillas modificadas: `admin/users.html`, `salon/desk.html`, `sites/editor.html` y `sites/public.html`. La compilación Python y `git diff --check` de los archivos corregidos terminaron correctamente.
- **No se hizo un recorrido visual con navegador** durante esta auditoría ni se verificaron cobros, correo/SMS, IA externa, tarea programada del radar o AR en dispositivos. Las referencias a plantillas indican dónde está codificada la UI, no una confirmación de que esté publicada o accesible en producción.
- Los reportes XML históricos del repositorio se trataron como evidencia anterior, no como resultado de esta ejecución; el resultado actual verificable es la suite local segura indicada arriba.
