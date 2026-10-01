-- Minimal real schema for the credential-delivery ledger tests.
--
-- The ledger table below mirrors the live production shape, captured from
-- 162.35.184.69 on 2026-10-01 via psql \d. That fidelity is the point of the
-- test — NOT NULL constraints, the foreign key, and the varchar widths are
-- what the assertions exercise — so this file is deliberately hand-written
-- from production rather than generated from the ORM.
--
-- The parent table styxproxy_credentials is NOT here: the test fixture creates
-- it from the ORM metadata, so it cannot drift from the model. Only the ledger
-- table and its 026 columns are applied from this file.
--
-- Idempotent: safe to re-run.

-- The ledger table, exactly as it exists in production today.
CREATE TABLE IF NOT EXISTS credential_notifications (
    id                 SERIAL PRIMARY KEY,
    credential_id      INTEGER      NOT NULL
                       REFERENCES styxproxy_credentials(id) ON DELETE CASCADE,
    notification_type  VARCHAR(50)  NOT NULL,
    channel            VARCHAR(20)  NOT NULL DEFAULT 'sms',
    target             VARCHAR(255) NOT NULL,
    enabled            BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_credential
    ON credential_notifications(credential_id, enabled) WHERE enabled;

-- Columns migration 026 adds. The ORM expects these, so a ledger write
-- against a schema without them would fail — which is the point.
ALTER TABLE credential_notifications
    ADD COLUMN IF NOT EXISTS order_id   VARCHAR(20),
    ADD COLUMN IF NOT EXISTS status     VARCHAR(20),
    ADD COLUMN IF NOT EXISTS error      TEXT,
    ADD COLUMN IF NOT EXISTS message_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_notifications_order
    ON credential_notifications(order_id);

