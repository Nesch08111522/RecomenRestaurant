# Fase 11 — QA integral, seguridad, contratos API y regresión

## Alcance

Se añadió una batería específica para verificar rutas públicas, contratos de búsqueda, cabeceras HTTP, protección de endpoints administrativos, rechazo de entradas inválidas, unicidad de endpoints y ausencia de modo debug. La suite también conserva las pruebas de migración, seguridad CSRF, RBAC, aprobación, recomendaciones, geolocalización y BI.

## Incidencia encontrada y resolución

La primera ejecución de la nueva prueba tuvo dos fallos en el propio test: asumía `/login` y `/api/favorites/toggle`, mientras que el mapa real de Flask conserva los prefijos `/auth/login` y `/auth/api/favorites/toggle`. No se modificó la aplicación para adaptarla al test; se corrigió únicamente `test/test_phase11_qa.py` para reflejar los contratos reales descubiertos mediante el mapa de rutas. La segunda ejecución fue satisfactoria.

## Archivos afectados

| Archivo | Cambio | Validación |
|---|---|---|
| `test/test_phase11_qa.py` | Pruebas QA de rutas, seguridad y contratos | 4 pruebas específicas |
| `inspect_routes.py` | Herramienta reproducible de inspección de rutas | Confirmó prefijos reales |
| `phase11_qa_test_output.txt` | Evidencia de ejecución | Suite completa |

## Resultado

- Compilación de módulos Python: correcta.
- Suite completa: **24 passed**, con una advertencia externa de `pyDatalog` sobre una secuencia de escape.
- Se verificaron rutas públicas, endpoint BI administrativo, búsqueda, favoritos, cabeceras `X-Content-Type-Options` y `X-Frame-Options`, entradas inválidas y ausencia de endpoints duplicados.
- No quedan fallos conocidos en la batería automatizada de esta fase.
