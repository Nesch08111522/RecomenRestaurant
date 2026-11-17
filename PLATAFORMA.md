# SmartResto · entrega de la plataforma

## Alcance y arquitectura

El proyecto conserva la aplicación Flask, sus blueprints y los dos esquemas PostgreSQL de Supabase. El catálogo de restaurantes, la carta, el menú del día, las reservas y los favoritos siguen disponibles. El mercado añade ofertas fechadas, inventario por receta, pedidos, transacciones, conversaciones, evidencias y reclamos. Los datos históricos JSON se utilizan exclusivamente como insumo de migración. El análisis anterior del PDF y la correspondencia entre sus 17 propuestas y las capacidades implementadas están en [MERCADO.md](MERCADO.md).

Antes de extender la plataforma se revisaron los controladores, los permisos por negocio, el almacenamiento JSONB, los cobros por vendedor, las pruebas existentes y los tres entornos de usuario. Se detectaron sesiones que perdían las preferencias al reconstruirse, formularios de búsqueda con dos manejadores, consultas de autenticación que recorrían toda la colección y claves de moderación repetidas en el histórico.

## Recorridos implementados

| Perfil | Entrada | Operaciones y datos |
|---|---|---|
| Comensal | Portada y `/mercado/` | Recomendaciones explicadas, filtros por modalidad, categoría, presupuesto, distancia y exclusiones. Ficha de plato y variantes disponibles, carrito, cupón, compra programada, reserva, constancia, seguimiento y valoración de compra entregada. El perfil permite gestionar direcciones, consentimiento de promociones, reseñas y cupones de favoritos. |
| Empresario | `/owner/dashboard` | Selección de establecimiento, ventas entregadas y pagadas, pedidos, demanda, ingredientes críticos, margen con costos conocidos y comparación entre períodos. Acceso a la ficha pública, carta, inventario, disponibilidad, cupones, pedidos, reservas y acreditación. |
| Administrador | `/admin/dashboard` | Indicadores por período y categoría, actividad, demanda, verificación, moderación, embudo de recomendaciones, incidencias de pagos, operación detallada, restricciones editables y auditoría. Las comisiones de plataforma se omiten mientras no exista un registro contable. |

Los tres perfiles disponen de bandeja, contacto con soporte y notificaciones. Los mensajes privados entre cliente y negocio son visibles para sus participantes. Los hilos de soporte admiten intervención administrativa. Las descargas de evidencias requieren acceso al hilo o expediente. Los reclamos originados en pedidos tienen código, seguimiento, responsable, prioridad, motivos y decisión. El centro de notificaciones puede consultarse directamente y la cabecera actualiza los contadores cada treinta segundos con la pestaña visible.

La portada usa fotografía WebP local con versión móvil, tema persistente, navegación de teclado y menú móvil. Los testimonios proceden de compras verificadas. La cuenta del empresario puede compartir la ficha del negocio con metadatos Open Graph.

## Contratos y seguridad

| Método y ruta | Contrato |
|---|---|
| `GET /mercado/` | Catálogo público filtrado y paginado, doce ofertas por página. El cliente puede guardar presupuesto por comida, diario y semanal, dieta, ingredientes y modalidad. |
| `GET /mercado/oferta/<id>` | Precio, porciones y variantes publicadas. El comprador puede revisar los ingredientes y la declaración de contacto cruzado. |
| `POST /api/search` | Consulta de lectura. Admite filtros y paginación opcional con `page` y `per_page`. Conserva el cuerpo de lista y la cabecera `X-Search-Total`. |
| `POST /mercado/cocina/<id>/cupon` y `POST /mercado/carrito/cupon` | El titular configura vigencia y porcentaje. El carrito aplica el mayor beneficio entre cupón y fidelización. El servidor vuelve a validar en la compra. |
| `POST /mercado/comprar` | Revalida precio, dieta, stock, turno y modalidad dentro de la transacción. La clave de idempotencia identifica el reintento. |
| `POST /mercado/pagos/<id>/notificar` | Verifica firma y consulta al proveedor. Comprueba vendedor, pedido, moneda e importe. Una incidencia confirmada genera aviso administrativo. |
| `GET /bandeja/`, `/bandeja/reclamos`, `/bandeja/notificaciones` | Consultas autenticadas por identidad. Responder, marcar leído y actualizar el expediente requieren POST y CSRF. |
| `GET/POST /auth/seguridad` y `/auth/recuperar` | Activación voluntaria de autenticador TOTP y generación de clave de recuperación de un uso. Se pide la contraseña actual. La recuperación revoca las sesiones y el TOTP anterior. |

El estado «En reparto» corresponde al delivery. Las ofertas agotadas se excluyen del catálogo. La cocina puede confirmar el pedido antes de prepararlo. El pago digital requiere confirmación del proveedor para avanzar. Los asistentes proponen filtros o borradores y los importes se calculan en Python. El negocio confirma la publicación.

