# Auditoría · Propuesta de evolución vs. estado real del código

<!-- Secciones: metodología, resumen 17 capacidades, detalle por bloques, fases, indicadores, escenario estrella, hallazgos críticos, no verificado -->

**Fecha:** 2026-11-17 · **Proyecto:** SmartResto / RecomenRestaurant (Flask + Supabase PostgreSQL)
**Referencia:** `Propuesta de evolución.pdf` (26 págs., 17 funcionalidades + 4 fases + 8 indicadores)
**Modo:** SOLO LECTURA. No se modificó ningún archivo del proyecto. Este informe es el único archivo nuevo.

## 1. Metodología y alcance

- Se leyó la propuesta completa (26 páginas) y se auditó el código real (.py, .js, .html, .sql), **no** la documentación. `MERCADO.md` y `PLATAFORMA.md` afirman que las 17 propuestas están implementadas; esta auditoría contrasta esa afirmación contra el código y matiza varias.
- Verificación en 4 bloques paralelos (recomendación/consumo, comercio/pagos/inventario, IA/visión/voz, confianza/roles/métricas) + comprobación directa de hallazgos críticos.
- Cada capacidad se clasifica: **IMPLEMENTADO** (existe y funciona según código), **PARCIAL** (existe pero falta un sub-elemento pedido o está simplificado), **AUSENTE** (no hay código).
- Las pruebas automatizadas **no se ejecutaron** en esta auditoría (requieren PostgreSQL desechable; no se tocó ninguna base viva). El conteo de funciones de test es estático.
- Evidencia citada como `archivo:línea`. Todo lo afirmado como "implementado" tiene función real detrás; lo que solo existe en documentación se señala explícitamente.

## 2. Resumen ejecutivo · las 17 capacidades

| # | Capacidad de la propuesta | Estado real | Brecha principal |
|---|---|---|---|
| 1 | Recomendador personalizado explicable | **IMPLEMENTADO** (avanzado) | Distancia en línea recta; horario no calculado server-side para el consumidor; colaborativo usa favoritos/reseñas, no pedidos |
| 2 | Visión computacional para platos | **IMPLEMENTADO** (API Gemini) | Hash exacto, no perceptual; precisión de clasificación no medida |
| 3 | Copiloto gastronómico del empresario | **IMPLEMENTADO** | La IA responde en texto libre; no alimenta el simulador automáticamente |
| 4 | Predicción de demanda y desperdicios | **IMPLEMENTADO** (estadística determinista) | Promedio simple, sin modelo predictivo; riesgo de excedente solo al cierre |
| 5 | Marketplace: compras, reservas y pagos | **IMPLEMENTADO** (reservas PARCIAL) | Pagos probados solo con mocks; reservas sin mesas/capacidad; reembolsos manuales |
| 6 | Asistente conversacional del consumidor | **PARCIAL** | El chat no conoce porciones/ingredientes/alérgenos/horarios; sin fallback local en `/api/ai/*` |
| 7 | Inventario inteligente conectado al menú | **IMPLEMENTADO** | Sustituciones solo sugeridas, no ejecutadas; un lote por insumo |
| 8 | Mapa gastronómico inclusivo | **PARCIAL** | Sin rutas ni tiempos de viaje; zonas texto libre; `map_sidebar.html` vacío |
| 9 | Fidelización y predicción de recompra | **PARCIAL** | Puntos sin canje; campañas para inactivos AUSENTES; cupones no personalizados |
| 10 | Moderación inteligente y reputación verificable | **IMPLEMENTADO con brecha grave** | `/api/reviews` permite reseñas SIN compra y contamina el rating; ofertas del mercado no pasan el filtro de contenido |
| 11 | Motor de compatibilidad alimentaria | **IMPLEMENTADO** | Sin historial de preferencias; matching por subcadena (falsos positivos posibles) |
| 12 | Gestión por voz | **PARCIAL** | Solo dictado→borrador de ofertas; NO consulta ventas ni resumen del día; una sola plantilla de frase |
| 13 | Últimas porciones (excedentes) | **IMPLEMENTADO** | Sin tests propios de la ventana de rescate |
| 14 | Trazabilidad del plato | **IMPLEMENTADO** | Fecha de preparación y origen son texto libre sin validar; sin vínculo lote→proveedor |
| 15 | Simulador de rentabilidad | **IMPLEMENTADO** (determinista) | Sin comparación de escenarios ni persistencia |
| 16 | Gestión multinegocio y multicanal | **IMPLEMENTADO** | Equipo sin roles granulares por empleado |
| 17 | Planificador gastronómico semanal | **PARCIAL** | 1 comida/día; sin cercanía ni horarios en el plan; sin descargo "no es plan nutricional clínico" |

