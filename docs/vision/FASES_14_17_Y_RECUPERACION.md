# SmartResto: menú inmersivo, inteligencia, Copilot y confianza

Implementación y alcance — 18 de noviembre de 2026 (America/Lima).

## Accesos

- `/inteligencia`: administrador y empresarios; la información se filtra por propiedad antes de consultar operaciones. Permite período de 7/30/90 días, intervalo de hasta 366 días y selección de negocio.
- `/api/inteligencia`: informe agregado privado, sin contactos de clientes.
- `/copilot`: asistente autenticado para comensal, empresario y administrador.
- `/admin/confianza`: supervisión administrativa de integraciones, duplicados, modelos, contenido, incidencias y auditoría.
- `/auth/recuperar`: solicitar código al contacto asociado o utilizar la clave de recuperación previamente guardada.
- `/auth/seguridad`: asociar correo y teléfono confirmando contraseña actual y autenticador, si está habilitado.

## Fase 14: visor de platos

El negocio puede subir un GLB autocontenido de hasta 1,5 MB, con un máximo de 500 nodos y 200 mallas. Las texturas incorporadas se validan y se limitan a 4096 píxeles por lado y 16 megapíxeles. No se aceptan URI externas ni extensiones que requieran decodificadores de terceros.

Cada presentación se asocia a una oferta. Cambiar de variante conserva la relación con su propia fotografía, modelo, fecha, porción y precio. El visor se descarga solo al pulsar Cargar modelo. Incluye giro manual, zoom, vistas frontal/lateral/superior, rotación voluntaria y comparación con la fotografía publicada por el negocio. El visor y Chart.js se sirven localmente, con sus licencias en `static/vendor`.

El negocio declara ancho, alto, profundidad (cm) y porción (g). El servidor no permite que el propietario se marque como escala verificada. Un administrador debe revisar las medidas; el visor comprueba además la proporción del GLB antes de habilitar AR con escala fija. Sin medidas aprobadas se mantiene la exploración 3D y se informa que la escala no está garantizada. AR requiere HTTPS o localhost y un dispositivo compatible; no se afirma una prueba física en todos los teléfonos. Una foto con relieve no es una reconstrucción completa de 360 grados.

Las herramientas de visión y de generación editorial existentes ayudan a preparar descripciones e imágenes. No se ha conectado un proveedor que reconstruya automáticamente GLB exactos a partir de una sola fotografía; los modelos reales los aporta y confirma el negocio.

## Fase 15: inteligencia y predicción

Se calculan ventas pagadas y entregadas excluyendo reembolsos, pedidos confirmados, ticket medio, costos conocidos, cobertura de costos, margen solamente con costos completos, comparación contra un intervalo anterior de igual duración, productos más/menos vendidos, clientes nuevos/recurrentes/inactivos, ventas diarias y pedidos por hora.

Las vistas del sitio son cargas agregadas por negocio y día, sin identificador de visitante. No representan visitantes únicos. Se registra merma por ingrediente y unidad sin mezclar gramos con unidades. Los movimientos nuevos conservan su unidad; los históricos sin esa evidencia se muestran como unidad no registrada. El embudo usa las vistas, clics y pedidos realmente registrados. Las entregas de campañas no prueban causalidad de ventas.

La previsión utiliza una media histórica por día de semana, hasta ocho semanas. Exige al menos diez compras completadas y cuatro fechas comparables. El intervalo es descriptivo; no es una garantía ni un modelo de aprendizaje entrenado. Con datos insuficientes se muestra ese estado.

**Pendiente de datos operativos de las fases previas:** ocupación por hora, rotación y espera necesitan sesiones de mesa y cola instrumentadas. Este trabajo no fabrica esos eventos ni los sustituye por ubicación del teléfono. El sistema no puede acreditar esos tres indicadores como operativos sin esa fuente de datos.

## Fase 16: Copilot por rol

El servidor construye el contexto: carta de negocios permitidos, historial y puntos propios para el comensal, métricas de sus negocios para el empresario, y señales agregadas de plataforma para el administrador. Se descartan los negocios que el navegador intente inyectar como contexto. Las credenciales y contactos de los clientes no se envían al modelo.

