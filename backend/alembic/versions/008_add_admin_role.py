"""Add admin role + align admin_audit_log to existing schema

Revision ID: 008_add_admin_role
Revises: 007_add_support_threads
Create Date: 2026-07-22

NOTE: Both changes were applied directly to production Postgres (role column
on admin_auth, admin_audit_log table existed with the integer-id schema),
this migration exists purely to record that in version history.
"""
from typing import Sequence, Union
from sqlalchemy import String, Integer, Index, DateTime, Text
from alembic import op
import sqlalchemy as sa


revision: str = "008_add_admin_role"
down_revision: Union[str, None] = "007_add_support_threads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # role column on admin_auth (already applied to live DB; idempotent no-op if rerun)
    op.execute("ALTER TABLE admin_auth ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'admin'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_admin_auth_role ON admin_auth(role)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_admin_auth_role")
    op.execute("ALTER TABLE admin_auth DROP COLUMN IF EXISTS role")
