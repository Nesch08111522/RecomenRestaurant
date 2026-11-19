= Impacto esperado de la solución

== Criterio de evaluación

El impacto de SmartResto es una hipótesis de producto, no un resultado medido en esta entrega. El APF2 plantea reducir fricción de búsqueda y acercar la oferta gastronómica local al público universitario; sus porcentajes de encuesta son históricos y requieren recuperar ficha técnica. Para verificar beneficios futuros se necesita comparar tareas reales con una línea base, describir la muestra y registrar resultados sin atribuir causalidad a una sola pantalla.

Se consideran cuatro dimensiones de la rúbrica: tecnológica, organizacional, económica y social. También se registra privacidad y sostenibilidad operativa porque las funciones usan ubicación, perfiles, fotografías, proveedores IA, almacenamiento, pedidos y notificaciones. Ninguna dimensión se declara positiva por la sola existencia de una función.

== Impacto tecnológico

La arquitectura común puede reducir duplicación de cuentas, negocios y catálogos entre marketplace, portal empresarial y mercado. El beneficio esperado depende de conservar IDs canónicos y permisos de negocio. Si cada fase crea una copia separada, los cambios de precio, sucursal o disponibilidad divergen. El repositorio todavía combina documentos JSONB con escrituras relacionales selectivas; las consultas completas en Python y la integridad del esquema son límites que deben medirse antes de ampliar volumen.

El uso de proveedores de mapas e IA puede acelerar búsqueda, geocodificación y preparación de borradores. A cambio, agrega disponibilidad externa, políticas, cuotas, costos, límites geográficos y tratamiento de datos. Una respuesta generada no es dato comercial verificado. SmartResto reduce ese riesgo cuando guarda una propuesta como draft y exige confirmar. El mapa debe dejar alternativa manual; la recomendación básica debe funcionar sin proveedor generativo.

La capa visual premium 3D soft realism puede distinguir fichas e identidad gastronómica, pero exige activos GLB, fotografías coherentes, peso controlado y escala revisada. El visor no sustituye fotos reales ni información de ingredientes. El impacto se medirá por comprensión y conversión de tareas, no por el número de modelos alojados.

== Impacto organizacional

Para restaurantes pequeños, el portal y el catálogo podrían reunir descripción, horario, menú, ofertas y formas de atención en un canal editable. La operación puede facilitar actualización de menú y coordinación de pedidos. La contrapartida es una nueva carga de mantenimiento: corregir precios, registrar stock, responder reclamos, moderar contenido y verificar derechos de imágenes. Si el empresario necesita duplicar datos en otros canales, el valor de una página propia puede reducirse.

Para estudiantes, el buscador pretende disminuir trabajo de comparar fuentes dispersas. El beneficio requiere cobertura suficiente de negocios, datos recientes y criterios comprensibles. Una tarjeta que no muestra horario o disponibilidad puede empeorar la decisión en lugar de simplificarla. El sistema debe comunicar campos no verificados y ofrecer un medio de corrección.

Para el equipo, el monolito modular facilita una sola ruta de publicación y reduce costos de operar servicios separados. También crea concentración de riesgo: una falla de sesión, base o despliegue puede afectar muchos módulos. La planificación incremental, las pruebas por contrato y límites entre dominios reducen ese riesgo.

== Impacto económico esperado

Los empresarios podrían obtener mayor visibilidad, consultas atribuidas, pedidos programados y herramientas para estimar costos por receta. La plataforma podría capturar valor mediante suscripción, tarifa o servicio, pero los modelos de ingresos incluidos en el APF2 son hipótesis. No se dispone de cotización de hosting, almacenamiento, Google Places, OpenRouter, Gemini, mensajería, Mercado Pago o dominio. Por ello no se afirma rentabilidad, costo cero ni disposición a pagar.

El costo variable por flujo debe estimarse separando infraestructura fija, almacenamiento/transferencia, llamadas a proveedor y comisiones de pago. Antes del piloto es posible medir el costo por propuesta IA y el costo por pedido completado en condiciones de prueba, pero no extrapolarlo a un volumen futuro sin un supuesto documentado.

Para un negocio, el margen por plato solo puede calcularse cuando existen costos completos de receta y lotes vigentes. Si faltan ingredientes o mermas, se debe marcar cobertura incompleta. El dashboard no debe atribuir un aumento de ventas a una promoción sin grupo de comparación o diseño de evaluación.

== Impacto social y experiencia de usuario

El producto puede apoyar a personas que deciden con restricciones de presupuesto, tiempo, distrito o alimentación. La exposición de filtros debe evitar inferencias médicas: los ingredientes y alérgenos son declaraciones del restaurante y no una certificación clínica. Ante información incompleta, el sistema debe mostrar incertidumbre o excluir una recomendación según la regla elegida por el usuario.

La búsqueda por texto y distrito puede ser más inclusiva que exigir ubicación GPS. Una interfaz responsive facilita el acceso desde móvil, pero no demuestra accesibilidad completa. Es necesario verificar contraste, navegación por teclado, mensajes de error, etiquetas de formularios, lectores de pantalla, tamaños de texto y alternativas a mapas/voz.

