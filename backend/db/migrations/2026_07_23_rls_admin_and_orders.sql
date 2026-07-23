-- 2026-07-23  RLS migration for admin_auth, admin_invites, orders.
--
-- Why: Per user directive, "use this avenue to make sure there is RLS on
-- the database where needed." This round we touched admin_auth (login),
-- admin_invites (setup), and orders (list endpoint). All three hold
-- sensitive data — admin credentials, invite codes, customer orders.
--
-- What it does:
--   1. Creates a non-superuser role 'styxproxy_app' for future app use.
--   2. Enables RLS on the three tables.
--   3. Adds permissive policies ('USING true' / 'WITH CHECK true') so
--      the future app role sees the same rows it does today. RLS here
--      is defence-in-depth: app-level RoleChecker + JWT remain the real
--      authorisation layer; RLS catches the case where a leaked
--      connection string is used by an unauthorised role.
--
-- Production status: the api container still connects as 'styxproxy'
-- (superuser), which BYPASSES RLS. So this migration is a no-op for
-- runtime behaviour today. To actually benefit from RLS, also:
--   - Change DATABASE_URL to use styxproxy_app (NOT styxproxy)
--   - Rotate the password in this migration file before applying
--   - Move migrations/schema-management to a dedicated superuser
--     connection (separate env var, e.g. DATABASE_MIGRATION_URL)

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'styxproxy_app') THEN
    CREATE ROLE styxproxy_app LOGIN PASSWORD 'styxproxy_app_change_me'
      NOSUPERUSER NOINHERIT;
  END IF;
END $$;

GRANT CONNECT ON DATABASE styxproxy TO styxproxy_app;
GRANT USAGE ON SCHEMA public TO styxproxy_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO styxproxy_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO styxproxy_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO styxproxy_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO styxproxy_app;

ALTER TABLE admin_auth    ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders        ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS admin_auth_all ON admin_auth;
CREATE POLICY admin_auth_all ON admin_auth
  FOR ALL TO styxproxy_app
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS admin_invites_all ON admin_invites;
CREATE POLICY admin_invites_all ON admin_invites
  FOR ALL TO styxproxy_app
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS orders_all ON orders;
CREATE POLICY orders_all ON orders
  FOR ALL TO styxproxy_app
  USING (true) WITH CHECK (true);

-- Verify
SELECT c.relname AS table, c.relrowsecurity AS rls_enabled
FROM pg_class c
WHERE c.relname IN ('admin_auth','admin_invites','orders') AND c.relkind = 'r';
