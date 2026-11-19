# Escala responsive

Se añadió una escala fluida compartida para tipografía, espaciado y controles. Las reglas responsive limitan el contenido a 90rem en pantallas ultrawide, adaptan rejillas y mantienen tablas desplazables dentro de su contenedor. Los diálogos se limitan a 90vw y 90vh. Las plantillas comunes cargan los estilos y el envoltorio de tablas.

## Verificación visual

`test/visual_browser.cjs` recorre 360, 768, 1024, 1366, 1440, 1920 y 2560 px en las vistas pública, usuario, propietario y administración, con temas claro y oscuro. Guarda capturas para 360, 1366, 1920 y 2560 px, y falla si el documento o body desbordan horizontalmente. Requiere el servidor visual y credenciales de prueba descritos en `test/visual_server.py`.

## Archivos incluidos

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
- `static/css/owner.css`
- `static/css/premium-system.css`
- `static/css/recommendations.css`
- `static/css/responsive-layout.css`
- `static/css/responsive-tokens.css`
- `static/css/shell.css`
- `static/css/theme-components.css`
- `static/js/admin.js`
- `static/js/ai-assistant.js`
- `static/js/app.js`
- `static/js/responsive-layout.js`
- `static/js/search.js`
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
- `templates/catalog/explore.html`
- `templates/detail.html`
- `templates/favorites.html`
- `templates/index.html`
- `templates/owner/base.html`
- `templates/owner/menu_import_preview.html`
- `templates/owner/menu_management.html`
- `templates/owner/restaurants.html`
- `templates/partials/restaurant_card.html`
- `templates/sites/public.html`
- `test/visual_browser.cjs`
