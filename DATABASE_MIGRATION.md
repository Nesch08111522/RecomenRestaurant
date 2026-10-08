# Diseño y migración JSON → PostgreSQL

## Decisión de compatibilidad

El backend JSON permanece activo por defecto mediante `DATA_BACKEND=json`. PostgreSQL es opt-in con `DATA_BACKEND=postgresql` y `DATABASE_URL`. La aplicación no crea tablas ni ejecuta migraciones durante `create_app()`: la operación se invoca explícitamente con el migrador y se ejecuta dentro de una transacción.

Esta decisión evita que un despliegue inesperado cambie el almacenamiento o deje el servidor parcialmente migrado. Los archivos JSON originales se conservan intactos y el migrador guarda un manifiesto SHA-256 en `migration_runs`.

## Mapeo de entidades

| Origen JSON | Destino PostgreSQL | Regla de transformación | Tratamiento de incertidumbre |
|---|---|---|---|
| `users.json` | `users`, `user_preferences` | Se conserva el hash existente, rol, email, nombre, preferencias y restricciones | No se vuelve a calcular ni se expone el hash; rol inválido queda sujeto a validación posterior |
| `categories.json` | `categories` | Se preservan IDs, nombre, slug, icono e imagen | El slug se normaliza solo para la columna auxiliar |
| `restaurants.json` | `businesses`, `restaurants`, `restaurant_locations` | `owner_id` se transforma en relación 1:1 con `businesses`; campos de listas se conservan como JSONB; coordenadas se validan por rango | `verified=true` se migra como estado histórico compatible, con `approval_source=LEGACY_IMPORT`; no se afirma que una IA lo hubiera aprobado |
| `dishes.json` | `dishes`, `ingredients`, `dish_ingredients` | Ingredientes textuales se deduplican por nombre exacto normalizado; no se inventan cantidades, unidades ni recetas | Las cantidades quedan nulas porque no existen en el JSON |
| `daily_menu.json` | `menus`, `menu_dishes` | Cabecera por restaurante y fecha; platos anidados se convierten en referencias si el ID existe | Platos sin ID válido se conservan en `source_snapshot`, pero no se convierten en FK falsa |
| `favorites.json` | `favorites` | Clave primaria compuesta `(user_id, restaurant_id)` | Duplicados se ignoran de forma idempotente |
| `reviews.json` | `ratings` | Restricción única por usuario/restaurante | Rating se limita al dominio 1–5; filas inválidas detienen la migración |
| `promotions.json` | `promotions` | Descuento y fecha con restricciones | El descuento se valida entre 0 y 100 |
| `moderation.json` | `approvals`, `approval_events` | Se conserva snapshot, usuario, estado, flags y timestamps | No se atribuye al modelo una decisión histórica; el evento se marca `LEGACY_IMPORT` |
| `history.json` | `interactions` | Preparado para eventos de interacción | El dataset actual está vacío y no se inventan eventos |
| `notifications.json` | `notifications` | Se conservan mensajes, enlaces y lectura | El dataset actual está vacío |

## Estados de aprobación

La tabla `restaurants` y el flujo `approvals` restringen los estados a `APROBADO_AUTOMATICAMENTE`, `PENDIENTE_REVISION`, `RECHAZADO` y `SUSPENDIDO`. Una futura evaluación de IA debe guardar su veredicto, confianza, reglas activadas y snapshot en `ai_evaluation`, pero no debe convertirlo en autoridad final: un administrador autorizado puede revertir el estado y cada transición queda en `approval_events`.

## Ejecución segura

La validación inicial se ejecuta con:

```bash
python3 migrations/migrate_json.py --dry-run --data-dir data
```

La migración real requiere una DSN explícita y un PostgreSQL preparado:

```bash
DATA_BACKEND=postgresql DATABASE_URL='postgresql://usuario:clave@host:5432/smartresto' \
python3 migrations/migrate_json.py --dsn "$DATABASE_URL" --data-dir data
```

El comando real ejecuta `database/schema.sql`, registra una fila `STARTED`, importa dentro de una transacción, actualiza secuencias y marca `COMPLETED`. Cualquier excepción provoca rollback y deja los JSON intactos. Antes de activar el backend PostgreSQL se debe ejecutar un conteo comparativo por tabla, validar todas las FK y comprobar que las respuestas de las rutas públicas y administrativas sean equivalentes.

## PostGIS

La primera versión usa `latitude`, `longitude`, restricciones de rango e índices B-tree. Esto aporta almacenamiento estructurado y búsquedas básicas sin forzar una dependencia operativa que el dataset actual todavía no justifica. PostGIS debe incorporarse en una migración posterior cuando el volumen, las consultas de radio o la necesidad de precisión espacial lo demuestren; el modelo ya mantiene una tabla independiente `restaurant_locations` para facilitar esa extensión.
