# Tema oscuro predeterminado

Se unificó el tema de la plataforma, administración, editor y sitios públicos.
El script inline en el head usa oscuro salvo que `localStorage.theme` sea exactamente `light`.
No consulta `prefers-color-scheme`. La preferencia se guarda solo al cambiar manualmente y se sincroniza entre pestañas del mismo origen. Si el almacenamiento está bloqueado, el cambio sigue funcionando en la visita actual.

Los botones usan controles nativos de teclado, nombre estable «Tema oscuro», `aria-pressed`, indicación de la acción y foco visible.
Los gráficos reciben colores CSS resueltos y se actualizan con `themechange`.

## Tokens

Todos se definen en `static/css/theme-tokens.css`, con oscuro en `:root` y claro en `[data-theme="light"]`.
Los nombres anteriores se conservan como aliases para compatibilidad; los componentes consumen variables.

| Token | Oscuro | Claro |
| --- | --- | --- |
| `--theme-shadow-rgb` | `9 17 22` | `24 36 44` |
| `--theme-bg` | `#14191d` | `#f3f5f6` |
| `--theme-surface` | `#1d252b` | `#ffffff` |
| `--theme-elevated` | `#29333b` | `#e6ecef` |
| `--theme-text` | `#f2f6f8` | `#18242c` |
| `--theme-muted` | `#c3ced5` | `#41515d` |
| `--theme-border` | `#81939f` | `#667b88` |
| `--theme-accent` | `#a6dfc6` | `#17533f` |
| `--theme-accent-bg` | `#233b34` | `#dcece5` |
| `--theme-success` | `#a6dfc6` | `#17533f` |
| `--theme-success-bg` | `#233b34` | `#dcece5` |
| `--theme-warning` | `#f2d08b` | `#674500` |
| `--theme-warning-bg` | `#3c3424` | `#f4ead4` |
| `--theme-danger` | `#ffb9bb` | `#852737` |
| `--theme-danger-bg` | `#402c32` | `#fae4e8` |
| `--theme-info` | `#b7d8ff` | `#214d78` |
| `--theme-info-bg` | `#283748` | `#e1ecf9` |
| `--theme-focus` | `#f2d08b` | `#674500` |
| `--theme-shadow` | `#09111666` | `#18242c26` |
| `--theme-edge` | `#c3ced51a` | `#ffffffb3` |
| `--theme-overlay` | `#10171de6` | `#e6eceff2` |
| `--theme-chart-1` | `#a6dfc6` | `#17533f` |
| `--theme-chart-2` | `#b7d8ff` | `#214d78` |
| `--theme-chart-3` | `#f2d08b` | `#674500` |
| `--theme-chart-4` | `#ffb9bb` | `#852737` |
| `--theme-chart-5` | `#d6c6ff` | `#584182` |
| `--theme-chart-6` | `#a7dce2` | `#23535b` |
| `--theme-brand-primary` | `#245447` | `#245447` |
| `--theme-brand-secondary` | `#d8a65d` | `#d8a65d` |

## Validación y alcance

- Pruebas de arranque oscuro, preferencias válidas/inválidas, almacenamiento bloqueado, teclado, sincronización entre pestañas y actualización de gráficos.
- 112 combinaciones de texto/fondo de la paleta: mínimo 7.39:1 en oscuro y 6.71:1 en claro, superiores a WCAG AA 4.5:1.
- Revisión estática de todas las hojas de estilo propias, plantillas y JavaScript de interfaz, con prueba de regresión contra literales de color y referencias CSS inválidas.
- Pruebas de navegador con datos ficticios para administración, sitio público, editor, informes, categorías, usuarios, formulario de restaurante, catálogo, login, registro, mercado y carta. Se comprueba persistencia, teclado y contraste de texto visible en ambos temas.
- La prueba de contraste de navegador no es una certificación completa de accesibilidad: imágenes externas, todos los estados interactivos y todos los datos reales requieren validación de integración. Las pruebas visuales aíslan llamadas API, fuentes externas, mapas y Chart.js; los gráficos se validan además con una prueba de su plugin.

No quedan literales de color de interfaz en los archivos auditados fuera de la fuente de tokens. Las excepciones explícitas son `brand_defaults.html` (datos editables de marca para los inputs de color) y el bundle Three.js `static/js/auth/food-scene.js` (biblioteca/materiales de la escena 3D, no estilos de interfaz). Los colores de fotografías, logos, mapas externos y modelos no se convierten en tokens CSS. No se afirma ausencia absoluta de colores fijos en esos recursos.

Las superficies legibles del sitio público usan la paleta accesible. El color elegido por cada empresario se conserva como dato y como matiz decorativo; no determina el contraste del texto.

## Ejecutar

```text
python -m pytest test/test_theme_contract.py -q
python test/render_theme_fixtures.py
node test/theme_browser.cjs
```

La prueba de navegador requiere Playwright para Node y Edge, o `THEME_BROWSER` apuntando a Chromium/Chrome. Escribe capturas y resultados en `outputs/theme-qa/`. No usa la base de datos.

## Archivos modificados o creados

- `static/css/adaptive-experience.css`
- `static/css/auth.css`
- `static/css/business-plans.css`
- `static/css/business-sites.css`
- `static/css/catalog.css`
- `static/css/components.css`
- `static/css/discovery.css`
- `static/css/forest-depth.css`
- `static/css/forest-home.css`
- `static/css/interface.css`
- `static/css/main.css`
- `static/css/management.css`
- `static/css/market.css`
- `static/css/owner.css`
- `static/css/premium-system.css`
- `static/css/recommendations.css`
- `static/css/shell.css`
- `static/css/theme-components.css`
- `static/css/theme-tokens.css`
- `static/js/admin-dashboard.js`
- `static/js/admin.js`
- `static/js/ai-assistant.js`
- `static/js/app.js`
- `static/js/business-sites.js`
- `static/js/map.js`
- `static/js/market-map.js`
- `static/js/search.js`
- `static/js/shell.js`
- `static/js/theme-charts.js`
- `static/js/theme.js`
- `templates/400.html`
- `templates/404.html`
- `templates/500.html`
- `templates/admin/analytics.html`
- `templates/admin/categories.html`
- `templates/admin/moderation.html`
- `templates/admin/restaurant_form.html`
- `templates/admin/restaurants.html`
- `templates/admin/users.html`
- `templates/auth/profile_content.html`
- `templates/base.html`
- `templates/detail.html`
- `templates/discovery/dashboard.html`
- `templates/favorites.html`
- `templates/index.html`
- `templates/owner/menu_import_preview.html`
- `templates/owner/menu_management.html`
- `templates/owner/restaurants.html`
- `templates/partials/brand_defaults.html`
- `templates/partials/header.html`
- `templates/partials/restaurant_card.html`
- `templates/partials/theme_head.html`
- `templates/partials/theme_toggle.html`
- `templates/sites/editor.html`
- `templates/sites/public.html`
- `test/render_theme_fixtures.py`
- `test/test_theme_contract.py`
- `test/theme_browser.cjs`
- `test/theme_runtime.cjs`
- `THEME_IMPLEMENTATION.md`
