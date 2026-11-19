= Desarrollo preliminar: demo, simulación y arquitectura

== La vertical que se puede explicar en la sustentación

El corte actual permite presentar una vertical web concreta: el visitante abre una portada de descubrimiento, consulta establecimientos aprobados, introduce criterios y revisa una ficha; un usuario autenticado puede guardar favoritos, y un empresario dispone de formularios para gestionar cartas. El backend ejecuta controladores Flask, utiliza reglas de recomendación y consulta datos PostgreSQL a través del repositorio. El alcance verificable de esta demo debe quedar separado de los flujos de compra o de proveedores que necesitan configuración real.

La portada `GET /` se implementa en `views/main.py::index`; consulta restaurantes aprobados, categorías y estadísticas, y renderiza `templates/index.html`. El buscador `GET /api/search` y la evaluación `GET /api/restaurant/<id>/evaluate` se encuentran más adelante en el mismo módulo. La pantalla de detalle usa `/restaurant/<restaurant_id>`. Las funciones de filtros y enriquecimiento se apoyan en `utils/functional.py` y `utils/geo.py`; las reglas se delegan en `logic/recommender.py` y `logic/hybrid_recommender.py`. El resultado visible es una grilla de tarjetas y controles de filtro, no una recomendación generada desde un LLM en cada búsqueda.

La autenticación se concentra en `views/auth.py`. El login valida credenciales y límites de intentos, revalida al usuario, crea una sesión mínima y decide el destino según rol. Registro normaliza los datos y limita el rol público a comensal o empresario. Recuperación presenta instrucciones genéricas y aplica códigos temporales si existe configuración de entrega. Las capturas QA muestran el aspecto de login y registro, pero no identifican navegador, commit ni fixture utilizada; por eso el informe no las usa como prueba actual de una transacción con PostgreSQL.

== Mapa del flujo de búsqueda y recomendación

#figure(
  table(
    columns: (1.5fr, 0.55fr, 1.8fr, 0.55fr, 2fr),
    stroke: none,
    inset: (x: 6pt, y: 7pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Etapa*], [*→*], [*Código principal*], [*→*], [*Salida al usuario*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Búsqueda y filtros], [→], [`static/js/search.js` y ruta de búsqueda de `views/main.py`], [→], [Parámetros de búsqueda y tarjetas con resultados.],
    [Controlador], [→], [`views/main.py` valida entrada y coordina modelos.], [→], [JSON o plantilla HTML.],
    [Ranking/compatibilidad], [→], [`logic/recommender.py`, `logic/hybrid_recommender.py`, helpers geográficos.], [→], [Orden, coincidencias y justificaciones declaradas.],
    [Persistencia], [→], [`models/`, `database/repository.py`, `database/connection.py`.], [→], [Restaurantes, categorías, platos y relaciones cargados.],
    [Presentación], [←], [`templates/index.html`, `templates/restaurant_detail.html` y CSS.], [←], [Nombre, ubicación, categoría, carta y acciones disponibles.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Secuencia de la consulta pública descrita por código],
) <fig-demo-search-flow>

Para una demo repetible, el equipo debe utilizar una base desechable o fixtures controlados, registrar el caso de prueba y no introducir restaurantes ficticios en el entorno operativo. Una recomendación aceptada debe estar vinculada a entradas identificables: preferencia, restricción, presupuesto o zona. Si el sistema no conoce un ingrediente o el cálculo falla, la pantalla debe mostrar un estado seguro o un resultado explícitamente “no evaluado”, no asumir compatibilidad.

== Evidencia visual disponible

La captura de escritorio de acceso muestra un panel gastronómico oscuro con tratamiento volumétrico y una zona de formulario. El diseño usa el concepto visual solicitado para SmartResto —realismo 3D suave—; el código de sitios empresariales también indica esa dirección estética en el prompt de propuesta de marca. La captura se conserva como evidencia de interfaz y no identifica un modelo 3D escaneado ni que se haya medido su escala.

#figure(image("../assets/login-1440-dark.png", width: 100%), caption: [Inicio de sesión en escritorio, tema oscuro. Captura existente en `qa_capturas/login-1440-dark.png`; origen de ejecución no identificado.]) <fig-login-desktop>