**Balance:** 11 implementadas (2 con brechas relevantes), 6 parciales, 0 ausentes por completo. La documentación es mayormente fiel al código, pero omite las brechas de reseñas sin compra, voz limitada, chat sin datos de plato y campañas de fidelización inexistentes.

## 3. Detalle por capacidad (evidencia en código)

### 3.1 Recomendador personalizado explicable — IMPLEMENTADO (avanzado)

**Qué tiene (verificado):**
- Tres motores reales coexistiendo: reglas pyDatalog con justificaciones (`logic/recommender.py:83-337`), híbrido ponderado contenido+contexto+colaborativo con `score_breakdown` y mezcla 0.45/0.35/0.20 (`logic/hybrid_recommender.py:28-156`, integrado en `views/main.py:421-427`), y descubrimiento de mercado (`logic/market_discovery.py`).
- Presupuesto por comida y por día con gasto acumulado desde pedidos reales (`market_discovery.py:11-19,44`); gustos, exclusiones y dietas del perfil; modalidad desde texto o perfil; "X minutos" → filtra por día y lead de la cocina; historial de compras entregadas suma al score con razón "ya lo compraste" (`market_discovery.py:38,71-75`).
- Explicación por opción visible al usuario (campo `why`, `templates/market/browse.html:34`).
- Alergias: exige alérgenos declarados y contacto cruzado "declared"; sin declaración excluye (`logic/market.py:64-70`).

**Qué falta o está simplificado:**
- Distancia haversine en línea recta, sin rutas ni ETA (`utils/geo.py:29-38`; el propio template lo admite).
- `is_open_now` nunca se calcula server-side para el consumidor en `/api/search` (`utils/functional.py:102-105`); solo admin y JS de cliente lo calculan.
- El colaborativo usa favoritos y reseñas, no pedidos (`hybrid_recommender.py:87-127`); el pyDatalog solo maneja vegano/vegetariano/celiaco, no alergias arbitrarias (esas viven solo en el flujo mercado).
- No hay modelo entrenado; es determinista (declarado honestamente en el docstring).
- Tests: `test_phase7_recommender.py`, `test_phase8_geo.py`, smoke. **`market_discovery.discover` no tiene test directo.**

### 3.2 Visión computacional para platos — IMPLEMENTADO (vía API Gemini)

**Qué tiene:** foto → nombre, descripción, categoría y etiquetas con `gemini-2.5-flash` (`utils/kitchen_assistant.py:29-63`, ruta `views/market_kitchen.py:262-274`); huella SHA-256 que bloquea foto repetida en el negocio (`kitchen_assistant.py:41`, `market_kitchen.py:227-228`) y detecta coincidencias entre negocios para el admin (`views/market_trust.py:35-36`); calidad visual por resolución mínima 320 px; miniatura JPEG 640×480 re-codificada sin EXIF (`utils/gemini_menu.py:64-90`); el empresario confirma/corrige antes de publicar y se registra si aceptó la sugerencia (`vision_used/vision_accepted`, `market_kitchen.py:224-225`). Extra: carta completa fotografiada (hasta 6 fotos) → borrador revisable plato por plato (`gemini_menu.py:168-232`, `views/owner.py:483-578`).

**Qué falta:** es API externa, no modelo propio (la propuesta lo permite); sin `GEMINI_API_KEY` degrada a borrador manual; hash exacto no detecta duplicados re-comprimidos (no hay hash perceptual); **precisión de clasificación no medida** (solo tasa de aceptación, que la propia doc reconoce que requiere fotos etiquetadas); la lectura de carta no calcula huella ni calidad. Tests: solo la rama sin Gemini (`test_market_flow.py:33-41`).

### 3.3 Copiloto gastronómico — IMPLEMENTADO

**Qué tiene:** insumos vigentes + presupuesto + porciones objetivo → IA propone recetas, cantidades, faltantes y sustituciones (`utils/kitchen_assistant.py:14-26`; filtra insumos vencidos antes de enviar, `market_kitchen.py:283`); el prompt prohíbe a la IA calcular precios; **toda la economía es determinista en Python con Decimal/céntimos** (`logic/market.py:73-83`, simulador `market_kitchen.py:288-309`: porciones posibles, faltantes con alternativas registradas, costo de lote, precio para margen objetivo). Fallback sin IA explícito.

**Qué falta:** la salida de la IA es **texto libre** (`templates/market/kitchen.html:53`); no se parsea a receta estructurada ni alimenta el simulador: el empresario debe transcribir. "Porciones estimadas y costos" de la propuesta IA no existen como campos, solo en el simulador con recetas ya registradas. Sin test del copiloto ni del fallback.