El acceso tiene límites compartidos en PostgreSQL por cuenta y origen. El secreto del autenticador se cifra y la clave de recuperación se almacena mediante un resumen autenticado. El despliegue debe conservar su clave de aplicación de forma segura. Para recuperar una cuenta mediante este flujo, el usuario debe haber guardado la clave de recuperación. Los códigos se muestran una vez.

## Puesta en marcha y operación

1. Instalar las dependencias y configurar el entorno según [README.md](README.md). Aplicar los dos scripts SQL, incluido el actualizado de índices de búsqueda, negocio y notificaciones.
2. Configurar HTTPS, cookies seguras y secretos del servidor. Los proveedores de IA y el cobro digital requieren configuración propia. Los tokens de vendedores sólo deben existir en el servidor.
3. Para repetir las pruebas funcionales, configurar una base PostgreSQL desechable mediante las dos variables de entorno indicadas en el README. Ejecutar `python -m pytest -q test`.
4. Para el recorrido visual, disponer de Node con Playwright y navegador Chromium o Edge. Configurar `VISUAL_OUTPUT`, `EDGE_PATH`, la raíz del repositorio en `PYTHONPATH` y ejecutar `python test/visual_server.py` con la base de pruebas. El script registra tres cuentas de prueba y un negocio, comprueba el cambio de tema, recorre nueve anchos y compara las capturas de móvil y escritorio en dos ejecuciones. Para una regresión entre versiones, configurar `VISUAL_BASELINE` con el directorio de capturas aprobadas y usar el mismo navegador, datos, fecha de referencia y fuentes.

## Evidencia de verificación

Las 111 pruebas automatizadas pasaron en 55,24 segundos. Se ejecutaron pruebas funcionales sobre PostgreSQL 17 temporal con TLS. Cubren los tres roles, el inicio de sesión y el segundo factor, el uso único de la clave de recuperación, CSRF, autorización por establecimiento y conversación, ciclo de venta, doble envío del mismo pedido, disputa por la última plaza, cambios de estado, cupones, incompatibilidades alimentarias, pagos con proveedor de prueba, moderación, reservas y auditoría. La importación de prueba leyó 346 registros de 12 colecciones sin escribir en Supabase ni alterar archivos históricos.

Edge abrió portada, mercado del comensal, gestión de un negocio y centro administrativo a 320, 375, 480, 640, 768, 1024, 1280, 1440 y 1920 px. Se comprobaron ambos temas, persistencia al recargar, apertura del menú y cierre con Escape, copia del enlace por el empresario y acceso a la ficha pública. Dos recorridos consecutivos de 72 combinaciones produjeron las mismas 16 capturas de referencia a 375 y 1440 px. El mayor desbordamiento horizontal medido fue 0 px. Se separaron las hojas de estilo del panel empresarial y se corrigió un salto durante su carga.

La última medición local registró un LCP en el percentil 75 de 1016 ms y un CLS máximo de 0. En 68 muestras se observó una interacción de al menos 16 ms, con un percentil 75 de 40 ms y máximo de 72 ms. Este dato corresponde al evento de prueba. La medición de INP de campo requiere tráfico real. Las pruebas de navegador utilizaron recursos locales y bloquearon las solicitudes a terceros.

## Límites y próximos pasos operativos

- Validar el alta del vendedor, pago, notificación y devolución con las credenciales de prueba de Mercado Pago en la URL HTTPS del despliegue. La suite comprueba firmas, moneda, importes, duplicados e idempotencia con respuestas controladas. No se efectuaron cobros reales.
- Probar en el entorno de destino la disponibilidad de Groq y Gemini, sus cuotas, latencia, calidad de identificación fotográfica y coste por consulta. El análisis de reclamos recibe únicamente estados, categoría e indicadores de pago. Su propuesta requiere una decisión humana. Una regla local ofrece orientación si falta el proveedor.
- Auditar con lector de pantalla y en dispositivos físicos el recorrido completo, especialmente editores, mapas y paneles con contenidos extensos. Las mediciones cubren cuatro pantallas y dos temas. La conformidad WCAG 2.2 AA de todas las vistas sigue pendiente.
- El mapa externo, las fuentes, los iconos de terceros y los tiempos de red requieren verificación en el despliegue. Las distancias geográficas se distinguen de los tiempos estimados de viaje. Las redes sociales oficiales y datos del responsable legal requieren información del titular de la plataforma.
- Medir carga concurrente con el volumen esperado antes de dimensionar la operación. El índice por día limita la consulta de ofertas, pero el ranking y varios agregados administrativos aún se calculan en memoria. La actualización de notificaciones usa consulta periódica. No se midieron tiempos ni capacidad del Supabase de producción.
- La recuperación autónoma requiere una clave emitida previamente. Definir un proceso operativo con comprobación de identidad para quienes pierdan todos sus factores. Planificar respaldo y rotación de la clave de cifrado antes de activar el segundo factor en producción.
