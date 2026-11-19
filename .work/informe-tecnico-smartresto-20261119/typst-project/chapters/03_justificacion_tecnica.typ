= Justificación técnica de las tecnologías

== Python, Flask y utilidades WSGI

Python es el lenguaje principal del backend, de las reglas de negocio y de las herramientas de datos. Su documentación presenta un lenguaje con estructuras de alto nivel y tipado dinámico; eso permite escribir módulos que reciben documentos, aplican validaciones y construyen respuestas sin introducir una capa de compilación propia del proyecto (Python Software Foundation, 2026). En SmartResto se observa en `app.py`, `views/`, `models/`, `logic/`, `database/` y `utils/`. No existe un pin de Python en `requirements.txt`; el README indica Python 3.12 para el procedimiento de instalación, dato que describe la guía de ejecución y no la versión que se haya comprobado en cada entorno.

Flask resulta adecuado para la forma actual del sistema porque expone rutas y blueprints en un proceso web modular. La documentación de Flask describe la instancia como una aplicación WSGI y muestra el vínculo entre una URL y una función que produce una respuesta (Pallets Projects, s. f.-a). El archivo `app.py` crea el contexto, configura CSRF, registra blueprints y establece hooks. Los controladores como `views/main.py`, `views/auth.py` y `views/market.py` separan descubrimiento, identidad y comercio. La salida visible es HTML renderizado o JSON; no se observó un frontend separado que requiera una API GraphQL.

Werkzeug acompaña a Flask con utilidades WSGI, HTTP, routing y request/response. La versión declarada es 3.0.1, compatible con la rama de Flask 3.0 requerida por el repositorio. El registro de cambios documenta correcciones específicas de esa publicación, incluida una mejora de análisis multipart frente a entradas grandes (Pallets Projects, s. f.-b, 2023a, 2023b). En SmartResto aparece en módulos de carga de archivos, utilidades de formularios y servidores de prueba. Su presencia mejora la base de utilidades del framework; no reemplaza la validación de permisos, tamaño y contenido que cada ruta debe aplicar.

=== Flask-Login y el flujo de identidad real

El archivo de dependencias declara `Flask-Login==0.6.3`, biblioteca que documenta gestión de sesiones y vistas autenticadas; su guía aclara que no define por sí misma el almacenamiento de usuarios, la recuperación de cuentas ni los permisos (Flask-Login, s. f.). El inventario estático no encontró import directo de `flask_login`. En cambio, `utils/security.py` y `app.py` revalidan la sesión contra el usuario y su época de autenticación, y los controladores inspeccionados aplican utilidades de rol.

Por ello, en el informe se registra Flask-Login como dependencia declarada con uso directo no localizado, no como la tecnología que implementa actualmente el login. La pantalla de acceso sí aparece en las capturas QA. Esa imagen demuestra el aspecto almacenado de la interfaz, pero no prueba que Flask-Login esté activo ni que la autenticación haya funcionado en ese momento. La diferencia es importante para que el inventario de dependencias no se convierta en una descripción ficticia del flujo real.

== Formularios, CSRF y configuración

Flask-WTF conecta formularios WTForms con Flask. Su documentación explica el campo oculto CSRF y la validación del envío mediante `validate_on_submit()` (WTForms, s. f.). En SmartResto, `app.py` inicializa `CSRFProtect`; `utils/security.py` agrupa el helper de seguridad y las plantillas incluyen `csrf_token`. Las peticiones POST de clientes JSON envían el token en `X-CSRFToken`, de acuerdo con el README del repositorio.

La protección es relevante porque el producto mezcla formularios HTML con mutaciones de favoritos, catálogos, pedidos y administración. Su existencia en el arranque no demuestra que todo formulario esté conectado correctamente, ni sustituye autorización por rol, comprobación de propiedad o validación de valores. La prueba documentada en `CONECTIVIDAD.md` que envía un POST de login sin CSRF y espera un 400 es una expectativa/resultado histórico del propio registro; la repetición actual debe analizarse con el test vigente y el servidor de prueba.

