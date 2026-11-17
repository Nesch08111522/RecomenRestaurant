# SmartResto 2.0

## OpenRouter

La configuración local selecciona OpenRouter. Pega la clave en `OPENROUTER_API_KEY` dentro de `.env` y reinicia Flask. La plantilla `.env.example` debe conservar ese campo vacío.

```dotenv
AI_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=
AI_MODEL=openai/gpt-4o-mini
AI_VISION_MODEL=openai/gpt-4o-mini
ADMIN_AI_MODEL=
```

Se configuró el modelo pago `openai/gpt-4o-mini`. Para cambiar de modelo, modifica `AI_MODEL` por su identificador y selecciona un modelo compatible con imágenes en `AI_VISION_MODEL`. Administración hereda el proveedor y modelo generales, con sobrescrituras opcionales `ADMIN_AI_BASE_URL`, `ADMIN_AI_MODEL` y `ADMIN_AI_API_KEY`. La extracción histórica de cartas que utiliza Gemini mantiene su configuración independiente.

La clave se usa en el servidor. Las pruebas automatizadas sustituyen credenciales y respuestas externas. La disponibilidad real, los límites y los resultados del proveedor necesitan una comprobación con una clave vigente. [Documentación de OpenRouter](https://openrouter.ai/developers)

## Incorporado en esta entrega

| Área | Implementación |
| --- | --- |
| Contexto | `/experiencias/` combina ánimo, ocasión, horario, historial y etiquetas declaradas, después de los filtros alimentarios y de presupuesto. |
| Clima | Open-Meteo con consentimiento, coordenadas aproximadas y caché. El contexto caduca a las cuatro horas y se puede desactivar. |
| Recovery Food | Filtro de platos declarados sin alcohol y preferencias suaves. |
| Grupos | Invitaciones privadas de siete días, presupuesto y exclusiones individuales, opciones comunes, votos y costo por persona. Los cambios de integrantes o preferencias reinician los votos. |
| Escaneo | Fotografía enviada al proveedor configurado para identificar tentativamente un plato y buscar ofertas. La compatibilidad alimentaria usa la declaración del negocio. |
| 3D y AR | Carga empresarial de GLB autocontenido, revisión administrativa y visor bajo demanda en la ficha del plato. |
| Negocio | Ventas pagadas, clientes nuevos/frecuentes/inactivos, ingredientes y platos afectados, referencia de demanda y precio sugerido para 30% de margen sobre receta. |
| Campañas | Bandeja interna para compradores con consentimiento. Límite de una campaña por cliente y negocio cada siete días. |
| Recompensas | Puntos derivados de compras entregadas y pagadas, canje de diez puntos por el beneficio configurado y restitución al cancelar. |
| Administración | Oferta y demanda por distrito, revisión de publicaciones con auditoría y acceso al módulo existente de confianza. |
| Reservas | Capacidad compartida, duración configurable, protección transaccional y solapamientos que cruzan medianoche. |
| Reseñas | La API exige una compra entregada y pagada que todavía pueda calificarse. |

Las ofertas nuevas requieren aprobación. Se preservó la visibilidad de las ofertas históricas sin campo de moderación. La capacidad inicial de reservas es de veinte plazas durante noventa minutos hasta que el empresario la configure. Los puntos usan una unidad por cada S/10 de cada compra completada.

## Validación y dependencias

La ejecución del 17 de noviembre de 2026 terminó con 122 pruebas aprobadas en PostgreSQL local desechable. Cubren los tres roles, CSRF, compras, inventario, pagos simulados, moderación, reservas, grupos privados, recompensas, acceso a modelos, selección de proveedor y respuesta ante fallos de conexión. La integración real de pagos, clima, modelos de IA y AR móvil requiere sus servicios y dispositivos correspondientes.

Los modelos 3D deben ser aportados por los negocios y representar sus platos. El visor usa model-viewer 4.1.0 y requiere acceso al CDN. El soporte AR depende del dispositivo. [Documentación del visor](https://modelviewer.dev/docs/index.html)

Para explotación comercial del clima revisa el plan y licencia de Open-Meteo. `WEATHER_API_KEY` selecciona su endpoint comercial. [Planes de Open-Meteo](https://open-meteo.com/en/pricing)

## Alcance pendiente del documento de evolución

La propuesta completa todavía incluye trabajo adicional. Quedan pendientes ETA conectado con rutas y disponibilidad real de repartidores, operaciones empresariales completas por voz con confirmación, avisos automáticos de rescate, misiones de fidelización, mapas territoriales de demanda, atribución de conversiones y campañas, y validación predictiva con históricos suficientes. La selección en grupo muestra costos compartidos y utiliza el carrito existente, con un comprador responsable del pago.

## SQL de datos históricos

`database/importar_restaurantes.sql` contiene los 26 restaurantes. `database/importar_json_faltantes.sql` contiene 320 registros adicionales de los JSON del repositorio, agrupados en once colecciones. Ambos necesitan `database/app_records.sql`. La importación conserva los registros cuyos identificadores ya existen y avanza la secuencia sin reducirla.

El archivo adicional incluye datos de cuentas e historial procedentes del origen. Consérvalo con acceso restringido. La generación comparó los archivos locales, y la ejecución SQL decide qué identificadores faltan en la base de destino. La importación en Supabase queda por ejecutar.