La captura de registro en tema claro presenta el formulario sobre un panel de marca y una escena visual de comida; el test de contrato y la guía del repositorio describen variantes responsive. Las capturas móviles permiten documentar distribución a 375 px, no una verificación de todos los breakpoints. La evidencia del sitio empresarial se explica desde su template y guía Fase 4; no se sustituye por un mockup inventado.

#figure(
  grid(columns: (1fr, 1fr), gutter: 7pt,
    image("../assets/register-1440-light.png", width: 100%),
    image("../assets/login-375-dark.png", width: 100%),
  ),
  caption: [Registro en escritorio con tema claro y login móvil con tema oscuro. Capturas conservadas de QA; su fecha/versiones de navegador no están registradas.],
) <fig-register-and-mobile>

== Correcciones recientes presentables

En el escenario de autenticación, `templates/auth/experience.html` establece la relación semántica entre panel visual y panel de formulario. `static/css/auth.css` y `static/css/layout-system.css` conservan la escena en una columna y el formulario en la otra; el ratio indicado es 40/60. El canvas queda contenido en la celda para que sus dimensiones no alteren el cálculo de altura del formulario. Los cambios mantienen el orden responsive y los controles de cambio login/registro.

`templates/auth/recovery.html` comparte ahora el layout del área de acceso y mantiene CSRF, campos de recuperación y estados de error. `static/css/adaptive-experience.css` utiliza el token de superficie del tema para el pie. `views/salon.py` recibió una corrección únicamente de indentación en la importación `models.flow` dentro de `desk(rid)`; `py_compile` pasó en la verificación posterior. `test/test_openrouter.py` simula las lecturas de catálogo para probar el manejo de CSRF y del proveedor sin requerir PostgreSQL.

La suite aislada del corte actual obtuvo 414 pruebas aprobadas, 67 omitidas y un timeout en la comprobación visual a 1920 px. El caso repetido individualmente pasó. Este dato no elimina la incidencia inicial ni se debe mezclar con resultados anteriores de `CONECTIVIDAD.md` o de las guías de fase. El archivo de test explica qué se simuló y qué no se validó contra servicio externo.

== Matriz de estado del plan maestro

Las dieciocho fases siguientes traducen el plan proporcionado al código disponible. En “cómo se ve” se distingue captura observada de comportamiento descrito en plantilla o documentación. Cuando la evidencia es documental y no una corrida de esta sesión, se señala expresamente.

#pagebreak()
=== Fase 1. Arquitectura general y estructura central

*Módulo y ubicación:* `app.py`, `config.py`, `core/platform_context.py`, `core/permissions.py`, `database/connection.py`, `database/repository.py`, `models/`, `views/`, `templates/` y `static/`.

*Qué hace:* centraliza arranque, configuración, sesiones, autorización, acceso a la base y registro de blueprints. La guía de arquitectura declara Flask modular y PostgreSQL/Supabase, contexto de plataforma compartido y endpoints de manifiesto y salud en `/api/platform/manifest` y `/api/platform/health`.

*Cómo se ve:* el manifiesto y la salud son endpoints JSON; las páginas del sitio reutilizan navegación, estructura base y selector de tema. Los endpoints de salud no sustituyen pruebas de los módulos ni validan un proveedor IA.

*Estado:* base técnica implementada en código y documentada. La proporción de operaciones todavía almacenadas como JSONB y la integridad de esquema reportada en `CONECTIVIDAD.md` requieren evolución manual. No se afirma que Supabase estuviera disponible durante el test aislado de este informe.

#pagebreak()
=== Fase 2. Usuarios, roles y perfiles

*Módulo y ubicación:* `views/auth.py`, `utils/security.py`, `utils/account_security.py`, `core/permissions.py`, `core/profile.py`, modelos de usuario, favoritos y comunicación; plantillas en `templates/auth/` y `templates/`.

*Cómo se ve:* las rutas cubren login, alta, seguridad, recuperación, perfil y favoritos; los formularios muestran validación, advertencias y destino por rol. El sitio ofrece pantallas de login/register desktop y móvil en `qa_capturas/`. Empresarios y administradores ven enlaces distintos.

