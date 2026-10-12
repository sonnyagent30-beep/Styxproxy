"""Migration 021: Migrate startup DDL patches to Alembic.

H1 from STYXv2-001-ARCH: The main.py lifespan previously ran 13 ALTER TABLE
ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS statements on EVERY uvicorn
startup. With multiple uvicorn workers (S0.7), all 13 fire simultaneously on each
worker's first request, taking brief table locks on PostgreSQL.

This migration consolidates those patches into a single Alembic versioned migration
so they are applied exactly once at deploy time via `alembic upgrade head`.

Down-revision: 020_plan_settings
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "021_startup_patches_to_alembic"
down_revision = "020_plan_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── platform_accounts ─────────────────────────────────────────────────────
    # device_id: anonymous device session UUID (no PII, no uniqueness constraint)
    op.add_column(
        "platform_accounts",
        sa.Column("device_id", sa.String(64), nullable=True),
    )
    # Index already defined in model __table_args__; create it only if not present.
    # SQLite (tests) doesn't support IF NOT EXISTS for CREATE INDEX, so we guard
    # with postgresql_only.  Tests that define the column manually should also
    # create the index as part of their fixture.
    op.create_index(
        "idx_platform_device",
        "platform_accounts",
        ["device_id"],
        if_not_exists=True,
        postgresql_only=True,
    )

    # ── styxproxy_credentials: rotation tracking ─────────────────────────────
    op.add_column(
        "styxproxy_credentials",
        sa.Column("rotation_count", sa.Integer(), server_default="0", nullable=False),
    )

    # ── styxproxy_credentials: sticky session + country targeting ─────────────
    op.add_column(
        "styxproxy_credentials",
        sa.Column("country_target", sa.String(2), nullable=True),
    )
    op.add_column(
        "styxproxy_credentials",
        sa.Column(
            "sticky_session_minutes", sa.Integer(), server_default="0", nullable=False
        ),
    )

    # ── styxproxy_credentials: bandwidth alerting ──────────────────────────────
    op.add_column(
        "styxproxy_credentials",
        sa.Column(
            "bandwidth_alert_pct", sa.Integer(), server_default="80", nullable=False
        ),
    )

    # ── styxproxy_credentials: password rotation tracking ─────────────────────
    op.add_column(
        "styxproxy_credentials",
        sa.Column("password_rotated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "styxproxy_credentials",
        sa.Column(
            "password_rotations_today",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "styxproxy_credentials",
        sa.Column(
            "password_rotations_reset_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_date(),
            nullable=False,
        ),
    )

    # ── styxproxy_credentials: last-seen IP tracking ──────────────────────────
    op.add_column(
        "styxproxy_credentials",
        sa.Column("last_ip_country", sa.String(2), nullable=True),
    )
    op.add_column(
        "styxproxy_credentials",
        sa.Column("last_ip_address", sa.String(45), nullable=True),  # IPv6 max 45 chars
    )

    # ── styxproxy_credentials: per-session sticky session ───────────────────
    op.add_column(
        "styxproxy_credentials",
        sa.Column("session_id", sa.String(50), nullable=True),
    )
    op.add_column(
        "styxproxy_credentials",
        sa.Column("session_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Drop in reverse order of creation (best-effort; some may already be absent)
    op.drop_column("styxproxy_credentials", "session_expires_at")
    op.drop_column("styxproxy_credentials", "session_id")
    op.drop_column("styxproxy_credentials", "last_ip_address")
    op.drop_column("styxproxy_credentials", "last_ip_country")
    op.drop_column("styxproxy_credentials", "password_rotations_reset_at")
    op.drop_column("styxproxy_credentials", "password_rotations_today")
    op.drop_column("styxproxy_credentials", "password_rotated_at")
    op.drop_column("styxproxy_credentials", "bandwidth_alert_pct")
    op.drop_column("styxproxy_credentials", "sticky_session_minutes")
    op.drop_column("styxproxy_credentials", "country_target")
    op.drop_column("styxproxy_credentials", "rotation_count")
    # Index drop is idempotent but not strictly reversible in tests that re-create the column
    op.drop_index("idx_platform_device", table_name="platform_accounts")
    op.drop_column("platform_accounts", "device_id")
