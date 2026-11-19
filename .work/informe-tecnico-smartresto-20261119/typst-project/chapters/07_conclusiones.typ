= Conclusiones y próximos pasos

== Conclusiones parciales

SmartResto cuenta con una base técnica que rebasa el nivel de bosquejo: la aplicación Flask organiza sesiones, blueprints, dominios, repositorios y reglas; los templates y assets representan interfaces concretas; las guías de fase describen flujos empresariales, descubrimiento y comercio; y existen pruebas por módulo. Esa evidencia permite exponer un desarrollo preliminar real. No acredita por sí sola que la aplicación completa esté operativa en producción ni que el alcance de dieciocho fases haya sido terminado.

La selección de tecnologías mantiene coherencia con el objetivo original. Flask y PostgreSQL/Supabase sostienen una aplicación web unificada; HTML/Jinja y JavaScript proporcionan las pantallas; mapas, bibliotecas de importación, reglas lógicas y proveedores IA se integran en tareas identificables. Los modelos 3D GLB añaden una experiencia visual premium, pero escala, AR, costo, disponibilidad y calidad del contenido requieren validaciones separadas. Una mayor cantidad de tecnologías no es evidencia automática de mayor transformación digital.

La arquitectura de datos ofrece flexibilidad mediante JSONB, pero las guías identifican consultas que recorren colecciones en Python y tareas de integridad que requieren decisión manual. No debe desplegarse un cambio de esquema por la sola presencia de SQL en el repositorio. La capa central de conexión y el pool aportan controles locales, aunque todo cambio en tablas, índices, TLS o políticas requiere pruebas de staging y aprobación de responsables.

El código y las capturas de autenticación muestran una experiencia visual desarrollada, con el estilo premium de realismo 3D suave como dirección. La composición de acceso quedó alineada a un grid 40/60 y la recuperación comparte el layout. Las capturas disponibles no registran su commit ni su navegador de origen y por eso se citan como evidencia visual almacenada, no como grabación de la versión actual.

Las pruebas de esta sesión respaldan calidad local en el subconjunto que pudo ejecutarse sin secretos ni DSN reales. El resultado fue de 414 pruebas aprobadas, 67 omitidas y un timeout visual a 1920 px; el caso repetido por separado pasó. Esta ejecución no reemplaza las pruebas de escritura en PostgreSQL desechable ni los servicios externos omitidos. Los resultados anteriores de más de 440 pruebas en `CONECTIVIDAD.md` corresponden a otros entornos y cortes.

La rúbrica solicita aproximadamente 20 % de desarrollo. El repositorio demuestra avance tangible, pero no contiene una medida reproducible del porcentaje total. No se debe inferir ese porcentaje por archivos o líneas de código. Para defenderlo académicamente, el equipo necesita un backlog ponderado, criterios de aceptación, fecha de corte, responsables y evidencia de pruebas aprobadas por historia.

== Próximos pasos priorizados

*Prioridad 1: rebase y propiedad del trabajo.* Confirmar integrantes, sección, docente, fechas y reparto de tareas para APF3; el informe los trasladó desde el APF2 y no presupone que sigan vigentes. Recuperar ficha técnica del sondeo y separar lo que puede ser citado de lo que requiere una nueva muestra. Aprobar el backlog ponderado y delimitar el MVP a búsqueda, filtros, catálogo y recomendación determinista.

*Prioridad 2: cerrar el riesgo de compatibilidad.* Revisar el fallback de `logic/recommender.py` que devuelve compatible ante excepción. Añadir pruebas que obliguen al comportamiento conservador frente a una exclusión, dato ausente, error de proveedor o perfil vacío. La salida “no evaluada” debe distinguirse de una compatibilidad afirmativa. Revisar las rutas relacionadas y comprobar permisos de recurso, no solo sesión.

*Prioridad 3: demostrar una vertical con datos controlados.* Ejecutar el recorrido en PostgreSQL desechable con TLS y esquemas instalados. Registrar versión del commit, comando, ambiente, fixture, resultado, omisiones y fallos. Capturar los estados de carga, error, sin resultados y éxito a móvil y escritorio; incluir navegador y resolución en el pie de cada captura. No usar datos reales sin consentimiento.

*Prioridad 4: medir usabilidad del MVP.* Recuperar o repetir entrevistas y tareas con estudiantes y al menos un negocio, con consentimiento y anonimización. Comparar tiempo de búsqueda manual y con SmartResto mediante el mismo guion. Documentar muestra, criterios de relevancia y limitaciones. Una prueba pequeña debe emplearse para iteración, no como estimación representativa de la ciudad.

*Prioridad 5: cerrar integraciones en secuencia.* Probar mapas autorizados y atribuidos; luego la extracción IA en una página autorizada; después correo/SMS en entorno sandbox; posteriormente pagos con vendedores/compradores de prueba. Dejar para una fase posterior el pipeline de producción, carga sostenida, modelos GLB exactos y previsión cuando haya suficientes datos. Ningún proveedor se debe activar sin presupuesto, política de datos, límites y comportamiento de degradación.

== Decisión técnica recomendada

El equipo puede perseverar en SmartResto como plataforma común si obtiene evidencia de que la búsqueda y el catálogo resuelven un problema frecuente para sus usuarios, si los negocios mantienen información actualizada y si la infraestructura sostiene la interacción sin costos fuera del alcance. Si la cobertura de datos o el mantenimiento empresarial son barreras, conviene ajustar el MVP al subconjunto que genera valor antes de ampliar inventario, pagos, Smart Flow o analítica.

La siguiente entrega debe mostrar menos módulos, pero con mayor profundidad de verificación: una consulta desde la interfaz, autorización en servidor, lectura de datos de prueba, aplicación de reglas, resultado comprensible, manejo de error y prueba reproducible. Ese flujo tendrá más valor para la rúbrica que afirmar que toda la visión de dieciocho fases está completa.
