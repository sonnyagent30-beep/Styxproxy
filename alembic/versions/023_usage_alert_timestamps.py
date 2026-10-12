"""Migration 023: Add usage alert tracking columns (S2.6 / BIZ STYXv2-004 §4.2).

Tracks when 75% and 95% usage alert emails were sent so we don't re-send
on every cron run.

Down-revision: 022_trial_sessions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "023_usage_alert_timestamps"
down_revision = "022_trial_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "styxproxy_credentials",
        sa.Column(
            "alert_sent_75pct_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "styxproxy_credentials",
        sa.Column(
            "alert_sent_95pct_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Indexes for efficient "where alert_sent_75pct_at IS NULL AND usage >= 75%"
    op.create_index(
        "idx_cred_alert_75_pending",
        "styxproxy_credentials",
        ["alert_sent_75pct_at"],
        postgresql_where=sa.text("alert_sent_75pct_at IS NULL"),
    )
    op.create_index(
        "idx_cred_alert_95_pending",
        "styxproxy_credentials",
        ["alert_sent_95pct_at"],
        postgresql_where=sa.text("alert_sent_95pct_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_cred_alert_95_pending", table_name="styxproxy_credentials")
    op.drop_index("idx_cred_alert_75_pending", table_name="styxproxy_credentials")
    op.drop_column("styxproxy_credentials", "alert_sent_95pct_at")
    op.drop_column("styxproxy_credentials", "alert_sent_75pct_at")