La reputación comercial puede reducir la asimetría entre negocios y clientes si las reseñas verificadas se moderan con criterios transparentes. Puede perjudicar a pequeños negocios si un error de identidad o una reseña falsa cambia su visibilidad. Los procesos de reclamo, revisión y reversión deben conservar evidencia y permitir una respuesta documentada.

== Privacidad, confianza y externalidades

Las coordenadas, restricciones alimentarias, historial, identificadores de compra, fotos y códigos de recuperación son datos que pueden revelar rutinas o preferencias. La arquitectura de privacidad propuesta minimiza la información enviada a IA, solicita consentimiento separado por ubicación, comunicaciones y marketing y evita incluir contactos en contextos de Copilot. Esa separación debe verificarse en cada ruta y en los logs. No se declara cumplimiento legal por disponer de controles técnicos; hace falta revisión de tratamiento, retención, base legal y proveedores.

Las imágenes de platos, negocios y usuarios requieren autorización y una política de retiro. Los videos referenciados no deben descargarse o republicarse sin permiso. El radar excluye la extracción indiscriminada de plataformas restringidas; una URL visible no equivale a licencia de uso. Las fichas temporales deben mostrar procedencia y estado de verificación.

El servicio de mapas puede trasladar solicitudes y coordenadas a un proveedor. El usuario debe conocer esa transferencia. Las llamadas IA podrían transmitir consultas de búsqueda y contenidos de menú. Para minimizar exposición, el backend envía solo campos necesarios, limita el texto y excluye datos de contacto. El despliegue deberá establecer retención y acuerdos contractuales.

== Indicadores para medir el piloto

La tabla siguiente define mediciones prospectivas y sus denominadores. Las líneas base no se rellenan con supuestos. El equipo debe fijar cada instrumento, período y tamaño de muestra antes de recoger datos.

#figure(
  table(
    columns: (1.25fr, 2.6fr, 2.2fr),
    stroke: none,
    inset: (x: 6pt, y: 5pt),
    fill: (_, y) => if y > 0 and calc.even(y) { rgb("#F7F0EA") } else { none },
    table.hline(stroke: 1pt + rgb("#555555")),
    table.header([*Dimensión*], [*Indicador propuesto y fórmula*], [*Evidencia a levantar*]),
    table.hline(stroke: 0.5pt + rgb("#888888")),
    [Descubrimiento], [Mediana de minutos entre inicio de tarea y selección de una opción; comparar con mismo guion y tarea manual.], [Grabación de tiempo, tarea, perfil y número de opciones revisadas.],
    [Relevancia], [Resultados juzgados pertinentes en las primeras k posiciones / k; mantener k fijo y criterio previo.], [Muestra de consultas evaluadas por dos revisores.],
    [Restricciones], [Recomendaciones bloqueadas o advertidas ante exclusión / casos con exclusión declarada.], [Casos positivos, negativos e información desconocida; no usar IA como fuente de verdad.],
    [Facilidad de uso], [Tareas completadas sin ayuda / tareas intentadas.], [Errores, retrocesos, dudas y comentarios de participantes.],
    [Catálogo], [Registros con campos obligatorios actuales / total de registros evaluados.], [Fecha de actualización, procedencia y campos faltantes.],
    [Operación de menú], [Minutos de edición hasta un preview válido; proporción de borradores corregidos por el empresario.], [Registro de importación, cambios y revisión final.],
    [Costo], [Costo variable atribuible / transacciones completadas o propuestas aceptadas.], [Consumo de proveedor, moneda, fecha y cuota usada.],
    [Confiabilidad], [Solicitudes exitosas / intentos elegibles y tasa de errores por dependencia.], [Estado HTTP, timeout, fixture, proveedor y fecha; sin secretos.],
    [Privacidad], [Eventos con consentimiento verificable / eventos que requieren permiso.], [Registros de consentimiento, revocación y acceso; nunca almacenar PII innecesaria.],
    table.hline(stroke: 1pt + rgb("#555555")),
  ),
  caption: [Marco de medición del impacto sin resultados inventados],
) <tab-impact-metrics>

No se asignan metas numéricas antes de obtener línea base y tamaño de muestra. Para comparar alternativas, el protocolo debe definir tarea, población, exposición, criterios de “pertinente”, tiempo, tratamiento de abandono y análisis. Un piloto con pocos participantes sirve para encontrar problemas y ajustar hipótesis; no representa automáticamente a todos los estudiantes de Trujillo.

== Balance del impacto

El valor esperado de SmartResto no se limita a acumular tecnologías. Depende de que las capas de negocio y datos reduzcan incertidumbre sin ocultarla; de que el empresario mantenga información veraz; y de que la experiencia siga siendo útil cuando IA, GPS o AR no estén disponibles. El impacto debe juzgarse con datos de uso consentidos, transacciones observadas y costos completos, y publicarse junto con sus limitaciones.
