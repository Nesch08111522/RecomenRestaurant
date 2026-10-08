# Fase 5 — Diseño e implementación PostgreSQL y migración conservadora

## Objetivo

Construir la base relacional mínima sin sustituir de golpe el backend JSON. La solución deja JSON como predeterminado, ofrece PostgreSQL como modo explícito y no ejecuta migraciones durante el arranque.

## Archivos afectados

| Archivo | Cambio | Problema que soluciona | Riesgo controlado |
|---|---|---|---|
| `config.py` | Añade `DATA_BACKEND` y `DATABASE_URL` desde entorno | Evita secretos y activaciones implícitas | El valor predeterminado sigue siendo `json` |
| `requirements.txt` | Añade `psycopg[binary]==3.2.3` | Hace reproducible la conexión PostgreSQL | El backend JSON no importa la dependencia durante el arranque |
| `database/schema.sql` | Crea entidades, relaciones, checks, índices y estados controlados | Elimina la dependencia futura de estructuras anidadas para relaciones críticas | Requiere ejecutar explícitamente contra una base preparada |
| `database/connection.py` | Conector opt-in, rollback y cierre garantizado | Centraliza conexión y evita migraciones ocultas | Sin `DATABASE_URL` o dependencia, falla de forma clara |
| `database/repository.py` | CRUD genérico con allowlist de columnas | Evita interpolación de campos controlados por usuario | Las subclases deben declarar columnas explícitamente |
| `migrations/migrate_json.py` | Dry-run, manifiesto, validación FK, inserción idempotente y transacción | Permite migrar sin borrar JSON y detectar inconsistencias antes de escribir | La ejecución real requiere un PostgreSQL accesible; no se simuló una base inexistente |
| `DATABASE_MIGRATION.md` | Documenta mapeos y procedimiento | Hace auditable la transformación y sus supuestos | PostGIS queda preparado, no instalado sin evidencia de valor operativo |
| `test/test_migration.py` | Pruebas con el dataset real y allowlist | Evita regresiones en validación y preservación de fuentes | No reemplaza una prueba de integración contra PostgreSQL real |

## Evidencia del dataset

El dry-run validó **10 categorías, 3 usuarios, 24 restaurantes, 84 platos, 12 menús diarios, 4 favoritos, 14 moderaciones, 2 promociones y 2 reseñas**, sin errores de referencias, IDs duplicados ni coordenadas fuera de rango. El historial y las notificaciones están vacíos y no se inventaron filas.

## Decisiones de integridad

Los IDs legacy se mantienen en las tablas principales. Las listas de ingredientes se convierten en entidades deduplicadas sin inventar cantidades o unidades. Los menús normalizan su cabecera y relación con platos solo cuando el ID existe. Las aprobaciones históricas se registran como importación legacy y no se atribuyen retrospectivamente a una decisión de IA. Los estados futuros solo pueden adoptar los cuatro valores controlados definidos por el requerimiento.

## Pruebas

- `python3 migrations/migrate_json.py --dry-run --data-dir data`: correcto, sin conexión ni modificación de fuentes.
- `python3 -m compileall -q app.py config.py models views utils database migrations`: correcto.
- `python3 -m pytest -q`: **10 passed**, con una advertencia externa de `pyDatalog`.
- Se verificó que el hash SHA-256 de `restaurants.json` no cambia durante las pruebas del migrador.

## Riesgos pendientes

No existe un servidor PostgreSQL local en el entorno de auditoría, por lo que no se pudo ejecutar el DDL ni una transacción real. Antes de activar `DATA_BACKEND=postgresql` en un entorno operativo se debe ejecutar el migrador contra una instancia de staging, comparar conteos y FK, probar rollback y validar los contratos de las rutas. La integración de cada modelo con el repositorio PostgreSQL debe hacerse de forma gradual, con una bandera de backend y pruebas de equivalencia JSON/PostgreSQL.
