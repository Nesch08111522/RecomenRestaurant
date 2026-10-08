# Fase 6 — Roles, RBAC, aprobación híbrida y auditoría

## Objetivo

Reducir el riesgo de privilegios obsoletos, asignación masiva y decisiones de moderación irreversibles sin sustituir la sesión JSON ni romper las rutas existentes.

## Cambios realizados

| Área | Estado anterior | Evolución aplicada | Validación |
|---|---|---|---|
| Estados de moderación | `pending`, `approved`, `rejected` y flags dispersos | Estados controlados `APROBADO_AUTOMATICAMENTE`, `PENDIENTE_REVISION`, `RECHAZADO`, `SUSPENDIDO`, manteniendo campos legacy | Pruebas de transición y compatibilidad |
| Prechequeo | `ContentFilter` usado directamente en vista | `ModerationModel.preliminary_evaluate()` guarda versión, reglas, confianza, señales y exigencia de revisión humana | Contenido crítico queda pendiente, no se rechaza de forma irreversible |
| Aprobación | Endpoints solo approve/reject sin historial | Acciones approve/reject/suspend/pending/revert con `status_history` y actor | Reversión verificada en pruebas |
| Auditoría | No existía registro central | `utils/audit.py` persiste acción, actor, recurso, request ID, huella IP y metadatos limitados | Hash de IP; secretos y tokens son descartados |
| Administración de usuarios | `request.json` se persistía prácticamente entero | Allowlist de username, role, status y perfil; rechazo de campos desconocidos y credenciales | Suite de regresión y validación de payload |
| Auto-filtro | El frontend llamaba un endpoint inexistente | Endpoint real que ejecuta preevaluación y marca para revisión, sin convertir señales en decisión humana | Contrato de respuesta conservado |
| Historial | No consultable | Endpoint admin-only de historial por restaurante | Protegido por `@admin_required` |

## Causa y riesgo controlado

La causa principal era que la decisión administrativa mezclaba flags históricos (`verified`, `rejected`) con un filtro heurístico ejecutado en una plantilla, sin estados ni historial formal. Esto podía provocar decisiones no explicables y dificultaba revertir cambios. La nueva separación entre `ai_verdict`, `final_status`, `decision_source` y `status_history` permite que la evaluación automática sea preliminar, que los rechazos críticos permanezcan pendientes y que un administrador autorizado revierta cualquier estado.

## Compatibilidad

Las rutas existentes siguen aceptando `action=approve` y `action=reject`; sus respuestas continúan incluyendo `success`, `message` y ahora añaden `status`. Los campos legacy se actualizan de forma paralela (`verified`, `rejected`, `suspended`, `publication_status`) para que el frontend actual no se rompa mientras se modernizan los templates.

## Pruebas

- `python3 -m compileall -q app.py config.py models views utils database migrations`: correcto.
- `python3 -m pytest -q`: **12 passed**, con una advertencia de sintaxis externa de `pyDatalog`.
- Se verificó que contenido con palabras críticas produce `ai_verdict=RECHAZADO` pero `final_status=PENDIENTE_REVISION`.
- Se verificó transición administrativa aprobado → rechazado → pendiente y conservación de tres eventos de historial.

## Riesgos pendientes

La auditoría JSON es segura para la transición, pero aún no es append-only criptográfica ni está respaldada por PostgreSQL en producción. La gestión de categorías todavía necesita pasar por el mismo repositorio atómico y registrar auditoría. La comunicación entre roles sigue limitada a notificaciones; el modelo relacional ya prepara conversaciones y mensajes, pero su API se implementará después de estabilizar los contratos principales.
