-- 2026-07-24  Add admin_invites.feature_overrides (JSONB).
--
-- Why: Superadmin creates an invite and grants permission to specific
-- features (e.g. blog_draft, charon_eval) at invite time. Stored on
-- the invite as a JSONB list; applied to feature_flags.admin_overrides
-- when the new admin consumes the invite via /setup/complete.
--
-- Co-fixes:
--   - backend/app/models.py — AdminInvite.feature_overrides = JSON, nullable.
--   - backend/app/schemas.py — AdminInviteCreateRequest/Response gain
--     `feature_overrides: Optional[list[str]]`.
--   - backend/app/routers/auth.py — /invites writes feature_overrides;
--     /setup/complete applies them to feature_flags.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS is Postgres 9.6+.
ALTER TABLE admin_invites
  ADD COLUMN IF NOT EXISTS feature_overrides JSONB;

COMMENT ON COLUMN admin_invites.feature_overrides IS
  'JSONB list of feature-flag names enabled for the new admin when they consume this invite. NULL = role default only.';