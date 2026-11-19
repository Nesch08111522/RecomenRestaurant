= Plan de trabajo del proyecto

== Enfoque y horizonte temporal

El APF2 registró la semana 10 como semana actual y propuso trabajo entre las semanas académicas 10 y 18. Conserva la secuencia de recuperar evidencias, validar el problema, probar prototipos, construir el MVP, probar reglas, hacer QA, pilotear y analizar resultados. Este capítulo actualiza esa lógica como plan de nueve semanas. Las semanas se presentan como hitos relativos del curso, no como fechas calendario confirmadas; el docente y el equipo deben rebaselarlas según el cronograma de entrega (Cabanillas Llontop et al., 2026, pp. 21–22).

El alcance del plan es un MVP verificable de descubrimiento y recomendación contextual, con un flujo de autenticación y catálogo como base. Los dieciocho dominios del plan maestro sirven para ordenar la evolución, pero no deben ejecutarse en paralelo ni convertirse en condición para completar la demo. Pagos, inventario por receta, predicción, IA de publicación y realidad aumentada se mantienen fuera del primer piloto salvo que el equipo demuestre una dependencia y acuerde un incremento separado.

== Gantt propuesto

La barra `●` indica semanas de trabajo planeado. Un bloque de desarrollo termina con un entregable verificable; la columna final establece el punto de control. Las tareas pueden solaparse únicamente cuando no dependen de datos o aprobaciones pendientes. La distribución no representa trabajo ejecutado.

#figure(
  table(
    columns: (2.6fr, 0.48fr, 0.48fr, 0.48fr, 0.48fr, 0.48fr, 0.48fr, 0.48fr, 0.48fr, 0.48fr, 1.4fr),
    stroke: none,
    inset: (x: 3.5pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Trabajo y evidencia de cierre*], [*10*], [*11*], [*12*], [*13*], [*14*], [*15*], [*16*], [*17*], [*18*], [*Hito*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Línea base del repositorio, responsables y datos pendientes], [●], [●], [], [], [], [], [], [], [], [M0: inventario acordado],
    [Recuperación de instrumentos y entrevistas con consentimiento], [], [●], [], [], [], [], [], [], [], [M1: evidencia primaria],
    [Validar problema, journey, criterios de aceptación y prototipo], [], [], [●], [●], [], [], [], [], [], [M2: prototipo probado],
    [Vertical MVP: alta, catálogo y búsqueda acotada], [], [], [], [], [●], [], [], [], [], [M3: flujo ejecutable],
    [Filtros y recomendación determinista con explicación], [], [], [], [], [], [●], [], [], [], [M4: reglas reproducibles],
    [QA funcional, seguridad básica, accesibilidad y responsive], [], [], [], [], [], [], [●], [], [], [M5: regresiones priorizadas],
    [Piloto pequeño con estudiantes y un negocio, si hay consentimiento], [], [], [], [], [], [], [], [●], [], [M6: observaciones sin extrapolar],
    [Analizar resultados, riesgos y decisión de iteración], [], [], [], [], [], [], [], [], [●], [M7: paquete de cierre],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Cronograma Gantt propuesto para la ventana académica 10–18],
) <fig-gantt-apf3>

== Hitos y definición de terminado

M0 cierra cuando el equipo confirma el repositorio de referencia, versiones, responsables y ubicación de evidencias. El entregable es una matriz de requisitos a código y una lista de brechas; no debe contener claves ni datos personales. M1 requiere recuperar la ficha técnica de las encuestas, las preguntas, el tamaño y selección de la muestra, el consentimiento y notas anonimizadas. Si esos insumos no están disponibles, el informe identifica cada porcentaje del APF2 como histórico y no prepara conclusiones poblacionales.

M2 entrega un prototipo de descubrimiento probado por tareas: buscar un tipo de comida, filtrar por distrito o presupuesto, inspeccionar ficha y explicar por qué una tarjeta aparece. Se registran errores de comprensión y cambios en etiquetas. M3 agrega el mínimo flujo con autenticación si la búsqueda restringida lo exige; el backend valida valores, la consulta devuelve datos de prueba y la interfaz presenta resultados vacíos, cargando y error.

M4 debe demostrar recomendaciones reproducibles con casos positivos y negativos. Una restricción alimentaria desconocida no se interpreta como compatible. M5 conserva un reporte por navegador y tamaño, los defectos encontrados y los defectos corregidos. M6 es un piloto con consentimiento explícito; se limita al grupo disponible y no se generaliza. M7 presenta medidas observadas, incidencias, límites de muestra y una decisión sustentada de continuar, ajustar o pivotar.

La definición de terminado por incremento combina cinco piezas que exige el plan maestro: interfaz, backend, base de datos/migración, integraciones cuando correspondan y pruebas. Una pantalla sin autorización del servidor no cierra la función; una tabla creada sin una ruta que la use tampoco. La validación de negocio debe especificar quién puede crear, modificar y ver cada registro.

== Recursos y condiciones de ejecución