`python-dotenv` permite cargar pares de un archivo `.env` y, por defecto, no sobrescribe variables ya presentes en el proceso (Kumar, 2023). `app.py` contiene la carga opcional de entorno; el README asigna prioridad a las variables del proceso. La configuración `config.py` valida `SECRET_KEY`, DSN PostgreSQL y TLS antes del arranque normal. El informe no leyó valores del archivo `.env` y no incluye claves. Esta herramienta ayuda a separar configuración del código, pero el archivo debe mantenerse privado y los secretos de producción deben ir en un gestor de secretos.

`cryptography` se declara como rango `>=44,<51` y se importa en `utils/account_security.py`. PyCA diferencia recetas de alto nivel y primitivas de bajo nivel, y recomienda preferir las recetas cuando cubran el caso (The Python Cryptographic Authority, s. f.-b). Su documentación de Fernet describe cifrado simétrico autenticado, rotación mediante MultiFernet y límites de memoria/timestamp (The Python Cryptographic Authority, s. f.-a). En SmartResto esa referencia es técnica; el algoritmo y el ciclo exacto de cada dato deben documentarse desde el módulo que lo invoca y no se deducen únicamente del nombre de dependencia.

#pagebreak()
== PostgreSQL, JSONB, Psycopg y Supabase

PostgreSQL se selecciona como almacenamiento común de usuarios, restaurantes, menús, pedidos y auditoría, según README y `database/`. El repositorio actual utiliza de forma amplia `public.app_records`, donde una fila representa colección, identificador y payload JSONB. La estructura flexible favorece la evolución de documentos de dominio, mientras que las transacciones PostgreSQL protegen cambios que deben persistir juntos. No toda entidad está normalizada en tablas dedicadas; existen escrituras selectivas a `sr_businesses`, `sr_branches`, `sr_memberships` y `ai_decisions`.

La documentación de PostgreSQL distingue `json` y `jsonb`: el segundo conserva una representación descompuesta y permite búsquedas e indexación, aunque no preserva orden ni espacios originales; la guía también describe índices GIN (PostgreSQL Global Development Group, s. f.). En SmartResto, `database/app_records.sql` declara la estructura de almacenamiento documental y `database/repository.py` adapta payloads. La ventaja es admitir estructuras heterogéneas por colección; el coste es que muchos `.all()` recuperan documentos y filtran en Python, según la auditoría `CONECTIVIDAD.md`.

El driver `psycopg[binary]==3.2.3` conecta Python con PostgreSQL. La documentación del driver describe adaptación de valores JSON a `json`/`jsonb` por medio de `Json` y `Jsonb`, con serialización/deserialización personalizables (Psycopg, s. f.). `database/connection.py` centraliza el acceso, TLS, pool, timeouts y transacciones; `database/repository.py` implementa repositorios; modelos de dominio delegan en ellos. El pool local está acotado y, según `CONECTIVIDAD.md`, evita reintentos automáticos para no duplicar escrituras.

Supabase se describe en README como proyecto PostgreSQL administrado y destino de la base. Supabase documenta conexiones directas, poolers y Data APIs con diferencias según entorno; el modo transaction de un pooler compartido no admite prepared statements (Supabase, s. f.-a, s. f.-b). La documentación interna declara una conexión pooler y exige copiar host/usuario reales del panel, no inventarlos. Esta elección depende de red, límite de conexiones y TLS; este informe no ejecuta nuevas conexiones ni verifica el estado de un servidor remoto.

=== Límites observados de consistencia de datos

Los scripts `database/schema.sql` y `migrations/migrate_json.py` describen un esquema relacional amplio y un camino de migración. La existencia del DDL no demuestra que los modelos de ejecución hayan sustituido `app_records`. `CONECTIVIDAD.md` registra, para una inspección previa, una tabla `app_records` sin clave primaria general y RLS desactivado, junto con privilegios públicos revisados como denegados. Estos hallazgos deben presentarse como reporte fechado del equipo y requieren nueva verificación antes de cualquier cambio en producción.

La ventaja de la flexibilidad JSONB convive con riesgos de integridad, índices y consistencia entre estructuras. No se recomienda migrar todo durante esta entrega: la guía interna plantea comparar consultas reales, revisar duplicados, probar en staging y aprobar manualmente restricciones. Ese enfoque evita que el informe confunda una propuesta de DDL con una mejora ya desplegada.

