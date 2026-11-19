# SmartResto: operación presencial, comercio, cocina, Flow y fidelización

Implementación y alcance de las fases 8 a 12 — 19 de noviembre de 2026 (America/Lima).

## Resumen

Se completó la operación presencial sobre la arquitectura existente: carta digital por QR, mesas, sesiones de atención, pedidos desde la mesa, solicitudes al mozo, cuenta y división del consumo, cola virtual con aforo, y una billetera de puntos con visitas verificadas y reseñas. No se añadieron dependencias de ejecución: los QR usan `qrcode`, ya presente, y las pantallas reutilizan los tokens de tema y componentes del proyecto.

Las fases 9 y 10 ya tenían una base funcional (carrito, pedidos para recojo/delivery, compras programadas, reservas, cupones, Mercado Pago, webhooks, constancias, cancelaciones, reembolsos, inventario, recetas por oferta, merma, simulador de costos y predicción descriptiva). Esta entrega cierra sus brechas de operación en mesa y agrega las alertas de inventario y el historial de producción que faltaban.

## Accesos nuevos

- `/mesa/<token>`: carta digital de una mesa. Escanear no abre ni ocupa la mesa.
- `/mesa/<token>/sesion`: estado de la sesión, pedidos, solicitudes, división y reseña.
- `/owner/salon` y `/owner/salon/<rid>`: pisos, zonas, mesas, capacidad, plano y QR.
- `/salon/<rid>`: panel del salón para propietario, personal autorizado y administrador.
- `/cola/<rid>`: registro público de turnos sin instalar aplicación.
- `/salon/<rid>/cola`: atención de la cola, llamados, asignación de mesa, aforo y patrón de llegadas.
- `/puntos`: billetera, niveles, insignias, visitas e historial.
- `/owner/puntos/<rid>`: clientes nuevos, frecuentes e inactivos y reputación del negocio.

## Fase 8: carta digital, QR y mesas

Cada mesa pertenece a un establecimiento (un `rid` por sucursal), con piso, zona, capacidad, posición opcional en el plano y un token QR único de 32 caracteres hexadecimales. El QR se descarga como SVG desde la administración del salón.

Estados operativos derivados de hechos registrados: Disponible, Ocupada, Pedido enviado, En preparación, Servido, Solicita atención, Solicita cuenta, Pendiente de pago y Limpieza. Las solicitudes pendientes tienen prioridad sobre el estado de cocina. Una sesión finalizada permanece en Limpieza hasta que el personal la marca limpia; una mesa en limpieza no admite una nueva sesión.

La carta muestra categorías, platos, descripción, ingredientes y alérgenos declarados, precio de carta, porciones disponibles, variantes, adicionales declarados, videos declarados, fotografía y enlace a la ficha/visor 3D cuando la oferta tiene modelo. Los adicionales se informan; su cobro automático no está conectado al carrito.

Una precisión deliberada: abrir la carta no crea ocupación. La sesión nace cuando el comensal autenticado confirma «Iniciar atención» o cuando el personal abre la mesa. Un comensal que escanea una mesa ya abierta puede unirse si la sesión no está vinculada a otra cuenta.

## Fase 9: pedidos por QR y división

Los pedidos desde mesa reutilizan el mismo motor de ofertas, stock, recetas, descuentos y auditoría del mercado. Se registran con canal «Local», mesa, sesión, etiqueta de mesa y método «Cuenta». El cobro se confirma al cerrar la mesa; no se inventa un pago digital presencial.

La división acepta partes iguales entre 2 y 30 personas o importes personalizados que deben sumar exactamente el total. Los céntimos se reparten sin pérdida. Si se agrega un pedido nuevo, la división anterior se invalida para evitar un reparto obsoleto.

Se mantienen las modalidades existentes: recojo, delivery, compras programadas, cupones, reservas con disponibilidad, pagos digitales con Mercado Pago, webhooks firmados, constancias, cancelaciones, reembolsos y seguimiento. Las credenciales de Mercado Pago y el origen HTTPS siguen siendo configuración del servidor; no se probó un cobro real en esta entrega.

## Fase 10: cocina, lotes y producción

Se añadieron alertas visibles de inventario: agotado, vencido, vence en tres días o no cubre las porciones publicadas. El cálculo compara la receta y el stock de las ofertas vigentes con el lote registrado. También se muestra el historial de producción por oferta.

Siguen vigentes el inventario por insumo con lote, vencimiento, costo y unidades de compra; las recetas por oferta; el descuento de ingredientes al vender; la merma; el simulador de costos y margen; las sustituciones; la predicción descriptiva por día de semana; y el asistente que propone recetas con el inventario disponible.

