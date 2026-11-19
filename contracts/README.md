# Anclaje de reseñas en Polygon Amoy

`Anchor.sol` implementa la llamada `anchor(bytes32)` usada por
`utils/anchor_job.py`. Guarda el primer timestamp por hash y emite `Anchored`.
Repetir el mismo hash no revierte ni genera un segundo evento, por lo que un
reintento después de perder la respuesta RPC no duplica el registro lógico.
El contrato no recibe texto, identificadores de usuario ni datos de pedidos.

## Despliegue y verificación

1. Revisa `Anchor.sol` y compílalo con Solidity 0.8.24. Conserva el ABI y los
   artefactos generados junto al manifiesto `deployment-amoy.example.json`.
2. Despliega en Polygon Amoy (chain ID `80002`) desde una cuenta de prueba.
   No reutilices la clave privada configurada para la aplicación.
3. Verifica el contrato en PolygonScan Amoy con exactamente la misma versión
   del compilador, optimización y argumentos de despliegue. Completa dirección,
   hash de transacción y hash del bytecode de runtime en una copia del manifiesto.
4. Antes de configurar el backend, confirma en el explorador que el bytecode
   corresponde a esta fuente y prueba `anchor(bytes32)` y `anchoredAt(bytes32)`.
5. Configura `CHAIN_RPC_URL`, `CHAIN_ID=80002`,
   `ANCHOR_CONTRACT=<dirección verificada>` y
   `ANCHOR_CONTRACT_METHOD=anchor` en el entorno del worker.

La dirección configurada actualmente en el entorno **no queda validada por este
archivo**. No reemplaces el contrato activo hasta comparar su bytecode y ABI.
Si el contrato desplegado no tiene el mismo comportamiento idempotente, haz el
despliegue como una migración controlada y cambia la dirección después de
verificarlo.

## Ejecución del worker

Aplica `database/anchor_worker.sql` una vez con el rol PostgreSQL del servidor.
Después, `python anchor_run.py` ejecuta una pasada; `python anchor_run.py
--watch` inicia sondeo recurrente. `ANCHOR_STORE=postgres` es obligatorio para
operación persistente.

El lease en PostgreSQL evita dos workers activos incluso en hosts distintos.
Usa una cuenta firmante exclusiva para este worker: el lease coordina instancias
de esta aplicación, pero no otros procesos que usen la misma clave.

Las transacciones enviadas se guardan como `submitted` antes de consultar el
recibo. Si aún no hay recibo se vuelven a consultar en la siguiente pasada; un
timeout no vuelve a enviar la transacción. Los fallos previos al envío usan
backoff (`ANCHOR_RETRY_BASE_SECONDS`, `ANCHOR_RETRY_MAX_SECONDS`) hasta
`ANCHOR_MAX_ATTEMPTS`. Un recibo revertido queda en `reverted` para revisión
operativa. Ajusta `ANCHOR_RECEIPT_TIMEOUT` y
`ANCHOR_RECEIPT_POLL_SECONDS` según el intervalo y el proveedor RPC.
