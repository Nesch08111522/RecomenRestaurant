# -*- coding: utf-8 -*-
"""Sección 2: Arquitectura general y estructura central (Fase 1)."""
from report_lib import (
    para, heading1, heading2, heading3, bullets, table, page_break,
)


def build(doc):
    heading1(doc, "2. Arquitectura general y estructura central (Fase 1)", page_break=True)

    heading2(doc, "2.1. Arquitectura real de SmartResto")
    para(doc,
         "SmartResto se implementa como un monolito modular construido con el patrón de fábrica de "
         "aplicación de Flask. La función create_app() del archivo app.py crea la instancia, aplica la "
         "configuración desde la clase Config, valida los secretos y la base de datos, inicializa la protección "
         "CSRF y registra los blueprints que agrupan las rutas por dominio. El resultado es una separación por "
         "capas —presentación, negocio y persistencia— dentro de un único proceso desplegable, lo que reduce la "
         "complejidad operativa del proyecto académico sin renunciar a la modularidad.")
    para(doc,
         "La capa de presentación está formada por plantillas Jinja2 y archivos estáticos; la capa de negocio "
         "por los módulos views, logic, core y utils; y la capa de persistencia por los modelos y el repositorio "
         "de documentos. Las vistas no acceden directamente a la base de datos: invocan los modelos, que delegan "
         "en PostgresDocumentRepository, y este ejecuta las operaciones sobre PostgreSQL. Esta mediación permite "
         "cambiar el almacenamiento sin modificar los controladores y concentra la lógica de acceso a datos en "
         "un único componente.")
    para(doc,
         "El punto de entrada de ejecución es el bloque principal de app.py, que invoca create_app(), captura "
         "los errores de configuración y conexión, y publica el servidor en http://127.0.0.1:5000. La "
         "configuración se resuelve en el orden siguiente: variables de entorno, archivo .env cargado por "
         "python-dotenv y valores por defecto de la clase Config. La validación de arranque exige una "
         "SECRET_KEY de al menos treinta y dos caracteres, un DATA_BACKEND igual a postgresql y una "
         "DATABASE_URL con esquema postgres; sin estas condiciones la aplicación se niega a iniciar.")

    heading2(doc, "2.2. Registro de blueprints y organización del código")
    para(doc,
         "La aplicación registra veintidós blueprints, cada uno con un prefijo de URL y una responsabilidad "
         "delimitada. La Tabla 2 relaciona cada blueprint con su prefijo y las rutas principales que expone, "
         "según se verifica en los decoradores de ruta de la carpeta views.")
    table(doc,
          "Blueprints registrados, prefijos y rutas representativas",
          ["Blueprint", "Prefijo", "Rutas representativas"],
          [
              ["main", "/", "/", "/restaurant/<id>", "/api/search", "/explorar", "/ofertas", "/api/dishes/search"],
              ["auth", "/auth", "/login", "/register", "/logout", "/profile", "/favorites", "/seguridad", "/recuperar"],
              ["admin", "/admin", "/dashboard", "/restaurants", "/moderation", "/users", "/categories", "/analytics", "/controles", "/operaciones"],
              ["owner", "/owner", "/dashboard", "/menu/<id>", "/menu/<id>/import", "/dish/add", "/generate_menu"],
              ["ai", "/", "/api/ai/interpret", "/api/ai/chat"],
              ["market", "/mercado", "/", "/carrito", "/comprar", "/pedidos", "/consultar"],
              ["market_kitchen", "/mercado", "/cocina/<rid>", "/cocina/<rid>/oferta", "/cocina/<rid>/inventario", "/cocina/<rid>/copiloto"],
              ["market_trust", "/mercado", "/confianza", "/cocina/<rid>/acreditar"],
              ["ecosystem", "/experiencias", "/", "/escena", "/scan", "/grupos", "/ciudad", "/negocio/<rid>", "/recompensas"],
              ["communication", "/bandeja", "/", "/nueva", "/mensajes/<id>", "/reclamos", "/notificaciones"],
              ["platform", "/api/platform", "/manifest", "/health", "/me", "/me/profile"],
              ["discovery", "/", "/admin/discovery", "/reclamar", "/owner/discovery", "/api/discovery/candidates"],
              ["sites", "/", "/owner/sites", "/owner/api/sites/<rid>", "/negocio/<slug>", "/negocio/<slug>/sucursal/<branch_id>"],
              ["catalog", "/", "/owner/catalog", "/owner/api/catalog/<rid>/photo", "/owner/api/catalog/<rid>/voice", "/catalog/qr/<token>"],
              ["recommendations", "/", "/recomendaciones", "/api/recomendaciones", "/api/recomendaciones/contexto"],
              ["recommendation_history", "/", "/api/recomendaciones/historial"],
              ["food_experience", "/", "/api/food-experience"],
              ["intelligence", "/", "/inteligencia", "/api/inteligencia"],
              ["copilot", "/", "/copilot", "/api/copilot/chat", "/api/copilot/actions"],
              ["trust_center", "/", "/admin/confianza", "/admin/api/confianza"],
              ["salon", "/", "/mesa/<token>", "/mesa/<token>/carrito", "/mesa/<token>/pedido", "/owner/salon"],
              ["flow", "/", "/cola/<rid>", "/salon/<rid>/cola", "/salon/<rid>/aforo.json"],
              ["loyalty", "/", "/puntos", "/owner/puntos/<rid>"],
              ["admin_ai", "/admin/api/ai", "/health", "/analyze", "/moderation-query"],
          ],
          note="El prefijo vacío indica que las rutas del blueprint se registran en la raíz. Los subdominios de mercado (cocina y confianza) añaden rutas al blueprint market.")

    heading2(doc, "2.3. Responsabilidades de las carpetas principales")
    table(doc,
          "Estructura de directorios y responsabilidades",
          ["Carpeta", "Responsabilidad"],
          [
              ["views/", "Controladores y blueprints por dominio: procesan la petición, invocan la lógica y devuelven plantillas o JSON"],
              ["models/", "Modelos de dominio y colecciones: definen la forma de los documentos y delegan la persistencia al repositorio"],
              ["logic/", "Lógica de negocio pura: recomendación híbrida, motor por fases, catálogo de productos, mercado, radar y contexto"],
              ["core/", "Servicios transversales: permisos, contexto de plataforma, manifiesto, perfil y experiencia alimentaria"],
              ["utils/", "Utilidades especializadas: seguridad, proveedor de IA, geolocalización, auditoría, filtros de contenido, importación"],
              ["database/", "Conexión, pool, repositorio de documentos, métricas y scripts SQL de esquema y migración"],
              ["templates/", "Plantillas Jinja2 organizadas por rol y por módulo"],
              ["static/", "Hojas de estilo, scripts JavaScript, imágenes y dependencias de terceros"],
              ["test/", "Pruebas automatizadas con pytest organizadas por fase y por módulo"],
              ["migrations/", "Importación de documentos JSON históricos a PostgreSQL"],
              ["scripts/", "Utilidades de línea de comandos: creación de usuario, secretos y actualización del radar"],
              ["analytics/", "Cálculo de indicadores de inteligencia y gestión para los paneles"],
              ["data/", "Archivos JSON históricos que sirven de origen para la migración manual"],
          ],
          note="La separación entre views, logic y models materializa las capas de presentación, negocio y persistencia dentro del monolito.")

    heading2(doc, "2.4. Modelo de datos")
    para(doc,
         "El almacenamiento operativo es PostgreSQL gestionado por Supabase, sin backend de archivos. Conviven "
         "dos mecanismos de persistencia complementarios. Por un lado, el esquema relacional de schema.sql define "
         "tablas con claves primarias, claves foráneas, restricciones CHECK e índices para las entidades canónicas "
         "de la primera fase: usuarios, roles, negocios, restaurantes, ubicaciones, horarios, platos, etiquetas, "
         "condiciones dietéticas, ingredientes, recetas, menús, preferencias, interacciones, valoraciones, "
         "favoritos, recomendaciones, aprobaciones, promociones, notificaciones, conversaciones, auditoría y "
         "eventos de inteligencia de negocio.")
    para(doc,
         "Por otro lado, la tabla public.app_records actúa como almacén de documentos JSONB para las colecciones "
         "dinámicas que usan los modelos Flask. Su clave primaria compuesta (collection, id) y el índice GIN sobre "
         "el payload permiten recuperar documentos completos y consultar campos internos. La tabla habilita "
         "seguridad a nivel de fila y revoca todo permiso a los roles anon y authenticated de Supabase, de modo "
         "que el acceso se realiza exclusivamente con la credencial de servidor, sin exponer la tabla a la API "
         "del navegador.")
    para(doc,
         "El esquema de platform_foundation.sql añade las entidades canónicas de la plataforma —negocios "
         "(sr_businesses), sucursales (sr_branches), membresías (sr_memberships), configuración (sr_settings) y "
         "auditoría (sr_audit_events)— con seguridad a nivel de fila activada. La tabla public.ai_decisions "
         "registra las consultas del copiloto administrativo: tipo, entidad, actor, resumen de entrada, hash, "
         "salida de la IA, modelo, confianza, latencia y estado, y sirve como auditoría de las decisiones "
         "asistidas. Las relaciones entre usuarios, negocios, sucursales, platos y publicaciones se modelan "
         "mediante claves foráneas en el esquema relacional y mediante identificadores referenciados dentro de "
         "los documentos JSONB.")
    table(doc,
          "Tablas relacionales principales del esquema",
          ["Grupo", "Tablas"],
          [
              ["Identidad y roles", "roles, users, businesses, categories"],
              ["Negocio y oferta", "restaurants, restaurant_locations, restaurant_hours, dishes, tags, restaurant_tags"],
              ["Dieta e ingredientes", "dietary_conditions, user_dietary_conditions, dish_dietary_conditions, ingredients, recipes, recipe_ingredients, dish_ingredients"],
              ["Menú", "menus, menu_dishes"],
              ["Interacción", "user_preferences, interactions, ratings, favorites, recommendations, recommendation_items"],
              ["Gobernanza", "approvals, approval_events, promotions, notifications, conversations, conversation_participants, messages, audit_events"],
              ["Operación", "migration_runs, bi_events"],
          ],
          note="Las tablas sr_* de platform_foundation.sql y ai_decisions completan el modelo de plataforma y de auditoría de IA.")

    heading2(doc, "2.5. Seguridad y servicios centrales")
    para(doc,
         "La autenticación se apoya en la sesión de Flask y en un identificador de usuario almacenado en ella. "
         "La función fresh_session_user del módulo utils.security revalida el rol contra el almacenamiento en "
         "cada petición y compara una marca de época de autenticación para invalidar sesiones cuando la cuenta "
         "cambia o se cierra en otro dispositivo. Las contraseñas se almacenan como resúmenes generados con "
         "werkzeug.security, nunca en texto plano. La protección CSRF se aplica globalmente mediante "
         "Flask-WTF; los formularios incluyen el token y los clientes JSON lo envían en la cabecera X-CSRFToken.")
    para(doc,
         "La autorización se declara en core.permissions mediante un diccionario que asigna a cada rol un "
         "conjunto de permisos. El rol canónico se resuelve a partir de alias (user→diner, owner→business_owner) "
         "y la función can(role, permission) decide si una operación está permitida. El alcance por negocio y "
         "sucursal se valida por separado en los controladores, de modo que un empresario o un trabajador no "
         "pueda leer ni modificar los datos de otro establecimiento. La Tabla 5 resume los permisos por rol.")
    table(doc,
          "Matriz de permisos declarada en core.permissions",
          ["Rol", "Permisos representativos"],
          [
              ["Invitado", "catalog.read, business.read, profile.read.public"],
              ["Comensal (diner)", "profile.read/update, preferences.update, favorites.manage, orders.read.own, reviews.create.own, notifications.manage.own, rewards.read.own"],
              ["Empresario (business_owner)", "business.manage, branch.manage, catalog.manage, orders.read.business, staff.invite/manage, analytics.read.business, rewards.manage.business"],
              ["Gerente (manager)", "branch.read, catalog.manage, orders.read.business, staff.invite, analytics.read.business"],
              ["Cajero / mozo / cocina", "profile.read/update, branch.read, orders.read.business"],
              ["Administrador", "platform.users.manage, platform.roles.manage, platform.verification.manage, platform.moderation.manage, platform.audit.read, platform.settings.manage, analytics.read.platform"],
          ],
          note="Los roles de personal (manager, cashier, waiter, kitchen) corresponden a las membresías sr_memberships; el aislamiento por negocio se aplica en los controladores.")
    para(doc,
         "Los secretos se administran mediante variables de entorno y el archivo .env, que no se versiona. La "
         "aplicación añade cabeceras de seguridad —X-Content-Type-Options, X-Frame-Options, Referrer-Policy, "
         "Permissions-Policy y un identificador de petición— y aplica Cache-Control no-store a las rutas "
         "autenticadas y de inteligencia artificial. Los errores se manejan con controladores específicos que "
         "distinguen respuestas JSON de páginas HTML, y la indisponibilidad de la base de datos se traduce en "
         "una respuesta 503 controlada. La salud se expone en GET /api/platform/health y el contrato no sensible "
         "en GET /api/platform/manifest.")
    para(doc,
         "La auditoría registra eventos en audit_events (actor, acción, recurso, identificador de petición, hash "
         "de IP y metadatos) y en sr_audit_events para las operaciones de negocio; las decisiones asistidas por "
         "IA quedan en ai_decisions. El sistema de notificaciones central se apoya en la colección notifications y "
         "en la tabla del mismo nombre, con endpoints para listar y marcar como leídas. El límite de uso de la "
         "IA de administración se controla mediante una reserva por usuario de diez solicitudes por minuto.")

    heading2(doc, "2.6. Interfaz y arquitectura visual")
    para(doc,
         "La interfaz se organiza sobre una plantilla base (templates/base.html) que define el documento HTML, la "
         "cabecera, el pie de página, la navegación móvil y el aviso de consentimiento de ubicación. El atributo "
         "data-theme selecciona el tema claro u oscuro mediante una hoja de tokens, y el cuerpo distingue las "
         "páginas públicas de las privadas por el rol de sesión. La tipografía principal es Manrope, con Material "
         "Icons y Font Awesome para iconos. Los mapas usan Leaflet 1.9.4 y los gráficos Chart.js; el visor "
         "tridimensional se apoya en model-viewer. Las hojas de estilo se reparten en componentes (main.css, "
         "components.css, shell.css, interface.css, premium-system.css, theme-components.css) y en un sistema de "
         "layout responsivo (responsive-tokens.css, responsive-layout.css, layout-system.css) que define los "
         "puntos de ruptura y el comportamiento en pantallas pequeñas. La accesibilidad incorpora un enlace de "
         "salto al contenido principal y atributos aria; la validación integral de WCAG queda como trabajo "
         "pendiente.")
    para(doc,
         "La Figura 1 presenta la portada pública y la Figura 2 la vista móvil de la misma, como evidencia del "
         "renderizado real de la aplicación en ejecución y de su adaptación a una resolución de teléfono.")
    page_break(doc)
