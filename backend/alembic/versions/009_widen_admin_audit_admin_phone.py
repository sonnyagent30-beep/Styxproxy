"""Widen admin_audit_log.admin_phone to 255

Revision ID: 009_audit_phone_widen
Revises: 008_add_admin_role
Create Date: 2026-07-22

The legacy column was VARCHAR(20) (from the phone-era schema). With email
identities the value is an email, often longer. Widen so audit-log writes
work without truncation errors.

Also creates admin_audit_log when it is absent. The ALTER below was the first
statement in this revision, but nothing in the chain ever created the table:
001_initial creates customer_audit_log instead (models.py:492), and
AdminAuditLog (models.py:617) is a separate integer-PK model that production
grew by hand. So `alembic upgrade head` on a clean database died here with
`relation "admin_audit_log" does not exist`, and only ever succeeded against
production, which already had the table.

Creating it here (rather than in a new revision) keeps this chain at a single
head. The CREATE is guarded so it is a no-op on production, where the table
already exists.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "009_audit_phone_widen"
down_revision: Union[str, None] = "008_add_admin_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Matches the AdminAuditLog model (models.py:617-625).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id SERIAL PRIMARY KEY,
            admin_phone VARCHAR(255),
            action VARCHAR(50) NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            details TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_admin_audit_log_admin_phone ON admin_audit_log (admin_phone)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_admin_audit_log_action ON admin_audit_log (action)")

    op.execute("ALTER TABLE admin_audit_log ALTER COLUMN admin_phone TYPE VARCHAR(255)")


def downgrade() -> None:
    op.execute("ALTER TABLE admin_audit_log ALTER COLUMN admin_phone TYPE VARCHAR(20)")
