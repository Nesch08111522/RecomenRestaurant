# Mercado de barrio

Desde **Mercado** en la cabecera se accede a `/mercado/`. Un negocio puede vender sin publicar su domicilio. El mercado usa la misma instancia PostgreSQL y la tabla `public.app_records` que el resto de SmartResto. Las ventas, el stock, los documentos privados y la medición tienen colecciones separadas.

## Primer recorrido

1. Registra una cuenta empresarial y crea un negocio. Elige si quieres mostrar solo el distrito. Un administrador debe aprobarlo para hacerlo visible al consumidor.
2. En **Mercado → Gestionar cocina**, selecciona el negocio, el tipo y los canales. Para recojo, indica un punto público y el número de turnos por hora. Para delivery, define zonas y, opcionalmente, un pin público y un radio.
3. Registra un lote. Por ejemplo, ingresa 1 000 g de arroz, su fecha de vencimiento y el costo por 1 000 g. En **Publicar porciones**, una receta `arroz=200` permite vender hasta cinco porciones aunque se publiquen ocho. El stock de ingredientes se comparte entre todas las ofertas del mismo negocio.
4. Publica para una fecha y hora futuras. Con otra cuenta, busca por distrito, presupuesto o recojo. Añade platos del mismo negocio y día, elige hora de atención y confirma el pedido. El servidor vuelve a calcular precios, cupos y disponibilidad.
5. En la cocina, avanza el pedido por **Preparando → Listo → Entregado**. El consumidor puede seguirlo, descargar la constancia, valorar la compra o iniciar un reclamo. El administrador responde desde **Mercado → Confianza**.

## Las 17 propuestas en la aplicación

| Propuesta | Dónde probarla y qué hace |
|---|---|
| Recomendación personalizada | El mercado cruza gustos, exclusiones, presupuesto, modalidad, compras previas y disponibilidad. Explica las coincidencias y puede ordenar por distancia a un punto público. |
| Visión para platos | En cocina, la foto genera un borrador con Gemini. Se comprueba resolución y duplicación por huella de la imagen normalizada. El empresario edita y confirma. Se publica una miniatura JPEG sin los metadatos del original. |
| Copiloto empresarial | Propone recetas con los insumos vigentes, el presupuesto y las porciones objetivo. El simulador usa las cantidades de la receta y los precios registrados para el cálculo final. |
| Demanda y desperdicio | La cocina estima unidades para mañana con ventas de días comparables en las últimas ocho semanas. Indica cuántos días sustentan la estimación. Muestra vencimientos, faltantes, merma y porciones sin vender al cierre. |
| Comercio y pagos | Carrito, compra programada, cupos, contraentrega, Checkout Pro por vendedor, seguimiento, cancelación y constancia. La firma del webhook y la consulta al proveedor confirman el pago. |
| Asistente de consumo | Interpreta una pregunta en filtros. Los resultados y precios proceden del catálogo. También hay búsqueda local por texto cuando el proveedor de IA no responde. |
| Inventario y recetas | Cada venta descuenta insumos por porción en la misma transacción que crea el pedido. Una cancelación antes de preparar revierte la reserva del lote correspondiente. El conteo físico registra diferencias. |
| Mapa inclusivo | Búsqueda por zona sin exigir un local público. Los negocios eligen qué punto mostrar. El mapa representa la cobertura declarada. Las distancias se calculan en línea recta. |
| Fidelización | Puntos por compras completadas, descuento por recompra configurable por negocio y reconstrucción de un combo con precios y stock actuales. Las sugerencias de regreso son opcionales. El intervalo estimado aparece a partir de tres días distintos de compra. |
| Confianza y reputación | Acreditación documental privada, reclamos asociados a pedidos y reseñas de compras entregadas. Las fotos coincidentes y los patrones de cancelación generan señales que un administrador puede revisar. |
| Compatibilidad alimentaria | El negocio declara ingredientes, alérgenos, dietas y situación del contacto cruzado. Ante exclusiones se omiten ofertas con información incompleta. La declaración comercial no es una certificación clínica. |
| Gestión por voz | La voz o el texto preparan un borrador de porciones, nombre, fecha y precio en la cocina. El empresario revisa y publica. El micrófono depende del soporte y los permisos del navegador. |
| Últimas porciones | Ofertas del día con descuento real hasta su hora de cierre. Se comprueban tanto la vigencia como la hora de atención al comprar. Se mide el ahorro en ventas entregadas. |
| Trazabilidad | La ficha muestra receta, origen, preparación, fecha y declaraciones del negocio. El pedido registra los lotes y cantidades descontados. |
| Rentabilidad | El simulador calcula costo por porción, contribución, margen, punto de equilibrio, costo del lote, precio para el margen objetivo y unidades posibles. Muestra faltantes y sustituciones aprobadas para evaluar. |
| Multinegocio y multicanal | Cada negocio tiene equipo, recetas, inventario, ventas y configuración propios. El propietario concede acceso por usuario y conserva el control de los reembolsos y la acreditación. |
| Plan semanal | Selecciona una comida por día, cubre el mayor número posible de días dentro del presupuesto y usa el saldo restante para favorecer variedad. Las propuestas se comprueban de nuevo al ordenar. |