*Alcance:* el login aplica limitación de intentos, valida credenciales y crea una sesión mínima. El registro público no deja elevarse a administrador. Las guías describen permisos para comensal, empresario, personal de negocio y administrador. Tener autenticación no equivale a autorizar cada recurso, por lo que también se comprueba propiedad y ámbito.

*Estado:* flujo y pantallas presentes; las capturas históricas no verifican DB actual. Recuperación por correo/SMS necesita credenciales del proveedor, remitente autorizado y prueba sin enviar códigos reales. La guía de seguridad reporta adaptadores y límites de códigos, pero mantiene la entrega externa pendiente.

#pagebreak()
=== Fase 3. Radar gastronómico y descubrimiento de negocios

*Módulo y ubicación:* `logic/business_radar.py`, `utils/discovery_sources.py`, `models/discovery.py`, `views/discovery.py`, plantillas `templates/discovery/`, `static/js/discovery.js`, `scripts/refresh_discovery.py` e instalador de tarea Windows.

*Cómo se ve:* el administrador entra a `/admin/discovery` y revisa fuentes, corridas, candidatos, duplicados y reclamaciones. El empresario utiliza `/owner/discovery`; la vista de invitación permite iniciar un reclamo. Los candidatos son fichas provisionales, no anuncios públicos automáticos.

*Qué está integrado:* el informe Fase 3 documenta fuente autorizada, evidencia, completitud, duplicados, aprobación y puente a registros de negocio/sucursal. Google Places se consulta bajo demanda y de forma efímera; los enlaces detectados a redes no se consideran automáticamente oficiales. El score de completitud no es una probabilidad de verdad.

*Estado:* código integrado, validación externa pendiente. La consulta real de OSM/Overpass dio timeout en el corte descrito por README y la tarea diaria no fue registrada automáticamente. El worker CLI y el instalador existen; no se acreditan como servicio periódico encendido. La ficha no debe publicarse antes de verificar titularidad y datos.

#pagebreak()
=== Fase 4. Portal empresarial y páginas de marca

*Módulo y ubicación:* `views/business_sites.py`, `models/business_site.py`, `templates/sites/editor.html`, `templates/sites/public.html`, `static/css/business-sites.css` y `static/js/business-sites.js`.

*Cómo se ve:* el empresario abre `/owner/sites`, edita borrador de marca, sube logotipo y consulta preview privado. La página publicada usa `/negocio/<slug>` y una ruta por sucursal. El editor ofrece plantillas, colores, galería, contenido y botones para revisar propuesta. El snapshot publicado está separado del borrador.

*Integración:* el servidor valida propiedad del negocio, campos permitidos, URLs y derechos declarados; la IA devuelve una propuesta acotada de textos y colores que el usuario puede aplicar al formulario. El prompt de diseño nombra “premium 3D soft realism”, pero la salida selecciona plantillas de marca; no implica la creación automática de mallas GLB.

*Estado:* la guía Fase 4 registra código integrado y dos solicitudes técnicas a OpenRouter con HTTP 200 (texto y raster sintético), sin guardar publicaciones. No hay despliegue público, dominio ni CDN confirmados. Los valores de historial, premios o salud requieren verificación humana.

#pagebreak()
=== Fase 5. Catálogo, menú e importación inteligente

*Módulo y ubicación:* `views/owner.py`, `views/catalog.py`, `utils/catalog_workbook.py`, `utils/menu_documents.py`, `utils/gemini_menu.py`, `utils/restaurant_import_ai.py` y plantillas de gestión/importación de menú.

*Cómo se ve:* el empresario abre `/owner/menu/<restaurant_id>`, selecciona fecha, descarga plantilla XLSX/DOCX, carga archivo o fotografías y revisa un preview antes de aplicar. El formulario valida nombre, precio, categoría, horario y tipo de menú. La aplicación exige selección explícita de platos del borrador y limita la cantidad por solicitud.

