"""Add Charon conversation and message tables

Revision ID: 20260827_charon_conversations
Revises: 20260827_missing_indexes
Create Date: 2026-08-27 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers
revision = "20260827_charon_conversations"
down_revision = "20260827_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # charon_conversations
    op.create_table(
        "charon_conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        sa.Column("channel", sa.String(20), default="web"),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("escalated", sa.Boolean, default=False),
        sa.Column("escalation_reason", sa.Text, nullable=True),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("rating_comment", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("message_count", sa.Integer, default=0),
        sa.Column("tokens_used", sa.Integer, default=0),
        sa.Column("page_context", JSON, nullable=True),
        sa.Column("experiment_variant", sa.String(20), nullable=True),
    )
    op.create_index("idx_charon_conv_session", "charon_conversations", ["session_id"])
    op.create_index("idx_charon_conv_status", "charon_conversations", ["status"])
    op.create_index("idx_charon_conv_escalated", "charon_conversations", ["escalated"])
    op.create_index("idx_charon_conv_last_activity", "charon_conversations", ["last_activity_at"])

    # charon_messages
    op.create_table(
        "charon_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("charon_conversations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tool_calls", JSON, nullable=True),
        sa.Column("tokens_used", sa.Integer, default=0),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_charon_msg_conv", "charon_messages", ["conversation_id"])
    op.create_index("idx_charon_msg_ts", "charon_messages", ["ts"])


def downgrade() -> None:
    op.drop_table("charon_messages")
    op.drop_table("charon_conversations")
