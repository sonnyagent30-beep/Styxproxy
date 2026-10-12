"""Add order_renewals table

Revision ID: 20261007_order_renewals
Revises: 20260827_charon_conversations
Create Date: 2026-10-07 21:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20261007_order_renewals"
down_revision = "20260827_charon_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_renewals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.String(20), sa.ForeignKey("orders.order_id"), nullable=False),
        sa.Column("renewal_tx_ref", sa.String(100), nullable=False),
        sa.Column("quantity_gb", sa.Integer(), nullable=False),
        sa.Column("amount_paid_ngn", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_renewals_order", "order_renewals", ["order_id"])
    op.create_index("idx_renewals_tx_ref", "order_renewals", ["renewal_tx_ref"])
    op.create_index("idx_renewals_status", "order_renewals", ["status"])


def downgrade() -> None:
    op.drop_index("idx_renewals_status", table_name="order_renewals")
    op.drop_index("idx_renewals_tx_ref", table_name="order_renewals")
    op.drop_index("idx_renewals_order", table_name="order_renewals")
    op.drop_table("order_renewals")
