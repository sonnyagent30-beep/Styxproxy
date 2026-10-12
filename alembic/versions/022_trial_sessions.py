"""Migration 022: Add trial_sessions table (S2.3 / S2.4 TheoremReach → trial pipeline).

S2.3 requirement: Track trial_started_at, trial_expires_at in a trial_sessions table.
Each row = one trial grant from one TheoremReach survey completion (2 hours each, max 24h).

Down-revision: 021_startup_patches_to_alembic
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "022_trial_sessions"
down_revision = "021_startup_patches_to_alembic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── trial_sessions table ─────────────────────────────────────────────────
    op.create_table(
        "trial_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Platform account link (nullable for anonymous users)
        sa.Column(
            "platform_account_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("platform_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # TheoremReach device identifier
        sa.Column("device_id", sa.String(64), nullable=True, index=True),
        # The survey that triggered this trial
        sa.Column("survey_id", sa.String(100), nullable=True, unique=True),
        # Trial window
        sa.Column(
            "trial_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=False),
        # Cumulative hours: 1 survey = 2h, capped at 24h per device
        sa.Column("total_hours_granted", sa.Numeric(6, 2), nullable=False, default=0.0),
        # Links to the proxy credential created for this trial
        sa.Column(
            "styxproxy_credential_id",
            sa.Integer(),
            sa.ForeignKey("styxproxy_credentials.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # 3proxy SOCKS5 port allocated for this trial
        sa.Column("threeproxy_port", sa.Integer(), nullable=True),
        # Delivery status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            default="pending",
            index=True,
        ),
        # Trial-to-paid conversion timestamp
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        # Audit timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Indexes for common query patterns
    op.create_index("idx_trial_sessions_device_id", "trial_sessions", ["device_id"])
    op.create_index("idx_trial_sessions_status", "trial_sessions", ["status"])
    op.create_index("idx_trial_sessions_expires", "trial_sessions", ["trial_expires_at"])
    op.create_index("idx_trial_sessions_started", "trial_sessions", ["trial_started_at"])


def downgrade() -> None:
    op.drop_index("idx_trial_sessions_started", table_name="trial_sessions")
    op.drop_index("idx_trial_sessions_expires", table_name="trial_sessions")
    op.drop_index("idx_trial_sessions_status", table_name="trial_sessions")
    op.drop_index("idx_trial_sessions_device_id", table_name="trial_sessions")
    op.drop_table("trial_sessions")