== OpenAI SDK, OpenRouter, Gemini y Pydantic

El paquete `openai` se declara en un rango de versiones y se importa desde `utils/llm_provider.py` y `utils/admin_ai.py`. OpenAI describe su biblioteca como SDK oficial Python para acceder a su API, con clientes síncronos/asíncronos y tipos de solicitud/respuesta (OpenAI, s. f.). El README de SmartResto configura OpenRouter como endpoint compatible por defecto. OpenRouter documenta formatos Chat Completions y Responses y explica el uso del SDK OpenAI con una URL base propia (OpenRouter, s. f.-a, s. f.-b).

La compatibilidad de interfaz evita escribir un cliente HTTP diferente para cada proveedor, pero no hace equivalentes sus modelos, precios, límites, retención ni garantías. SmartResto limita solicitudes y documenta `max_retries=0` en la capa compartida de proveedor. Las rutas de interpretación, chat, moderación asistida y Copilot devuelven errores controlados cuando faltan configuración o respuestas válidas. Ninguna solicitud externa se realizó para este documento, así que no se reporta latencia ni calidad actual de modelo.

`google-genai` se declara con rango mayor o igual a 1 y menor que 2. Google identifica el paquete Python como `google-genai` y recomienda su SDK para Gemini API (Google AI for Developers, s. f.-a). `utils/gemini_menu.py`, `utils/kitchen_assistant.py` y `utils/restaurant_import_ai.py` muestran usos en extracción o preparación de menú y cocina. El catálogo de Gemini publica identificadores y modalidades por modelo, que pueden cambiar (Google AI for Developers, 2026; s. f.-b). La selección de modelo con visión o texto debe revisarse contra la tarea y las condiciones de proveedor; una respuesta no se convierte directamente en verdad de ingredientes o alérgenos.

Pydantic, con rango `>=2.8,<3`, aparece en `utils/admin_ai.py`. Sus modelos describen campos y validan la instancia resultante, con posibles conversiones de valores de entrada (Pydantic Services Inc., s. f.). Esto es útil para limitar la forma de solicitudes IA y convertir salidas a estructuras esperadas. La validación del tipo no prueba la veracidad semántica: un texto correctamente tipado puede seguir conteniendo precio, disponibilidad o ingredientes incorrectos.

#pagebreak()
== HTML, Jinja, CSS, JavaScript y Chart.js

Las plantillas comparten `templates/base.html`, parciales de navegación y layouts. Flask entrega contexto con `render_template`; las páginas extienden shells por dominio, incluyen macros y declaran URLs de formularios o de `fetch`. El estándar HTML modela documentos como árboles de elementos y texto que el navegador transforma en DOM (WHATWG, s. f.). Los archivos `static/css/` controlan tema y responsive; el inventario encuentra JavaScript nativo en `static/js/`, sin evidencia de que React o Vue formen el cliente principal.

CSS separa presentación y estructura y se organiza en módulos; W3C presenta CSS como un lenguaje para describir la representación de documentos en pantalla y otros medios (World Wide Web Consortium, CSS Working Group, 2026). En el proyecto, `theme-tokens.css`, `responsive-layout.css`, `layout-system.css`, `auth.css` y `adaptive-experience.css` configuran tema, grids y breakpoints. JavaScript se ocupa de eventos, validaciones, solicitudes fetch y estado de controles; ECMAScript define el lenguaje estandarizado que sustenta JavaScript en navegadores y otros runtimes (Ecma International, 2026).

La ventaja de la pila de plantillas es servir páginas desde el mismo backend que aplica roles y permisos. El costo de una interfaz multipágina con código JS y estilos repartidos es mantener consistencia entre plantillas y contratos API. Por ello cada afirmación de “se ve así” en este informe se limita a capturas almacenadas o al código de plantilla; no se afirma que todos los módulos se hayan recorrido en un navegador actual.

Chart.js aparece en `static/js/admin.js` y `templates/admin/analytics.html`. Su documentación 4.5.1 indica que los gráficos se dibujan en `canvas` y que el estilo CSS no se aplica directamente a los elementos internos; colores, plugins y opciones se controlan por la biblioteca (Chart.js, 2025). Esta decisión permite crear líneas y barras para indicadores, pero exige etiquetas legibles, colores con contraste y datos en formato correcto. La existencia de varias instancias de Chart en la plantilla no acredita precisión de métricas ni actualización de datos.

