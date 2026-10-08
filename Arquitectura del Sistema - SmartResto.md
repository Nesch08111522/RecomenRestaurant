# Arquitectura del Sistema - SmartResto

## Flujo de Datos
1. El usuario realiza una búsqueda o aplica un filtro en la UI.
2. El cliente envía una petición AJAX a `/api/search` con los criterios.
3. El controlador (`views/main.py`) carga los datos de `RestaurantModel`.
4. Se aplica el **Paradigma Funcional** (`utils/functional.py`) para filtrar y enriquecer los datos (distancias, scores iniciales).
5. Los resultados pasan por el **Motor Lógico** (`logic/recommender.py`) que aplica reglas de pyDatalog basadas en el perfil del usuario.
6. El motor lógico añade justificaciones dinámicas o excluye restaurantes no aptos.
7. Los resultados finales se ordenan por ranking y se envían al cliente como JSON.
8. La UI actualiza la grilla de tarjetas y los marcadores del mapa dinámicamente.

## Componentes Principales
- **Base de Datos**: Archivos JSON normalizados para facilitar la portabilidad y personalización.
- **Geolocalización**: Uso de `haversine` para distancias y `geopy` para direcciones.
- **Seguridad**: Hasheo de contraseñas con `werkzeug.security`.
