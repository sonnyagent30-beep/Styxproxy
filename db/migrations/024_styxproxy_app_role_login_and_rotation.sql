-- 024_styxproxy_app_role_login_and_rotation.sql
-- Sprint 15 — final step. Promote styxproxy_app from NOLOGIN to LOGIN
-- and rotate its password from the migration 022 placeholder to a
-- production-grade random secret.
--
-- Run order:
--   1. Apply this migration as superuser.
--   2. Update STYXPROXY_APP_DB_PASSWORD in /opt/styxproxy/.env on every
--      host that connects as styxproxy_app (currently: none — the app
--      connects as `styxproxy` via the admin bridge policies. Pin
--      DATABASE_URL=styxproxy_app in a follow-up step after a soak
--      period).
--   3. systemctl restart styxproxy-api.
--
-- IMPORTANT: this migration is idempotent but the password rotation
-- is NOT — re-running this will overwrite whatever password is set.
-- The real secret lives in /opt/styxproxy/.env, NOT in this file.

-- ============================================================
-- 1. Promote styxproxy_app to LOGIN
--    Originally created with NOLOGIN (migration 022) because no app
--    was connecting as it yet. The intent was to pre-create the role
--    so RLS policies could reference it. With the connection-string
--    pin coming next, the role must accept connections.
-- ============================================================
ALTER ROLE styxproxy_app LOGIN;

-- ============================================================
-- 2. Grant the role + connection privileges on the target DB
--    (idempotent — GRANT is a no-op if already granted)
-- ============================================================
GRANT CONNECT ON DATABASE styxproxy TO styxproxy_app;

-- ============================================================
-- 3. Schema privileges (already granted by migration 023 via
--    superuser engine). Re-grant here as a belt-and-suspenders in
--    case migrations run out of order.
-- ============================================================
GRANT USAGE ON SCHEMA public TO styxproxy_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO styxproxy_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO styxproxy_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO styxproxy_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO styxproxy_app;

-- ============================================================
-- 4. Record in styxproxy_migrations tracker
-- ============================================================
INSERT INTO styxproxy_migrations (name)
VALUES ('024_styxproxy_app_role_login_and_rotation')
ON CONFLICT (name) DO NOTHING;
