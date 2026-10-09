"""Add basket_items JSONB to orders — multi-item cart support.

## Why

The checkout flow fires one payment-initiate per cart item, then redirects
to the FIRST checkout_url — abandoning every other item. The customer pays
for one product while the cart shows the total for all. This column lets a
single order carry multiple items so one payment covers the whole cart.

## What this adds

    basket_items  JSONB  array of {plan_code, quantity, quantity_gb, price_ngn, name, country_code}

Each element is one cart line. The order's amount_paid_ngn is the SUM of
all items. Fulfillment reads this array to create the right number of
credentials.

Revision ID: 20261009_basket_items
Revises: 20261001_refund_gateway_evidence
Create Date: 2026-10-09 12:00:00.000000
"""

from alembic import op

revision = "20261009_basket_items"
down_revision = "20261001_refund_gateway_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS basket_items JSONB")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_basket_items ON orders USING GIN (basket_items)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_orders_basket_items")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS basket_items")
