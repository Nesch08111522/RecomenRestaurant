# Fase 7 — ML, recomendaciones híbridas y menús sustentados

## Diagnóstico confirmado

El proyecto no contenía un entrenamiento ML reproducible con dataset suficiente. El motor existente era principalmente un conjunto de reglas PyDatalog sobre rating, promociones y restricciones dietéticas. Las señales colaborativas reales eran insuficientes: favoritos y reseñas tenían volumen pequeño y no existía historial de interacción utilizable para entrenar un modelo robusto. Por ello no se inventó un modelo estadístico ni se eliminó el motor lógico existente.

## Solución aplicada

Se creó `logic/hybrid_recommender.py` como capa adicional y compatible. El motor combina contenido, reglas de negocio, contexto y distancia cuando hay cold start. Solo activa la señal colaborativa si existen interacciones suficientes, y registra en cada resultado el método, el desglose de puntuación, las razones y la marca `cold_start`. Las señales utilizadas proceden exclusivamente de preferencias, restricciones, etiquetas, categoría, rating, precio, promoción, disponibilidad explícita, distancia calculada, favoritos y reseñas existentes.

La ruta histórica `POST /api/search` continúa devolviendo una lista JSON para no romper el consumidor antiguo, pero cada restaurante puede incluir ahora `hybrid_score` y `recommendation`. El motor PyDatalog se conserva para la compatibilidad de evaluación y explicación individual.

## Generación de menús

El generador de empresario dejó de utilizar `random.sample`. Ahora selecciona de forma determinista platos disponibles, con categoría reconocida y precio registrado, priorizando los marcados como recomendados y usando el precio/ID como desempate estable. La respuesta mantiene `entradas`, `fondos`, `postres` y `bebidas`, y agrega evidencia explícita de que no se inventaron ingredientes, nombres ni precios. Si el catálogo no tiene datos suficientes, devuelve un error controlado en vez de completar el menú con información ficticia.

## Riesgo corregido

El muestreo aleatorio producía resultados no reproducibles, no explicables y podía presentar datos incompletos como una recomendación inteligente. La ausencia de datos colaborativos también hacía riesgoso afirmar que existía filtrado colaborativo real. La implementación actual diferencia claramente el fallback de cold start del modo híbrido con evidencia.

## Archivos afectados

| Archivo | Motivo |
|---|---|
| `logic/hybrid_recommender.py` | Nuevo motor explicable de contenido, contexto, colaboración condicionada y menús sustentados |
| `views/main.py` | Integración del ranking híbrido manteniendo el contrato histórico |
| `views/owner.py` | Sustitución del muestreo aleatorio por propuesta determinista verificable |
| `test/test_phase7_recommender.py` | Pruebas de cold start, colaborativo condicionado y catálogo sin invención |

## Validación

- Compilación de `app.py`, `config.py`, `models`, `views`, `utils`, `logic`, `database` y `migrations`: correcta.
- Suite completa: **15 passed**, con una advertencia externa de `pyDatalog` sobre una secuencia de escape.
- Se verificó que el colaborativo no se activa sin evidencia suficiente.
- Se verificó que un menú nunca incluye platos no disponibles y conserva precios del catálogo.

## Limitaciones honestas

El sistema todavía necesita más interacciones reales para justificar entrenamiento supervisado o modelos de embeddings. En esta fase se priorizó precisión trazable sobre complejidad artificial. La siguiente fase prepara búsquedas geográficas y filtros avanzados con coordenadas validadas, sin exigir PostGIS hasta demostrar que aporta valor real.
