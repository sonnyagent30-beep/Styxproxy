-- Migration 014: plan_audit_log + plan edit history
--
-- Tracks every INSERT/UPDATE/DELETE on the plans table for compliance,
-- debugging, and rollback. Populated by triggers added in a follow-up
-- migration (015), not by application code.
--
-- Created (Jul 29 2026, Theme E).

CREATE TABLE IF NOT EXISTS plan_audit_log (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id         INTEGER      REFERENCES plans(id) ON DELETE SET NULL,
    action          VARCHAR(20)  NOT NULL,
    actor_admin_id  UUID         REFERENCES admin_auth(id) ON DELETE SET NULL,
    actor_email     VARCHAR(255),
    before          JSONB,
    after           JSONB,
    changed_fields  JSONB,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plan_audit_log_plan_id    ON plan_audit_log(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_audit_log_actor      ON plan_audit_log(actor_admin_id);
CREATE INDEX IF NOT EXISTS idx_plan_audit_log_created    ON plan_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_plan_audit_log_action     ON plan_audit_log(action);

GRANT ALL ON plan_audit_log TO styxproxy;
