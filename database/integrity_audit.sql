-- Additive integrity schema for sensitive audit events and finalized AI decisions.
-- Run after database/app_records.sql and database/ai_decisions.sql.
BEGIN;

ALTER TABLE public.app_records
    ADD COLUMN IF NOT EXISTS integrity_sequence BIGINT,
    ADD COLUMN IF NOT EXISTS integrity_prev_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS integrity_payload_hash CHAR(64);

ALTER TABLE public.ai_decisions
    ADD COLUMN IF NOT EXISTS integrity_sequence BIGINT,
    ADD COLUMN IF NOT EXISTS integrity_prev_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS integrity_payload_hash CHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS app_records_audit_integrity_sequence_uidx
    ON public.app_records (integrity_sequence)
    WHERE collection = 'audit_events' AND integrity_sequence IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ai_decisions_integrity_sequence_uidx
    ON public.ai_decisions (integrity_sequence)
    WHERE integrity_sequence IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.integrity_roots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stream VARCHAR(32) NOT NULL CHECK (stream IN ('audit_events', 'ai_decisions')),
    sequence_from BIGINT NOT NULL CHECK (sequence_from > 0),
    sequence_to BIGINT NOT NULL CHECK (sequence_to >= sequence_from),
    event_count INTEGER NOT NULL CHECK (event_count > 0),
    root_hash CHAR(64) NOT NULL,
    signature CHAR(64) NOT NULL,
    signature_algorithm VARCHAR(32) NOT NULL CHECK (signature_algorithm = 'HMAC-SHA256'),
    signing_key_id CHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    verification_status VARCHAR(16) NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending', 'verified', 'failed')),
    UNIQUE (stream, sequence_from, sequence_to)
);

CREATE INDEX IF NOT EXISTS integrity_roots_stream_created_idx
    ON public.integrity_roots(stream, created_at DESC);

ALTER TABLE public.integrity_roots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.integrity_roots FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.integrity_roots_id_seq FROM anon, authenticated;

COMMIT;
