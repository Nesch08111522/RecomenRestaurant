# SmartResto — Fase 4: Portal empresarial y sitios de marca

**Fecha:** 17 de noviembre de 2026.  
**Estado:** código integrado en el proyecto Flask existente; IA pagada validada en texto e imagen. No se ha desplegado ni publicado una web en Internet como parte de esta entrega. No se modificó `.env`.

## 1. Cómo entrar y crear el sitio

Reinicia tu servidor si estaba abierto antes de los cambios:

```powershell
python app.py
```

Inicia sesión como **empresario** y abre **Mi sitio y marca** en la navegación, o entra en `http://127.0.0.1:5000/owner/sites`.

1. Selecciona uno de tus establecimientos registrados. Cada empresario solo ve y modifica sus negocios.
2. Edita nombre visible, dirección personalizada —slug—, descripción, historia, colores y plantilla.
3. Sube tu logotipo PNG, JPG o WebP. El servidor valida el archivo, lo convierte a PNG y extrae una paleta de hasta cinco colores.
4. Describe la identidad que buscas y pulsa el asistente IA. La solicitud incluye los datos actuales del formulario, colores y, cuando es un logo propio subido, su imagen. No necesitas guardar antes para que la propuesta use ese logo.
5. Revisa la propuesta. **Aplicar** solo actualiza el formulario; **Guardar borrador** conserva los cambios en Supabase.
6. Abre **Previsualizar**. La vista previa requiere tu sesión y no es indexable ni pública.
7. Confirma que tienes derechos sobre texto, imágenes y videos. Un negocio aprobado puede publicar su snapshot; los negocios pendientes de aprobación pueden preparar su diseño pero no publicarlo.

La dirección resultante es `/negocio/tu-slug`. Los espacios públicos por sucursal relacionada son `/negocio/tu-slug/sucursal/ID_DEL_ESTABLECIMIENTO`.

Editar el borrador no cambia la versión publicada. **Publicar** guarda una copia separada, y **Retirar** desactiva la página pública. Un error al guardar impide que el botón publique accidentalmente una versión anterior.

## 2. Qué hace la IA pagada

Se utiliza `utils/llm_provider.py`, el mismo proveedor configurado para SmartResto. Las claves permanecen en servidor. No se creó una clave alternativa ni se sustituyó la configuración.

Se comprobaron dos llamadas reales a **OpenRouter**, ambas con **HTTP 200**:

- Propuesta basada en texto, negocio y colores usando `openrouter/auto`.
- Propuesta multimodal usando un raster sintético en memoria como logo y su paleta, con `openrouter/auto`.

Estas fueron pruebas técnicas: sus resultados no se guardaron ni se publicaron como negocios reales. No equivalen a validar todas las marcas, todos los modelos ni todos los casos visuales.

Cuando existe un logo propio, se usa `AI_VISION_MODEL` si está configurado; de lo contrario se usa el modelo compartido. El proveedor debe admitir imágenes para ese caso. Si falla, el editor informa del problema en lugar de fingir una propuesta correcta.

La IA devuelve un esquema cerrado: nombre, tagline, descripción, historia, color principal, color secundario, plantilla y textos SEO. El diseño especial se construye combinando esa propuesta con los componentes premium existentes. **No se entrena un nuevo modelo de lenguaje por empresa ni se ejecuta HTML/CSS/JavaScript generado por el proveedor.** Esto mantiene todas las páginas dentro del mismo ecosistema y reduce inyección de código y cambios no autorizados.

Las plantillas son `atelier`, `bistro` y `studio`, con diferencias visuales declarativas. La IA selecciona y personaliza una de ellas; el titular puede cambiarla. Debe revisar los textos antes de publicar, especialmente afirmaciones sobre historia, ingredientes, premios o beneficios de salud.

Hay una cuota persistente de **20 solicitudes por empresario y hora**, con separación mínima de **20 segundos**. También se acota la salida a 1.400 tokens por llamada. Los intentos fallidos consumen cuota para impedir reintentos ilimitados. Esta cuota no sustituye un presupuesto monetario configurado en OpenRouter.

## 3. Cobertura de los 18 requisitos

