# Fase 9 — Business Intelligence y métricas orientadas a datos

## Problema y causa

El sistema tenía una página de analíticas con cálculos aislados de restaurantes, favoritos, rating y precio, pero no disponía de un contrato versionado para integrar métricas de usuario, empresario, administrador, calidad de recomendaciones ni auditoría. La ausencia de un esquema estable dificultaba una futura extracción hacia Power BI y podía incentivar la creación de indicadores no sustentados.

## Solución aplicada

Se creó `analytics/metrics.py` con `build_bi_snapshot`, una función pura que recibe los repositorios existentes y produce un documento `bi.v1`. El snapshot separa actividad de usuarios, rendimiento empresarial, calidad de datos/recomendaciones, auditoría administrativa y metadatos de exportación.

El nuevo endpoint `GET /admin/api/bi/overview` exige `admin_required`, reutiliza JSON como fuente actual y no altera el backend activo. El resultado no contiene contraseñas, hashes, tokens, IP en claro ni contenido privado de conversaciones. Los promedios sin datos se expresan como `null`, no como ceros inventados. La calidad de recomendaciones declara `INSUFICIENTE_PARA_EVALUACION` mientras favoritos y reseñas no alcancen un umbral mínimo definido para esta primera versión.

## Métricas cubiertas

| Perfil | Métricas actuales |
|---|---|
| Usuario | Distribución por rol, usuarios con interacciones, eventos de favoritos y reseñas |
| Empresario | Restaurantes por estado y categoría, platos disponibles, menús, favoritos por restaurante |
| Administrador | Eventos de auditoría por acción y total de eventos |
| Calidad | Promedios de reseñas y rating, volumen de feedback y estado de suficiencia para evaluar recomendaciones |

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `analytics/metrics.py` | Nuevo agregador BI puro y versionado |
| `views/admin.py` | Endpoint protegido `/admin/api/bi/overview` y reutilización de modelos existentes |
| `test/test_phase9_bi.py` | Pruebas de agregación, privacidad y ausencia de valores inventados |

## Validación

- Compilación de aplicación y módulos: correcta.
- Suite completa: **20 passed**, con una advertencia externa de `pyDatalog`.
- Se verificaron roles, estados, categorías, feedback, auditoría, versionado y métricas vacías.
- No se introdujo una conexión directa con Power BI ni se expusieron datos personales; el snapshot queda listo para una futura extracción controlada.
