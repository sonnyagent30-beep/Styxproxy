"""Add basket_items JSONB column to orders

Revision ID: 20261009_add_basket_items
Revises: 34fb2d417cdc
Create Date: 2026-10-09 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = "20261009_add_basket_items"
down_revision = "34fb2d417cdc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("basket_items", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "basket_items")
