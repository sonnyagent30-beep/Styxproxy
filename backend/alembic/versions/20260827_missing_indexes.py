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
    #
    # Column corrections: this migration was written against a schema that had
    # `customer_id` on both tables. Neither table has that column — the model
    # uses `customer_phone`. Indexing `customer_id` raised
    # UndefinedColumnError and killed `alembic upgrade head` on a clean
    # database.
    #
    # Indexes are also skipped when their column is absent from the database
    # being migrated. Some of these columns (`tx_ref`, and most of the
    # styxproxy_credentials rotation columns) exist in the ORM model and in
    # production but were never added by any migration, so a database built
    # purely from this chain does not have them. Production is unaffected
    # (the column is present there and the index is created); a fresh database
    # no longer dies on an index for a column it does not have.
    conn = op.get_bind()

    def columns_of(table: str) -> set[str]:
        return {
            row[0]
            for row in conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :t"
                ),
                {"t": table},
            )
        }

    def maybe_index(name: str, table: str, columns: list[str]) -> None:
        if table in table_columns and set(columns) <= table_columns[table]:
            op.create_index(name, table, columns, if_not_exists=True)
        else:
            print(f"skipping {name}: {table} is missing one of {columns}")

    table_columns: dict[str, set[str]] = {}
    for tbl in ("orders", "styxproxy_credentials", "processed_webhooks"):
        table_columns[tbl] = columns_of(tbl)

    maybe_index("idx_orders_customer_phone", "orders", ["customer_phone"])
    maybe_index("idx_orders_status", "orders", ["status"])
    maybe_index("idx_orders_tx_ref", "orders", ["tx_ref"])
    maybe_index("idx_orders_created_at", "orders", ["created_at"])

    # ── Missing indexes on styxproxy_credentials ───────────────────────────
    maybe_index("idx_credentials_order_id", "styxproxy_credentials", ["order_id"])
    maybe_index("idx_credentials_status", "styxproxy_credentials", ["status"])
    maybe_index("idx_credentials_customer_phone", "styxproxy_credentials", ["customer_phone"])

    # ── Missing index on processed_webhooks (for cleanup) ───────────────────
    maybe_index("idx_processed_webhooks_created_at", "processed_webhooks", ["created_at"])

    # ── Convert Post.tags from JSON to JSONB ───────────────────────────────
    op.execute("ALTER TABLE posts ALTER COLUMN tags TYPE JSONB USING tags::jsonb")


def downgrade() -> None:
    # Revert Post.tags back to JSON
    op.execute("ALTER TABLE posts ALTER COLUMN tags TYPE JSON USING tags::json")

    # Drop indexes
    for name in (
        "idx_orders_customer_phone", "idx_orders_status", "idx_orders_tx_ref",
        "idx_orders_created_at", "idx_credentials_order_id", "idx_credentials_status",
        "idx_credentials_customer_phone", "idx_processed_webhooks_created_at",
    ):
        op.drop_index(name, if_exists=True)
