CREATE TABLE IF NOT EXISTS public.ai_decisions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo VARCHAR(40) NOT NULL,
    entidad VARCHAR(40) NOT NULL,
    entidad_id BIGINT,
    actor_user_id BIGINT NOT NULL,
    entrada_resumida JSONB NOT NULL DEFAULT '{}'::jsonb,
    entrada_hash CHAR(64) NOT NULL,
    salida_ia JSONB,
    modelo VARCHAR(120),
    confianza NUMERIC(5,4) CHECK (confianza IS NULL OR confianza BETWEEN 0 AND 1),
    decision_final_del_admin VARCHAR(40),
    aceptada_bool BOOLEAN,
    latencia_ms INTEGER NOT NULL DEFAULT 0 CHECK (latencia_ms >= 0),
    estado VARCHAR(24) NOT NULL CHECK (estado IN ('reserved','ok','error','cache','rate_limited','unavailable')),
    error_codigo VARCHAR(48),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ai_decisions_actor_created_idx ON public.ai_decisions(actor_user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS ai_decisions_lookup_idx ON public.ai_decisions(actor_user_id,tipo,entrada_hash,modelo,created_at DESC) WHERE estado='ok';
CREATE INDEX IF NOT EXISTS ai_decisions_entidad_idx ON public.ai_decisions(entidad,entidad_id,created_at DESC);
REVOKE ALL ON public.ai_decisions FROM anon,authenticated;
REVOKE ALL ON SEQUENCE public.ai_decisions_id_seq FROM anon,authenticated;
