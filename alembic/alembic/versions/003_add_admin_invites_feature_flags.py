"""Add admin_invites and feature_flags tables.

Revision ID: 003_add_admin_invites_feature_flags
Revises: 002_add_protocol
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_add_admin_invites_feature_flags"
down_revision: Union[str, Sequence[str], None] = "002_add_protocol"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # admin_invites table
    op.create_table(
        "admin_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invite_code", sa.String(32), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="admin"),
        sa.Column("created_by", sa.String(20), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by", sa.String(20), nullable=True),
        sa.Column("max_uses", sa.Integer, nullable=False, server_default="1"),
        sa.Column("uses_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_admin_invites_code", "admin_invites", ["invite_code"], unique=True)
    op.create_index("idx_admin_invites_email", "admin_invites", ["email"])

    # feature_flags table
    op.create_table(
        "feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("enabled_for", sa.String(20), nullable=True),
        sa.Column("admin_overrides", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_feature_flags_name", "feature_flags", ["name"], unique=True)

    # Add role column to admin_auth (we'll track it via invites)
    # For now, admin_auth stays as-is, role is tracked in AdminInvite


def downgrade() -> None:
    op.drop_index("idx_feature_flags_name", table_name="feature_flags")
    op.drop_table("feature_flags")
    op.drop_index("idx_admin_invites_email", table_name="admin_invites")
    op.drop_index("idx_admin_invites_code", table_name="admin_invites")
    op.drop_table("admin_invites")
