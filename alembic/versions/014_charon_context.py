"""CharonContext table — per-session rolling memory for Charon conversations.

Theme C — give Charon (the AI sales agent) persistent memory across page
reloads. Today Charon reconstructs context from the escalations table
and the knowledge base only. With this table, Charon can:
  - Remember the customer's last intent (e.g. "asked about pricing for 3GB")
  - Resume a conversation if the customer returns within 24h
  - Surface "what we talked about last time" to the agent

A rollback is safe: DROP TABLE cascades nothing important (no FK from
other tables yet — this is a brand-new table).

Retention: 24h, enforced by a daily cron (cleanup_charon_context.py).
After 24h the customer's intent is no longer "in-flight" and forcing
the agent to ask clarifying questions is better than serving stale
context.

NOTE: applied directly via psql per the styxproxy-dev-db-quirks skill
(live DB has no alembic_version table). The SQLAlchemy model is added
to models.py in the same commit so the next Base.metadata.create_all()
or migration will see the same definition.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "014_charon_context"
down_revision = "013_health_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "charon_context",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", sa.String(100), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_intent", sa.String(255), nullable=True),
        sa.Column("last_topics", sa.dialects.postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("conversation_id", name="uq_charon_context_conversation"),
    )
    op.create_index("idx_charon_context_conversation", "charon_context", ["conversation_id"])
    op.create_index("idx_charon_context_expires", "charon_context", ["expires_at"])
    op.create_index("idx_charon_context_customer_email", "charon_context", ["customer_email"])


def downgrade() -> None:
    op.drop_index("idx_charon_context_customer_email", table_name="charon_context")
    op.drop_index("idx_charon_context_expires", table_name="charon_context")
    op.drop_index("idx_charon_context_conversation", table_name="charon_context")
    op.drop_table("charon_context")