*Tecnologías:* openpyxl y python-docx leen hojas y documentos; Pillow procesa imágenes; Gemini/Qwen u otro cliente AI puede proponer borradores según configuración. El resultado se muestra en editor, no se guarda de forma automática. Una auditoría de coherencia etiqueta incoherencias y datos desconocidos, pero informa que no certifica inocuidad ni ausencia de alérgenos.

*Estado:* flujo de carga y revisión está implementado en código y aparece cubierto por pruebas de fase. La llamada externa depende de proveedor, modelo, credenciales y contenido permitido. No se verificó aquí una extracción real ni la calidad de ingredientes.

#pagebreak()
=== Fase 6. Marketplace y búsqueda

*Módulo y ubicación:* `views/main.py`, modelos de restaurante, categoría, plato y menú; `utils/functional.py`, `static/js/search.js`, `static/js/map.js`, `static/js/market-map.js` y templates de inicio/detalle/ofertas.

*Cómo se ve:* la página `/` muestra restaurantes aprobados, categorías, ofertas o destacados según datos; `/ofertas` filtra por distrito, búsqueda y precio máximo; `/restaurant/<id>` presenta detalle y menú. La búsqueda API devuelve datos para actualizar resultados sin recargar toda la pantalla. Leaflet/MapLibre aparece en rutas de mapa con controles de zona.

*Reglas y límites:* el controlador filtra restaurantes aprobados antes de construir tarjetas; la fecha de menú se acota para evitar solicitudes arbitrarias. La distancia geográfica en línea recta no equivale a ruta de tránsito. El código usa consultas de catálogos y reviews, pero el dataset local no equivale a catálogo real de Trujillo.

*Estado:* módulos y templates están presentes; el recorrido integral actual requiere una DB de pruebas para comprobar datos y permisos. No se atribuye actualización en vivo ni ubicaciones de usuarios si la geolocalización no ha sido consentida.

#pagebreak()
=== Fase 7. Recomendador inteligente

*Módulo y ubicación:* `logic/recommender.py`, `logic/hybrid_recommender.py`, `logic/phase7_recommender.py`, `logic/market_discovery.py`, `utils/geo.py`, endpoints de `views/main.py` y búsqueda del mercado.

*Cómo se ve:* el visitante ve tarjetas ordenadas y mensajes con coincidencias o explicación de criterios; el mapa puede marcar puntos públicos. En mercado, filtros estructurados pueden ser interpretados por un asistente, pero la lista final proviene del catálogo de negocio.

*Qué calcula:* hay motores deterministas, reglas declarativas con pyDatalog, preferencias, exclusiones, presupuesto, disponibilidad y distancia. Las guías de fases comerciales describen explicación de coincidencias y ranking. Los históricos de pedidos pueden influir solo cuando hay registros permitidos.

*Estado y riesgo:* código de recomendación existe, pero en `logic/recommender.py` se observó un fallback que, ante excepción, retorna compatible. Ese comportamiento puede dar falso positivo en una exclusión alimentaria; debe tratarse como riesgo prioritario y probarse con casos negativos antes de vender la salida como “segura”. La calidad del ranking no está medida con usuarios.

#pagebreak()
=== Fase 8. Carta QR y administración de mesas

*Módulo y ubicación:* `utils/catalog_qr.py`, `views/salon.py`, `logic/salon.py`, módulos de pedidos y plantillas de salón/catálogo. La corrección reciente en `views/salon.py` fue solo de indentación para dejar `models.flow` dentro de `desk(rid)`.

*Cómo se ve:* el QR lleva a la carta o ruta que identifica negocio, sucursal o mesa. La interfaz de salón puede presentar estado de mesas, pedidos o atención cuando cuenta con datos y permisos. `MERCADO.md` documenta QR como elemento de operación presencial, pero el mapa completo de mesas y la sesión presencial requieren smoke test propio.

*Integración:* crear el QR no crea una sesión de mesa ni confirma la llegada del comensal. La relación código→mesa debe resolverse en servidor, no confiar en un identificador enviado libremente. La disponibilidad de piso/zona/mesa y su liberación deben tener transacciones y estados válidos.

