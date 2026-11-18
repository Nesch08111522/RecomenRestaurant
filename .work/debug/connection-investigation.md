# Diagnóstico de conexión — 2026-11-17

Sin escribir `.env`. Host directo: db.kfapwgyhgiiueodxyvcp.supabase.co.

Red universitaria: registro A ausente, AAAA presente. Socket IPv6 falla con 10051; Python getaddrinfo devuelve 11001. No prueba proyecto pausado. La explicación anterior de pausa no estaba sustentada.

Nueva red de datos compartidos: getaddrinfo devuelve IPv6, TCP 5432 conectado, check_connection() SELECT 1=True, check_application_schema() OK.

Otra causa en la traza del usuario: override de PowerShell contiene literalmente HOST_POOLER y tiene prioridad sobre dotenv. Se debe quitar ese override en su consola para usar la configuración original. No adivinar un host pooler.

Documentación oficial:
- https://supabase.com/docs/guides/database/connecting-to-postgres — conexión directa IPv6, session pooler IPv4; copiar host y usuario del diálogo, no componer host por región.
- https://supabase.com/kb/troubleshooting/supabase--your-network-ipv4-and-ipv6-compatibility-cHe3BP — alternativas para redes sin IPv6.

Huella inicial del .env SHA256: BB1F2E400D03723926AC6F1C3CCFD18CEBF04E9977566CF4D2C43F5B703A9CB3.
