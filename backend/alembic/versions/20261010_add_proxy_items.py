"""Add proxy_items table and proxy_item_id to order_renewals.

Implements Option A from BULK-ORDER-DESIGN.md: parent order + N child
proxy records. Each proxy_item is one manageable proxy pointing to one
credential. Existing bulk orders get backfilled from their credentials.

Revision ID: 20261010_add_proxy_items
Revises: 20261009_basket_items
Create Date: 2026-10-10 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20261010_add_proxy_items"
down_revision = "20261009_basket_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create proxy_items table ─────────────────────────────────────────
    op.create_table(
        "proxy_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(length=20), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False, server_default="Proxy"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("plan_type", sa.String(length=20), nullable=True),
        sa.Column("plan_code", sa.String(length=50), nullable=True),
        sa.Column("country", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.order_id"]),
        sa.ForeignKeyConstraint(["credential_id"], ["styxproxy_credentials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_proxy_items_order", "proxy_items", ["order_id"])
    op.create_index("idx_proxy_items_credential", "proxy_items", ["credential_id"])
    op.create_index("idx_proxy_items_status", "proxy_items", ["status"])
    op.create_index("idx_proxy_items_expires", "proxy_items", ["expires_at"])

    # ── Add proxy_item_id to order_renewals ─────────────────────────────
    op.add_column(
        "order_renewals",
        sa.Column("proxy_item_id", sa.Integer(), nullable=True),
    )
    op.create_index("idx_renewals_proxy_item", "order_renewals", ["proxy_item_id"])
    op.create_foreign_key(
        "fk_order_renewals_proxy_item_id",
        "order_renewals",
        "proxy_items",
        ["proxy_item_id"],
        ["id"],
    )

    # ── Backfill: create proxy_items for existing orders ─────────────────
    # For each order that has credentials, create one proxy_item per credential.
    # This covers both legacy multi-IP orders (quantity > 1) and basket orders.
    op.execute(
        """
        INSERT INTO proxy_items (order_id, credential_id, label, status, expires_at, plan_type, plan_code, country)
        SELECT
            c.order_id,
            c.id AS credential_id,
            'Proxy ' || ROW_NUMBER() OVER (PARTITION BY c.order_id ORDER BY c.id) AS label,
            c.status,
            c.expires_at,
            o.plan_type,
            o.plan_code,
            o.country
        FROM styxproxy_credentials c
        JOIN orders o ON o.order_id = c.order_id
        WHERE c.order_id IS NOT NULL
        ORDER BY c.order_id, c.id
        """
    )


def downgrade() -> None:
    # Drop FK first, then index, then column
    op.drop_constraint("fk_order_renewals_proxy_item_id", "order_renewals", type_="foreignkey")
    op.drop_index("idx_renewals_proxy_item", table_name="order_renewals")
    op.drop_column("order_renewals", "proxy_item_id")

    # Drop proxy_items table (indexes cascade)
    op.drop_table("proxy_items")
