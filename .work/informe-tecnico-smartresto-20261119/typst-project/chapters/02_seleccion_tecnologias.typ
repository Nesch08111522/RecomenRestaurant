= Selección de tecnologías de transformación digital

== Arquitectura observada en el repositorio

La estructura corresponde a una aplicación web Python/Flask organizada por dominios. `app.py` construye la aplicación, carga `Config`, inicializa CSRF y registra blueprints; los controladores de `views/` responden con HTML o JSON; `logic/`, `models/` y `utils/` implementan reglas, acceso a datos y utilidades; `templates/` y `static/` presentan la experiencia de usuario. El diseño es un monolito modular en el sentido operativo de un proceso Flask que reúne los dominios; no se observó una arquitectura de microservicios desplegados por separado.

#figure(
  table(
    columns: (1.35fr, 0.5fr, 1.35fr, 0.5fr, 1.45fr),
    stroke: none,
    inset: (x: 6pt, y: 7pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Interfaz*], [*→*], [*Rutas Flask*], [*→*], [*Reglas y datos*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Jinja, HTML, CSS y JavaScript en `templates/` y `static/`.], [→], [`views/` valida la solicitud y prepara JSON o una plantilla.], [→], [`logic/`, modelos y `utils/` aplican reglas y acceden a repositorios.],
    [Fetch, formularios y atributos `data-*`.], [→], [Blueprints por dominio, sesiones, CSRF y controles de rol.], [→], [`database/connection.py` y `database/repository.py`.],
    [Mapa, tarjetas, formularios, gráficos y pantallas por rol.], [←], [Contexto enviado a la plantilla o respuesta API.], [←], [PostgreSQL con documentos JSONB y escrituras relacionales selectivas.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Flujo arquitectónico que se desprende de los archivos inspeccionados],
) <fig-architecture-flow>

La evidencia de base de datos apunta a Supabase PostgreSQL como almacenamiento operativo descrito por el README, con `public.app_records` y `payload` JSONB como ruta documental extensa. Se identifican además escrituras selectivas a tablas `sr_*` y `public.ai_decisions`, junto con DDL relacional y scripts de migración que no prueban adopción completa. La convivencia de estos artefactos exige cautela al describir el modelo como “totalmente relacional” o afirmar que una migración fue aplicada.

== Requisitos de aplicación y seguridad

La siguiente matriz toma las versiones de `requirements.txt`. Un pin es una restricción del proyecto, no una prueba de lo instalado en el entorno. La detección de imports directos se realizó por lectura estática y solo afirma que se encontraron imports en los módulos listados.

