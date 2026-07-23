-- 2026-07-23  Rename orders.bunche_credential_id → styxproxy_credential_id.
-- The Python model declares styxproxy_credential_id (per Jul 22 rename) but
-- the live DB still has bunche_credential_id. SELECT against orders crashed
-- with UndefinedColumnError, breaking /api/admin/orders.
-- Co-fix: backend/app/auth.py + backend/app/routers/auth.py:
--   - admin_only() now decodes JWT instead of doing static-token comparison.
--   - create_access_token() now embeds 'role' in JWT payload.
--   - RoleChecker now falls back to payload['sub'] when 'email' is absent.
BEGIN;
ALTER TABLE orders DROP CONSTRAINT orders_bunche_credential_id_fkey;
ALTER TABLE orders RENAME COLUMN bunche_credential_id TO styxproxy_credential_id;
ALTER TABLE orders ADD CONSTRAINT orders_styxproxy_credential_id_fkey
  FOREIGN KEY (styxproxy_credential_id) REFERENCES styxproxy_credentials(id);
COMMIT;
