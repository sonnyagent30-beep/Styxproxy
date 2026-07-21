"""Add password reset token columns to admin_auth.

Revision ID: 006_add_password_reset_tokens
Revises: 005_add_plans
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_add_password_reset_tokens"
down_revision: Union[str, Sequence[str], None] = "005_add_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add reset_token columns to admin_auth table
    op.add_column(
        "admin_auth",
        sa.Column("reset_token_hash", sa.String(255), nullable=True),
    )
    op.add_column(
        "admin_auth",
        sa.Column("reset_token_expires", sa.DateTime(timezone=True), nullable=True),
    )
    # Add index for faster lookups
    op.create_index(
        "idx_admin_auth_reset_token",
        "admin_auth",
        ["reset_token_expires"],
        unique=False,
        postgresql_where=sa.text("reset_token_expires IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_admin_auth_reset_token", table_name="admin_auth")
    op.drop_column("admin_auth", "reset_token_expires")
    op.drop_column("admin_auth", "reset_token_hash")