### 3.4 Predicción de demanda y desperdicios — IMPLEMENTADO (determinista)

**Qué tiene:** estimación de unidades para mañana = promedio de pedidos "Entregado" del mismo día de semana en las últimas 8 semanas, con conteo de días que la sustentan e "Historial insuficiente" si no hay datos (`logic/market.py:112-121`, `market_kitchen.py:56-57`); mayor rotación (`analytics/management.py:56-65`); **horario pico sí existe** (`models/market.py:227,230`, mostrado en dashboard y cocina); vencimientos próximos, inventario crítico/agotado, alertas automáticas "Producto agotado"/"Inventario bajo" (≤3 porciones) (`models/market.py:160-166`); merma auditada y porciones sin vender al cierre con % (`market_kitchen.py:53-55,158-164`).

**Qué falta:** es promedio histórico, no series temporales ni ML (la propuesta pide empezar así, es fiel); el "pico" mide hora programada de entrega, no demanda real por franja; no hay alerta proactiva de riesgo de excedente antes de producir. Test del forecast solo cubre el caso vacío (`test_market.py:27`).

### 3.5 Marketplace: compras, reservas y pagos — IMPLEMENTADO (reservas PARCIAL)

**Qué tiene:**
- Carrito multi-item bloqueado a un negocio y un día, compra programada con fecha/hora futura Lima (máx. 30 días, lead del negocio), cupos de recojo por hora configurables, y **revalidación transaccional completa al comprar**: precio recalculado, stock por receta, vencimiento, turno, dieta, zona/radio de delivery y total esperado del cliente, con `SELECT … FOR UPDATE` (`models/market.py:107-172`, `views/market.py:165-171`).
- Idempotencia por `request_key` UUID con dedup transaccional (`models/market.py:107-115`); test de concurrencia real con 2 hilos disputando el último cupo (`test_market_transactions.py:33`).
- Mercado Pago Checkout Pro **por vendedor** (token `MP_ACCESS_TOKEN_<id>`), moneda PEN, `external_reference` determinista, webhook con firma HMAC-SHA256 y **confirmación canónica contra el proveedor** (id, referencia, estado, moneda, importe en céntimos) (`utils/market_payments.py:14-77`, `views/market.py:346-384`). Contraentrega cobrada al entregar. Incidencias `rejected/charged_back` avisadas a admins. CLI `flask market liberar-vencidos` (`views/market.py:403-416`).
- Estados Recibido→Confirmado→Preparando→Listo→En reparto/Entregado con historial, notificaciones y bloqueo de avance sin pago digital confirmado; cancelación revierte stock **y el lote exacto** (`models/market.py:186-220`).
- Constancia descargable TXT que aclara que el comprobante tributario corresponde al negocio (`views/market.py:387-400`).
- División de cuenta: calculadora con reparto exacto de céntimos (`divmod`), declarando "un solo pedido y un solo pago" (`views/market.py:196-197`).

**Qué falta:**
- **Pagos nunca probados contra Mercado Pago real/sandbox**: `payments.call` se mockea en tests; sin evidencia de cobros reales (la doc lo admite).
- Reembolsos: solo totales y manuales por el dueño (el automático solo cubre pago tardío de pedido cancelado); no parciales.
- La firma del webhook **no valida antigüedad del timestamp** (`market_payments.py:66-71`): replay teórico posible, mitigado por idempotencia + consulta canónica.
- Sin emisión de comprobantes tributarios (SUNAT); constancia es TXT plano.
- **Reservas sin mesas, numeración ni capacidad**: dos reservas a la misma hora se aceptan; sin vista de cancelación por el comensal ni moderación de conflictos de reserva (`models/reservation.py:12-23`, `views/main.py:248-308`). Los cupos de recojo sí están completos.
- El comprador puede cancelar incluso en "Preparando"; carrito vive en sesión (no persiste entre dispositivos); sin edición de cantidades.
- Sin tests de checkout, reembolso, constancia, CLI de vencidos ni división de cuenta.

### 3.6 Asistente conversacional del consumidor — PARCIAL

**Qué tiene:** NL→filtros estructurados con validación contra categorías reales y defensa anti-inyección (`views/ai_routes.py:76-163`); chat anclado a la BD: el servidor reconstruye la lista de negocios aprobados e ignora datos del cliente, filtra IDs inventados (`ai_routes.py:166-249`); rate limit 20/min/IP; asistente del mercado `/mercado/consultar` con **fallback local real por regex si la IA falla** (`views/market.py:122-150`, `market_discovery.py:11-41`).

