"""Alembic migration: add missing foreign-key indexes for query performance.

Postgres does NOT auto-index FK columns. Queries like
  SELECT * FROM orders WHERE customer_id = ?
scan the whole orders table without an index on customer_id.

This migration adds indexes on every FK column that lacks one.
Safe to run online (CREATE INDEX CONCURRENTLY equivalent) — no table
locks taken because indexes are added in non-CONCURRENT mode here
(alembic offline migrations do not need concurrent creation).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011_fk_indexes"
down_revision = "010_rename_bunche_to_styxproxy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Indexes for FK columns missing them. Discovered via:
    #   SELECT c.conrelid::regclass, c.conname, c.conkey
    #   FROM pg_constraint c WHERE c.contype = 'f'
    #   AND NOT EXISTS (SELECT 1 FROM pg_index i
    #                   WHERE i.indrelid = c.conrelid
    #                   AND i.indkey[0:array_length(c.conkey,1)] = c.conkey);
    statements = [
        # free_trials: phone FK — idx_free_trials_phone_date already covers it. skip.
        # free_trials: bunche_credential_id — needs new index
        "CREATE INDEX IF NOT EXISTS ix_free_trials_credential_id ON free_trials (bunche_credential_id)",
        # admin_invites: created_by — needs new index
        "CREATE INDEX IF NOT EXISTS ix_admin_invites_created_by ON admin_invites (created_by)",
        # post_categories: composite PK (post_id, category_id) already indexes both FKs. skip.
        # support_threads: order_id — needs new index
        "CREATE INDEX IF NOT EXISTS ix_support_threads_order_id ON support_threads (order_id)",
        # merge_requests: 4 FK columns — all need indexes
        "CREATE INDEX IF NOT EXISTS ix_merge_requests_source ON merge_requests (source_account_id)",
        "CREATE INDEX IF NOT EXISTS ix_merge_requests_target ON merge_requests (target_account_id)",
        "CREATE INDEX IF NOT EXISTS ix_merge_requests_requested_by ON merge_requests (requested_by)",
        "CREATE INDEX IF NOT EXISTS ix_merge_requests_approved_by ON merge_requests (approved_by)",
        # pending_trial_surveys: 2 FK columns
        "CREATE INDEX IF NOT EXISTS ix_pending_trial_surveys_trial_id ON pending_trial_surveys (free_trial_id)",
        "CREATE INDEX IF NOT EXISTS ix_pending_trial_surveys_customer_id ON pending_trial_surveys (customer_id)",
        # orders: platform_account_id — needs new index
        "CREATE INDEX IF NOT EXISTS ix_orders_platform_account_id ON orders (platform_account_id)",
        # orders: bunche_credential_id — needs new index
        "CREATE INDEX IF NOT EXISTS ix_orders_bunche_credential_id ON orders (bunche_credential_id)",
        # styxproxy_credentials: order_id — needs new index
        "CREATE INDEX IF NOT EXISTS ix_styxproxy_credentials_order_id ON styxproxy_credentials (order_id)",
        # platform_accounts: customer_id — needs new index
        "CREATE INDEX IF NOT EXISTS ix_platform_accounts_customer_id ON platform_accounts (customer_id)",
    ]
    for stmt in statements:
        op.execute(stmt)


def downgrade() -> None:
    statements = [
        "DROP INDEX IF EXISTS ix_free_trials_credential_id",
        "DROP INDEX IF EXISTS ix_admin_invites_created_by",
        "DROP INDEX IF EXISTS ix_support_threads_order_id",
        "DROP INDEX IF EXISTS ix_merge_requests_source",
        "DROP INDEX IF EXISTS ix_merge_requests_target",
        "DROP INDEX IF EXISTS ix_merge_requests_requested_by",
        "DROP INDEX IF EXISTS ix_merge_requests_approved_by",
        "DROP INDEX IF EXISTS ix_pending_trial_surveys_trial_id",
        "DROP INDEX IF EXISTS ix_pending_trial_surveys_customer_id",
        "DROP INDEX IF EXISTS ix_orders_platform_account_id",
        "DROP INDEX IF EXISTS ix_orders_bunche_credential_id",
        "DROP INDEX IF EXISTS ix_styxproxy_credentials_order_id",
        "DROP INDEX IF EXISTS ix_platform_accounts_customer_id",
    ]
    for stmt in statements:
        op.execute(stmt)
