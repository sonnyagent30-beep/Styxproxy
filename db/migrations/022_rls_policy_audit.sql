-- Migration 022: Extend RLS Policy Audit Table (Sprint 15)
--
-- Why:
--   The existing rls_policy table (created prior to this migration) tracks
--   per-table RLS state with policy_enabled BOOLEAN, applied_at /
--   rolled_back_at / last_audit timestamps. Sprint 15 needs to add the
--   policy body (USING / WITH CHECK clauses) so the admin endpoint can
--   actually toggle RLS in Postgres, not just record its state.
--
-- What it does:
--   1. Adds using_clause + role_name columns to rls_policy.
--   2. Backfills rls_policy with one row per table currently having RLS
--      (8 tables in DB: admin_audit_log, orders, styxproxy_credentials,
--      support_messages, admin_invites, customer_audit_log,
--      processed_webhooks, support_threads).
--   3. Records the migration in styxproxy_migrations (creates table if
--      missing — earlier migrations used ad-hoc tracking).

BEGIN;

ALTER TABLE rls_policy
    ADD COLUMN IF NOT EXISTS using_clause TEXT NOT NULL DEFAULT 'true',
    ADD COLUMN IF NOT EXISTS with_check TEXT NOT NULL DEFAULT 'true',
    ADD COLUMN IF NOT EXISTS role_name VARCHAR(32) NOT NULL DEFAULT 'styxproxy_app',
    ADD COLUMN IF NOT EXISTS policy_status VARCHAR(20) NOT NULL DEFAULT 'not_started',
    ADD COLUMN IF NOT EXISTS created_by VARCHAR(120);

-- Backfill: snapshot existing RLS-enabled tables
INSERT INTO rls_policy (table_name, policy_name, policy_enabled, using_clause, with_check, role_name, policy_status, created_by, notes)
SELECT
    c.relname,
    c.relname || '_all',
    c.relrowsecurity,
    'true',
    'true',
    'styxproxy_app',
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'not_started' END,
    'migration_022',
    'backfilled from pg_class on migration 022'
FROM pg_class c
WHERE c.relkind = 'r'
  AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
ON CONFLICT (table_name) DO NOTHING;

-- Index on policy_status for fast filtered reads
CREATE INDEX IF NOT EXISTS idx_rls_policy_status ON rls_policy(policy_status);

-- Track migration
CREATE TABLE IF NOT EXISTS styxproxy_migrations (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) UNIQUE NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO styxproxy_migrations (name) VALUES ('022_rls_policy_audit.sql') ON CONFLICT DO NOTHING;

COMMIT;