== Mapas, geografía y localización

Leaflet se observa en `static/js/map.js`, `static/js/market-map.js` y formularios de ubicación. La biblioteca expone mapa, marcadores, controles y `TileLayer`; la documentación advierte que muchos servidores requieren atribución visible (Leaflet, s. f.). MapLibre GL JS aparece en la página de descubrimiento y renderiza mapas interactivos WebGL a partir de teselas vectoriales y un documento de estilo (MapLibre contributors, s. f.). La existencia de ambos motores no significa que todas las pantallas los carguen simultáneamente; cada uso depende del template, assets y datos provistos.

`OpenStreetMap` se cita como fuente de teselas en algunas plantillas. La política de la OpenStreetMap Foundation aplica específicamente a los tiles raster estándar de `tile.openstreetmap.org`; exige atribución, identificación y caché, restringe descargas masivas y no promete SLA (OpenStreetMap Foundation, s. f.). No se hizo solicitud a ese servidor; la recomendación es revisar atribución y volumen antes del despliegue, no asumir que cualquier proveedor de mapas hereda esta política.

`geopy==2.4.1` aporta un cliente para geocodificación y cálculos geodésicos; `haversine==2.8.0` calcula distancias entre latitud/longitud y ofrece cálculo inverso. Los módulos `utils/geo.py` y `logic/phase7_recommender.py` preparan proximidad, ordenamiento y contexto. La distancia recta puede no coincidir con distancia de ruta, tiempos de transporte o cobertura comercial. El sistema necesita consentimiento para ubicación precisa y debe conservar una opción manual de distrito o zona.

=== Geolocalización como decisión de privacidad

El frontend describe consentimiento de ubicación y los endpoints guardan coordenadas cuando se permite. La recomendación no debe requerir coordenadas precisas si el usuario prefiere seleccionar distrito. La ubicación puede revelar hábitos y rutinas; el informe recomienda minimizar precisión y duración de retención y explicar el uso antes de solicitar permiso. No se presentan coordenadas individuales ni se abrieron datos de usuario.

#pagebreak()
== Importación, contenido y archivos gastronómicos

Pillow se importa en modelos y utilidades de IA para operaciones con imágenes. La documentación de Pillow enumera formatos y herramientas de filtro, dibujo y transformación (Pillow contributors, s. f.). En SmartResto se combina con captura de fotografía, análisis de menú y recursos de sitios de negocio. La selección ayuda a procesar formatos de imagen en Python, pero no acredita reconocimiento confiable ni derechos de publicación; una imagen analizada debe quedar asociada a origen, permiso y revisión.

`openpyxl` y `python-docx` aparecen en `utils/catalog_workbook.py`, `utils/menu_documents.py` y módulos de importación. openpyxl permite leer y escribir libros de Excel; su tutorial advierte que algunos elementos, como formas, pueden perderse al abrir y guardar (openpyxl contributors, s. f.). python-docx crea o edita documentos Word y añade párrafos, tablas e imágenes (Canny, s. f.). SmartResto convierte esos archivos a un preview revisable; ese paso es más seguro que publicar automáticamente una extracción.

Pandas está declarado como requisito (`pandas>=2.2.3`), pero el barrido estático de módulos Python no encontró import directo. Aunque su documentación ofrece herramientas de análisis tabular, limpieza, agregación y formatos como CSV, Excel, SQL y JSON (pandas development team, 2026; s. f.), su papel concreto en el flujo actual no se puede establecer con la evidencia revisada. Debe conservarse en el inventario como dependecia declarada con uso no localizado, no como motor activo confirmado.

`qrcode==8.2` se importa en `utils/catalog_qr.py` y genera códigos para dirigir al usuario a una ficha, sucursal o contexto de mesa. El paquete documenta salidas PNG y SVG y parámetros de corrección; sus estilos no garantizan lectura universal (Lincoln Loop, 2025). La validación debe incluir lectura en dispositivos variados y URL de destino vigente. Generar el archivo QR no demuestra que exista una operación de mesas habilitada.

