"""Widen admin_audit_log.admin_phone to 255

Revision ID: 009_audit_phone_widen
Revises: 008_add_admin_role
Create Date: 2026-07-22

The legacy column was VARCHAR(20) (from the phone-era schema). With email
identities the value is an email, often longer. Widen so audit-log writes
work without truncation errors.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "009_audit_phone_widen"
down_revision: Union[str, None] = "008_add_admin_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE admin_audit_log ALTER COLUMN admin_phone TYPE VARCHAR(255)")


def downgrade() -> None:
    op.execute("ALTER TABLE admin_audit_log ALTER COLUMN admin_phone TYPE VARCHAR(20)")
