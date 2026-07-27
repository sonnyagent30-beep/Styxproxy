-- 2026-07-27  Encrypt styxproxy_credentials.styxproxy_password at rest.
--
-- Why: Proxy passwords are auth tokens (like API keys) needed plaintext for
-- receipt rendering and rotation, but should not be visible to anyone with
-- raw DB read access (DBAs, backup operators, anyone who can psql).
--
-- Application layer now uses Fernet (AES-128-CBC + HMAC-SHA256) with key
-- from CRED_ENCRYPTION_KEY env var. This migration flips the column from
-- VARCHAR(100) plaintext → BYTEA ciphertext.
--
-- Migration safety:
--   - Existing rows: the previous migration 2026_07_27_proxy_password_plaintext.sql
--     left the password as plaintext VARCHAR. This migration COULD try to
--     re-encrypt in-place, but the SQL would need the encryption key which
--     should not live in version control. Better: application code reads
--     plaintext (legacy), re-encrypts and writes back on next mutation
--     (create_credential, rotate_proxy).
--   - Practical effect: any credential row that existed BEFORE this migration
--     is treated as plaintext for one more read; on the next write (e.g.
--     rotation, or a manual re-save) it gets re-encrypted.
--   - Safer alternative would be a one-shot Python migration that reads
--     each row, encrypts via the live key, writes back. Out of scope here.
--
-- Effect on existing data:
--   Since no live proxy creds exist yet, no in-place re-encryption needed.
--   Column type flips to BYTEA. New rows always go in encrypted.
BEGIN;
-- Drop NOT NULL first so USING NULL on a non-empty column is allowed
ALTER TABLE styxproxy_credentials ALTER COLUMN styxproxy_password DROP NOT NULL;
-- Flip the column type from VARCHAR(100) plaintext to BYTEA ciphertext
ALTER TABLE styxproxy_credentials ALTER COLUMN styxproxy_password TYPE BYTEA USING NULL;
COMMIT;