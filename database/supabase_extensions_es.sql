-- Extensiones aditivas para la base existente descrita en el requerimiento.
-- Ejecutar una sola vez en Supabase > SQL Editor después de revisar los
-- chequeos de duplicados de este archivo. No renombra ni borra tablas/filas.
BEGIN;

ALTER TABLE public.restaurantes
    ADD COLUMN IF NOT EXISTS latitud NUMERIC(9,6),
    ADD COLUMN IF NOT EXISTS longitud NUMERIC(9,6);

ALTER TABLE public.etiquetas
    ADD COLUMN IF NOT EXISTS motivo_rechazo_etiqueta TEXT;

-- El DDL original mezclaba "contiene" con "es apto para" en la misma relación.
-- Las filas existentes quedan sin interpretar hasta revisarlas; no afirmamos
-- retrospectivamente que un plato sea seguro para una alergia.
ALTER TABLE public.condiciones_platos
    ADD COLUMN IF NOT EXISTS relacion_condicion VARCHAR(24) NOT NULL DEFAULT 'SIN_CLASIFICAR',
    ADD COLUMN IF NOT EXISTS verificado BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS fuente_evidencia VARCHAR(40) NOT NULL DEFAULT 'MANUAL';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'restaurantes_latitud_rango'
          AND conrelid = 'public.restaurantes'::regclass
    ) THEN
        ALTER TABLE public.restaurantes ADD CONSTRAINT restaurantes_latitud_rango
            CHECK (latitud IS NULL OR latitud BETWEEN -90 AND 90);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'restaurantes_longitud_rango'
          AND conrelid = 'public.restaurantes'::regclass
    ) THEN
        ALTER TABLE public.restaurantes ADD CONSTRAINT restaurantes_longitud_rango
            CHECK (longitud IS NULL OR longitud BETWEEN -180 AND 180);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'condiciones_platos_relacion_valida'
          AND conrelid = 'public.condiciones_platos'::regclass
    ) THEN
        ALTER TABLE public.condiciones_platos ADD CONSTRAINT condiciones_platos_relacion_valida
            CHECK (relacion_condicion IN ('CONTIENE', 'APTO_PARA', 'SIN_CLASIFICAR'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'condiciones_platos_apto_verificado'
          AND conrelid = 'public.condiciones_platos'::regclass
    ) THEN
        ALTER TABLE public.condiciones_platos ADD CONSTRAINT condiciones_platos_apto_verificado
            CHECK (relacion_condicion <> 'APTO_PARA' OR verificado = TRUE);
    END IF;
END $$;

-- Evita fallar tarde al crear índices únicos: si ya existen duplicados que
-- solo difieren en mayúsculas/espacios, la transacción termina con un mensaje
-- claro y sin aplicar parcialmente la migración.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.etiquetas
        GROUP BY lower(trim(nombre_etiqueta)) HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Hay etiquetas duplicadas por mayúsculas/espacios; unifícalas y vuelve a ejecutar la migración.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.condiciones_dieteticas
        GROUP BY tipo_condicion, lower(trim(nombre_condicion)) HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Hay condiciones dietéticas duplicadas; unifícalas y vuelve a ejecutar la migración.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.usuarios
        WHERE email_usuario IS NOT NULL
        GROUP BY lower(trim(email_usuario)) HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Hay emails duplicados sin distinguir mayúsculas; corrígelos y vuelve a ejecutar la migración.';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_etiquetas_nombre_normalizado
    ON public.etiquetas (lower(trim(nombre_etiqueta)));
CREATE UNIQUE INDEX IF NOT EXISTS uq_condiciones_tipo_nombre_normalizado
    ON public.condiciones_dieteticas (tipo_condicion, lower(trim(nombre_condicion)));
CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_email_normalizado
    ON public.usuarios (lower(trim(email_usuario))) WHERE email_usuario IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_restaurantes_latitud_longitud
    ON public.restaurantes (latitud, longitud);
CREATE INDEX IF NOT EXISTS idx_etiquetas_restaurantes_etiqueta
    ON public.etiquetas_restaurantes (id_etiqueta_rest_fk, id_restaurante_etq_fk);
CREATE INDEX IF NOT EXISTS idx_condiciones_platos_condicion
    ON public.condiciones_platos (id_condicion_pla_fk, relacion_condicion, verificado);

COMMIT;