**Qué falta:**
- **El chat no puede responder porciones, ingredientes, alérgenos, horarios ni modalidades**: el contexto que recibe el LLM solo tiene nombre, distrito, precio por persona, rating, etiquetas y distancia (`ai_routes.py:190-202`). Esos datos existen en el catálogo pero no se inyectan en la conversación.
- `/api/ai/chat` y `/api/ai/interpret` no tienen fallback local (devuelven 502); solo el mercado lo tiene.
- El texto libre `reply` no se verifica fácticamente: el LLM podría citar un precio erróneo en prosa (solo se validan los IDs).
- Sin tests de interpret, consultar ni del fallback.

### 3.7 Inventario inteligente conectado al menú — IMPLEMENTADO

**Qué tiene:** lotes con vencimiento, unidad y costo; recetas por porción (`arroz=200`); **descuento de insumos en la misma transacción de la venta** con registro de lote usado (`models/market.py:153-159`); reversión al cancelar verificando el lote exacto (`models/market.py:202-211`); insumo compartido entre ofertas del mismo negocio; vencidos no vendibles (`logic/market.py:57-59`); alertas de agotado/bajo; merma validada contra stock; **conteo físico que fija la cantidad real y registra el delta** (`market_kitchen.py:138,157-164`); pausa manual de ofertas.

**Qué falta:** las **sustituciones aprobadas no se ejecutan**: son una lista de palabras que se muestra como alternativas en el simulador o sugiere la IA; ningún flujo descuenta el insumo alternativo. Un solo lote por insumo (sin multi-lote FIFO). El conteo registra la diferencia pero no genera alerta ni indicador agregado. Sin tests de conteo, sustituciones ni alertas.

### 3.8 Mapa gastronómico inclusivo — PARCIAL

**Qué tiene:** negocios sin local físico (`delivery_only`/`pickup_only`, tipos "Cocina desde casa"/"Comida casera"); zonas de cobertura, punto de recojo público, pin y radio 0–100 km configurables y **validados al pedir** (`market_kitchen.py:79-101`, `models/market.py:119-124`); búsqueda por distrito/zona; mapa Leaflet/OSM real con marcadores y círculos de cobertura, orden por cercanía con geolocalización del navegador y fallback por distrito (`static/js/market-map.js:16-48`); distancia haversine honesta (sin coordenadas = 999.99, nunca "cercano"); geocodificación inversa cacheada (Nominatim).

**Qué falta:** **sin rutas viales ni tiempos estimados de entrega** (no existe ETA en todo el repo; lo único temporal es el lead de preparación); zonas son texto libre sin polígonos ni distritos normalizados, sin búsqueda por referencias; sin geocodificación directa de direcciones del consumidor; `templates/partials/map_sidebar.html` está **vacío**; negocios sin pin quedan fuera del mapa aunque operen por zonas. El radio de delivery no tiene test.

### 3.9 Fidelización y predicción de recompra — PARCIAL

**Qué tiene:** puntos por compra completada (1 pto/S/10, informativos); descuento por recompra configurable 0–30% que exige compra previa entregada (`models/market.py:80-84`); cupones por negocio con vigencia y %; combo = repetir pedido completo revalidando preferencias y stock (`views/market.py:305-329`); recordatorios **opt-in con consentimiento**; intervalo de recompra estimado con mediana sobre ≥3 días distintos de compra (`views/market.py:290-298`); clientes que repiten / tasa de retorno en cocina y dashboard.

**Qué falta:** puntos **sin ledger ni canje** (solo se muestran); cupones y descuentos globales del negocio, **no personalizados por cliente**; **campañas para recuperar clientes inactivos: AUSENTES** (no hay código); recordatorios solo se muestran en "Mis pedidos", sin notificación push/email programada.

### 3.10 Moderación inteligente y reputación verificable — IMPLEMENTADO con BRECHA GRAVE

**Qué tiene:** filtro de contenido con niveles, anti-evasión (leet, homoglifos, des-espaciado) y frases seguras ("matar el hambre", "death by chocolate") sin falsos positivos por subcadena (`utils/content_filter.py`); triaje HUMAN/AUTO_OK/ASK_AI donde **contenido grave nunca se rechaza definitivamente sin decisión humana** (`models/moderation.py:126-129,165`); cola de revisión con motivos explicables (`utils/moderation_explain.py`); señales deterministas de fotos coincidentes y ≥3 cancelaciones por negocio con expediente revisable (`views/market_trust.py:35-63`); acreditación documental privada (PDF validado, descarga solo admin) con sello "Documentación revisada"; reclamos vinculados a pedido con código SR-#######, prioridad, responsable, historial y evidencias con acceso controlado; reseña verificada solo de compra entregada, pagada, no reembolsada y única (`views/market.py:459-480`); IA administrativa que solo propone, con salida Pydantic estricta, redacción de PII, cuota atómica y registro en `ai_decisions` (`utils/admin_ai.py`, `models/ai_decision.py`).

