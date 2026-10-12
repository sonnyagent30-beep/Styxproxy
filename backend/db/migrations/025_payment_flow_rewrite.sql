-- 025_payment_flow_rewrite.sql
-- Payment Flow Rewrite Sprint — Phase 2
--
-- Adds idempotency_key to orders, creates schema_migrations tracker,
-- and adds index for order expiry cron.
--
-- Run order:
--   1. Apply this migration as superuser.
--   2. No restart needed (code changes pick up the new column).
--
-- Idempotent: safe to re-run.

-- ============================================================
-- 1. Create schema_migrations tracker (if not exists)
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 2. Add idempotency_key to orders
-- ============================================================
ALTER TABLE orders ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(64);

-- Unique partial index: only one active order per idempotency key
-- Expires after 30 min (same as order TTL) — old keys can be reused
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency_key
    ON orders (idempotency_key)
    WHERE status NOT IN ('cancelled', 'expired', 'refunded');

-- Index for order expiry cron
CREATE INDEX IF NOT EXISTS idx_orders_pending_expiry
    ON orders (created_at)
    WHERE status = 'pending';

-- ============================================================
-- 3. Record in schema_migrations
-- ============================================================
INSERT INTO schema_migrations (name)
VALUES ('025_payment_flow_rewrite')
ON CONFLICT (name) DO NOTHING;
