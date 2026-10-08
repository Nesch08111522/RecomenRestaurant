# Priorización ejecutable SmartResto

## Baseline registrado

La ejecución inicial con las dependencias instaladas produjo **5 pruebas aprobadas y 1 fallida**. La falla reproducible es `SmokeTest.test_api_search`: el backend devuelve un objeto `{filters, results, stats, total}`, mientras el test exige una lista. Esto confirma una inconsistencia de contrato frontend/backend o test/backend, no un fallo de importación. Los chequeos manuales de resolución de rutas e importaciones básicas finalizaron correctamente.

## Orden de intervención

| Orden | Hallazgos | Nivel | Motivo de precedencia | Criterio de salida |
|---:|---|---|---|---|
| 1 | H-01, H-02, H-03, H-04, H-05, H-06, H-07, H-08, H-20 | P0/P1 seguridad | Pueden permitir compromiso de sesión, CSRF, escalamiento o filtración | Configuración segura, CSRF, sesión mínima, allowlists, errores genéricos y pruebas negativas |
| 2 | H-15, H-16, H-17, H-18, H-10 | P1 integridad/funcionalidad | Pueden corromper datos o romper administración/moderación | Persistencia protegida, contratos coherentes y estados controlados |
| 3 | H-14, H-19, H-21 | P1/P2 contexto/datos | Afectan disponibilidad, proximidad, filtros y calidad de catálogo | Validadores, horarios reales y consultas reproducibles |
| 4 | H-09, H-11 | P1 aprobación | El flujo debe ser auditable antes de automatizar más | Máquina de estados, evaluación versionada y reversión |
| 5 | H-12, H-13, H-22 | P1/P2 recomendación | No se puede medir ML sin eventos y fallback seguro | Motor explicable en sombra, métricas y cold-start |
| 6 | H-23 | P1 QA transversal | Las correcciones necesitan regresión automatizada | Unitarias, integración, API, seguridad y migración |

## Reglas de ejecución

Cada cambio se hará sobre la copia de trabajo, con hash previo/posterior, registro de archivos afectados, prueba focalizada, regresión completa y rollback posible. No se eliminarán JSON, pyDatalog, rutas existentes ni funciones de menú hasta disponer de una sustitución comparada y validada.

La primera corrección abordará seguridad de configuración, gestión de sesión, CSRF, validación allowlist y contratos de API. Después se introducirá la capa de persistencia relacional y la migración validada. Los estados de aprobación y el motor híbrido se construirán sobre datos trazables, no sobre heurísticas no auditadas.