| Requisito | Implementación |
|---|---|
| 1. Página pública por negocio | Sitio SSR de marca por slug; publicación explícita de snapshot |
| 2. Página independiente por sucursal | Ruta con dirección, horario, carta y reseñas del establecimiento; exige mismo negocio canónico y propietario, además de aprobación |
| 3. Nombre, logotipo e identidad | Nombre editable, subida raster validada, paleta del logo y propuesta IA |
| 4. Descripción empresarial | Edición manual y propuesta asistida |
| 5. Historia y presentación | Campo dedicado; la IA recibe instrucciones de no inventar años o hechos |
| 6. Galería | Hasta veinte referencias a imágenes propias o autorizadas; renderizado sin copiar fotografías de terceros |
| 7. Videos cortos | Hasta ocho URLs HTTPS directas MP4/WebM, con controles y sin autoplay; esta fase no transcodifica ni verifica la duración de clips externos |
| 8. Especialidades y platos destacados | Hasta doce especialidades y doce IDs de platos propios; el servidor rechaza platos ajenos |
| 9. Carta digital | Reutiliza los platos disponibles de `DishModel`; no duplica carta o precios en otra base |
| 10. Promociones y descuentos | Presenta la promoción existente del restaurante. La aplicación efectiva de descuentos sigue las reglas del mercado; el sitio no crea un motor adicional de cupones ni inventa descuentos |
| 11. Horarios y ubicación | Datos reales del establecimiento y sucursal; faltantes aparecen como pendientes de confirmar |
| 12. Delivery y recojo | Campos informativos editables y enlace al mercado existente |
| 13. Reseñas | Solo compras verificadas, no ocultas ni rechazadas; se muestran rating, comentario y fecha, no IDs privados del comensal |
| 14. Redes sociales | Enlaces HTTPS validados a plataformas admitidas y web del negocio |
| 15. Colores y plantillas | Dos colores hexadecimales, plantillas seleccionables y preview; editor claro/oscuro |
| 16. Metadatos sociales | Title, descripción, Open Graph, Twitter Card y JSON-LD en HTML inicial |
| 17. Dirección personalizada | Slug reservado entre borradores y publicados bajo bloqueo transaccional; no se compra ni configura un dominio externo automáticamente |
| 18. Asistente de redacción | Propuesta con tu IA pagada, revisión, aplicación al formulario y guardado separados |

El botón de pedidos enlaza al mercado ya existente. No se implementó un segundo checkout ni un servicio de pedidos desconectado para cada sitio.

## 4. Relación con Supabase y los módulos anteriores

No se requieren nuevas tablas o migraciones para esta fase. Se usa `public.app_records` para las colecciones auxiliares:

- `business_sites`: borrador, snapshot publicado y hasta veinte revisiones previas.
- `business_site_media`: logos reencodificados, paleta y titular/establecimiento propietario.
- `business_site_ai_quota`: ventana de consumo por empresario.

Los datos comerciales siguen en los modelos actuales de restaurante, platos, reseñas y mercado. Los establecimientos enlazados desde el radar conservan sus `business_id` y `branch_id` existentes. Las páginas de sucursal no combinan negocios que solo comparten un nombre o un propietario.

**Importante para datos históricos:** un restaurante sin `business_id` no se agrupa automáticamente con otros locales del empresario. Las sucursales deben estar relacionadas correctamente antes de aparecer juntas. Las ramas públicas corresponden a establecimientos operativos registrados, no a una sucursal canónica vacía que todavía no tenga su carta/datos comerciales vinculados.

## 5. Seguridad y privacidad

Las escrituras requieren sesión empresarial revalidada, propiedad del restaurante y CSRF. No se confía en `owner_id`, estado publicado, código, CSS o permisos enviados por el navegador. Las referencias a logos internos se comprueban contra el propietario y establecimiento.

Se rechazan URLs con credenciales, HTTP, redes locales y rangos inseguros. La galería y los videos son referencias: el backend no navega URLs arbitrarias ni ejecuta sus scripts. Se requiere confirmación de derechos antes de publicar; una casilla no sustituye una licencia real ni elimina la obligación de atender retiros de contenido.

El logo tiene límite de 2 MB y 8 megapíxeles, admite PNG/JPEG/WebP y se reencodifica a PNG, sin metadatos EXIF. No admite SVG activo. No se expone el archivo subido originalmente. Para un catálogo grande se recomienda almacenamiento de objetos y CDN con políticas de propietario; guardar logos pequeños en JSONB es una solución de esta fase, no una arquitectura ideal para videos de gran tamaño.