Límites reales: se guarda un lote por insumo, no varios lotes simultáneos del mismo insumo. La receta vive en la oferta, no en una ficha independiente del plato. El dictado existente prepara ofertas; no se implementó un dictado específico de ingredientes. No hay órdenes de compra ni recepción de proveedores.

## Fase 11: SmartResto Flow

El aforo se calcula con la capacidad de las mesas activas y las sesiones abiertas. Se muestra por piso y zona, con mesas libres, ocupadas y en limpieza. El máximo configurado bloquea sentar grupos que lo excedan.

La cola pública registra nombre o iniciales y número de personas, sin pedir teléfono ni ubicación. Genera un código diario (`T-001`), posición y estimación. Los turnos se pueden llamar, sentar en una mesa compatible, cancelar o marcar como no presentados. Al sentar se crea una sesión real y se vincula el turno.

La estimación usa la mediana de sesiones cerradas de los últimos 30 días. Con menos de tres muestras usa la duración declarada por el negocio y lo indica. No es un modelo entrenado ni una garantía. Las notificaciones de llamado y mesa asignada son internas de SmartResto y respetan la preferencia «turnos y lista de espera»; no se envía SMS ni WhatsApp.

Las reservas existentes siguen confirmándose en la cocina, pero no asignan automáticamente una mesa física; por eso el panel no presenta «mesas reservadas» como un estado derivado.

## Fase 12: fidelización, visitas y reputación

La billetera calcula puntos con hechos registrados: compras entregadas y pagadas (1 punto por cada S/ 10), visitas cerradas y pagadas (10 puntos) y bonos explícitos. Una compra cancelada o no pagada no genera puntos. Un reembolso de una compra entregada muestra la compra y su reversión, con saldo neto cero. Los canjes registrados en pedidos descuentan su saldo.

Niveles: Bronce, Plata (200), Oro (500) y Diamante (1000), sobre puntos históricos. Insignias por primera visita, tres negocios, cinco visitas al mismo negocio, diez compras, tres reseñas verificadas y cumpleaños. El beneficio de cumpleaños otorga 50 puntos una vez al año y exige la fecha registrada en el perfil.

Las visitas verificadas provienen de sesiones de mesa cerradas con consumo pagado. La reseña de mesa queda vinculada a la sesión, exige calificación de 1 a 5 y actualiza la reputación del negocio. Los clientes nuevos, frecuentes e inactivos se calculan con compras reales y no exponen correos ni teléfonos. Los favoritos y el historial de platos consumidos se mantienen.

Límites: las promociones personalizadas no generan campañas automáticas; solo se respeta el consentimiento de marketing. No hay vencimiento de puntos. La subida de fotografías en reseñas no tiene interfaz, aunque el modelo admite referencias. La billetera global y la recompensa local por negocio (10 puntos → descuento) siguen siendo conceptos separados y así se muestra.

## Privacidad y seguridad

- El QR de mesa es un token físico; no se expone el identificador de usuario en la carta pública.
- El estado público de la cola no devuelve nombres de otros grupos.
- Las solicitudes de mesa se deduplican por tipo mientras estén pendientes.
- Propietario, personal autorizado y administrador se validan en el servidor; un empresario ajeno recibe 404.
- Comensal, personal y cocina usan CSRF en todos los formularios.
- El cierre de mesa bloquea el negocio y luego la sesión, en el mismo orden que el checkout, para evitar interbloqueos.
- La capacidad máxima y la limpieza se validan dentro de la transacción de apertura.

## Verificación

- **485 pruebas aprobadas, 0 fallos** en la suite completa, ejecutada contra un clúster PostgreSQL 17 desechable en el puerto 5433 con TLS, base `smartresto_it`, sin tocar Supabase ni el servidor local de la usuaria. Resultado en `.work/qa-fases-8-12.xml`.
- **42 pruebas nuevas** para estas fases: reglas puras de estados, división y espera; mesas/sesiones/solicitudes; pedidos por mesa y stock; Flow; puntos, reembolsos, cumpleaños y reseñas; alertas de cocina; rutas públicas y de personal.
- La suite existente se mantiene en verde; no se deshabilitó ni relajó ninguna prueba.

No se ejecutó una prueba visual con navegador de las pantallas nuevas ni un cobro real de Mercado Pago. Las plantillas se renderizaron en las pruebas de ruta y usan los tokens del tema, pero la revisión de resoluciones y la validación del proveedor de pagos siguen pendientes.