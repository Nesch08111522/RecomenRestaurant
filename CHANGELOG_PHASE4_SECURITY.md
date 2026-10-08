# Fase 4 — Correcciones de seguridad, validación y compatibilidad

## Alcance

Esta fase corrige riesgos críticos identificados en el diagnóstico sin eliminar el almacenamiento JSON ni alterar las tecnologías existentes. La copia auditada original permanece intacta en `/home/ubuntu/restaurantrecomm-audit`; los cambios se aplicaron únicamente sobre `/home/ubuntu/restaurantrecomm-work`.

## Cambios aplicados

| Problema | Causa | Archivos afectados | Riesgo de ruptura | Verificación | Ventaja frente al estado anterior |
|---|---|---|---|---|---|
| Ausencia de protección CSRF consistente | Formularios y mutaciones no tenían defensa centralizada | `utils/security.py`, `app.py`, `config.py`, `templates/base.html`, `static/js/security.js`, formularios de autenticación/perfil, `requirements.txt` | Clientes legítimos que ejecuten mutaciones sin token recibirán 400; la búsqueda de solo lectura conserva su compatibilidad | `phase4_security_check.py`, login/perfil sin token rechazados | La regla crítica vive en backend y el frontend solo automatiza el token; se cubren formularios y fetch same-origin |
| Exposición potencial de datos sensibles en sesión/perfil | Se copiaba el usuario persistido completo a la sesión | `views/auth.py`, `utils/security.py` | Las plantillas reciben una identidad más pequeña; campos no previstos dejan de estar disponibles | Arranque y suite completa: 6 pruebas | Se evita transportar hashes y se reduce la superficie de datos sensibles |
| Roles obsoletos o manipulables por estado de sesión antiguo | Decoradores administrativos confiaban solo en `session['user']['role']` | `views/admin.py` | Un usuario suspendido requiere limpiar sesión; es comportamiento intencional | Suite y prueba de arranque | El rol se revalida contra el almacenamiento antes de autorizar |
| Asignación masiva en restaurantes y platos | `request.json` o diccionarios completos se persistían sin allowlist | `views/admin.py`, `views/owner.py` | Campos nuevos no se aceptan automáticamente; requieren una decisión explícita | `compileall`, suite y pruebas de contratos existentes | Solo se persisten campos de negocio permitidos y validados |
| Tipos, longitudes y rangos sin validación backend | La validación estaba dispersa o dependía del navegador | `views/admin.py`, `views/owner.py`, `views/auth.py` | Solicitudes antiguas con datos inválidos reciben 400 en lugar de persistirse | Suite, prueba de CSRF y compilación | Se evitan precios, coordenadas, valoraciones, fechas e identificadores corruptos |
| Exposición de excepciones internas | Algunas APIs retornaban `str(e)` al cliente | `views/auth.py`, `views/main.py`, `views/owner.py` | El cliente recibe mensajes genéricos; los detalles siguen en logs | Suite y logs de ejecución | Reduce fuga de rutas, consultas y detalles internos |
| Contrato roto de búsqueda | El backend devolvía objeto enriquecido mientras la prueba histórica y parte del contrato esperaban lista | `views/main.py`, `static/js/search.js` | Los metadatos dejan de ir en el cuerpo y pasan a `X-Search-Total` | La suite pasó de 5/6 a 6/6 | Se mantiene compatibilidad con consumidores antiguos y el frontend tolera ambas formas |
| Persistencia JSON no atómica | Escrituras concurrentes podían truncar archivos o duplicar identificadores | `models/base.py` | Aumenta el uso de locks temporales durante escrituras | Debe cubrirse con pruebas de concurrencia en la fase de QA | Reduce corrupción mientras JSON siga activo y prepara una migración segura |

## Pruebas ejecutadas

- `python3 -m compileall -q app.py config.py models views utils`: correcto.
- `python3 -m pytest -q`: **6 passed**, una advertencia externa de `pyDatalog` por escape regular no corregida en esta fase.
- `phase4_security_check.py`: CSRF de mutaciones rechazado, formulario sin token rechazado, login sin token rechazado, búsqueda de solo lectura compatible y cabeceras de seguridad verificadas.
- Prueba de factory Flask: `create_app=ok`, 50 rutas registradas.

## Pendientes controlados

La protección CSRF de `/api/search` permanece exenta deliberadamente porque es una lectura aunque use POST; la autorización y validación de entrada siguen en backend. Las fases siguientes deben agregar pruebas específicas para la exención, rate limiting, auditoría de eventos, aprobación híbrida y migración PostgreSQL. La migración no debe eliminar ni sobrescribir los JSON originales.
