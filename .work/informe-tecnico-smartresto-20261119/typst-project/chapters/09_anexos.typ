#heading(numbering: none)[Anexos]

#heading(numbering: none)[Anexo A. Fuentes internas revisadas]

La revisión de esta entrega utilizó la versión local del repositorio cuyo `HEAD` corto era `3725a99`, con cambios presentes en el árbol de trabajo. Los nombres listados a continuación son rutas del proyecto, no fuentes públicas ni resultados de despliegue. La clasificación de estado del cuerpo se basa en estas piezas y en pruebas/documentos explícitos.

#figure(
  table(
    columns: (1.7fr, 2fr, 2.2fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Familia*], [*Rutas de referencia*], [*Uso en el análisis*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Arranque y configuración], [`app.py`, `config.py`, `requirements.txt`, `README.md`], [Stack, orden de arranque, variables requeridas y límites de integración.],
    [Persistencia y conectividad], [`database/connection.py`, `pool.py`, `repository.py`, `metrics.py`, `CONECTIVIDAD.md`], [Conexión, JSONB, transacciones, pool, test de seguridad y hallazgos de infraestructura.],
    [Autenticación], [`views/auth.py`, `utils/security.py`, `utils/account_security.py`, `templates/auth/`, `static/css/auth.css`], [Login, registro, recuperación, controles de sesión y presentación visual.],
    [Marketplace], [`views/main.py`, `views/owner.py`, `views/market.py`, `views/market_kitchen.py`, `MERCADO.md`], [Búsqueda pública, catálogo, importación de menús y operación comercial descrita.],
    [Radar y portal], [`FASE_3_RADAR_GASTRONOMICO.md`, `FASE_4_PORTAL_EMPRESARIAL.md`, `views/discovery.py`, `views/business_sites.py`], [Borradores, revisión, sitios empresariales, publicación y dependencias externas.],
    [Tecnología 3D e IA], [`views/food_experience.py`, `views/copilot.py`, `utils/llm_provider.py`, `static/js/dish-model.js`, `static/models/`], [Modelos, visualización, proveedores y límites de interpretación.],
    [QA], [`test/`, `qa_capturas/`, `docs/connectivity/tests-summary.json`, `docs/RESPONSIVIDAD.md`], [Pruebas históricas/locales y capturas visuales no fechadas.],
    [Documentos académicos], [APF2 integrado, guía APF3, rúbrica AV3 y plan maestro de fases], [Objetivos, calendario histórico, criterios de evaluación y hoja de ruta.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Trazabilidad de fuentes internas utilizadas],
) <tab-internal-sources>

Las fuentes técnicas oficiales externas se presentan alfabéticamente en Referencias. Los archivos `.env`, llaves, contraseñas, cookies y cuerpos de solicitudes no se inspeccionaron ni se trasladan a este informe.

#pagebreak()
#heading(numbering: none)[Anexo B. Matriz rápida de tecnología y experiencia visible]

#figure(
  table(
    columns: (1.1fr, 1.7fr, 1.8fr, 1.8fr),
    stroke: none,
    inset: (x: 5pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Tecnología*], [*Dónde vive*], [*Salida visible*], [*Límite a comunicar*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Python/Flask], [`app.py`, `views/`, `core/`, `logic/`], [Páginas HTML y APIs JSON por rol.], [No prueba un deploy separado por módulo.],
    [PostgreSQL/Psycopg], [`database/`, modelos], [Catálogos, perfiles, registros, pedidos.], [Servidor y esquema requieren DSN y pruebas.],
    [OpenRouter/OpenAI SDK], [`utils/llm_provider.py`, rutas IA], [Borrador de contenido o interpretación cuando está configurado.], [Sin proveedor no hay llamada; respuesta requiere validación.],
    [Gemini], [`utils/gemini_menu.py`, cocina/importación], [Propuesta de extracción de documentos/fotos.], [No publica automáticamente ni verifica ingredientes.],
    [HTML/Jinja/CSS/JS], [`templates/`, `static/`], [Formularios, grillas, filtros, estados, temas.], [Capturas existentes no demuestran ejecución actual.],
    [Leaflet/MapLibre], [`static/js/map.js`, `market-map.js`, templates], [Mapa de comercios o zona de servicio.], [Coordenadas, teselas y atribución dependen del entorno.],
    [Chart.js], [`templates/admin/analytics.html`, `static/js/admin.js`], [Gráficos de ventas y métricas agregadas.], [La métrica depende de cobertura/calidad del dato.],
    [model-viewer/glTF], [`static/js/dish-model.js`, `static/models/`], [Visor GLB con giro, zoom y fotos.], [Escala y AR solo con compatibilidad/aprobación.],
    [openpyxl/python-docx/Pillow], [`utils/catalog_workbook.py`, `menu_documents.py`], [Preview importable de cartas, fotos y archivos.], [Extracción puede fallar; revisión humana necesaria.],
    [pytest/Playwright], [`test/`, `visual_browser.cjs`], [Aserciones, smoke tests y capturas.], [MocK/skips no equivalen a integración real.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Relación entre stack técnico y comportamiento que podría observarse],
) <tab-technology-ui-map>

