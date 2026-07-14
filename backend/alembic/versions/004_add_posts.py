"""Add posts table for blog CMS.

Revision ID: 004_add_posts
Revises: 003_add_admin_invites_feature_flags
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_add_posts"
down_revision: Union[str, Sequence[str], None] = "003_add_admin_invites_feature_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Posts table for blog CMS
    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("excerpt", sa.Text, nullable=True),
        sa.Column("cover_image_url", sa.Text, nullable=True),
        sa.Column("author", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(20), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_description", sa.Text, nullable=True),
        sa.Column("tags", postgresql.JSON, nullable=True),
        sa.Column("view_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_posts_slug", "posts", ["slug"], unique=True)
    op.create_index("idx_posts_status", "posts", ["status"])
    op.create_index("idx_posts_published", "posts", ["published_at"])
    op.create_index("idx_posts_scheduled", "posts", ["scheduled_at"])


def downgrade() -> None:
    op.drop_index("idx_posts_scheduled", table_name="posts")
    op.drop_index("idx_posts_published", table_name="posts")
    op.drop_index("idx_posts_status", table_name="posts")
    op.drop_index("idx_posts_slug", table_name="posts")
    op.drop_table("posts")
