"""Add missing indexes and convert Post.tags to JSONB.

This migration adds:
1. Missing indexes on frequently queried columns (orders, credentials, processed_webhooks)
2. Converts Post.tags from JSON to JSONB for proper containment queries

Revision ID: 20260827_missing_indexes
Revises: merge_20260819_three_heads
Create Date: 2026-08-27 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, use Alembic.
revision = "20260827_missing_indexes"
down_revision = "merge_20260819_three_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Missing indexes on orders ──────────────────────────────────────────
    op.create_index("idx_orders_customer_id", "orders", ["customer_id"])
    op.create_index("idx_orders_status", "orders", ["status"])
    op.create_index("idx_orders_tx_ref", "orders", ["tx_ref"])
    op.create_index("idx_orders_created_at", "orders", ["created_at"])

    # ── Missing indexes on styxproxy_credentials ───────────────────────────
    op.create_index("idx_credentials_order_id", "styxproxy_credentials", ["order_id"])
    op.create_index("idx_credentials_status", "styxproxy_credentials", ["status"])
    op.create_index("idx_credentials_customer_id", "styxproxy_credentials", ["customer_id"])

    # ── Missing index on processed_webhooks (for cleanup) ───────────────────
    op.create_index("idx_processed_webhooks_created_at", "processed_webhooks", ["created_at"])

    # ── Convert Post.tags from JSON to JSONB ───────────────────────────────
    op.execute("ALTER TABLE posts ALTER COLUMN tags TYPE JSONB USING tags::jsonb")


def downgrade() -> None:
    # Revert Post.tags back to JSON
    op.execute("ALTER TABLE posts ALTER COLUMN tags TYPE JSON USING tags::json")

    # Drop indexes
    op.drop_index("idx_orders_customer_id")
    op.drop_index("idx_orders_status")
    op.drop_index("idx_orders_tx_ref")
    op.drop_index("idx_orders_created_at")
    op.drop_index("idx_credentials_order_id")
    op.drop_index("idx_credentials_status")
    op.drop_index("idx_credentials_customer_id")
    op.drop_index("idx_processed_webhooks_created_at")