#figure(
  table(
    columns: (1.15fr, 1.35fr, 2.7fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Paquete y requisito*], [*Importación observada*], [*Función o cautela*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [`Flask==3.0.0`], [`flask` en `app.py` y vistas], [Arranque web, rutas, solicitudes, sesiones y respuestas.],
    [`Werkzeug==3.0.1`], [Modelos, seguridad, vistas y utilidades], [Utilidades WSGI/HTTP; versión fijada junto a Flask.],
    [`Flask-WTF==1.2.1`], [`Flask-WTF` y `CSRFProtect`], [Protección CSRF inicializada en `app.py` y `utils/security.py`.],
    [`Flask-Login==0.6.3`], [No se encontró import directo], [Declarada en requisitos; el flujo examinado usa utilidades de sesión propias. No se atribuye la autenticación a esta biblioteca.],
    [`python-dotenv==1.0.0`], [`dotenv` en `app.py` y scripts], [Carga opcional de entorno; no se inspeccionaron valores de `.env`.],
    [`cryptography>=44,<51`], [`cryptography` en `utils/account_security.py`], [Capa criptográfica en el flujo de códigos/seguridad; no se describe un uso distinto sin evidencia.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Dependencias de aplicación, solicitudes y seguridad],
) <tab-requirements-web>

== Persistencia, IA y validación de datos

#figure(
  table(
    columns: (1.2fr, 1.25fr, 2.6fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Paquete y requisito*], [*Importación observada*], [*Función o cautela*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [`psycopg[binary]==3.2.3`], [`psycopg` en conexión, repositorio, modelos y migraciones], [Driver PostgreSQL y adaptación de datos; instalación, DSN real y esquema no se validaron durante la redacción.],
    [`openai>=1.0.0,<3`], [`openai` en `utils/llm_provider.py` y `utils/admin_ai.py`], [SDK compatible usado por wrappers de IA; el README configura OpenRouter como proveedor predeterminado, sin que este informe invoque el servicio.],
    [`google-genai>=1.0,<2`], [`google.genai` en `utils/gemini_menu.py` y utilidades IA], [Cliente usado en extracción/generación asistida de menús y cocina, con borradores revisables.],
    [`pydantic>=2.8,<3`], [`pydantic` en `utils/admin_ai.py`], [Validación/modelado de datos de IA según esquemas.],
    [`pandas>=2.2.3`], [Sin import directo en los módulos Python analizados], [Declarada, con uso directo no localizado en el barrido; no se afirma que sea parte de un flujo activo.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Dependencias de persistencia, proveedores de IA y datos estructurados],
) <tab-requirements-data-ai>

La integración de IA se separa en dos familias. `utils/llm_provider.py` crea un cliente compatible con API de chat y `views/ai_routes.py`, `views/admin_ai_routes.py`, `views/copilot.py` y `views/owner.py` definen distintas rutas de uso. Para Gemini, `utils/gemini_menu.py` y módulos relacionados procesan materiales de menú. En ambos casos la existencia de una llamada en código no comprueba que haya credenciales, cuota, respuesta válida o continuidad de servicio.

== Frontend, datos estructurados y pruebas

#figure(
  table(
    columns: (1.2fr, 1.35fr, 2.5fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Paquete y requisito*], [*Importación o activo observado*], [*Uso y alcance*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [`Pillow>=10,<13`], [`PIL` en modelos, utilidades e IA], [Procesamiento de imagen en importaciones y recursos; la experiencia concreta depende del flujo.],
    [`openpyxl>=3.1.5,<4`], [`utils/catalog_workbook.py`, `utils/menu_documents.py`], [Lectura y escritura de hojas de cálculo para importación con previsualización.],
    [`python-docx>=1.1.2,<2`], [`utils/menu_documents.py`, `utils/restaurant_import_ai.py`], [Lectura de documentos Word para extracción de cartas y menús.],
    [`pyDatalog==0.17.4`], [`logic/recommender.py`], [Reglas lógicas de compatibilidad/justificación; no se observó entrenamiento de ML.],
    [`geopy==2.4.1` y `haversine==2.8.0`], [`utils/geo.py`], [Geocodificación/distancias; la geocodificación directa requiere proveedor y configuración.],
    [`qrcode==8.2`], [`utils/catalog_qr.py`], [Generación de QR de catálogo/mesa; el uso no acredita automáticamente una operación de salón activa.],
    [`pytest>=8,<10`], [`test/`], [Suites unitarias, de integración, contratos y fixtures; el resultado actual se describe en capítulo 5.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Dependencias de medios, importación, geografía, reglas y pruebas],
) <tab-requirements-ui>

Además de las dependencias Python, los archivos frontend y las plantillas referencian JavaScript nativo, CSS y HTML/Jinja. Se observan Chart.js para analítica, Leaflet y MapLibre GL JS para mapas, OpenStreetMap en capas de teselas, `model-viewer` para visualizar archivos GLB y la Web Speech API para dictado opcional. El repositorio conserva un harness Playwright/Node para pruebas de navegador. Estas bibliotecas no aparecen en `requirements.txt`; su versión se determina por archivos estáticos o configuración frontend separada, no por la lista Python.

== Por qué la selección se agrupa por función

El stack prioriza un único backend Flask porque las funciones comparten sesión, autorización, contexto de negocio y modelos. Las reglas de recomendación permanecen en módulos Python separados de las rutas, lo cual facilita probarlas con datos suministrados. PostgreSQL proporciona una persistencia central; la adopción de JSONB permite registrar payloads flexibles, aunque mantiene en Python varias agregaciones que podrían crecer en coste con el catálogo.

El cliente usa bibliotecas especializadas donde hay una necesidad visible: Chart.js para series, Leaflet/MapLibre para mapas, `model-viewer` para una ficha 3D y herramientas de importación para reducir captura manual. El valor de esas tecnologías depende de la integración: los mapas requieren coordenadas y teselas; la voz depende del navegador; la realidad aumentada necesita dispositivos compatibles; la IA exige proveedor, configuración y validación humana.

== Stack no equivalente a capacidad validada

Una tecnología se considera seleccionada cuando aparece en requisitos o código. Para subirla a “función probada” se requiere evidencia de ejecución representativa. El paquete `Flask-Login`, por ejemplo, está fijado, pero no aparece en imports directos del código Python revisado; no se le atribuye el manejo real de sesiones. `pandas` está declarado sin import directo localizado. `trimesh` figura como dependencia de construcción en el README de activos 3D, no como ruta Python de producción demostrada.

Del mismo modo, un cliente OpenAI compatible puede dirigir tráfico a OpenRouter, pero la presencia del SDK no valida una respuesta del proveedor. La API Gemini está presente en rutas de extracción, pero el informe no la invocó. Esa separación entre dependencia, llamada programada, respuesta de servicio y resultado validado guía las siguientes justificaciones técnicas.
