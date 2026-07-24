-- 2026-07-24  Revert admin_invites.created_by to VARCHAR(255) holding email.
--
-- Root cause:  POST /api/admin/auth/invites 500s with
--              "invalid input syntax for type uuid" because the column was
--              migrated at some point to UUID + FK to admin_auth(id), but
--              the Python code writes the issuing admin's email (a string,
--              not a UUID). Alembic migration 003 originally created the
--              column as VARCHAR(20); a later session altered it to UUID
--              with an FK constraint, which broke the invite flow.
--
-- Fix:
--   1. Drop the foreign-key constraint (created_by should not be a UUID
--      pointing at admin_auth.id — it's the inviter's email, and
--      admin_auth.id is already cross-referenced via the invite's used_by
--      relationship when an invite is consumed).
--   2. Convert the column to VARCHAR(255) so the Python model's String(255)
--      matches the storage. This mirrors the Jul 23 used_by widening.
--   3. Drop the now-redundant index on a varchar column; recreate only if
--      we later need to query by inviter email (admin team page).
--
-- Co-fix:      backend/app/models.py — AdminInvite.created_by back to String(255).
--
-- Idempotent:  DROP CONSTRAINT IF EXISTS + ALTER COLUMN ... TYPE is safe
--              to re-run.
BEGIN;

ALTER TABLE admin_invites
  DROP CONSTRAINT IF EXISTS admin_invites_created_by_fkey;

ALTER TABLE admin_invites
  ALTER COLUMN created_by TYPE VARCHAR(255) USING created_by::text;

-- Recreate the index (drop+create is cheaper than CREATE INDEX IF NOT EXISTS
-- when the column type has changed; the IF NOT EXISTS path can stall on
-- an incompatible index signature).
DROP INDEX IF EXISTS ix_admin_invites_created_by;
CREATE INDEX IF NOT EXISTS ix_admin_invites_created_by
  ON admin_invites (created_by);

COMMIT;