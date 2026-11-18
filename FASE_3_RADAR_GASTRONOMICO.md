# SmartResto — Fase 3: Radar gastronómico

**Estado:** implementación técnica integrada; validación externa de descubrimiento y activación de la tarea periódica pendientes.  
**Fecha:** 17 de noviembre de 2026.

## 1. Qué cambia en SmartResto

El radar se incorpora al mismo proyecto Flask, a las sesiones existentes, al sistema central de permisos y al PostgreSQL de Supabase. No es una aplicación separada. No se modificó `.env`, no se sustituyeron credenciales ni se agregaron dependencias o migraciones para esta fase.

El recorrido implementado es:

**Fuente autorizada → captura con evidencia → ficha provisional → detección de faltantes y duplicados → revisión administrativa → invitación → solicitud empresarial → verificación de titularidad → registro comercial y moderación existentes.**

Los borradores no entran automáticamente al catálogo público ni al recomendador. Aprobar una ficha es aprobar su incorporación provisional, no afirmar que sus precios, horarios, platos o disponibilidad son reales. Tampoco una invitación demuestra propiedad.

## 2. Acceso y arranque

Si el servidor estaba abierto antes de estos cambios, detén únicamente tu servidor con `Ctrl+C` y vuelve a iniciar desde la raíz del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

| Perfil | Entrada | Función |
|---|---|---|
| Administrador | `http://127.0.0.1:5000/admin/discovery` | Radar, fuentes, fichas, evidencia, duplicados, corridas y reclamaciones |
| Administrador | `http://127.0.0.1:5000/admin/discovery/google-lookup` | Consulta puntual Google Places, sin persistencia ni mapa de otro proveedor |
| Empresario | `http://127.0.0.1:5000/owner/discovery` | Sus solicitudes y negocios reclamados; continuación al registro comercial |
| Invitado/empresario | `/reclamar#token=...` | Vista de invitación y solicitud de titularidad |

Los enlaces de radar administrativo y negocios reclamados están integrados en la navegación de cada perfil. Las rutas administrativas rechazan visitantes y comensales. La sesión se revalida desde el modelo de usuarios; no basta con alterar el rol de una cookie.

## 3. Cobertura de los requisitos del radar

| Requisito | Implementación y límite |
|---|---|
| 1. Búsqueda automática de negocios de comida | Consulta OSM/Overpass acotada por zona. Código disponible; las consultas reales desde este entorno terminaron en timeout y todavía requieren validación de conectividad. |
| 2. Fuentes públicas autorizadas | OSM bajo ODbL y páginas exactas registradas por el administrador con evidencia de permiso/licencia, alcance y vencimiento. No scraping de plataformas restringidas. |
| 3. Mapas y consultas Google Places | Mapa de candidatos OSM. Google en pantalla independiente y solo bajo demanda. Requiere clave y facturación; no se configuraron nuevas claves. |
| 4. Tipos de establecimientos | Restaurante, cafetería, panadería, pastelería, juguería, emprendimiento, cocina oculta, tienda y puesto de comida mediante etiquetas OSM o datos estructurados explícitos. No se infiere una categoría inexistente. |
| 5. Categorías gastronómicas | Categorías de cocina declaradas en OSM; el registro comercial permite al titular elegir la categoría interna correspondiente. |
| 6. Páginas y redes oficiales | Referencias detectadas a web, Facebook, Instagram, YouTube o TikTok. Se etiquetan como no verificadas; detectar un enlace no acredita oficialidad. |
| 7. Menús publicados | Detección de enlaces a carta, menú y PDF. No se afirma haber interpretado el contenido de todos esos documentos; no se copian automáticamente platos ni precios. |
| 8. Extracción con IA | OpenRouter/proveedor compartido, sin herramientas ni privilegios; solo campos básicos con citas exactas. Flujo implementado, no validado en vivo con una página oficial autorizada en esta sesión. |
| 9. Fotografías y videos disponibles | Referencias URL, sin descarga, reproducción en las tarjetas o reutilización de archivos cuya licencia se desconozca. |
| 10. Duplicados | Identidad fuente + ID; nombre normalizado + dirección o proximidad de hasta 75 m. Se marcan posibles coincidencias, no se fusionan automáticamente. El administrador puede documentar que son negocios/sucursales distintos. |
| 11. Información incompleta | Lista de campos ausentes y coordenadas no disponibles. No se reemplazan por hechos inventados. |
| 12. Confianza | Indicador transparente de completitud de seis campos y nivel alto/medio/bajo. No es una probabilidad de exactitud ni una verificación externa. |
| 13. Fichas provisionales | Estado inicial `pending_review`, evidencias por campo, fecha UTC, fuente y licencia. |
| 14. Invitación a reclamar | Enlace firmado, hash almacenado, TTL de siete días y un solo uso. Se genera para copiar/compartir: no se envió correo, WhatsApp ni invitación externa automáticamente. |
| 15. Actualización periódica | Worker CLI con fuentes activas/vencidas, cadencia por fuente y errores aislados. Instalador Windows incluido; tarea no registrada en esta sesión. |
| 16. Revisión administrativa | Aprobación/rechazo, resolución de falsos duplicados, propuestas de cambios, historial anterior y verificación independiente de titularidad, con auditoría central. |