El asistente puede explicar datos, orientar sobre cartas, importaciones, recetas y módulos disponibles. La consulta no modifica precios, stock, pedidos ni publicaciones. El único cambio ejecutable nuevo es actualizar un texto promocional: preparar propuesta, revisar, confirmar con token temporal, revalidar rol/propiedad y comprobar que el texto anterior no cambió. La confirmación caduca a los diez minutos y no puede reutilizarse. Ambas etapas se auditan.

Los flujos de voz, fotografías, recetas e importaciones continúan utilizando sus módulos existentes y su confirmación de publicación. No se atribuyen al chat acciones que no tenga implementadas.

## Fase 17: seguridad y confianza

Se añaden señales de fichas con mismo nombre/distrito, referencias de imagen compartidas, revisión de modelos, contenidos de sitios, imágenes de marca e incidencias de pago. Son señales para revisión, no acusaciones automáticas. El administrador puede revisar una vista privada del sitio y retirar una publicación o imagen con motivo documentado. Se conserva la evidencia; el sitio retirado no puede volver a publicarse hasta que se levante la restricción. Los enlaces de video se revisan en el sitio, sin copiar recursos externos ni afirmar que existe análisis automático de todos sus fotogramas.

Se mantienen los controles existentes de usuarios, roles, suspensión, documentos, moderación, pagos, reclamaciones y cuotas. Los modelos y proveedores se configuran en el entorno del servidor; el panel muestra disponibilidad de configuración, no secretos ni una garantía de entrega de cada proveedor.

## Códigos por Resend y Twilio

Decisión de la usuaria: Resend principal y Twilio opcional. Se añadieron variables vacías a `.env` y `.env.example`; no se almacenaron claves en el repositorio.

Para correo: `SECURITY_EMAIL_PROVIDER=resend`, `RESEND_API_KEY` y `SECURITY_FROM_EMAIL` (remitente de un dominio autorizado en Resend). Para SMS: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y `TWILIO_FROM_NUMBER` (número habilitado para el destino correspondiente). Existe adaptador SMTP opcional, con TLS obligatorio.

Los códigos tienen seis dígitos, vigencia de diez minutos, máximo de cinco intentos, límite de solicitudes por cuenta/IP y separación mínima de un minuto entre envíos. Se guardan con HMAC, vinculados a usuario, contacto, sesión de solicitud y versión de seguridad. No se devuelve el código al navegador ni se registran el código o destino en consola. El éxito cambia la contraseña e invalida sesiones previas; la recuperación por correo/SMS conserva el autenticador activo. La clave de recuperación guardada mantiene su flujo anterior.

La respuesta pública no confirma si existe el usuario ni revela el contacto. Los códigos que no fueron aceptados por el proveedor no se activan. Los cambios de contactos requieren contraseña actual y, si está activo, un código nuevo del autenticador, también cuando se intenta cambiar el correo desde el perfil genérico.

**Pendiente externo:** pegar credenciales y configurar dominio/número en los proveedores. No se ha enviado ningún código a un usuario real durante las pruebas. Las automatizaciones de Codex no son un servicio transaccional de autenticación para visitantes; la entrega se realiza desde el backend a los proveedores cloud seleccionados.

## Verificación

Resultado: **422 pruebas aprobadas** en la suite general, **17 pruebas específicas de seguridad e integración repetidas y aprobadas sobre la versión final** en la revisión final de los módulos nuevos, y **162 combinaciones de ancho y tema** aprobadas en nueve vistas/roles. Las pruebas usan PostgreSQL local desechable, cuentas de prueba y mensajes simulados. Los resultados se conservan en `qa-fases-14-17.xml`, `qa-seguridad-fases-14-17.xml` y `qa-responsive-fases-14-17.json`. El visor se probó con un GLB real servido localmente y los gráficos con Chart.js local. Las pruebas de SMS/correo verifican los adaptadores y los límites, sin realizar envíos reales.

Referencias: [Resend](https://resend.com/docs/api-reference/emails/send-email), [Twilio](https://www.twilio.com/docs/messaging/api/message-resource), [model-viewer y AR](https://modelviewer.dev/examples/augmentedreality/).
