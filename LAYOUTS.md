# Sistema de layouts

La librería Jinja vive en `templates/partials/layouts.html`; el CSS compartido está en `static/css/layout-system.css` y las entradas animadas progresivas en `static/js/layout-system.js`. `base.html` carga los recursos para el panel y `sites/public.html` los carga porque el sitio público es una página independiente. Los componentes heredan `--space-*`, `--theme-*` y la escala fluida del sistema.

## Componentes

Importa los macros con contexto: `{% from 'partials/layouts.html' import BentoGrid, SplitScreen, MasonryGrid, FullBleedSection, EditorialLayout with context %}`. Cada macro recibe `class_name` para combinar estilos de módulo y `label` si el grupo necesita nombre accesible.

```jinja
{% call BentoGrid(columns=4, gap='md', label='Resumen') %}
  <article data-layout-span="2x1">...</article>
  <article data-layout-span="1x1">...</article>
{% endcall %}

{% call SplitScreen(ratio='40-60', visual_side='left', stack='visual-first') %}
  <div data-layout-side="visual">...</div>
  <div data-layout-side="content">...</div>
{% endcall %}

{% call MasonryGrid(columns=3, gap='md', label='Galería') %}...{% endcall %}
{% call FullBleedSection(class_name='hero', id='inicio', label='Presentación') %}...{% endcall %}
{% call EditorialLayout(class_name='story') %}...{% endcall %}
```

Bento acepta `data-layout-span="1x1|2x1|1x2|2x2"`. Masonry usa CSS columns y mantiene cada tarjeta unida; columnas se ajustan a dos en tablet y una en móvil. Split admite proporciones `50-50`, `40-60` y `60-40`; en móvil apila los lados según `stack`. Editorial usa dos columnas asimétricas y se apila en móvil. Full bleed elimina el margen del viewport. Los elementos de galería usan carga diferida y proporción reservada para evitar saltos.

## Aplicaciones

| Módulo | Layout | Uso |
| --- | --- | --- |
| Administración, dashboard | Bento | Métricas, gráficas y actividad |
| Panel de empresario, dashboard | Bento | KPIs y operación/inventario |
| Catálogo del empresario | Bento + Masonry | Resumen y tarjetas de productos dinámicas |
| Acceso y registro | Split Screen | Formularios y escena gastronómica; conserva la transición existente |
| Sitio público del empresario | Full Bleed + Editorial + Bento + Masonry | Hero, historia, platos destacados, galería y reseñas |

Las animaciones aparecen solo cuando IntersectionObserver está disponible y no se solicitan si `prefers-reduced-motion` está activo. Sin JavaScript, el contenido conserva su visibilidad y el layout funciona con CSS.