## 4. Persistencia y relación con las tablas existentes

Se utilizan las tablas que ya existen en Supabase. Los datos auxiliares se guardan en `public.app_records` con colecciones `discovery_sources`, `discovery_runs`, `discovery_candidates`, `discovery_invitations` y `discovery_claims`.

La aprobación de una ficha crea un negocio en `sr_businesses` y una sucursal en `sr_branches`, ambos en estado `draft`. Reaprobar una actualización conserva esos IDs en vez de generar entidades duplicadas. La verificación de un empresario crea su vínculo en `sr_memberships`. La posesión de una invitación no realiza esa operación.

En **Negocios reclamados**, el empresario continúa al formulario comercial existente. El servidor vuelve a verificar titular, estado de la ficha y ausencia de alta previa. Los IDs de negocio y sucursal se derivan del registro autorizado, no de campos enviados por el navegador. El restaurante queda sin verificar y sigue la moderación habitual. Precio, calificación, modalidad y horarios no se completan desde conjeturas de IA.

Las operaciones sensibles usan transacciones PostgreSQL y un bloqueo advisory para evitar doble consumo de invitaciones, altas repetidas y corridas simultáneas de una misma fuente. La auditoría registra actor, recurso, decisión y motivo, sin tokens ni claves.

## 5. Actualización periódica local

El worker no corre dentro del servidor Flask ni depende del recargador de desarrollo. Se ejecuta desde la raíz:

```powershell
python -m scripts.refresh_discovery
```

Procesa hasta veinte fuentes activas cuya fecha `next_refresh_at` ya venció. La cadencia inicial es de siete días por fuente, configurable entre uno y treinta días. Una fuente que falla no impide actualizar la siguiente, no elimina el catálogo anterior y se programa para un intento posterior. No se publican fichas por esta vía.

Para registrar la tarea diaria, ejecuta desde **tu PowerShell de usuario**:

```powershell
.\scripts\install_discovery_task.ps1
```

La tarea se llamará `SmartResto-Discovery-Refresh`, se ejecutará a las **04:15 en la hora local de Windows** y comprobará qué fuentes realmente están vencidas. Usa el Python de `.venv`, requiere sesión de usuario, equipo encendido y red; no es un servicio 24/7. Se ignoran ejecuciones solapadas y se limita la ejecución a diez minutos.

Puedes elegir otro horario o retirar únicamente esta tarea:

```powershell
.\scripts\install_discovery_task.ps1 -Time '09:00'
.\scripts\install_discovery_task.ps1 -Remove
```

**No se registró la tarea bajo la cuenta técnica de herramientas.** El instalador tampoco solicita ni guarda contraseñas. Si una tarea del mismo nombre existe, no se sustituye sin retirarla expresamente. El proyecto debe conservar su ruta o reinstalarse la tarea al moverlo.

## 6. Proveedores y permisos

### OpenStreetMap/Overpass

