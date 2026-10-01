"""Migration 019: trial phone uniqueness + consent_events table.

Part 1 — free_trials: add UNIQUE constraint on (phone, trial_date) to prevent
the same phone from claiming more than one trial per calendar day. An existing
partial duplicate can be cleaned up manually; this prevents future duplicates.

Part 2 — consent_events: new table tracking every consent interaction for GDPR
compliance (cookie consent, marketing consent, terms acceptance). Immutable log.

Part 3 — add consent_given/consent_version/consent_at columns to customers table
(already in model but not yet migrated).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "019_trial_consent"
down_revision = "018_charon_chunks_and_dante_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Part 1: Trial uniqueness ───────────────────────────────────────────────
    # Drop the non-unique index and replace with a proper UNIQUE constraint
    # on (phone, trial_date). We use a unique index, not a table constraint,
    # because (phone, trial_date) allows multiple NULL phone rows (no FK violation).
    op.drop_index("idx_free_trials_phone_date", table_name="free_trials")
    op.create_index(
        "uq_free_trials_phone_trial_date",
        "free_trials",
        ["phone", "trial_date"],
        unique=True,
        postgresql_where=sa.text("phone IS NOT NULL"),
    )

    # ── Part 2: Consent events ──────────────────────────────────────────────────
    op.create_table(
        "consent_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column("consent_type", sa.String(50), nullable=False),  # cookie | marketing | terms
        sa.Column("consent_version", sa.String(20), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),  # IPv4 or IPv6
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_consent_customer", "consent_events", ["customer_id"])

    # ── Part 3: Customer consent columns ────────────────────────────────────────
    # These are already in the SQLAlchemy model but may not exist in prod DB.
    # safe to run on both fresh and existing DBs (Postgres ignores no-op ALTER).
    op.add_column(
        "customers",
        sa.Column("consent_given", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "customers",
        sa.Column("consent_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_index("uq_free_trials_phone_trial_date", table_name="free_trials")
    op.create_index(
        "idx_free_trials_phone_date",
        "free_trials",
        ["phone", "trial_date"],
        unique=False,
    )
    op.drop_index("idx_consent_customer", table_name="consent_events")
    op.drop_table("consent_events")
    op.drop_column("customers", "consent_at")
    op.drop_column("customers", "consent_version")
    op.drop_column("customers", "consent_given")
