-- 023_rls_phase2_ownership_setup.sql
-- Sprint 15 — Phase 2 prerequisite steps (idempotent / safe to re-run).
--
-- Purpose: ensure styxproxy_migrate has the privileges needed by the
-- RLS toggle endpoint (services/rls.py::get_migrate_engine) to issue
-- ALTER TABLE … ENABLE ROW LEVEL SECURITY + CREATE POLICY … TO
-- styxproxy_app on every public-schema table.
--
-- Background:
--   The toggle endpoint opens a SECOND async engine connected as
--   styxproxy_migrate (the table owner role). styxproxy (the app's
--   runtime user) has no DDL privileges on tables owned by postgres.
--   Tables in this DB were historically created by either `postgres`
--   (most tables, by the original setup scripts) or `styxproxy_migrate`
--   (by Alembic-style migrations). The toggle needs the SAME role to
--   own every table it might be asked to enable RLS on, otherwise
--   ALTER TABLE raises "must be owner of table …".
--
-- This migration is reconciliation + role-setup, not schema change.
-- Re-running it is safe (ALTER TABLE … OWNER TO is no-op when already
-- the owner; CREATE ROLE IF NOT EXISTS-style logic is hand-rolled).

-- ============================================================
-- 1. Ensure styxproxy_migrate role exists + has CREATEROLE
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'styxproxy_migrate') THEN
        CREATE ROLE styxproxy_migrate NOLOGIN NOSUPERUSER NOINHERIT CREATEROLE;
    END IF;
    -- GRANT CREATEROLE if it doesn't already have it (idempotent enough).
    -- If already present, this is a no-op.
    EXECUTE 'ALTER ROLE styxproxy_migrate CREATEROLE';
END $$;

-- ============================================================
-- 2. Bulk transfer ownership of all public tables + sequences
--    from postgres → styxproxy_migrate (idempotent)
-- ============================================================
DO $$
DECLARE r record;
BEGIN
    FOR r IN
        SELECT c.relname, c.relkind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'S')  -- ordinary tables + sequences
          AND (SELECT rolname FROM pg_roles WHERE oid = c.relowner) = 'postgres'
    LOOP
        IF r.relkind = 'r' THEN
            EXECUTE format('ALTER TABLE public.%I OWNER TO styxproxy_migrate', r.relname);
        ELSIF r.relkind = 'S' THEN
            EXECUTE format('ALTER SEQUENCE public.%I OWNER TO styxproxy_migrate', r.relname);
        END IF;
    END LOOP;
END $$;

-- ============================================================
-- 3. Ensure styxproxy_app role exists + has table/sequence grants
--    on public schema. This is the role the RLS policies target.
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'styxproxy_app') THEN
        CREATE ROLE styxproxy_app NOLOGIN NOSUPERUSER NOINHERIT;
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO styxproxy_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO styxproxy_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO styxproxy_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO styxproxy_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO styxproxy_app;

-- ============================================================
-- 5. Set postgres password so the toggle endpoint can connect as
--    superuser via get_superuser_engine() to issue GRANTs.
--    Idempotent: ALTER USER … PASSWORD re-hashes if it already exists.
--    Required because the toggle service uses styxproxy_migrate for DDL
--    but needs postgres (BYPASSRLS) for GRANT — styxproxy_migrate
--    lacks GRANT OPTION on tables it didn't create.
-- ============================================================
ALTER USER postgres PASSWORD 'postgres';
INSERT INTO styxproxy_migrations (name)
VALUES ('023_rls_phase2_ownership_setup')
ON CONFLICT (name) DO NOTHING;