La vista previa no publica ni indexa. Los endpoints privados usan `Cache-Control: no-store`. Los datos dinámicos se escapan con Jinja y las propuestas IA se insertan como texto en el editor. Las operaciones de borrador/publicación/retiro/propuesta se registran mediante la auditoría central, sin incluir claves o prompts completos.

La reserva de slugs y publicación usan el mismo advisory lock transaccional. Esto protege las escrituras realizadas por la aplicación. Acceso directo privilegiado a Supabase puede eludir invariantes de JSONB: restringir ese acceso y añadir índices/constraints dedicados si se permite escritura externa o el volumen crece.

## 6. URLs públicas, metadatos y despliegue

Los slugs funcionan localmente desde el momento en que publicas un negocio aprobado. Para que sean accesibles desde fuera del equipo, todavía necesitas desplegar **esta misma aplicación**, TLS y un dominio real. No se abrió ningún puerto al Internet ni se compró un dominio durante la implementación.

Canonical y `og:url` no se construyen desde el Host enviado por el cliente. Se emiten únicamente cuando `SMARTRESTO_PUBLIC_ORIGIN` contiene un origen HTTPS público configurado. No se modificó `.env`: esta variable puede suministrarse desde el entorno del servidor al desplegar.

Ejemplo solo después de disponer de un dominio real:

```powershell
$env:SMARTRESTO_PUBLIC_ORIGIN = 'https://TU-DOMINIO-REAL'
python app.py
```

No uses el marcador como un dominio operativo. Para imágenes sociales locales se antepone ese origen explícito; sin un origen público no se inventan URLs de compartición. Los metadatos no garantizan por sí solos una vista previa en una red social: la página y su imagen deben ser alcanzables públicamente.

Las fuentes e iconos usan Google Fonts con fallback; una red que bloquee ese proveedor puede mostrar la tipografía de respaldo. No se realizó una inspección interactiva completa en navegador de todas las combinaciones de plantilla/color/resolución en esta entrega.

## 7. Verificación confirmada

| Comprobación | Resultado |
|---|---|
| Suite global `python -m pytest -q` | **172 aprobadas, 24 omitidas, 0 fallidas** |
| Smoke Supabase de solo lectura | **8 comprobaciones, 0 fallos**, incluyendo editor activo de empresario, previews, API de lectura, assets y sitio público SSR usando snapshot solo en memoria |
| Templates | **69 compiladas** |
| Python y JavaScript del portal | Sintaxis correcta |
| IA pagada — texto | OpenRouter HTTP 200, propuesta válida, sin guardar |
| IA pagada — logo/imagen | OpenRouter HTTP 200, propuesta válida, sin guardar |
| Diff Git | Sin errores de espacios; avisos normales LF/CRLF de Windows |

Las pruebas nuevas cubren defaults sin datos ficticios, validación de colores/plantillas/URLs, eliminación de campos privilegiados, logo raster/paleta, rechazo de otro propietario, ocultamiento de borradores, snapshot separado, aprobación obligatoria, conflicto de slugs y cuota persistente. Las 24 omitidas no se cuentan como aprobadas; los motivos pueden revisarse con `python -m pytest -q -rs`.

Las pruebas de persistencia usan repositorio en memoria, y el smoke real no escribe ni publica. Sigue siendo recomendable ejecutar pruebas transaccionales concurrentes de escritura en un PostgreSQL desechable antes de producción y realizar revisión visual end-to-end en móvil/tableta/escritorio.

## 8. Archivos principales

- `models/business_site.py`: esquema declarativo de marca, persistencia, paleta, publicación y cuotas.
- `views/business_sites.py`: editor, APIs, preview, público, sucursales y proveedor IA.
- `templates/sites/editor.html` y `templates/sites/public.html`: interfaz privada y sitio SSR.
- `static/css/business-sites.css` y `static/js/business-sites.js`: visuales e interacciones.
- `test/test_phase4_sites.py`, `test/test_phase4_publication.py` y `test/test_phase4_ai_quota.py`: regresiones.

La Fase 4 continúa en el mismo SmartResto; no crea proyectos web aislados por negocio ni cambia tu autenticación, Supabase o proveedor pagado.