**Brechas (la más crítica de toda la auditoría):**
- **`POST /api/reviews` (`views/main.py:629-667`, verificado directamente) permite a cualquier usuario autenticado reseñar cualquier negocio verificado SIN compra**, y el rating promedio incluye esas reseñas no verificadas (`models/review.py:47-76`, escrito en `restaurant.rating` en `main.py:661-662`). Esto contradice la garantía "reseñas vinculadas a compras verificadas" que el flujo mercado sí cumple.
- Las **ofertas del mercado no pasan por `ContentFilter`** (`market_kitchen.py:179-244`): nombre, descripción y procedencia de ofertas se publican sin moderación de contenido.
- La ruta `ASK_AI` queda pendiente para el humano pero **no hay flujo que envíe automáticamente esos casos al LLM**; el análisis IA es un endpoint manual.
- `AUTO_OK` sí aprueba automáticamente por reglas deterministas (no por LLM) — matiz frente a "todo pasa por humano".
- **Código muerto:** `models/moderation_filter.py` (estafas, precio sospechoso) no lo importa nadie.
- La acreditación documental es opcional para vender (basta `verified`); sin caducidad/renovación ni metadatos (RUC, tipo de documento).

### 3.11 Motor de compatibilidad alimentaria — IMPLEMENTADO

**Qué tiene:** alérgenos e ingredientes declarados por oferta (solo si el negocio marca "He revisado los alérgenos", si no `None`); contaminación cruzada en 3 niveles distinguibles (unknown/possible/declared) con UI que diferencia "Sin declaración" de "Ninguno declarado"; **regla conservadora: información incompleta = no compatible ante exclusiones** (`logic/market.py:64-70`), exactamente lo que pide la propuesta; dietas Vegetariano/Vegano/Sin gluten ampliables por admin; restricciones del perfil fusionadas con preferencias de mercado (celiaco→Sin gluten, "alergia X"→avoid); aplicado en descubrimiento, carrito, checkout, ficha y recompra.

**Qué falta:** **sin historial de preferencias alimentarias** (solo estado actual); alérgenos texto libre sin catálogo normalizado; matching por subcadena bidireccional puede dar falsos positivos ("leche" vs "leche de tigre"). Tests: `test_market.py:14`, `test_commerce_extensions.py:12`, `test_market_flow.py:44`.

### 3.12 Gestión por voz — PARCIAL

**Qué tiene:** voz real del navegador (Web Speech API, `lang='es-PE'`) con fallback a texto si no hay soporte (`static/js/market-voice.js:7-17`); parser local de números en palabras ("doce"→12) que rellena un **borrador** de porciones/nombre/fecha/precio; confirmación humana obligatoria antes de publicar, con validación server-side completa.

**Qué falta:**
- **No existe consulta de ventas, registro de faltantes ni resumen del día por voz** — lo pide la propuesta y solo aparece como intención; el único archivo de voz solo crea borradores de ofertas.
- El parser entiende **una sola plantilla de frase** ("N porciones de X mañana a Y soles"); dictados libres fuera del patrón no se interpretan (no usa LLM).
- Sin reconocimiento en servidor; sin ningún test del flujo.

### 3.13 Últimas porciones (mercado de excedentes) — IMPLEMENTADO

**Qué tiene:** publicación con descuento real obligatorio para hoy y vigencia hasta la hora de cierre (`market_kitchen.py:198-200,223`); precio efectivo de rescate calculado por hora (`logic/market.py:124-126`); revalidación de vigencia y ventana de rescate al comprar (`models/market.py:148-152`); medición de porciones rescatadas y ahorro en céntimos (`models/market.py:232-233`); excedentes producidos vs. sobrantes al cierre.

**Qué falta:** el precio se fija a la hora de compra, no de recojo; **sin tests propios** de `effective_price` ni de la ventana de rescate (ningún test usa `rescue_price`).

### 3.14 Trazabilidad del plato — IMPLEMENTADO

**Qué tiene:** ficha pública con receta/ingredientes, procedencia, fecha de preparación, descripción de elaboración, alérgenos y contacto cruzado (`market_kitchen.py:218-226`, `templates/market/dish.html:4-6`); lotes con UUID, vencimiento y costo; **el pedido registra por línea el lote y la cantidad descontada** (`models/market.py:154-158`); movimientos de inventario auditados con actor y fecha.

**Qué falta:** `prepared` es texto libre truncado a 16 caracteres sin validación de fecha real; `origin` texto libre sin vínculo a proveedor ni al lote de origen del insumo (trazabilidad hacia atrás incompleta); los platos legacy del directorio no tienen ficha de trazabilidad.

