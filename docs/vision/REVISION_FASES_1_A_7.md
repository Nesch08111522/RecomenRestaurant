# Revisión operativa de SmartResto: fases 1 a 7

Fecha: 18 de noviembre de 2026 (America/Lima).
Referencia: smartresto-plan-maestro-2026-11-18.txt y smartresto-ecosistema-2026-11-18.txt.

## Alcance y método

Se contrastaron los módulos actuales con las primeras siete fases. Las pruebas de escritura e integración se ejecutaron en PostgreSQL local desechable con TLS y los esquemas app_records, ai_decisions y platform_foundation. No se importaron cuentas ni pedidos de producción. La comprobación de Supabase fue de lectura. Se probaron además respuestas reales de texto, visión y meteorología.

Las pruebas de navegador utilizan cuentas locales y datos controlados. Se bloquean recursos externos para medir estructura, adaptación, navegación y respuesta HTTP de manera reproducible; por tanto, esas pruebas no acreditan por sí solas la entrega de mapas, fuentes, multimedia externa o cada proveedor de terceros.

## Matriz por fase

| Fase | Elementos revisados | Evidencia y alcance |
| --- | --- | --- |
| 1. Arquitectura | PostgreSQL, módulos Flask, APIs, contexto de negocio, auditoría, CSRF, temas | Pruebas platform_foundation, platform_health, database_connection, phase11_qa. Supabase respondió y las tablas centrales existen. |
| 2. Usuarios y permisos | Autenticación, recuperación, 2FA, perfiles, presupuestos, consentimiento, membresías y personal | account_security, phase2_permissions, platform_profile_api, navigation y business_flow. Se valida rol y propiedad en servidor. |
| 3. Descubrimiento | Procedencia, fuentes autorizadas, duplicados, reclamaciones, cuotas, SSRF, actualización periódica | Todas las pruebas phase3. Fuente OSM habilitada y tarea diaria registrada con autorización de la usuaria. Primera recuperación externa no completada por timeout del proveedor: pendiente de corrida real satisfactoria. |
| 4. Portal empresarial | Editor por propietario, publicación, páginas públicas, sucursales, contenido asistido, cuotas | phase4_sites, phase4_publication, phase4_ai_quota. Editor revisado en navegador y ancho móvil corregido. |
| 5. Catálogo multimodal | Productos, variantes, ingredientes, medios, borradores, importación Excel, confirmación | phase5_catalog, phase5_ai_nullable, phase5_workbook, phase5_flow. Visión real respondió con una fotografía editorial. Dictado depende del navegador/micrófono; existe transcripción manual. |
| 6. Marketplace | Rubros, filtros, comparación, ficha, geografía, disponibilidad, favoritos y buscador | phase6_catalog, phase6_rbac, phase8_geo, forest_home, business_flow. Revisados /explorar, /mercado y /ofertas. |
| 7. Recomendaciones | Preferencias, restricciones, presupuesto, horarios, clima, compras confirmadas, descubrimiento y explicaciones | phase7_recommender, phase7_personalization, recommendations_routes, recommendation_history y prueba concurrente nueva. Texto y clima reales respondieron. |

## Correcciones realizadas durante la revisión

- El motor pyDatalog se inicializa por solicitud/hilo y descarta los hechos anteriores. Se corrigió la aridad de las reglas de exclusión para que se correspondan con los hechos alimentarios. La prueba concurrente comprueba aislamiento usando el mismo usuario y restaurante.
- El listado administrativo/empresarial ya admite restaurantes sin horario. Reutiliza la lógica de horario de Lima, incluyendo atención que cruza medianoche.
- Login y registro conservan la página de destino al cambiar de vista sin guardar credenciales en el navegador.
- La decoración del editor de sitios queda contenida en su composición, evitando el desbordamiento móvil.
- Se actualizaron pruebas antiguas que esperaban un mapa lateral, tres restaurantes destacados, un panel visual móvil y transiciones internas que ya fueron sustituidos por decisiones de interfaz posteriores.
- Los paneles de gestión usan los mismos tokens de texto, superficie y bordes que el tema activo, corrigiendo enlaces de bajo contraste en modo oscuro.
- El manifiesto público describe la implementación actual: trabajador nativo de descubrimiento y web adaptable. Se retiraron afirmaciones sobre PWA o Redis/Celery que no correspondían a servicios activos.
- Los fallos conocidos de proveedores de descubrimiento conservan un diagnóstico seguro más específico en el historial.

## Integraciones reales y operación

- **Supabase:** conexión y existencia de tablas centrales verificadas en lectura.
- **OpenRouter texto:** respuesta HTTP 200 utilizando el modelo configurado localmente; no se publicaron credenciales.
- **OpenRouter visión:** respuesta HTTP 200; devuelve un borrador que requiere revisión del empresario.
- **Open-Meteo:** respuesta válida para coordenadas públicas de Trujillo.
- **OpenStreetMap/Overpass:** fuente creada/habilitada con radio de 3 km sobre el centro configurado de Trujillo y frecuencia diaria. Las primeras consultas agotaron su tiempo de espera. No se publicaron fichas ni se inventaron resultados.
- **Tarea Windows:** SmartResto-Discovery-Refresh, diaria a las 04:15 en SA Pacific Standard Time (UTC−05, Lima). Requiere equipo encendido, sesión del usuario y acceso de red. No ejecuta publicaciones ni envía invitaciones externas.
- **Voz:** SpeechRecognition del navegador cuando está disponible; no se afirma compatibilidad universal. La transcripción manual mantiene disponible la preparación asistida.
- **Mapas y WebGL:** existen alternativas sin compartir ubicación y fotografía de respaldo; los permisos del navegador y del dispositivo siguen siendo necesarios.

No se añadieron dependencias sin una necesidad funcional. La fase 3 no se declara completamente operativa hasta que exista una corrida externa real satisfactoria. La validación de resoluciones representativas tampoco equivale a probar físicamente todos los dispositivos o todos los navegadores.

## Resultados de pruebas

Resultado consolidado: **405 pruebas aprobadas**, sin fallos, en 183,58 segundos. Se registra en qa-fases-1-7.xml. La matriz de páginas y tamaños queda en qa-responsive-fases-1-7.json: **29 páginas, 270 casos**, en temas claro y oscuro, sin respuestas HTTP fallidas ni desbordamiento horizontal. Se probaron 320, 375, 480, 640, 768, 1024, 1280, 1440 y 1920 px en páginas principales; el resto se revisó a 375, 768 y 1440 px. Las pruebas por rol se ejecutaron con administrador, empresario, comensal y visitante. No se guardan contraseñas, cookies ni claves en estos informes.

Referencias de proveedores: [Overpass API y políticas de uso](https://wiki.openstreetmap.org/wiki/Overpass_API), [documentación de OpenRouter](https://openrouter.ai/docs).