*Estado:* utilidades y rutas aparecen en el repositorio; `py_compile` de la corrección puntual pasó. No se realizó aquí una compra o pedido QR real, ni se presentó evidencia de un salón desplegado.

#pagebreak()
=== Fase 9. Comercio electrónico, pedidos y pagos

*Módulo y ubicación:* `views/market.py`, `views/market_kitchen.py`, `views/market_payments.py`, modelos de pedido y operaciones, rutas `/mercado/` y módulos de webhook indicados en la guía Mercado.

*Cómo se ve:* el cliente explora ofertas, arma un carrito de un vendedor, selecciona fecha/hora y modalidad; la cocina avanza pedido por estados y el cliente consulta seguimiento/constancia. Mercado Pago Checkout Pro se configura por negocio. La contraentrega se marca al registrar entrega.

*Controles descritos:* el servidor vuelve a calcular total, cupos y disponibilidad; la guía requiere comprobar referencia, moneda PEN, importe y estado consultando al proveedor antes de acreditar. Webhook, credenciales y URL pública HTTPS son necesarios. Una redirección del navegador no acredita el pago.

*Estado:* lógica y tests se describen en `MERCADO.md`; pruebas de transacciones requieren PostgreSQL desechable. Esta sesión no configuró Mercado Pago, no envió pagos ni validó webhook con proveedor. Se clasifica como módulo de código presente, con integración externa no verificada aquí.

#pagebreak()
=== Fase 10. Cocina, recetas e inventario

*Módulo y ubicación:* `views/market_kitchen.py`, `views/owner.py`, `models/market.py`, `logic/market.py` y utilidades de recetas/costos; las colecciones de stock y pedidos se documentan en `MERCADO.md`.

*Cómo se ve:* el empresario configura productos, porciones, lotes, fechas de vencimiento, recetas, canales y ofertas programadas. La guía describe una vista de cocina que marca “Preparando”, “Listo” y “Entregado”, junto con stock crítico, ventas y demanda estimada. Las tarjetas de cliente muestran disponibilidad por turno y precio actual.

*Reglas:* la documentación interna indica descuento de insumos en la transacción que crea el pedido y reversión de reserva en cancelación antes de preparar. Estimaciones de ventas usan días comparables; si hay pocos registros no deben presentarse como predicción fiable. Los alérgenos son declaraciones comerciales, no certificación clínica.

*Estado:* componentes y pruebas de mercado existen, pero una escritura transaccional requiere la base desechable indicada en README. No se ejecutó un lote ni se midió stock en esta sesión. No se afirma que todas las integraciones de inventario estén listas para producción.

#pagebreak()
=== Fase 11. SmartResto Flow: aforo, turnos y espera

*Módulo y ubicación:* `views/flow.py`, `views/salon.py`, `logic/salon.py`, entidades de mesa, reservas, pedidos y sesiones. La arquitectura Fase 1 identifica Smart Flow como módulo transversal.

*Cómo se ve:* el empresario y personal deberían operar estados de mesas/turnos desde interfaces autenticadas; el visitante consultaría una fila o confirmación. Los indicadores dependen de eventos de sesión de mesa. La visión exige QR, número de personas, posición, tiempo estimado y asignación.

*Evidencia disponible:* el repositorio cuenta con código de salón y módulos de flujo, y el plan central enumera estos dominios. Sin embargo, la guía de inteligencia reconoce que ocupación por hora, rotación y espera requieren instrumentación previa; no se deben producir a partir de geolocalización del teléfono ni de supuestos.

*Estado:* parcial/no verificado en extremo a extremo. No se reporta un piloto de cola, una predicción validada ni tasas de rotación. El siguiente trabajo consiste en probar estados, concurrencia y recuperación después de cerrar mesa en un entorno aislado.

#pagebreak()
=== Fase 12. Fidelización, puntos y reputación

*Módulo y ubicación:* `views/loyalty.py`, `views/communication.py`, modelos de recompensas, favoritos, reviews y pedidos; las guías Mercado y Fase 14–17 describen reglas de compra verificada y comunicación.