El recurso de desarrollo existente es el repositorio local `RecomenRestaurant`, un entorno virtual Python y el set de pruebas. Para QA se necesita una base PostgreSQL desechable con los esquemas descritos en README; las pruebas de escritura no deben usar el DSN operativo. Se requieren credenciales ficticias o proveedores simulados para IA, servicio de mapas de prueba, navegadores compatibles y una lista de datos gastronómicos sintéticos. La sesión que redactó este informe bloqueó DSN y claves antes de ejecutar la suite completa.

Los recursos humanos se limitan a cuatro integrantes indicados en el APF2. El reparto siguiente es una propuesta de planificación, no un registro de habilidades ni de tareas históricas; el equipo debe aprobarlo antes de incorporarlo como compromiso formal.

#figure(
  table(
    columns: (0.5fr, 1.8fr, 2.2fr, 1.7fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Rol*], [*Asignación sugerida*], [*Responsabilidad propuesta*], [*Decisión que valida*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [A], [Cabanillas Llontop, Diego Rodrigo], [Producto, contacto con usuarios y coherencia del problema.], [Aprobación de criterios con evidencia primaria.],
    [B], [Lujan Zavaleta, Wilmer Enrique], [Backend, persistencia y contratos de API.], [Aprobación de consultas, permisos y datos de prueba.],
    [C], [Paredes Azabache, Miguel Alejandro], [Frontend, prototipo, accesibilidad y consistencia visual.], [Aprobación de recorridos y capturas QA.],
    [D], [Sandoval Chacón, Nancy Elizabeth], [Integración, pruebas, seguridad y documentación del avance.], [Aprobación de evidencias y cierre de defectos.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Responsabilidades de trabajo propuestas para validar con el equipo],
) <tab-roles-proposed>

La duración se estima por nueve semanas relativas. El APF2 no consigna horas por persona ni disponibilidad semanal, de modo que no se inventan horas-persona. Antes del inicio, el equipo debe asignar dedicación, vacaciones/feriados y fechas. Si los recursos no alcanzan, se reduce alcance en vez de mantener fechas ficticias.

== Costos y dependencias de servicio

No se cuenta con cotizaciones vigentes ni presupuesto aprobado. Por ello, el informe no declara la plataforma gratuita ni asigna montos a proveedores. El coste total del piloto se debe calcular a partir de hosting, PostgreSQL, almacenamiento de imágenes y modelos, consultas de mapas/geocodificación, tokens del proveedor IA, correo/SMS, dominio y medios de pago si se incorporan. Las pruebas pueden usar stubs y datos sintéticos para evitar cargos no autorizados.

La selección de proveedor se cierra antes del trabajo que la necesita: mapa para calcular proximidad; IA para extracción opcional; correo/SMS para recuperación de cuenta; pagos para una fase posterior. Cada integración requiere límites, gestión de errores, tiempo de espera, política de reintentos y trazabilidad sin cuerpos ni claves. Una respuesta del proveedor no puede publicar un menú, alterar precio o confirmar un pago sin reglas de servidor.

== Riesgos del plan y respuesta

#figure(
  table(
    columns: (1.45fr, 2.2fr, 2.3fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Riesgo*], [*Efecto en la entrega*], [*Respuesta planificada*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Instrumentos del APF2 no recuperados], [Los porcentajes históricos no sustentan estimaciones actualizadas.], [Solicitar ficha e instrumentos; reportar ausencia y reemplazar por piloto exploratorio.],
    [Esquema JSONB y relación no normalizada], [Queries de catálogo o permisos dependen de colecciones y entorno.], [Pruebas aisladas, contratos y consultas reales autorizadas; no DDL productivo automático.],
    [Proveedor IA no disponible o con costo], [Se interrumpe una función asistida, no el flujo determinista básico.], [Diseño degradable, mock local, presupuesto y confirmación humana.],
    [Timeout/red de base], [Búsqueda o autenticación puede devolver error seguro.], [Prueba con BD desechable, timeouts y captura de error; no reintentar escrituras automáticamente.],
    [Usuarios/negocio sin consentimiento], [No procede piloto con datos reales.], [Posponer piloto o usar datos sintéticos, anonimización y autorización documentada.],
    [Alcance de fases crece], [No se cierra vertical del MVP.], [Priorizar búsqueda y filtro; diferir pagos, IA predictiva, AR y ERP.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Riesgos principales y respuesta propuesta],
) <tab-risk-plan>

== Puerta de control de avance

El porcentaje APF3 esperado por la rúbrica no se debe calcular por cantidad de archivos, líneas de código, carpetas o funciones planificadas. La medida propuesta es suma ponderada de historias aceptadas dividida por puntos de esfuerzo aprobados antes del periodo, multiplicada por cien. El backlog y sus pesos no se recuperaron para este informe; por tanto, no se puede certificar “20 % ejecutado”. El corte sí acredita una base de software amplia, correcciones recientes, pruebas y evidencia visual histórica, pero no cubre por igual todos los módulos de la visión.

Antes de presentar una cifra, el equipo debe acordar denominador, historias, criterios de aceptación, fecha de corte y estado de cada historia. Se considera “aceptada” solo con entrega de interfaz, backend y persistencia cuando aplique, más caso de prueba. Las tareas bloqueadas por proveedor o datos quedan en progreso, no se cuentan como terminadas.
