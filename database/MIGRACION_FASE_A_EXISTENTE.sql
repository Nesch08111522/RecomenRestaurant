-- Ejecutar SOLO si ya creaste ai_decisions con el script anterior de Fase A.
ALTER TABLE public.ai_decisions DROP CONSTRAINT IF EXISTS ai_decisions_estado_check;
ALTER TABLE public.ai_decisions ADD CONSTRAINT ai_decisions_estado_check
CHECK (estado IN ('reserved','ok','error','cache','rate_limited','unavailable'));
CREATE INDEX IF NOT EXISTS ai_decisions_lookup_idx ON public.ai_decisions(actor_user_id,tipo,entrada_hash,modelo,created_at DESC) WHERE estado='ok';