*Cómo se ve:* el comensal consulta puntos o promociones vinculadas a compras; el empresario revisa repetición y reseñas; administración modera reclamos o publicaciones. La interfaz debe diferenciar reseñas verificadas, puntos acreditados y puntos reversibles por cancelación.

*Integración:* `MERCADO.md` describe recompensas por pedido entregado y permite que el negocio configure descuento por recompra. Las comunicaciones y consentimientos tienen preferencias separadas. Recompensas deben derivarse de pedidos confirmados en servidor, no de clicks o auto-reporte.

*Estado:* hay módulos de código y parte de la lógica comercial documentada; esta sesión no validó un ciclo transaccional completo, reversión, reclamación y consentimiento. No se presenta como sistema de puntos probado en producción.

#pagebreak()
=== Fase 13. SmartResto Home y cocina doméstica

*Módulo y ubicación:* el documento maestro toma NiriNutri como referencia para despensa, cámara, planificación de recetas y hábitos. En la lectura del repositorio no se encontró un flujo de hogar con evidencia equivalente a catálogo, pedidos o portal empresarial.

*Cómo se vería si se desarrolla:* el usuario registraría ingredientes, fechas y cantidades; la app propondría recetas y lista de compras, verificando alérgenos y presupuesto. La conexión al marketplace debe recuperar productos actuales y mostrar faltantes reales. La cocina en casa no debe reutilizar datos de restaurante como si fueran una despensa personal.

*Estado:* planificada/no verificada. La nota fuente indica que las propuestas visuales NiriNutri son prototipo, no implementación técnica comprobada. No se afirma que SmartResto escanee alimentos ni mida hábitos domésticos.

#pagebreak()
=== Fase 14. Experiencias 3D, GLB y realidad aumentada

*Módulo y ubicación:* `static/js/dish-model.js`, bundle local de `model-viewer`, activos en `static/models/`, componentes de ficha de plato y configuración declarativa. `FASES_14_17_Y_RECUPERACION.md` delimita el flujo.

*Cómo se ve:* el modelo no se descarga hasta que la persona pulsa “Cargar modelo”. El visor permite giro, zoom, vistas frontal/lateral/superior y comparación con la foto. El negocio declara dimensiones y porción; un administrador verifica la escala antes de habilitar AR a escala fija.

*Límites explícitos:* GLB autocontenido tiene restricciones de tamaño/nodos/mallas; no acepta URI externas. Sin medidas aprobadas se permite exploración 3D, pero se informa que la escala no está garantizada. AR requiere HTTPS o localhost y dispositivo compatible. Una fotografía con relieve no es reconstrucción de 360 grados; el proyecto no declara generación de GLB exactos desde una única foto.

*Estado:* visor y controles documentados, con prueba local de GLB descrita por guía, no una validación universal de AR. Modelos procedurales son referencias visuales y requieren aprobación del negocio.

#pagebreak()
=== Fase 15. Inteligencia empresarial y predicción

*Módulo y ubicación:* `views/intelligence.py`, página `/inteligencia`, endpoint privado `/api/inteligencia`, plantillas de analítica y Chart.js local.

*Cómo se ve:* panel para administración o empresarios con período de 7/30/90 días, rango acotado y selección del negocio autorizado. Los datos se agregan antes de pintar ventas, costos conocidos, pedidos por hora, clientes recurrentes, mermas o indicadores de contenido.

*Qué permite afirmar:* la guía de fase define ventas pagadas/entregadas excluyendo reembolsos, margen solo cuando hay costos completos y previsión por media de día de semana con umbrales mínimos. El intervalo es descriptivo, no una predicción garantizada ni modelo ML entrenado. No se acredita tráfico único si solo se cuentan vistas.

*Estado:* analítica reportada como implementada con filtros por propiedad; ocupación, rotación y espera quedan pendientes de instrumentar por fases anteriores. Las cifras requieren comprobar cobertura y denominador antes de compararlas entre negocios.

#pagebreak()
=== Fase 16. SmartResto Copilot

*Módulo y ubicación:* `views/copilot.py`, `static/js/copilot.js`, `utils/llm_provider.py`, contexto de permisos y módulos por dominio.