#pagebreak()
#heading(numbering: none)[Anexo C. Guion de demo técnica reproducible]

*Antes de iniciar.* Registrar fecha, commit, Python, navegador y estado de base. Usar una base PostgreSQL desechable con esquema instalado, o fixtures locales rotulados como simulación. Confirmar que `.env` no apunta a un recurso productivo; no mostrar consola con secretos. Preparar un usuario de prueba por rol y datos sintéticos no asociados a personas o negocios reales.

*Paso 1: sitio público.* Abrir la página inicial y describir las tarjetas/controles presentes. Cambiar un filtro de distrito o categoría. Registrar qué parámetro se envía, el código que lo recibe y el estado de “sin resultados”. No narrar el resultado como ranking IA si el orden proviene de reglas deterministas.

*Paso 2: ficha y explicabilidad.* Abrir una ficha controlada, revisar carta y datos no disponibles. Ejecutar un caso con presupuesto y preferencia. Si el motor muestra una justificación, identificar el atributo de entrada. Probar una restricción incompatible y otra desconocida; el desconocido debe distinguirse de compatible.

*Paso 3: autenticación y rol.* Abrir `/auth/login`, iniciar sesión como cuenta de prueba y mostrar el destino por rol. Cambiar a empresario y mostrar que solo administra su establecimiento. Intentar una acción con recurso ajeno o sin CSRF en el servidor de pruebas; documentar respuesta y protección. No exponer contraseña ni token.

*Paso 4: menú empresarial.* Abrir `/owner/menu/<id>`, descargar una plantilla vacía, cargar un archivo sintético y revisar el borrador. Corregir un precio y dejar en borrador; mostrar que aplicar/publicar es una operación distinta del análisis IA.

*Paso 5: evidencia visual.* Cambiar tema claro/oscuro y viewport móvil. Mostrar `login-1440-dark.png`, `register-1440-light.png` y `login-375-dark.png` como capturas previas; añadir una nueva captura fechada solo después de probar el build actual. Explicar que el panel 3D suave es dirección visual, no medición de escala.

*Paso 6: pruebas y cierre.* Ejecutar tests de contratos relevantes, presentar salida incluyendo skips/errores y explicar que el total de esta sesión fue aislado. Si una integración externa está apagada, mostrar el estado controlado sin intentar usar claves de producción. Cerrar con defectos abiertos y la acción siguiente.

#pagebreak()
#heading(numbering: none)[Anexo D. Casos de aceptación mínimos del MVP]

