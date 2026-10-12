-- Migration 026: grant the relay's DB role a SELECT-only policy on credentials
--
-- Why this migration exists
-- ------------------------
-- The paid relay (styxproxy-relay-paid.service) connects as DB role
-- `styxproxy`. `styxproxy_credentials` has `relforcerowsecurity = t` and,
-- before this migration, its ONLY policy (`creds_app_all`) was granted to
-- `styxproxy_app`. So the `styxproxy` role held SELECT/UPDATE grants it
-- could never exercise: FORCEd RLS filtered every row and `SELECT` returned
-- ZERO rows WITH NO ERROR.
--
-- Consequence: RelayAuth.refresh() cached zero users, so verify() rejected
-- EVERY customer credential at SOCKS5/HTTP auth. Measured on production
-- 2026-10-01: role `styxproxy` saw 0 of 35 credential rows while
-- `styxproxy_app` saw 35 (10 of them active with a password).
--
-- Why it was invisible: `styxproxy_relay_entries` has NO RLS, so bandwidth
-- metering kept reading and writing rows the whole time. Every "healthy"
-- signal stayed green while no customer could connect.
--
-- Why route (a) — a SELECT-only policy — and not repointing the DSN
-- ---------------------------------------------------------------------
-- Repointing the unit at `styxproxy_app` is a smaller diff but writes that
-- role's password into a systemd unit file and widens the relay to the full
-- app role's access. The relay's real requirement is narrower:
--   * READ credentials        -> refresh() / verify()
--   * UPDATE bandwidth counters on styxproxy_relay_entries (no RLS)
-- The BandwidthTracker flush is `UPDATE styxproxy_relay_entries ... FROM
-- styxproxy_credentials c`, so that statement ALSO needs to see credential
-- rows — a SELECT policy is exactly what that requires, and no more.
-- This is therefore the least-privilege expression of the real requirement.
--
-- Note we deliberately do NOT grant a policy permitting writes to
-- styxproxy_credentials for this role. The relay never writes that table.
--
-- Idempotent: re-running is a no-op. Records itself in styxproxy_migrations.

BEGIN;

-- ============================================================
-- 1. SELECT-only policy for the relay role.
--    USING (true) is correct here because the relay must be able to
--    authenticate every active credential; per-row predicates would
--    silently re-break auth for any credential the predicate misses.
--    Per-row scoping is the application's job (refresh() already
--    filters `WHERE c.status = 'active'`), not the database's.
-- ============================================================
DROP POLICY IF EXISTS creds_relay_select ON styxproxy_credentials;
CREATE POLICY creds_relay_select ON styxproxy_credentials
    FOR SELECT
    TO styxproxy
    USING (true);

-- ============================================================
-- 2. Belt-and-suspenders: the relay role needs SELECT to exercise the
--    policy at all, and USAGE on the schema to resolve the relation.
--    Both were already true in production, but migrations run on fresh
--    databases too, so make the requirement explicit rather than
--    depending on migration 016b's grant ordering.
-- ============================================================
GRANT CONNECT ON DATABASE styxproxy TO styxproxy;
GRANT USAGE ON SCHEMA public TO styxproxy;
GRANT SELECT ON styxproxy_credentials TO styxproxy;
GRANT SELECT, UPDATE ON styxproxy_relay_entries TO styxproxy;

-- ============================================================
-- 3. Record in styxproxy_migrations.
-- ============================================================
INSERT INTO styxproxy_migrations (name)
VALUES ('026_relay_role_credential_select')
ON CONFLICT (name) DO NOTHING;

COMMIT;
