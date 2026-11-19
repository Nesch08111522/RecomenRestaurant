# Resolución del merge y prueba de producción

## Conflictos resueltos

- `.env.example`: se conservaron las variables de blockchain, anclas, scheduler de integridad y límites de PostgreSQL. Se agregaron los parámetros operativos de pool/timeout y SMTP. No contiene credenciales reales; `AUDIT_SIGNING_KEY` queda vacío.
- `models/ai_decision.py`: se conservaron el encadenamiento `integrity_sequence`, `integrity_prev_hash`, `integrity_payload_hash`, `reserve()/finish()` y los límites de transacción PostgreSQL.
- `templates/detail.html`: se conservó la ficha visual moderna y se reincorporó el sello de `Compra verificada`, el botón `Comprobar huella` y la consulta del estado de anclaje.

## Fase 1: prueba real de reseña y blockchain

1. Ejecuta las migraciones en Supabase una sola vez, usando el rol de servidor recomendado por Supabase:

   ```sql
   -- database/app_records.sql
   -- database/ai_decisions.sql
   -- database/integrity_audit.sql
   -- database/anchor_worker.sql
   ```

2. En el entorno de producción configura, fuera de Git:

   ```text
   ANCHOR_STORE=postgres
   ANCHOR_MODE=onchain
   CHAIN_RPC_URL=<RPC de Polygon Amoy>
   CHAIN_ID=80002
   ANCHOR_CONTRACT=<dirección del contrato desplegado>
   ANCHOR_PRIVATE_KEY=<clave de la wallet publicadora>
   ANCHOR_CONTRACT_METHOD=anchor
   ANCHOR_PSEUDONYM_SECRET=<secreto estable de al menos 32 bytes>
   ```

   `ANCHOR_PRIVATE_KEY` debe corresponder a una wallet con MATIC/moneda nativa para gas. No debe ser la dirección pública ni una clave incluida en el repositorio.

3. Inicia la aplicación normalmente. Cuando `ANCHOR_STORE=postgres` y `ANCHOR_MODE=onchain`, `app.py` inicia automáticamente el worker de anclas como hilo daemon. No tienes que ejecutar `anchor_run.py` cada vez ni mantener una terminal adicional.

   ```bash
   python app.py
   ```

   El worker usa `anchor_worker_leases` para impedir dos workers simultáneos incluso si producción ejecuta varios procesos Flask. `ANCHOR_MODE=onchain` no simula: envía una transacción EVM mediante el RPC.

4. Crea la evidencia de negocio desde la web:

   - Inicia sesión como comensal.
   - Abre `/mercado`.
   - Agrega una porción al carrito y confirma el pedido con `Contraentrega` para la prueba más simple.
   - Como negocio, cambia el pedido por `Confirmado → Preparando → Listo → Entregado`.
   - En contraentrega, el estado `Entregado` marca el pedido como pagado.
   - Como comensal, abre `/mercado/pedidos` y publica **Publicar reseña verificada**.
   - Abre la ficha del negocio. Debe verse `Compra verificada` y `Comprobar huella`.

5. La evidencia esperada es:

   - Primero: la reseña existe con `verified_purchase=true` y `order_id`.
   - Después: la cola de anclas muestra `pending` y el worker la pasa a `submitted`.
   - Cuando la red confirma: pasa a `confirmed` y conserva `tx_hash`.
   - El botón público muestra `Huella confirmada en cadena`.

   Comprobación SQL:

   ```sql
   SELECT review_id, status, attempts, tx_hash, error, created_at, updated_at
   FROM public.trust_anchors
   ORDER BY id DESC
   LIMIT 20;
   ```

## Fase 2: trazabilidad de lote

Los pedidos nuevos guardan en cada línea una instantánea de `amount`, `unit`, `lot`, `expires` y `recorded_at`; ya no dependen del inventario actual. El comensal propietario puede consultar:

```text
GET /mercado/pedidos/<ID>/trazabilidad
```

En la web aparece el enlace **Ver trazabilidad de ingredientes y lotes** dentro de cada pedido.

Los pedidos antiguos que no tengan todos esos campos se marcan como `complete: false`; no se inventa información histórica.

## Fase 3: auditoría e integridad

Configura en el servidor:

```text
AUDIT_SIGNING_KEY=<secreto aleatorio estable de al menos 32 bytes>
INTEGRITY_AUTO_ENABLED=true
INTEGRITY_INTERVAL_SECONDS=300
INTEGRITY_BATCH_SIZE=500
```

Genera una clave en PowerShell:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

En Linux:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Reinicia la aplicación. El scheduler de integridad se inicia desde `create_app()` y firma/verifica raíces cada intervalo. En producción debe revisarse el log del proceso:

```text
Worker de integridad iniciado: intervalo=300s, lote=500
Integridad: raices nuevas firmadas=...
Verificacion periodica de integridad correcta; raices revisadas=...
```

Prueba manual:

```bash
python scripts/integrity_audit.py sign --batch-size 500
python scripts/integrity_audit.py verify
```

El scheduler de integridad y el worker blockchain son hilos automáticos distintos dentro del arranque de Flask. Activar `INTEGRITY_AUTO_ENABLED` firma/verifica auditoría; `ANCHOR_MODE=onchain` publica las reseñas. Ambos quedan activos mientras el proceso de producción esté activo.

## Regresión local ejecutada

```bash
python3 -m pytest -q test/test_traceability_phase2.py test/test_anchor_phase0.py test/test_phase3_review_update.py test/test_phase3_duplicate_review.py test/test_integrity.py test/test_integrity_scheduler.py test/test_market_transactions.py test/test_market_flow.py
```

Resultado de esta revisión: `29 passed, 4 skipped`.
