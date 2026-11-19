-- SOLO DIAGNÓSTICO. No crea/modifica tablas, permisos ni registros.
-- Ejecutar con el administrador de la base, en la conexión que usa Flask.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '4s';
SELECT relrowsecurity AS rls_enabled
FROM pg_class WHERE oid = 'public.app_records'::regclass;
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'public.app_records'::regclass;
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'app_records';
SELECT count(*) AS duplicate_groups FROM (
    SELECT collection, id FROM public.app_records
    GROUP BY collection, id HAVING count(*) > 1
) AS duplicates;
SELECT count(*) AS null_keys FROM public.app_records
WHERE collection IS NULL OR id IS NULL;
SELECT has_table_privilege('anon','public.app_records','SELECT') AS anon_read,
       has_table_privilege('authenticated','public.app_records','SELECT') AS authenticated_read;
EXPLAIN (ANALYZE, BUFFERS)
SELECT payload FROM public.app_records
WHERE collection = 'restaurants' ORDER BY id LIMIT 20;
ROLLBACK;

-- PROPUESTA PARA REVISIÓN MANUAL, deliberadamente comentada.
-- Antes: respaldo completo de PostgreSQL, verificar claves nulas/duplicadas,
-- restricciones reales, rol del backend, dependencias y una ventana operativa.
-- No usar el script heredado migrar.py para restaurar índices o restricciones.
-- Fuera de una transacción, si no existe una PK/índice equivalente:
-- CREATE UNIQUE INDEX CONCURRENTLY app_records_collection_id_review
--     ON public.app_records(collection, id);
-- Después de verificar que el índice sea válido y las columnas NOT NULL:
-- ALTER TABLE public.app_records ADD CONSTRAINT app_records_pkey
--     PRIMARY KEY USING INDEX app_records_collection_id_review;
-- Revisar el rol efectivo de Flask antes de activar RLS:
-- ALTER TABLE public.app_records ENABLE ROW LEVEL SECURITY;
-- REVOKE ALL ON TABLE public.app_records FROM anon, authenticated;
-- Probar lectura/escritura con el rol real del backend en staging.
-- No añadir GIN ni índices parciales sin planes de consultas representativas.
