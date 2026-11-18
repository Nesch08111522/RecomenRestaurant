# Políticas verificadas — 2026-11-17

## OpenStreetMap y Overpass

- Datos OSM bajo ODbL 1.0. Atribución visible y enlazada; al distribuir una base derivada aplican obligaciones de compartir esa porción bajo ODbL. Mantener separados y etiquetados los datos propios de empresarios.
- https://www.openstreetmap.org/copyright
- https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
- https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ
- https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
- https://wiki.openstreetmap.org/wiki/Overpass_API

La instancia principal https://overpass-api.de/api/interpreter recomienda servidor propio/pagado para uso comercial sostenido y está sobrecargada; el estado devolvió 502 por cola llena.

La alternativa verificada directamente es https://overpass.private.coffee/api/interpreter. Su operador permite cualquier proyecto, incluido comercial, sin registro. Exige consultas optimizadas, limitar simultáneas, evitar PII y respetar licencia OSM; notificar operaciones grandes (>10 req/s o >10 simultáneas). Servicio sin garantía. Fuente: https://overpass.private.coffee/ (términos actualizados 2026-04-10). Las pruebas HTTP desde este equipo agotaron timeout; no se afirmará descubrimiento real exitoso.

## Google Places

Consulta puntual no persistente y no sobre mapa no-Google. Solicitar FieldMask mínimo. No guardar nombres, direcciones, reseñas, fotos, horarios o lat/lng para construir catálogo propio. Place IDs tienen excepción de almacenamiento, pero este módulo opta por cero persistencia. Atribución visible Google Maps y proveedores devueltos; fotos/reseñas exigirían atribución de autores. Clave y facturación necesarias.

- https://developers.google.com/maps/documentation/places/web-service/policies
- https://developers.google.com/maps/documentation/places/web-service/text-search
- https://developers.google.com/maps/documentation/places/web-service/place-id
- https://cloud.google.com/maps-platform/terms
- https://cloud.google.com/maps-platform/terms/maps-service-terms

## Seguridad

- HTTPS a IP pública fijada, DNS A/AAAA globales, Host/SNI originales, certificado verificado, no redirects/proxies/cookies.
- Páginas oficiales solo con permiso documentado y vencimiento; robots no constituye licencia.
- IA extractiva sin herramientas, valores respaldados con cita exacta, salida escapada.
- Invitación: hash y TTL, propósito firmado, uso único y consumo transaccional; no prueba automática de titularidad.
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