El proveedor curado es `https://overpass.private.coffee/api/interpreter`, verificado en el directorio oficial OSM y directamente en sus términos. Permite uso comercial, consultas acotadas y sin registro; exige uso razonable, evitar PII, limitar simultaneidad y cumplir ODbL. Es un servicio sin garantía. No se emplea una URI de pooler inventada ni se altera Supabase.

La instancia principal `overpass-api.de` devolvió un estado 502 que indicaba trabajadores ocupados y cola llena. Private.coffee también agotó el tiempo de espera de HTTP desde este dispositivo. Se comprobó que hubo negociación TLS en direcciones del proveedor principal; eso no equivale a completar una consulta. Se probaron selección IPv4 pública validada y ALPN HTTP/1.1, sin desactivar certificados ni cifrado.

**Pendiente operativo:** completar una búsqueda real desde la red del usuario antes de afirmar que el descubrimiento automático está funcionando de extremo a extremo. La bandeja informa del fallo y conserva los datos; no muestra candidatos de prueba como descubrimientos reales.

### Páginas oficiales

El administrador registra una URL HTTPS exacta, evidencia de autorización y alcance. El permiso tiene vencimiento, treinta días por defecto. Se comprueba `robots.txt`; una respuesta bloqueada, inesperada o una redirección detiene la consulta. Robots no sustituye una licencia. Los activos visuales siguen con permiso de reutilización pendiente aunque la página autorice extraer texto.

El cliente valida A/AAAA, rechaza redes privadas, multicast y reservadas y conecta a una IP pública ya validada conservando Host/SNI. No acepta credenciales en URL, puertos alternativos, redirecciones, proxies o cookies. La captura HTML está limitada a 250 KB; no se navega ni ejecuta JavaScript de fuentes externas. Se requiere revisión adicional de infraestructura/egress y licencias antes de producción pública sostenida.

### Google Places

El adaptador usa `GOOGLE_PLACES_API_KEY` o `GOOGLE_MAPS_API_KEY` si ya existen en el entorno, sin escribir `.env`. Solicita una máscara de campos mínima y hasta diez resultados. La respuesta no se entrega al repositorio de importación, no se mezcla con el mapa OSM y muestra atribución Google Maps/proveedores. No se copian resultados a la base ni a logs del catálogo.

La clave, cuotas, facturación, términos públicos y política de privacidad aplicables deben estar configurados antes de habilitar esta integración para producción. No se afirmó una consulta Google real exitosa en esta implementación.

## 7. Contratos HTTP principales

Las escrituras JSON requieren el token CSRF del sitio. Los datos externos se presentan como texto escapado. Las respuestas del módulo usan `Cache-Control: no-store`; el flujo de reclamación además aplica `Referrer-Policy: no-referrer`. El token va en el fragmento del enlace y en el cuerpo POST, no en la ruta ni en parámetros de acceso del servidor.

| Método y ruta | Operación |
|---|---|
| `GET /admin/api/discovery/candidates` | Listar borradores; filtros `status` y `q` |
| `GET/POST /admin/api/discovery/sources` | Consultar o registrar fuentes autorizadas |
| `PATCH /admin/api/discovery/sources/<id>` | Activar/pausar con `enabled` booleano |
| `POST /admin/api/discovery/runs` | Consultar una fuente; `source: "osm"` o ID de fuente |
| `POST /admin/api/discovery/candidates/<id>/review` | `approve`, `reject`, `accept_update` o `mark_distinct`, con `notes` |
| `POST /admin/api/discovery/candidates/<id>/invite` | Generar enlace, vencimiento y estado `generated_not_sent` |
| `POST /admin/api/discovery/claims/<id>/review` | Aprobar/rechazar titularidad, con motivo |
| `POST /admin/api/discovery/google` | Consulta efímera con `q` |
| `GET /admin/api/discovery/export/osm` | Exportar campos OSM con atribución y enlace ODbL |
| `POST /api/discovery/invitations/preview` | Vista mínima de una invitación válida |
| `POST /api/discovery/claims` | Solicitud del empresario con `token` y `proof` |