#figure(
  table(
    columns: (0.5fr, 1.7fr, 2.3fr, 1.7fr),
    stroke: none,
    inset: (x: 5pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*ID*], [*Caso*], [*Criterio observable*], [*Resultado a registrar*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [A-01], [Abrir home con datos válidos], [Solo negocios aprobados se presentan como opción comercial.], [Captura, fixture, cantidad y fuente de dato.],
    [A-02], [Búsqueda sin coincidencias], [El estado vacío explica que no hay resultados y permite borrar filtros.], [Respuesta API y texto mostrado.],
    [A-03], [Presupuesto límite], [Precios numéricos válidos se aplican; entradas mal formadas reciben error sin romper página.], [Entrada, status HTTP y respuesta.],
    [A-04], [Restricción alimentaria], [Caso incompatible no se recomienda; dato desconocido no se marca compatible.], [Caso de regla y decisión.],
    [A-05], [Login no autenticado], [Muestra error genérico/rate-limit sin enumerar credenciales ni exponer secreto.], [HTTP, mensaje, estado de sesión.],
    [A-06], [CSRF ausente], [POST de cambio de estado se rechaza.], [Código de respuesta y log sin cuerpo.],
    [A-07], [Propietario equivocado], [No puede editar negocio que no le pertenece.], [Rol, recurso sintético y respuesta.],
    [A-08], [Importación de menú], [El análisis genera borrador y solo una confirmación explícita guarda cambios.], [Archivo, campos propuestos/corregidos.],
    [A-09], [Proveedor IA ausente], [La búsqueda base sigue disponible; los módulos IA informan no disponible.], [Configuración vacía y fallback.],
    [A-10], [Responsive], [Formulario y panel visual no se superponen a 375, 768, 1440 y 1920 px.], [Viewport, navegador, captura/resultado.],
    [A-11], [Vista de mesa/QR], [El ID de mesa se resuelve desde registro autorizado y no crea estado por parámetros manipulados.], [Contexto y decisión del servidor.],
    [A-12], [Pago de prueba], [Webhook firmado y consulta al proveedor confirman mismo pedido, moneda e importe.], [IDs sandbox, firma válida/inválida.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Matriz de aceptación priorizada para la vertical preliminar],
) <tab-acceptance-mvp>

Los casos A-11 y A-12 pertenecen a fases posteriores del roadmap y no deben mostrarse como aprobados por el hecho de que la matriz los incluya. La tabla convierte requisitos en escenarios de verificación; el estado inicial de cada caso es “pendiente de ejecución en entorno controlado”, salvo que exista una prueba actual asociada en `test/`.

#pagebreak()
#heading(numbering: none)[Anexo E. Glosario técnico]

*API.* Interfaz para que un componente solicite operaciones o datos a otro mediante contratos definidos.

*AR.* Realidad aumentada; superposición de elementos virtuales en una vista del entorno. Su ejecución depende de navegador, sistema y dispositivo.

*Blueprint.* Unidad Flask que agrupa rutas y comportamientos para registrarlos en una aplicación.

*CSRF.* Falsificación de petición entre sitios; un token y validación de origen ayudan a impedir que otra página fuerce una mutación autenticada.

*Dataset.* Conjunto de datos usados para pruebas, análisis o entrenamiento. Los archivos locales no equivalen necesariamente a datos de producción.

*Endpoint.* Dirección y método HTTP que expone una operación del servidor.

*Fixture.* Datos/servicios controlados que preparan una prueba reproducible.

*GLB.* Contenedor binario asociado a glTF que agrupa la descripción de escena y recursos del modelo 3D.

*Gantt.* Representación temporal de tareas, dependencias y duración mediante barras o marcas por período.

*GIN.* Índice PostgreSQL orientado a valores compuestos/documentos, incluido JSONB, que acelera ciertos operadores.

*JSONB.* Formato binario de PostgreSQL para documentos JSON con operadores e índices; no sustituye automáticamente un esquema relacional.

*Jinja.* Motor de plantillas utilizado para renderizar HTML en el servidor Flask.

*MVP.* Producto mínimo viable: alcance reducido para evaluar una hipótesis con comportamiento real y evidencia.

*OpenRouter.* Gateway de modelos que ofrece una API compatible con esquemas de chat; no es el modelo mismo.

*Psycopg.* Driver Python usado para conectarse a PostgreSQL y adaptar tipos de datos.

*RBAC.* Control de acceso basado en roles. La autorización también debe comprobar propiedad y alcance del recurso.

*RLS.* Seguridad a nivel de fila en PostgreSQL/Supabase, que restringe filas según política y rol.

*SSR.* Renderizado del lado del servidor; Flask/Jinja produce el HTML antes de enviarlo al navegador.

*Webhook.* Solicitud entrante de un proveedor, normalmente firmada, que avisa de un evento externo.

*JSON Schema.* Contrato que restringe forma, tipo y propiedades permitidas en datos estructurados.

*Pool de conexiones.* Conjunto acotado de conexiones reutilizables que reduce la apertura repetida al servidor de base.

*Rango semántico.* Intervalo de versiones de dependencia permitido por el archivo de requisitos.

*Localhost.* Nombre del equipo local; algunos navegadores lo consideran contexto seguro para pruebas.

*Pseudonimización.* Sustitución de identificadores directos por valores que reducen identificación inmediata, sin garantizar anonimato.

*Trazabilidad.* Relación verificable entre requisito, código, prueba, evidencia y estado.

*Timeout.* Límite de tiempo tras el cual una operación se interrumpe o reporta una espera excedida.

*Idempotencia.* Propiedad por la cual repetir una misma solicitud no duplica el efecto no deseado.

*JSONB payload.* Campo que conserva un documento flexible para una entidad o colección dentro de PostgreSQL.

*Consentimiento.* Elección documentada del usuario para una finalidad específica, como ubicación o comunicaciones.

*Borrador.* Propuesta editable que no se considera publicada o confirmada hasta una acción explícita.

*Snapshot.* Copia versionada de un estado publicado que no cambia con el borrador vigente.

*Soft realism.* Dirección visual que combina materiales, luz y volumen suaves con representación estilizada; no garantiza fotogrametría ni escala real.

*Geodistancia.* Distancia calculada sobre coordenadas geográficas; puede diferir del recorrido por calles.

*Completitud.* Proporción de campos requeridos presentes; no mide veracidad.

*P95.* Percentil 95 de una distribución de tiempos, que ubica el valor bajo el cual cae el 95 % de observaciones.

*Prueba de integración.* Verifica interacción entre componentes reales o controlados, no solo una función aislada.

*Prueba visual E2E.* Recorrido automatizado de UI en navegador, que puede verificar disposición e interacciones bajo un viewport definido.

#pagebreak()
#heading(numbering: none)[Anexo F. Estructura sugerida para la exposición APF3]

La guía APF3 asigna veinte minutos a la exposición y diez a preguntas. Esta secuencia propone distribuir el tiempo y conectar las diapositivas con el informe, sin crear ni dar por existente un archivo de presentación.

#figure(
  table(
    columns: (1.2fr, 0.8fr, 3.6fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Bloque*], [*Tiempo*], [*Contenido y evidencia*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Problema y continuidad APF2], [2 min], [Reto de elección gastronómica, alcance original y datos históricos por validar.],
    [Solución/MVP], [2 min], [Comensal, empresario y admin; vertical concreta de búsqueda y perfil.],
    [Stack y arquitectura], [4 min], [Flujo Flask → lógica → repositorio → PostgreSQL; tecnologías y límites.],
    [Demo guiada], [5 min], [Búsqueda controlada, ficha, filtros, compatibilidad y evidencia visual.],
    [Desarrollo y plan], [3 min], [Correcciones recientes, estado de pruebas, Gantt e hitos.],
    [Impacto y riesgos], [2 min], [Indicadores propuestos, privacidad, proveedores y trabajo fuera de alcance.],
    [Conclusiones], [2 min], [Decisiones, porcentaje no calculado sin backlog y próximos pasos.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Distribución sugerida de la exposición de veinte minutos],
) <tab-presentation-timing>

En la sección de preguntas se recomienda responder con la distinción entre código, integración, prueba y despliegue. Si se pregunta por “20 %”, explicar el alcance, el denominador aprobado y qué historia se aceptó. Si no existe medición, declarar que el repositorio prueba avance tangible, pero no porcentaje global. Si se pregunta por IA, explicar que el modelo prepara propuestas y el servidor valida y persiste únicamente después de una confirmación autorizada.

#pagebreak()
#heading(numbering: none)[Anexo G. Registro de pendientes antes de una entrega evaluable]

#figure(
  table(
    columns: (0.65fr, 2.2fr, 1.4fr, 2fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*ID*], [*Pendiente verificable*], [*Dueño inicial*], [*Evidencia de cierre*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [P-01], [Confirmar integrantes, docente, sección y fechas APF3.], [Equipo], [Portada corregida y aprobada.],
    [P-02], [Recuperar ficha metodológica de encuesta APF2 o repetir medición.], [Producto/validación], [Instrumento, muestra, consentimiento y datos anonimizados.],
    [P-03], [Revisar excepción de compatibilidad en recomendador.], [Backend], [Prueba negativa, cambio aprobado y regression test.],
    [P-04], [Ejecutar suite completa en PostgreSQL desechable.], [QA/DB], [Comando, versión, resultado y omisiones.],
    [P-05], [Repetir viewport 1920 px y guardar metadata.], [Frontend/QA], [Captura actual con navegador, commit y resolución.],
    [P-06], [Validar consulta OSM/Overpass sin sobrecargar proveedor.], [Backend], [Solicitud acotada, atribución y resultado/timeout.],
    [P-07], [Configurar mail/SMS de sandbox sin enviar a usuario real.], [Seguridad], [Prueba de entrega simulada, TTL, rate limit y logs limpios.],
    [P-08], [Definir presupuesto y permisos para integraciones.], [Producto/equipo], [Tabla de cuota, costo, consentimiento y límites.],
    [P-09], [Actualizar backlog ponderado y medir porcentaje.], [Equipo], [Aprobación de total y evidencia de tareas aceptadas.],
    [P-10], [Confirmar plan de despliegue, dominio y TLS antes de acceso público.], [Operaciones], [Entorno, checklist, rollback y health checks.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Pendientes que condicionan la siguiente versión del informe y la demo],
) <tab-pending-register>

El registro es un instrumento de trabajo. Ninguna fila se considera completada por aparecer en el anexo; el responsable debe adjuntar la evidencia indicada y fecha de cierre.