### 3.15 Simulador de rentabilidad — IMPLEMENTADO (determinista)

**Qué tiene:** costo por porción desde la receta y precios registrados, contribución, margen, punto de equilibrio (`ceil(fixed/contribution)`), unidades posibles con stock vigente, costo del lote, precio sugerido para margen objetivo, faltantes y sustituciones registradas para evaluar (`logic/market.py:73-83`, `market_kitchen.py:296-309`); el escenario de la propuesta ("si vendo a S/14 en vez de S/16…") se reproduce re-enviando el formulario. Tests: `test_market.py:14-16`, `test_market_flow.py:42`.

**Qué falta:** sin comparación de escenarios lado a lado ni persistencia de simulaciones; costos fijos los ingresa el usuario (no prorrateo automático).

### 3.16 Gestión multinegocio y multicanal — IMPLEMENTADO

**Qué tiene:** varios negocios por empresario con selector y 404 si el negocio no es propio (`views/owner.py:159-163`); equipo por negocio (hasta 20 usuarios validados) con autorización doble dueño/equipo y `owner_only` para configuración, cupones y reembolsos (`market_kitchen.py:24-33,92-99`); despensa, recetas, ofertas, pedidos y métricas separados por negocio; canales Recojo/Delivery/Local por negocio (mixto = combinación) con zonas/punto/radio validados; rol revalidado contra BD en cada request con `auth_epoch` (revocación en caliente probada en test).

**Qué falta:** equipo plano sin roles granulares (cualquier miembro gestiona inventario, ofertas y estados); empleados no acceden al dashboard financiero (posiblemente intencional); la taxonomía legacy del directorio (`category_id`, `service_mode`) no se sincroniza con las 3 dimensiones del mercado.

### 3.17 Planificador gastronómico semanal — PARCIAL

**Qué tiene:** algoritmo real que cubre 7 días maximizando días cubiertos dentro del presupuesto y reasigna el saldo priorizando variedad (`logic/market.py:86-109`); presupuesto semanal del perfil; opera solo sobre ofertas con stock real de negocios registrados; gasto total estimado visible; declara "La planificación no reserva stock"; toda propuesta se revalida en el checkout genérico. Tests unitarios: `test_market.py:21,30`.

**Qué falta:** **una sola comida por día** (no desayuno/almuerzo/cena); no considera horarios del usuario ni cercanía en la función de coste; preferencias/restricciones se aplican solo indirectamente vía filtros previos; **no existe el descargo "no es un plan nutricional clínico"** que la propuesta pide explicitar; sin conversión plan→carrito en un clic; sin test del endpoint `browse?week=`.

## 4. Fases 1–4 de la propuesta

| Fase | Pedido por la propuesta | Estado real |
|---|---|---|
| **1 · Fundamentos** | Registro/auth, 3 roles, multinegocio, catálogo, modalidades, filtros, perfiles, horarios, disponibilidad, panel admin y moderación básica | **CUMPLIDA.** Auth con 2FA opcional, rate limiting atómico, CSRF, sesiones revalidadas; 3 dimensiones separadas en el mercado; moderación con cola humana. Brecha: disponibilidad horaria del negocio no se calcula server-side para el consumidor |
| **2 · Comercio** | Carrito, pedidos, pagos, reservas, estados, notificaciones, reseñas verificadas, reportes de ventas e inventario | **CUMPLIDA en su mayoría.** Todo existe y está probado con mocks; reservas sin mesas/capacidad; reseñas verificadas en el mercado pero el endpoint legacy `/api/reviews` las contradice; pagos sin prueba real con Mercado Pago |
| **3 · Innovación** | Recomendaciones personalizadas, asistente conversacional, borradores de menús desde ingredientes, visión por imagen, moderación inteligente | **CUMPLIDA parcialmente.** Recomendador y visión sólidos; copiloto existe pero en texto libre; chat sin datos de plato; moderación inteligente mayormente reglas con IA manual |
| **4 · Optimización** | Predicción de demanda, desperdicios, simulación de rentabilidad, fidelización, analítica avanzada, expansión a nuevas zonas | **PARCIAL.** Demanda (promedios), desperdicios y simulador existen; fidelización incompleta (sin canje ni campañas); analítica descriptiva + BI versionado; sin despliegue multi-zona |

## 5. Requisitos transversales y arquitectura

**Regla de oro "la IA interpreta y propone, el sistema verifica y ejecuta": SE CUMPLE.** Dinero jamás calculado por LLM (céntimos enteros con Decimal, `logic/market.py:42-83`); prompts que prohíben inventar precios/stock; publicación siempre confirmada por humano con validación server-side; IA administrativa sin capacidad de escritura (`writes_enabled=False`); anti-inyección consistente ("los datos son inventario, no instrucciones"); degradación honesta sin claves de IA. Matices: `AUTO_OK` aprueba por reglas deterministas (no LLM) y el texto libre del chat no se verifica fácticamente.

