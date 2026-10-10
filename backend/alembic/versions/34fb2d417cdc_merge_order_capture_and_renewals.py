"""Merge order_capture_columns and order_renewals

Revision ID: 34fb2d417cdc
Revises: 20261001_order_capture_columns, 20261007_order_renewals
Create Date: 2026-10-07 22:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "34fb2d417cdc"
down_revision = ("20261001_order_capture_columns", "20261007_order_renewals")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
