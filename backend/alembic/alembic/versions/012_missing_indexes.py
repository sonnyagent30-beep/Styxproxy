"""Alembic migration 012: add missing FK indexes + query-path indexes.

Audited live DB Jul 28 16:30. Found:

MISSING FK INDEXES:
- free_trials.phone (FK to customers.phone) - admin lookups scan table

MISSING QUERY-PATH INDEXES (frequently queried columns):
- posts.scheduled_at (publishing scheduler cron)
- posts.status (filter by draft/published/scheduled)
- customer_audit_log.order_id (order debug page)
- admin_audit_log.created_at (admin dashboard recency)
- admin_audit_log.ip_address (security audit lookups)

Safe to run online (CREATE INDEX without CONCURRENTLY takes a brief
table-level lock but doesn't block reads on the tables in question
which are write-rare audit-style tables).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "012_missing_indexes"
down_revision = "011_fk_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
        # FK index
        "CREATE INDEX IF NOT EXISTS ix_free_trials_phone ON free_trials (phone)",

        # Posts query-path indexes
        "CREATE INDEX IF NOT EXISTS ix_posts_scheduled_at ON posts (scheduled_at) WHERE status = 'scheduled'",
        "CREATE INDEX IF NOT EXISTS ix_posts_status ON posts (status)",

        # Customer audit log
        "CREATE INDEX IF NOT EXISTS ix_customer_audit_log_order_id ON customer_audit_log (order_id)",

        # Admin audit log
        "CREATE INDEX IF NOT EXISTS ix_admin_audit_log_created_at ON admin_audit_log (created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_admin_audit_log_ip_address ON admin_audit_log (ip_address)",
    ]
    for stmt in statements:
        op.execute(stmt)


def downgrade() -> None:
    statements = [
        "DROP INDEX IF EXISTS ix_free_trials_phone",
        "DROP INDEX IF EXISTS ix_posts_scheduled_at",
        "DROP INDEX IF EXISTS ix_posts_status",
        "DROP INDEX IF EXISTS ix_customer_audit_log_order_id",
        "DROP INDEX IF EXISTS ix_admin_audit_log_created_at",
        "DROP INDEX IF EXISTS ix_admin_audit_log_ip_address",
    ]
    for stmt in statements:
        op.execute(stmt)