La cuenta se puede dividir entre comensales desde el carrito con reparto exacto de céntimos. Un cambio de precio exige revisar el total. Al agotarse el turno de recojo, el sistema pide otra hora antes de descontar ingredientes.

## Pagos y operación

Para habilitar Checkout Pro se requieren `MARKET_PUBLIC_URL` con la URL HTTPS pública, `MP_WEBHOOK_SECRET` con el secreto de firma y `MP_ACCESS_TOKEN_<ID_NEGOCIO>` con el token del vendedor correspondiente. Cada preferencia de pago indica su URL de notificación `/mercado/pagos/<id>/notificar`. Configura el evento de pagos en Mercado Pago y prueba primero con compradores y vendedores de prueba del proveedor. Las credenciales se configuran en el servidor. [Notificaciones de Checkout Pro](https://www.mercadopago.com.pe/developers/es/docs/checkout-pro-preferences/payment-notifications)

El retorno del navegador permite retomar el seguimiento. Para acreditar el dinero, el servidor comprueba en el proveedor el identificador, la referencia del pedido, el estado, la moneda PEN y el importe. La contraentrega queda cobrada al registrar la entrega. Un pago digital aprobado puede reembolsarse desde la cocina antes de preparar. Para incidencias posteriores, el administrador revisa el reclamo y el vendedor gestiona el caso con su proveedor. La constancia descargable resume el pedido; la emisión tributaria corresponde al negocio.

Ejecuta periódicamente `python -m flask --app app:create_app market liberar-vencidos` para liberar pedidos digitales impagados cuya hora de atención ya pasó. El comando se puede repetir. La frecuencia de ejecución se configura en el despliegue.

## Indicadores para un piloto

El panel de confianza muestra ofertas vistas, interacción y pedidos atribuidos; el embudo requiere JavaScript. Una misma oferta cuenta una vez por página mostrada y etapa. La cocina cuenta ventas entregadas, clientes que repiten, ingresos y contribución en pedidos con costos conocidos. Las existencias al cierre se distinguen de la merma física registrada por el negocio.

También se mide el tiempo desde la apertura del formulario hasta publicar, el tiempo de revisión de expedientes y cuántas señales se desestiman. La aceptación de un nombre sugerido por visión mide el uso de la sugerencia. Para medir precisión del clasificador hacen falta fotos etiquetadas independientemente.

Las pruebas de integración en `test/test_market_flow.py` y `test/test_market_transactions.py` requieren PostgreSQL desechable con el esquema instalado. El archivo README describe la preparación del entorno. Las pruebas de reglas y del plan semanal están en `test/test_market.py`.

