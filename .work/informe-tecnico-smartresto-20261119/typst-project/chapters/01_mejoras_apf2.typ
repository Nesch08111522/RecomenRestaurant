= Mejoras sobre el Avance 2

== Propósito de esta entrega y continuidad del problema

El Avance de Proyecto Final 3 solicita actualizar el avance anterior, seleccionar tecnologías relacionadas con la propuesta, justificar su uso, planificar recursos y responsables, evidenciar desarrollo preliminar, analizar impactos y cerrar con próximos pasos. La guía también reserva veinte minutos para la exposición y diez para preguntas. El presente documento se organiza conforme a esos apartados y separa el estado del código de lo que solo está descrito en los documentos del equipo (Curso Innovación y Transformación Digital, 2026a, pp. 1–2; Curso Innovación y Transformación Digital, 2026b).

El APF2 delimitó SmartResto como una plataforma para ayudar a estudiantes universitarios de Trujillo a descubrir restaurantes y platos según presupuesto, ubicación y restricciones alimentarias. El problema principal era la fricción en la elección, no una carencia general de restaurantes. Esa delimitación sigue siendo útil para ordenar el MVP y evitar que las fases futuras de inventario, pagos, realidad aumentada o cocina en casa se presenten como parte del primer resultado verificable (Cabanillas Llontop et al., 2026, pp. 4–8).

El APF2 reportó que 69,6 % de las personas consultadas recurría a plataformas genéricas y que 47,8 % dedicaba entre cinco y diez minutos a una búsqueda manual. En este informe esos valores se conservan como datos históricos que aparecen en el APF2. La ficha metodológica y los datos primarios no se recuperaron en el alcance actual; por ello no se actualizan, no se extrapolan a la población de Trujillo ni se usan como medición de impacto presente (Cabanillas Llontop et al., 2026, p. 4).

== Mejora de alcance: MVP frente a plan maestro

El segundo documento suministrado organiza SmartResto en dieciocho fases, desde arquitectura y perfiles hasta despliegue. Sirve como mapa de intención, pero no constituye evidencia de que las dieciocho fases estén terminadas. La revisión del repositorio encuentra código en varias de ellas y dependencias o brechas en otras. El informe, por tanto, utiliza la fase como agrupación del trabajo y asigna el estado a cada una según archivos, rutas, plantillas, pruebas y reportes disponibles (Plan maestro de desarrollo de SmartResto, s. f.).

La mejora frente a una descripción de producto puramente aspiracional consiste en distinguir tres niveles: el núcleo del descubrimiento, los flujos comerciales parcialmente integrados y las capacidades de evolución. El núcleo incluye búsqueda, fichas, cuentas, catálogos y lógica de recomendación. La compra, los pagos, la verificación de disponibilidad y la actualización operativa requieren evidencia adicional de integración. La cocina doméstica, la predicción basada en datos abundantes y la operación AR universal permanecen como visión o como capacidades condicionadas, no como resultados demostrados.

El APF2 ya recomendaba limitar las afirmaciones de impacto, diferenciar datos confirmados de datos declarados y usar recomendaciones deterministas antes de delegar restricciones críticas a IA generativa. El APF3 hace esa recomendación trazable a los módulos presentes. Por ejemplo, la salida de una propuesta IA puede preparar un borrador; el código exige revisión o confirmación antes de publicar en ciertos flujos. Un borrador no se clasifica como catálogo validado ni como publicación completada.

#pagebreak()
== Criterios utilizados para clasificar el estado

La clasificación responde a la instrucción de APF3 y al prompt maestro entregado. “Implementada” se reserva para una función con evidencia de código y funcionamiento suficiente en el alcance disponible. Cuando hay handlers, plantillas o lógica, pero no una prueba integral o integración, se usa “código presente; no verificado en extremo a extremo”. “Parcial” indica una etapa funcional acompañada por proveedor, datos, permisos, aprobación o componente faltante. “Planificada” se aplica solo cuando el documento la sitúa explícitamente en una hoja de ruta. “En pruebas” identifica un comportamiento sometido a pruebas con cobertura incompleta.

#figure(
  table(
    columns: (1.2fr, 2.6fr, 2.6fr),
    stroke: none,
    inset: (x: 7pt, y: 6pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Estado*], [*Qué lo respalda*], [*Qué no permite afirmar*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Implementada y verificada localmente], [Código más resultado reproducible de prueba local o evidencia visual verificable para ese comportamiento.], [No implica disponibilidad en producción, datos reales ni servicios externos operativos.],
    [Código presente; integración no verificada], [Ruta, función, plantilla o cliente aparecen en fuentes revisadas.], [No prueba que el Blueprint esté registrado, que la API responda o que la pantalla se haya recorrido en esta entrega.],
    [Parcial], [Se observa una parte del flujo y el propio código/documento identifica condiciones, faltantes o aprobación humana.], [No equivale al proceso completo ni a un resultado de negocio.],
    [En pruebas], [Existe un conjunto de casos o una ejecución local, pero queda cobertura omitida, fallo transitorio o dependencia no disponible.], [No se presenta como certificación, QA exhaustivo ni prueba de carga.],
    [Planificada], [Documento de visión o plan maestro la identifica como desarrollo futuro.], [No se cuenta como componente implementado por estar descrito.],
    [No verificada], [La evidencia disponible no permite resolver uso, integración, versión, configuración o resultado.], [No se interpreta como inexistente; requiere otra comprobación.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Criterios de lectura de la evidencia técnica],
) <tab-state-criteria>

