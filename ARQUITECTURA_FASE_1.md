# SmartResto — Arquitectura central, Fase 1

## Decisión base

SmartResto continúa como una aplicación Flask modular con PostgreSQL/Supabase como fuente operativa. No se crean aplicaciones separadas para marketplace, operación, IA o experiencia del comensal. Todos los módulos comparten identidad, negocio, sucursal, auditoría y configuración.

```text
Flask app
├── views/                 controllers HTTP y coordinación
├── logic/                reglas de recomendación y dominio
├── core/                 contratos transversales de plataforma
├── models/               acceso a entidades/documentos
├── database/             conexión, repositorios y migraciones SQL
├── utils/                proveedores, seguridad y procesadores puros
├── templates/ + static/  interfaz responsive y componentes visuales
└── test/                 pruebas de contrato e integración
```

## Contexto compartido

`core.platform_context` convierte la sesión en un contexto inmutable con `user_id`, `role`, `business_id` y `branch_id`. Las rutas y servicios deben usar este contexto para filtrar datos; no deben aceptar `business_id` confiado desde el navegador sin verificar membresía.

`GET /api/platform/manifest` publica capacidades y alcance actual sin credenciales. `GET /api/platform/health` expone solo readiness no sensible para observabilidad y UI.

## Módulos y límites

- **Marketplace:** descubrimiento, búsqueda y recomendaciones.
- **Businesses:** negocios, sucursales, membresías y configuración de establecimiento.
- **Catalog:** categorías, platos, variantes, carta digital y contenido multimedia.
- **Operations:** pedidos, reservas, cocina, pagos e inventario.
- **Smart Flow:** mesas, sesiones, aforo, turnos y lista de espera.
- **Rewards:** visitas verificadas, puntos, niveles y recompensas.
- **Home Kitchen:** despensa, recetas y planificación doméstica.
- **AI Copilot:** borradores asistidos; nunca publica ni cambia valores sensibles sin confirmación y validación de servidor.
- **Immersive Menu:** modelos 3D/GLB, escala declarada y experiencia AR referencial.
- **Communications:** notificaciones, mensajes, preferencias y consentimiento separado.

## Reglas de seguridad

1. PostgreSQL/Supabase es la fuente de verdad para operaciones transaccionales.
2. `app_records` permanece compatible con el código existente; `database/platform_foundation.sql` prepara las entidades canónicas de tenancy y auditoría.
3. Dinero, stock, disponibilidad, permisos, sesiones de mesa y puntos se validan en servidor.
4. Cookies, ubicación, notificaciones y marketing son consentimientos independientes.
5. Los datos de un negocio se consultan mediante membresía o rol de plataforma.
6. Los eventos sensibles deben registrar actor, negocio, recurso, acción y request id.
7. La IA propone y clasifica; el backend decide y persiste.

## Integraciones preservadas

- **Supabase/PostgreSQL:** se conserva `DATABASE_URL`, TLS y repositorio actual.
- **OpenRouter:** no se cambia la URL ni el modelo; el manifiesto solo describe el gateway.
- **Frontend:** se conserva Flask/Jinja, MapLibre/Leaflet, shell responsive y selector claro/oscuro.
- **APIs existentes:** las nuevas rutas viven bajo `/api/platform` para no colisionar con contratos actuales.
