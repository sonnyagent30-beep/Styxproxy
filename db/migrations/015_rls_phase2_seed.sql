-- Phase 2 RLS rollout: 8 tables enabled (Jul 29)
-- Run AFTER rls_enable.py <table> --apply for each
-- Just sets the feature flag admin_overrides so /api/admin/auth/flags/rls_enabled_tables reflects reality.

UPDATE feature_flags
SET admin_overrides = '[processed_webhooks,customer_audit_log,admin_audit_log,admin_invites,support_threads,support_messages,orders,styxproxy_credentials]'::json
WHERE name = 'rls_enabled_tables';