== Reglas lógicas y distancias

`pyDatalog==0.17.4` se importa en `logic/recommender.py`, donde expresa relaciones de compatibilidad y motivos de recomendación. La ventaja de reglas explícitas es inspeccionar por qué una condición aplica; el límite es que el resultado depende de hechos correctamente registrados y de reglas completas. La revisión de código observó un fallback que devuelve compatibilidad verdadera ante excepción en ese módulo. Dado que puede afectar restricciones alimentarias, debe revisarse y cubrirse con pruebas negativas antes de considerar ese motor apto para decisiones críticas.

GeoPy y Haversine complementan el contexto espacial, pero no sustituyen un motor de rutas. La geocodificación consulta servicios según proveedor configurado y tiene dependencias de cuota, conectividad y políticas. La regla operativa recomendada es comparar geodistancia con distancia real antes de prometer “a cinco minutos” como predicción; la captura existente muestra una etiqueta de ese tipo, pero no se presenta como cálculo en vivo verificado.

== Experiencia 3D y voz

El bundle `model-viewer` versionado en el repositorio y `static/js/dish-model.js` implementan la carga diferida de modelos 3D mediante `<model-viewer>`. La documentación de Google muestra compatibilidad glTF/GLB y modos AR condicionales (Google, s. f.-a). glTF 2.0 define un formato abierto de transmisión de activos y GLB permite agrupar descripción JSON y recursos binarios (Khronos Group, 2021). En SmartResto, la aprobación de medidas condiciona la afirmación de escala; el README de activos los caracteriza como referencias procedurales y no como escaneos exactos. No se declara precisión dimensional.

`trimesh==4.6.13` se documenta en el README de modelos como dependencia de construcción, no como biblioteca importada por el backend de producción. El proyecto puede crear o exportar mallas GLB con esa herramienta (Dawson-Haggerty, 2025; s. f.). El usuario final vería una pieza 3D giratoria únicamente cuando una página disponga de botón, modelo, metadatos y navegador compatible. Un modelo 3D no implica automáticamente realidad aumentada utilizable en todos los dispositivos.

La Web Speech API se usa como capacidad opcional de dictado en el catálogo. `SpeechRecognition` y `SpeechSynthesis` cubren reconocimiento y lectura de voz; MDN advierte que el reconocimiento puede procesarse localmente o enviarse a un servicio del navegador y que la disponibilidad varía (MDN contributors, 2026a, 2026b). El borrador del grupo comunitario de W3C no es un estándar final (Speech API Community Group, 2014). Por eso el flujo debe degradarse a entrada por teclado, pedir consentimiento al micrófono y no enviar voz a terceros sin aviso.

== Pruebas del stack de desarrollo

pytest organiza pruebas Python, aserciones y fixtures; su documentación describe descubrimiento de archivos y selección por módulo, directorio, keyword o marca (pytest, s. f.-a, s. f.-b). En `test/` se observan unit tests del pool, pruebas de rutas, fixture de base desechable y contratos de interfaz. Los mocks reducen dependencia externa, pero el resultado mockeado no valida proveedor, PostgreSQL remoto ni calidad de datos real.

Playwright permite automatizar Chromium, WebKit y Firefox; cada versión requiere binarios correspondientes y un runner de pruebas (Playwright, s. f.-a, s. f.-b). `test/test_auth_experience.py`, `test/visual_browser.cjs` y `test/forest_home.py` definen escenarios de distintos viewports, temas e interacciones. Node.js ejecuta JavaScript fuera del navegador e incluye `node:test` (Node.js contributors, s. f.-a, s. f.-b). Estos instrumentos permiten ver errores de overflow y flujos, pero se deben reportar skips, timeouts, fixtures y restricciones de red junto al conteo.

=== Conclusión de selección

La combinación es coherente con una entrega web que ya dispone de módulos Python y pantallas multipágina. No implica que SmartResto necesite todo el ecosistema listado para su MVP. Las capacidades esenciales pueden seguir operando con datos deterministas; IA, mapas, voz, 3D y pagos se activan por etapas, con controles de privacidad, coste y verificación. El plan del capítulo siguiente prioriza completar una vertical acotada antes de ampliar proveedores o predicción.
