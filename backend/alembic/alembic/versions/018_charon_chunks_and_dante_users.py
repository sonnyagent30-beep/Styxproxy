"""Migration 018: charon_blog_chunks + dante_users tables (Theme C).

Both additive. charon_blog_chunks keeps the RAG knowledge base
queryable; dante_users adds the per-customer Dante proxy account
foundation.

Direct psql migration per styxproxy-dev-db-quirks skill.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "018_charon_chunks_and_dante_users"
down_revision = "017_rls_policy_and_totp_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "charon_blog_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("post_id", "chunk_index", name="uq_charon_blog_chunks_post_index"),
    )
    op.create_index("idx_charon_blog_chunks_post", "charon_blog_chunks", ["post_id"])

    op.create_table(
        "dante_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("port_range_low", sa.Integer(), nullable=False, server_default=sa.text("10000")),
        sa.Column("port_range_high", sa.Integer(), nullable=False, server_default=sa.text("60000")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bytes_used", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_dante_users_customer", "dante_users", ["customer_id"])
    op.create_index("idx_dante_users_active", "dante_users", ["is_active"])
    op.create_index("idx_dante_users_expires", "dante_users", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_dante_users_expires", table_name="dante_users")
    op.drop_index("idx_dante_users_active", table_name="dante_users")
    op.drop_index("idx_dante_users_customer", table_name="dante_users")
    op.drop_table("dante_users")
    op.drop_index("idx_charon_blog_chunks_post", table_name="charon_blog_chunks")
    op.drop_table("charon_blog_chunks")
