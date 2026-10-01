"""Add gateway refund confirmation columns to orders

Item 3 of the go-live gate (t_f765263b). An admin refund used to flip
`status='refunded'`, revoke the credential and email the customer WITHOUT
calling a gateway, so the customer was told their money came back when it did
not. All 46 legacy `refunded` rows are administrative flips: they carry a
payment_reference but a NULL tx_ref, i.e. the gateway was never consulted.

These columns record the gateway's own refund id/status/amount and when we
recorded it, so a refund can be reconciled against the gateway afterwards.

Additive and nullable, with NO backfill: for the 46 historical rows we have no
evidence any money was refunded, so a fabricated value would be worse than NULL.
A NULL `gateway_refund_id` on a `refunded` row is itself the finding — it marks
an order whose status was flipped administratively and whose real refund state
is unknown.

Revision ID: 20261001_refund_gateway_columns
Revises: 20260827_charon_conversations
Create Date: 2026-10-01 10:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20261001_refund_gateway_columns"
down_revision = "20260827_charon_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("gateway_refund_id", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("gateway_refund_status", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("gateway_refund_amount", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("orders", sa.Column("gateway_refunded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_orders_gateway_refund_id", "orders", ["gateway_refund_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_gateway_refund_id", table_name="orders")
    op.drop_column("orders", "gateway_refunded_at")
    op.drop_column("orders", "gateway_refund_amount")
    op.drop_column("orders", "gateway_refund_status")
    op.drop_column("orders", "gateway_refund_id")