El corte documental corresponde al repositorio leído el 19 de noviembre de 2026. El identificador corto del `HEAD` era `3725a99`; el árbol de trabajo registraba 54 entradas con cambios al capturarse el corte. Por tanto, la evidencia describe una copia local no congelada en un commit limpio. La portada conserva los datos académicos del APF2 como referencia y advierte que integrantes, códigos, docente y sección deben confirmarse para esta entrega.

== Evidencia nueva y cambios recientes observables

El trabajo inmediato de esta sesión dejó correcciones acotadas en autenticación, tema, recuperación y salón. La composición de autenticación quedó alineada a un grid 40/60: el panel visual se mantiene en la primera columna y el formulario en la segunda; el canvas se contiene dentro de su celda para no desplazar los controles. La recuperación se incorporó al patrón de acceso común y el pie público sustituyó un color literal por un token de superficie.

También se corrigió una indentación en `views/salon.py`: la importación `models.flow` vuelve a quedar dentro de la ruta `desk(rid)`. La comprobación `py_compile` completó sin error después del cambio. No se alteró la lógica de la función. En `test/test_openrouter.py` se aislaron las lecturas de catálogo con dobles de prueba para que esa prueba no requiera una base externa.

La suite completa ejecutada en esta sesión, con DSN y credenciales de proveedores vacíos dentro del proceso, reportó 414 pruebas aprobadas, 67 omitidas y un timeout del escenario visual de autenticación a 1920 px. La repetición individual de ese escenario pasó. El resultado se informa como una ejecución aislada con un timeout no reproducido, no como una suite sin incidencias; las pruebas omitidas no validan los componentes que dependen de ellas.

== Correspondencia con la rúbrica

El entregable aborda los apartados exigidos y agrega trazabilidad entre selección de tecnologías, ubicación del código y experiencia visible. El plan de trabajo se formula como propuesta a rebaselinar con el calendario académico. El desarrollo preliminar se apoya en archivos fuente, capturas QA existentes y resultados de tests de esta sesión. La equivalencia exacta a “20 % del proyecto” no se deduce contando archivos; requiere una lista de tareas ponderadas aprobada por el equipo.

#figure(
  table(
    columns: (1.5fr, 3.7fr, 1.2fr),
    stroke: none,
    inset: (x: 7pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Criterio AV3*], [*Sección y evidencia dentro del informe*], [*Condición*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Mejoras sobre APF2], [Comparación del alcance, preservación del problema y precisión de cifras históricas.], [Datos primarios por recuperar.],
    [Selección tecnológica], [Matriz de requisitos y grupos funcionales del stack.], [Versiones son requisitos, no instalación.],
    [Justificación técnica], [Ventajas, límites, módulos, localización en código y apariencia de UI.], [Uso real marcado con caveats.],
    [Plan de trabajo], [Gantt propuesto, hitos, recursos, responsables tentativos y criterios de aceptación.], [Aprobación del equipo pendiente.],
    [Desarrollo preliminar], [Flujo vertical de autenticación/búsqueda, paneles, 3D de referencia y pruebas locales.], [Porcentaje global no calculado.],
    [Impacto esperado], [Efectos tecnológicos, organizacionales, económicos y sociales con indicadores propuestos.], [No se atribuye impacto medido.],
    [Conclusiones y siguientes pasos], [Riesgos, prioridades, decisiones y evidencia faltante.], [Fases futuras separadas.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Trazabilidad del informe respecto de la rúbrica de Avance 3],
) <tab-rubric-map>

== Delimitaciones que cambian la interpretación

La presencia de un Blueprint no demuestra que la aplicación lo registre en todas las configuraciones. Una plantilla que declara una URL no confirma que el endpoint responda, que el usuario tenga autorización o que los datos se guarden. Una regla de negocio que devuelve tarjetas no establece cuál de los motores alternativos se invoca en producción. Estas diferencias se mantienen en cada ficha de módulo y evitan inferir una experiencia completa a partir de un solo archivo.

El repositorio incluye reportes de conectividad y QA con resultados históricos. Los valores documentados por `CONECTIVIDAD.md`, como una reducción observada de latencia en tres muestras, no se vuelven a presentar como benchmark de este informe. Lo mismo ocurre con los conteos de pruebas que aparecen en documentos anteriores: se conservan como registros históricos y se separan del test actual de esta sesión.
