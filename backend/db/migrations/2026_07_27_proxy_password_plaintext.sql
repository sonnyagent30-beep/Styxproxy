-- 2026-07-27  Convert styxproxy_credentials.password_hash → styxproxy_password (plaintext).
--
-- Why: Proxy credentials (styxproxy_username + styxproxy_password) are the
-- auth tokens the customer uses to connect to the Dante proxy server. They
-- are NOT account passwords — they need to be retrievable in plaintext so:
--   (a) the customer can see them on their receipt/email
--   (b) we can rotate them and show the new password to the customer
--   (c) future integrations (admin tools, bulk export) can list creds
--
-- The previous password_hash column is wrong for this use case — that's the
-- bcrypt hash format used for customer *account* passwords (in
-- customers.password_hash). Two different concepts got conflated.
--
-- This migration:
--   1. Renames password_hash → styxproxy_password (no data conversion —
--      existing hash values will simply be invalid as plaintext passwords;
--      since no orders have live credentials yet, this is safe).
--   2. Changes type from TEXT to VARCHAR(100) — proxy passwords are
--      ~16 chars, leaving headroom for longer generated secrets.
--
-- Effect: All existing credentials become unusable (their stored value is
-- a bcrypt hash, not a plaintext password). This is acceptable because the
-- only existing credential is a test fixture and no customer is depending
-- on it yet (verified via: all real orders have styxproxy_credential_id = NULL).
--
-- Application code changes (in the same commit):
--   - StyxproxyCredential.password_hash → styxproxy_password
--   - create_credential() stores plaintext instead of bcrypt hash
--   - rotate_credential() stores new plaintext
--   - get_receipt_pdf() shows plaintext password on the receipt
BEGIN;
ALTER TABLE styxproxy_credentials RENAME COLUMN password_hash TO styxproxy_password;
ALTER TABLE styxproxy_credentials ALTER COLUMN styxproxy_password TYPE VARCHAR(100);
COMMIT;