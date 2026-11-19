# Responsividad de SmartResto

Revisión continuada después de generar la auditoría `CONECTIVIDAD.md`.

## Correcciones

- Unificado el cambio de navegación interna a 1100 px. Antes, CSS activaba el rail a 768 px mientras JavaScript esperaba 1100 px, dejando tabletas sin control coherente.
- El contenido privado usa el espacio restante al lado del rail. Se eliminó la suma de un margen lateral a un ancho ya calculado para toda la pantalla.
- El sitio público conserva navegación superior sin sidebar, incluso con sesión de administrador o empresario.
- Formularios, fieldsets, labels y controles pueden reducir su ancho; filtros y fechas ya no fuerzan el tamaño mínimo intrínseco del navegador.
- Tarjetas de estadísticas adaptadas a dos columnas en móvil, paginación con salto de línea y objetivos de 44 px.
- Tablas desplazables dentro de su contenedor, sin scroll horizontal de toda la página. Reutilizan sus envoltorios y se pueden enfocar con teclado; no se duplican contenedores.
- Asistente ajustado a pantallas bajas/horizontales; formulario de envío dentro del viewport. Mapas modales pueden desplazar su contenido sin perder controles.
- Controles de formularios a 16 px en móvil para reducir el zoom automático al enfocarlos en navegadores móviles.
- Se conservan los temas, la navegación por roles, el movimiento reducido y los estilos del proyecto.

## Archivos

`static/css/shell.css`, `static/css/responsive-layout.css`, `static/js/responsive-layout.js`. Los ajustes del contrato de colores están documentados también en `CONECTIVIDAD.md`.

## Validación

- 1500 combinaciones de 75 escenarios de plantillas/variantes, entre 320 y 1920 px y temas claro/oscuro: sin desbordamientos documentales ni controles fuera de pantalla detectados.
- Se incluyen autenticación, páginas públicas, formularios administrativos, catálogo, comunicación, mercado, inteligencia, sitios y ocho variantes empresariales.
- 30 escenarios adicionales de interacción: menú hamburguesa y Escape, filtros desplegados, tablas enfocables, asistente y navegación empresarial; incluye horizontal de 640 × 360.
- Revisión de capturas de móvil para gestión de restaurantes y mercado.

Los escenarios incluyen variantes de una misma vista y layouts base; no representan 75 pantallas diferentes. Las comprobaciones se ejecutaron con Edge/Playwright y datos aislados. No equivalen a pruebas físicas en todos los modelos de teléfono ni validan APIs externas, pagos, GPS o AR en dispositivos reales.

Evidencias: [resumen de tamaños](responsiveness/summary.json). La regresión completa de funciones se documenta en `CONECTIVIDAD.md`.
