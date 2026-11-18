# SmartResto — Fase 2: usuarios, roles y perfiles

## Estado de la fundación

SmartResto conserva el registro, inicio de sesión, recuperación, 2FA, sesión Flask, favoritos, administración y auditoría existentes. La Fase 2 añade una política central para que los módulos no decidan permisos de manera aislada.

## Roles

- **Comensal:** el rol histórico `user` se mantiene como alias compatible de `diner`.
- **Empresario:** `business_owner` administra negocio, sucursales, catálogo, personal, analítica y recompensas dentro de su alcance.
- **Personal empresarial:** `business_admin`, `manager`, `cashier`, `waiter` y `kitchen` tienen permisos limitados por función.
- **Administrador:** `admin` gestiona cuentas, roles, verificación, moderación, configuración y auditoría de plataforma.

La matriz vive en `core/permissions.py`. `permissions_for_role()` devuelve una copia ordenada y `can()` permite que cada controlador valide una capacidad explícita.

## Perfil del comensal

El perfil soporta ahora, además de nombre, correo, preferencias, restricciones, direcciones y favoritos:

- Presupuesto diario y semanal.
- Preferencias transaccionales, de reseñas, lista de espera y marketing.
- Consentimiento de cookies.
- Consentimiento de ubicación.
- Direcciones de delivery con límite de cinco.

La normalización está en `core/profile.py`; descarta campos no permitidos, valida correo y presupuesto, evita duplicados y no mezcla consentimientos entre sí.

## APIs

- `GET /api/platform/me`: identidad segura, alcance y permisos efectivos.
- `PATCH /api/platform/me/profile`: actualización JSON allowlisted del perfil autenticado. Requiere CSRF y no permite modificar rol, estado, contraseña ni negocio.
- `GET /api/platform/manifest`: manifiesto de capacidades y roles.

La sesión continúa exponiendo únicamente identidad mínima. La respuesta pública no incluye contraseña, correo privado fuera del perfil autorizado ni tokens de proveedores.

## Reglas de acceso

1. Autenticar no equivale a autorizar.
2. El permiso debe combinarse con el alcance de negocio/sucursal del contexto central.
3. El propietario nunca comparte credenciales con el personal.
4. El navegador no puede cambiar su propio rol, estado, membresía o negocio.
5. Suspensiones y revocaciones se siguen validando con `fresh_session_user()` antes de autorizar.
6. Las operaciones administrativas sensibles deben registrar auditoría.
