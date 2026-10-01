"""Migration 016: admin permissions family (Theme C).

4 tables that together form the future RBAC layer:
  - admin_permissions: catalog of valid permission codes
  - admin_role_permissions: role → default grants (superadmin/admin/viewer)
  - admin_user_permissions: per-admin overrides
  - permission_change_requests: approval workflow

Direct psql migration per styxproxy-dev-db-quirks skill.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "016_admin_permissions"
down_revision = "015_countries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_admin_permissions_category", "admin_permissions", ["category"])

    op.create_table(
        "admin_role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("permission_code", sa.String(64), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("role", "permission_code", name="uq_admin_role_permission"),
    )
    op.create_index("idx_admin_role_permissions_role", "admin_role_permissions", ["role"])

    op.create_table(
        "admin_user_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("admin_email", sa.String(255), nullable=False),
        sa.Column("permission_code", sa.String(64), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("granted_by", sa.String(255), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("admin_email", "permission_code", name="uq_admin_user_permission"),
    )
    op.create_index("idx_admin_user_permissions_email", "admin_user_permissions", ["admin_email"])

    op.create_table(
        "permission_change_requests",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("target_email", sa.String(255), nullable=True),
        sa.Column("target_role", sa.String(20), nullable=True),
        sa.Column("permission_code", sa.String(64), nullable=False),
        sa.Column("desired_state", sa.Boolean(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now() + interval '7 days'")),
    )
    op.create_index("idx_pcr_status", "permission_change_requests", ["status"])
    op.create_index("idx_pcr_target_email", "permission_change_requests", ["target_email"])
    op.create_index("idx_pcr_target_role", "permission_change_requests", ["target_role"])


def downgrade() -> None:
    op.drop_index("idx_pcr_target_role", table_name="permission_change_requests")
    op.drop_index("idx_pcr_target_email", table_name="permission_change_requests")
    op.drop_index("idx_pcr_status", table_name="permission_change_requests")
    op.drop_table("permission_change_requests")
    op.drop_index("idx_admin_user_permissions_email", table_name="admin_user_permissions")
    op.drop_table("admin_user_permissions")
    op.drop_index("idx_admin_role_permissions_role", table_name="admin_role_permissions")
    op.drop_table("admin_role_permissions")
    op.drop_index("idx_admin_permissions_category", table_name="admin_permissions")
    op.drop_table("admin_permissions")
