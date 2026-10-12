"""Migration 015: countries table (Theme C).

ISO 3166-1 country reference table. Replaces the hardcoded
`available_countries` dict in app/services/provider.py with a queryable
DB table. See scripts/seed_countries.py for the seed data.

Direct psql migration per styxproxy-dev-db-quirks skill (no alembic_version
in live DB). The SQLAlchemy model is added to models.py in the same commit.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "015_countries"
down_revision = "014_charon_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(2), nullable=False, unique=True),
        sa.Column("code3", sa.String(3), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("flag_emoji", sa.String(8), nullable=False),
        sa.Column("region", sa.String(50), nullable=True),
        sa.Column("subregion", sa.String(50), nullable=True),
        sa.Column("plan_type_eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_supported", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("proxy_pool", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_countries_supported", "countries", ["is_supported"])
    op.create_index("idx_countries_eligible", "countries", ["plan_type_eligible"])
    op.create_index("idx_countries_region", "countries", ["region"])


def downgrade() -> None:
    op.drop_index("idx_countries_region", table_name="countries")
    op.drop_index("idx_countries_eligible", table_name="countries")
    op.drop_index("idx_countries_supported", table_name="countries")
    op.drop_table("countries")
