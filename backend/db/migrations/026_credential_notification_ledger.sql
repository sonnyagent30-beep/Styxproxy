-- 026_credential_notification_ledger.sql
--
-- Turn credential_notifications from a configuration table into an observable
-- send ledger for credential delivery.
--
-- Background
-- ----------
-- `credential_notifications` was created by migration 019 as a per-credential
-- *preference* table ("send an sms to this target when this credential
-- changes"). It has had 0 rows and zero references anywhere in app/ — nothing
-- ever read or wrote it.
--
-- That left credential delivery unobservable: `send_order_active_email()`
-- returns an EmailResult carrying success/status/error, and until now the
-- fulfillment worker discarded it. There was no persisted record, by any path,
-- of whether a customer's credentials were ever sent, accepted, or rejected.
-- A Resend rejection was indistinguishable from a delivery.
--
-- This migration adds the columns needed to record an OUTCOME, not just an
-- intention. The existing columns alone cannot express failure: `target` is
-- NOT NULL and describes where to send, and `enabled` is a preference flag,
-- not a result.
--
--   status     'sent' | 'failed' | 'no_address' | 'skipped'
--              'sent'       provider accepted the message
--              'failed'     provider rejected it (EmailResult.success is false)
--              'no_address' no deliverable address could be resolved at all
--              'skipped'    send was not attempted
--   error      EmailResult.error, or the exception text, verbatim
--   order_id   the order this send belongs to. NOT derivable from
--              credential_notifications alone: credential_id points at
--              styxproxy_credentials, whose order_id is nullable and is not
--              unique (a multi-quantity order mints several credentials).
--   message_id provider message id, for correlation with the provider's logs
--
-- All four are nullable and additive, so this is safe to run against the live
-- table with existing rows and needs no backfill: rows written before this
-- migration are preferences, not send records, and are left untouched.
--
-- Idempotent: safe to re-run.
--
-- Run as: styxproxy_migrate (owns the table) — NOT the app role, which has
-- arwd on the table but not ALTER.

-- 1. Outcome columns
ALTER TABLE credential_notifications
    ADD COLUMN IF NOT EXISTS order_id   VARCHAR(20),
    ADD COLUMN IF NOT EXISTS status     VARCHAR(20),
    ADD COLUMN IF NOT EXISTS error      TEXT,
    ADD COLUMN IF NOT EXISTS message_id VARCHAR(255);

-- 2. Index for "what happened to this order's credentials?"
--    Partial on status IS NOT NULL so the preference rows this table was
--    designed for do not bloat the index.
CREATE INDEX IF NOT EXISTS idx_notifications_order
    ON credential_notifications(order_id)
    WHERE order_id IS NOT NULL;

-- 3. Index for "which sends failed and need a human?"
CREATE INDEX IF NOT EXISTS idx_notifications_failed
    ON credential_notifications(created_at DESC)
    WHERE status IN ('failed', 'no_address');
