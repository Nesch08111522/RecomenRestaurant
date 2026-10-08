# Fase 8 — Geolocalización, proximidad y preparación espacial

## Problema y causa

La utilidad geográfica aceptaba valores no finitos, trataba coordenadas en cero como si fueran ausentes y devolvía un valor centinela ante errores sin separar claramente coordenadas inválidas de restaurantes sin ubicación. Además, el enriquecimiento marcaba `is_open_now=True` aunque no existiera horario calculado, lo que podía producir recomendaciones y filtros con información inventada. La API de proximidad validaba el centro, pero no exponía filtros backend de categoría, precio, valoración y disponibilidad.

## Correcciones aplicadas

`utils/geo.py` ahora normaliza latitud y longitud a siete decimales, rechaza valores fuera de rango o no finitos y mantiene una distancia aproximada reproducible mediante Haversine. La geocodificación continúa siendo opcional, cacheada y separada de las búsquedas para no imponer una dependencia de red en cada consulta.

`utils/functional.py` ya no crea un estado horario ficticio. Solo conserva `is_open_now` si una fuente previa lo proporciona explícitamente. La distancia se calcula también para coordenadas válidas iguales a cero.

`views/main.py` amplía `GET /api/restaurants/nearby` con filtros validados en backend: `category_id`, `max_price`, `min_rating` y `available_only`. Se preserva la respuesta `{results, total, center, radius}` y el radio queda limitado a 100 km. `POST /api/save-location` usa JSON tolerante, normaliza coordenadas y no registra valores de ubicación en texto plano en los logs.

## Decisión sobre PostGIS

No se activa PostGIS en esta fase porque el sistema actual opera con JSON y todavía no existe una base PostgreSQL desplegada disponible en el entorno de validación. El esquema PostgreSQL preparado conserva `lat` y `lng` estructurados, por lo que una futura migración puede añadir una columna `geography(Point, 4326)` y un índice GiST cuando el volumen, la latencia o las consultas espaciales reales justifiquen su coste. Hasta entonces, Haversine en aplicación es suficiente para radios acotados y permite mantener el cambio reversible.

## Archivos afectados

| Archivo | Cambio | Riesgo controlado |
|---|---|---|
| `utils/geo.py` | Validación, normalización y distancia segura | Coordenadas corruptas, resultados erróneos y dependencia accidental de red |
| `utils/functional.py` | No inventar horario y aceptar coordenadas cero | Falsas afirmaciones de disponibilidad |
| `views/main.py` | Filtros de proximidad y guardado seguro de ubicación | Filtros solo frontend, rangos inválidos y logs sensibles |
| `test/test_phase8_geo.py` | Pruebas de coordenadas y ausencia de horario inventado | Regresiones en geolocalización |

## Validación

- Compilación de aplicación y módulos: correcta.
- Suite completa: **18 passed**, con una advertencia externa de `pyDatalog`.
- Se validaron coordenadas `0,0`, rangos inválidos, valores `NaN`, distancia inválida y fallback de recomendaciones sin horario explícito.
