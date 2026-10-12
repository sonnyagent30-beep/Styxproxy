"""Migration 017: rls_policy + admin_totp_sessions tables (Theme C).

Direct psql migration per styxproxy-dev-db-quirks skill.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "017_rls_policy_and_totp_sessions"
down_revision = "016_admin_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rls_policy",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(64), nullable=False, unique=True),
        sa.Column("policy_name", sa.String(100), nullable=False),
        sa.Column("policy_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_audit", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_rls_policy_enabled", "rls_policy", ["policy_enabled"])

    op.create_table(
        "admin_totp_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_email", sa.String(255), nullable=False),
        sa.Column("session_token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_fingerprint", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.dialects.postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_admin_totp_sessions_email", "admin_totp_sessions", ["admin_email"])
    op.create_index("idx_admin_totp_sessions_expires", "admin_totp_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_admin_totp_sessions_expires", table_name="admin_totp_sessions")
    op.drop_index("idx_admin_totp_sessions_email", table_name="admin_totp_sessions")
    op.drop_table("admin_totp_sessions")
    op.drop_index("idx_rls_policy_enabled", table_name="rls_policy")
    op.drop_table("rls_policy")
