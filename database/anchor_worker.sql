-- Cross-process lease for the review-anchor worker.
-- Apply once with the server-side PostgreSQL role before running anchor_run.py.
BEGIN;

CREATE TABLE IF NOT EXISTS public.anchor_worker_leases (
    lease_name TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    lease_until TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.anchor_worker_leases ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.anchor_worker_leases FROM anon, authenticated;

COMMIT;