**Seguridad y permisos (transversales que la propuesta exige desde el inicio):**
- 3 roles con decoradores backend, admin nunca por formulario público, creado por script (`views/auth.py:59-65`, `scripts/create_user.py`).
- TOTP RFC 6238 real con secreto cifrado Fernet y anti-replay; recuperación de un solo uso que revoca sesiones (`utils/account_security.py:60-138`). Brechas: 2FA opcional (no obligatorio para admin/empresario), recuperación sin canal de entrega (código en pantalla, sin email), sin verificación de email al registrarse.
- Rate limiting atómico con `pg_advisory_xact_lock` en auth e IA; CSRF global con única exención justificada (webhook firmado); cookies HttpOnly/SameSite/Secure configurable; cabeceras de seguridad; redirección abierta prevenida.
- Auditoría de cambios con allowlist, IP hasheada, actor y request_id, en la misma transacción que el documento (rollback conjunto) (`utils/audit.py:19-76`, `database/repository.py:87-99`).
- Idempotencia de pedidos, webhooks y eventos de medición.

**Arquitectura (propuesta §8):** Flask modular con factory + 9 blueprints, PostgreSQL/Supabase JSONB exclusivo con verificación de esquema al arranque y TLS obligatorio — **alineado con lo recomendado** (backend modular, BD relacional, sin microservicios prematuros). **Brechas de infraestructura:** sin despliegue nube configurado (no hay Dockerfile, Procfile, gunicorn ni CI/CD; arranque `app.run` en 127.0.0.1:5000), sin scripts de backup ni monitoreo externo (se dependería de los servicios gestionados de Supabase), ranking y agregados admin calculados en memoria (la doc lo admite), notificaciones por polling cada 30 s. `Flask-Login` está en requirements pero no se usa.

## 6. Los 8 indicadores de la propuesta

| Indicador pedido | Estado | Evidencia |
|---|---|---|
| Tasa de clics y conversión de recomendaciones | **SÍ** | Embudo con tickets firmados y deduplicados: vistas→interacción→pedidos atribuidos (`models/market_measurement.py:14-35`, `views/market_trust.py:38-39`) |
| Tiempo promedio para publicar un menú | **SÍ** | Reloj de borrador firmado (itsdangerous, máx. 7200 s) y promedio en panel confianza (`market_kitchen.py:64,237-241`, `market_trust.py:43,47`) |
| Pedidos completados por negocio | **SÍ** | `indicators` y reportes de ventas (`models/market.py:223-233`, `analytics/management.py:51-70`) |
| % de clientes que vuelven a comprar | **SÍ** | `repeat/customers` en cocina y dashboard (`models/market.py:225,231`) |
| % de excedentes sobre producción | **SÍ** | Producido vs. sobrante al cierre con % + porciones rescatadas y ahorro (`market_kitchen.py:53-55`, `models/market.py:232-233`) |
| Precisión de clasificación y aceptación de sugerencias | **PARCIAL** | Aceptación de visión sí se mide (`vision_used/accepted`); **precisión del clasificador no** (requiere fotos etiquetadas, la doc lo reconoce) |
| Falsos positivos y tiempo de revisión de moderación | **PARCIAL** | Señales del mercado: desestimadas vs. total y horas medias sí (`market_trust.py:40-46`); moderación de contenido guarda historial pero **no agrega falsos positivos ni tiempos** |
| Diferencias inventario registrado vs. real | **PARCIAL** | El conteo físico registra el delta por movimiento (`market_kitchen.py:160-164`) pero **no hay indicador agregado de varianza** en ningún dashboard |

Adicionales implementados: ingresos/contribución por negocio con comparación entre períodos, indicadores globales admin, snapshot BI versionado sin PII (`analytics/metrics.py`, `schema_version: bi.v1`, con tests que verifican que no inventa métricas vacías).

## 7. Escenario estrella "Gastronomía inteligente e inclusiva" (7 pasos)

