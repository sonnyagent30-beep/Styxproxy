-- 2026-07-23  Widen admin_invites.used_by to hold full email (was varchar(20),
--              too short for any real email address).
-- Root cause:  /api/admin/auth/setup/complete set invite.used_by = email,
--              which crashed with StringDataRightTruncationError (HTTP 500).
-- Co-fix:      backend/app/models.py — declared used_by as UUID, but DB
--              column was varchar. SQLAlchemy coerced email to UUID and
--              asyncpg rejected. Changed model to String(20) (now matches
--              widened DB). created_by kept as UUID (real FK to admin_auth.id).
ALTER TABLE admin_invites ALTER COLUMN used_by TYPE VARCHAR(255);