*Cómo se ve:* una pantalla autenticada recibe una consulta y presenta una respuesta o propuesta contextual según rol. El servidor selecciona catálogo permitido y métricas propias; el navegador no debe decidir el negocio ni añadir datos privados al contexto.

*Acciones y límites:* la guía describe explicación y orientación, no cambios automáticos de precios, stock, pedidos o publicación. Un cambio de texto promocional requiere propuesta, revisión, token temporal, nueva comprobación de propiedad y comparación del texto anterior. Ambas etapas se auditan. Los datos de contacto y credenciales no se envían al modelo.

*Estado:* código y reglas de confirmación documentados; la sesión no llamó al proveedor externo. La IA puede fallar, inventar o devolver formato incorrecto; su salida no sustituye validaciones de servidor ni políticas de seguridad.

#pagebreak()
=== Fase 17. Administración, seguridad y confianza

*Módulo y ubicación:* `views/admin.py`, `views/trust_center.py`, `views/admin_ai_routes.py`, permisos centrales, auditoría, límites de IA, controles de cuenta y `FASES_14_17_Y_RECUPERACION.md`.

*Cómo se ve:* un administrador consulta un panel privado de revisión, duplicados, modelos, contenidos e incidencias; empresario y comensal acceden a acciones de su alcance. Un permiso de administrador no se concede por interfaz: debe validarse contra sesión y recurso en servidor.

*Seguridad presente en documentación:* CSRF, revalidación de sesión, restricciones de rol, consentimiento por categoría, límites de intentos, control de URL/archivo y registro de decisiones. El diagnóstico de conectividad describe TLS `require` y reporta pendientes de PK/RLS/CA de forma condicionada; RLS desactivado no se interpreta automáticamente como exposición cuando los privilegios públicos revisados son falsos.

*Estado:* controles presentes, algunos pendientes manuales de infraestructura; el informe no es una auditoría de seguridad integral ni una certificación. No se leen claves ni se cambia producción.

#pagebreak()
=== Fase 18. Pruebas, integración y despliegue

*Módulo y ubicación:* `test/`, `test/conftest.py`, pruebas por fase, pruebas Playwright y configuración de despliegue indicada en README. Las bases de integración deben ser desechables y PostgreSQL, nunca productivas.

*Evidencia del corte:* el test aislado final ejecutado en esta sesión reportó 414 aprobadas, 67 omitidas y un timeout visual a 1920 px; la repetición individual del caso pasó. DSN y claves de proveedor se vaciaron en el proceso antes de importar la aplicación, por lo que las pruebas omitidas no equivalen a integración remota exitosa. Los reportes históricos de 443 aprobadas en `CONECTIVIDAD.md` pertenecen a otro corte/entorno y no se combinan con este total.

*Despliegue:* README explica arranque local con Python 3.12, variables privadas, Supabase y endpoints de salud. Fase 4 indica explícitamente que la publicación local no es despliegue en Internet. No se identificó evidencia de hosting, dominio público, TLS del sitio, pipeline CI/CD o monitoreo operativo en producción.

*Estado:* arnés de pruebas existente; validación integral incompleta por omisiones ambientales y timeout no reproducido. Despliegue/operación comercial permanecen no verificados.

== Lectura del avance preliminar

La materia prima del proyecto supera el nivel de una idea o un boceto: existen rutas, persistencia, módulos de negocio, plantillas, pruebas y guías. Eso acredita desarrollo tangible. No permite afirmar que todos los incrementos funcionen al mismo nivel ni calcular el porcentaje del producto completo. La evaluación APF3 pide alrededor de 20 % de desarrollo; la sustentación debe explicar ese porcentaje como meta de evidencia del plan y acompañarlo con backlog ponderado, no con el volumen total del repositorio.

La demo recomendada se mantiene dentro de un flujo que puede reproducirse con datos controlados: ingreso como comensal, filtros por zona/presupuesto, inspección de ficha, explicación de compatibilidad y cierre de sesión. Si la base de datos no está disponible, el equipo debe cambiar a una simulación explícita con fixtures y comunicar que los datos son simulados. No debe grabar una pantalla de un proveedor externo y describirla como parte de la ejecución actual.
