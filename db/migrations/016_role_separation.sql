-- Migration 016: Role separation — create styxproxy_migrate, transfer table ownership
--
-- Goal: day-to-day migrations use styxproxy_migrate (NOSUPERUSER) instead of postgres
-- Effect: Even if a migration script has a bug, it can't escape the database as a superuser.
--         The postgres superuser is reserved for emergency repair only.
--
-- SAFETY:
--   - styxproxy retains ALL its per-table GRANTs (SELECT/INSERT/UPDATE/DELETE)
--   - The app's DATABASE_URL still uses styxproxy user (unchanged behavior)
--   - The new role has CREATE on public schema so migrations can still add tables
--   - REVERSIBLE: REASSIGN OWNED BY styxproxy_migrate TO styxproxy; DROP ROLE styxproxy_migrate
--
-- Created (Jul 29 2026, Theme C closure).

-- 1. Create the migrate role (NOSUPERUSER, can login via TCP, can create tables/indexes)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'styxproxy_migrate') THEN
        CREATE ROLE styxproxy_migrate WITH
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            INHERIT
            NOREPLICATION
            NOBYPASSRLS
            PASSWORD 'styxproxy_migrate_2026';
    END IF;
END $$;

-- 2. Grant schema-level permissions needed for migrations
GRANT CREATE ON SCHEMA public TO styxproxy_migrate;
GRANT USAGE ON SCHEMA public TO styxproxy_migrate;
GRANT TEMPORARY ON DATABASE styxproxy TO styxproxy_migrate;

-- 3. Grant on future tables (so new migrations work without re-granting)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES, TRIGGER ON TABLES TO styxproxy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO styxproxy;

-- 4. Transfer ownership of all existing tables, sequences, views from styxproxy to styxproxy_migrate
--    (styxproxy's per-table GRANTs are preserved)
REASSIGN OWNED BY styxproxy TO styxproxy_migrate;

-- 5. Re-grant the new owner the CREATE-on-schema right it needs to ALTER tables
--    (Already done in step 2, but explicit is safer)
GRANT CREATE ON SCHEMA public TO styxproxy_migrate;