| Paso del escenario | ¿Demostrable hoy? | Matiz |
|---|---|---|
| 1. Emprendedora registra negocio de comida casera sin local físico | **SÍ** | Tipos "Comida casera"/"Cocina desde casa", canales delivery/recojo sin domicilio público; requiere aprobación admin |
| 2. Sube foto y la IA propone nombre, categoría y descripción | **SÍ con clave Gemini** | Sin `GEMINI_API_KEY` degrada a borrador manual (huella y calidad siguen) |
| 3. Registra ingredientes, porciones, costos y disponibilidad para mañana | **SÍ** | Lotes con vencimiento/costo, receta por porción, publicación fechada |
| 4. Copiloto propone menú con ingredientes restantes y calcula costos | **SÍ a medias** | La IA propone en texto libre; el cálculo determinista exige transcribir la receta al simulador |
| 5. Consumidor busca por presupuesto, recojo y restricciones alimentarias | **SÍ** | Filtros + NL con fallback local; compatibilidad conservadora ante alérgenos no declarados |
| 6. Recomendador explica opciones y permite comprar o reservar | **SÍ** | Campo `why` por oferta; compra con revalidación transaccional; reserva de mesa existe pero sin capacidad |
| 7. La venta actualiza inventario y el panel registra ingresos y demanda | **SÍ** | Descuento por lote en la misma transacción; dashboard con ventas, repetición, horario pico y forecast |

**Conclusión:** el escenario estrella es demostrable de principio a fin con dos condiciones: clave de Gemini configurada y aceptar que el paso 4 requiere transcripción manual de la receta sugerida.

## 8. Hallazgos críticos y brechas priorizadas

Ordenados por riesgo/impacto respecto a la propuesta:

1. **Reputación contaminable (grave):** `POST /api/reviews` (`views/main.py:629-667`) acepta reseñas sin compra verificada y el rating las incluye (`models/review.py:47-76`). Contradice el requisito "reseñas vinculadas a compras verificadas". El flujo mercado sí lo cumple; el legacy no.
2. **Ofertas del mercado sin moderación de contenido:** nombre/descripción/procedencia se publican sin pasar `ContentFilter` (`market_kitchen.py:179-244`). La propuesta exige moderar publicaciones.
3. **Pagos sin validación real:** todo probado con mocks; falta ciclo completo en sandbox de Mercado Pago con URL HTTPS (alta vendedor, pago, webhook, devolución). Además la firma no valida antigüedad del `ts` (replay teórico) y no hay reembolsos parciales.
4. **Voz incompleta:** solo dictado→borrador con una plantilla; faltan consulta de ventas, faltantes y resumen del día por voz (pedido explícito en la propuesta §12).
5. **Chat del consumidor sin datos de plato:** no puede responder porciones/ingredientes/alérgenos/horarios/modalidades porque no se inyectan al contexto del LLM; sin fallback local en `/api/ai/*`.
6. **Reservas sin capacidad ni mesas:** sobre-aforo posible; sin cancelación por el comensal ni moderación de conflictos.
7. **Fidelización incompleta:** puntos sin canje, cupones no personalizados, campañas para inactivos ausentes, recordatorios solo en pantalla.
8. **Plan semanal simplificado:** 1 comida/día, sin cercanía/horarios, sin descargo "no nutricional clínico".
9. **Infraestructura de despliegue ausente:** sin nube, backups, monitoreo ni scheduler para `liberar-vencidos` (depende de cron externo).
10. **Deuda de código y tests:** `models/moderation_filter.py` muerto; `templates/partials/map_sidebar.html` vacío; `Flask-Login` sin usar; sin tests de rescate/`effective_price`, conteo físico, CLI de vencidos, reembolso, constancia, radio de delivery, división de cuenta, voz, `market_discovery`, copiloto, ni del endpoint del plan semanal.
11. **Menores:** alergias por subcadena sin catálogo normalizado; sin historial de preferencias alimentarias; `prepared`/`origin` texto libre sin validar; taxonomía legacy sin sincronizar con las 3 dimensiones; equipo sin roles granulares; 2FA opcional; recuperación sin canal de entrega; direcciones sin geocodificar.

## 9. Qué NO se verificó en esta auditoría

- **No se ejecutó la suite de pruebas.** Requiere PostgreSQL desechable con TLS y no se tocó ninguna base viva. Conteo estático: **88 funciones `test_`** en `test/`; varias están parametrizadas (`test_content_filter.py`, `test_admin_ai.py`), lo que es compatible con los 111 casos recogidos que declara `PLATAFORMA.md`, pero **ese número y su aprobación no se re-verificaron en esta auditoría**.
- No se probó ninguna integración externa en vivo: Mercado Pago (sandbox o real), Groq/Qwen, Gemini, Nominatim/OSM. Su comportamiento real, cuotas, latencia y coste quedan sin verificar.
- No se hizo QA visual ni de accesibilidad en navegador (la doc reporta recorridos Playwright/Edge previos; no se repitieron).
- No se midió carga concurrente ni rendimiento del Supabase de producción.
- La auditoría es de código estático + lectura de tests: "implementado" significa que la lógica existe y es coherente, no que se ejecutó extremo a extremo en esta sesión.
- No se modificó ningún archivo del proyecto; este informe es el único entregable nuevo.