La consulta OSM inicial está limitada a 3 km y hasta cien fichas nombradas, con tope técnico de 200 y radio máximo de 10 km. Hay una pausa de dos minutos entre consultas de una misma fuente. La exploración no observa personas, visitas, aforo o ubicación de comensales.

## 8. Verificación realizada y pendientes

| Comprobación | Resultado confirmado |
|---|---|
| `python -m pytest -q` | **157 aprobadas, 24 omitidas, 0 fallidas** |
| Smoke Supabase de solo lectura | **33 comprobaciones, 0 fallos**; páginas, acceso, assets locales y preparación SQL mediante `EXPLAIN` |
| Plantillas Jinja | **66 compiladas** |
| Python y JavaScript nuevos/modificados | Compilación Python y `node --check` correctos |
| Instalador PowerShell | Sintaxis validada; no ejecutado para registrar tarea |
| Diff Git | Sin errores de espacios; avisos normales de conversión LF/CRLF de Windows |
| Consultas Overpass reales | **No completadas**: saturación/timeout; sin candidatos falsos ni publicación de prueba |
| Nueva extracción IA con página autorizada | **Pendiente de comprobación real** |
| Consulta Google real | **Pendiente de clave/facturación/configuración** |
| Pruebas de escritura en PostgreSQL desechable | No equivalen al smoke de solo lectura; las pruebas dependientes de entorno se omiten si no está configurado |
| Navegador end-to-end, mapa y responsive renderizados | No se realizó una sesión interactiva completa de navegador en esta entrega |

Las pruebas nuevas cubren evidencia, valores desconocidos, categorías, deduplicación, falsos duplicados, re-revisión canónica, conservación de titularidad, grounding IA, direcciones de red inseguras, permisos, claims de un solo uso, cabeceras privadas, worker y aislamiento del puente comercial. Las pruebas del repositorio en memoria no reemplazan una corrida de escritura en una base desechable.

Para revisar los motivos exactos de las pruebas omitidas: `python -m pytest -q -rs`. No se ejecutaron pruebas destructivas ni se agregaron cuentas, negocios o precios ficticios a Supabase para producir una demostración.

## 9. Organización del código

| Archivo | Responsabilidad |
|---|---|
| `logic/business_radar.py` | Normalización, clasificación explícita, evidencia, faltantes, completitud, coincidencias y transiciones |
| `utils/discovery_sources.py` | HTTP seguro, OSM, página autorizada, IA con citas y Google efímero |
| `models/discovery.py` | Colecciones auxiliares, transacciones, revisión, invitación y titularidad |
| `views/discovery.py` | APIs, RBAC, páginas y cabeceras privadas |
| `views/admin.py` | Puente autorizado a registro comercial existente |
| `templates/discovery/` | Radar, reclamación, consulta Google y espacio empresarial |
| `static/css/discovery.css`, `static/js/discovery.js` | Sistema premium soft realism, grillas, ambos temas y acciones seguras |
| `scripts/refresh_discovery.py` | Worker nativo por fuentes vencidas |
| `scripts/install_discovery_task.ps1` | Alta/remoción de tarea diaria Windows bajo usuario |
| `test/test_phase3_*.py` | Regresiones específicas |

## 10. Fuentes verificadas

Las reglas de OSM/ODbL se contrastaron con [Copyright and License](https://www.openstreetmap.org/copyright), [Attribution Guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines) y [Licence and Legal FAQ](https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ). La operación Overpass se contrastó con [su manual de uso compartido](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html), [directorio oficial de instancias](https://wiki.openstreetmap.org/wiki/Overpass_API) y [términos directos de Private.coffee](https://overpass.private.coffee/).

Google se contrastó con [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies), [Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search), [Google Maps Platform terms](https://cloud.google.com/maps-platform/terms) y [Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms). Antes de distribución pública, revisar su aplicación jurídica y contractual al negocio.

Los controles de seguridad siguen [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) y [token lifecycle guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).

---

**Criterio de cierre:** el módulo está implementado y conectado. No se presentará como una Fase 3 operativa al 100 % mientras falten la búsqueda externa real, la activación de la actualización periódica y las verificaciones de producción correspondientes. Las siguientes fases no deben saltarse esos pendientes.
