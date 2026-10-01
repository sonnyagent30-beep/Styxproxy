"""Merge three alembic heads.

The three head migrations (referral_system_v1, rls_platform_account_v1,
023_usage_alert_timestamps) all diverge from 013_health_snapshots but prod
DB already has the schema from all three (tables exist, columns added via
server-side patches). This merge file establishes a single linear path so
future migrations can be added cleanly.

This migration does NOT modify schema — it only unblocks the migration chain.

down_revision is a tuple of all three heads so alembic can merge them into one.

Revision ID: merge_20260819_three_heads
Revises: referral_system_v1, rls_platform_account_v1, 023_usage_alert_timestamps
Create Date: 2026-08-19 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "merge_20260819_three_heads"
down_revision = ("referral_system_v1", "rls_platform_account_v1", "023_usage_alert_timestamps")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op merge migration — just unblocks the migration chain."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
