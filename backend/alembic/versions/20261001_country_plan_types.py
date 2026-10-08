"""Create `country_plan_types` — the table every catalog code path reads.

## The gap

`country_plan_types` is the authoritative answer to "what is sellable", and it
is read by `app/services/catalog.py`, `app/routers/catalog.py`,
`app/routers/orders.py`, `app/routers/admin.py`, and
`app/services/charon/{tools,page_templates}.py`. Yet `grep -rn
country_plan_types backend/alembic/versions/` matched NOTHING and the table had
no ORM model either — production and `alembic_rehearsal` both have it (64 rows,
33 enabled) because it was created out-of-band, by hand.

So a fresh environment (restore-from-migration, a new developer DB, CI's
postgres service) had no such table and every one of those paths raised
`UndefinedTable`: `/api/catalog` and `/api/countries` both 500. The test suite
could not catch it because every relevant test fakes the session.

## Two provisioning paths, on purpose

1. `CountryPlanType` in `backend/app/models.py` — `main.py`'s lifespan runs
   `Base.metadata.create_all` on every boot, and this is the ONLY path that
   actually provisions a clean database here. `alembic upgrade head` fails on
   the FIRST revision (`001_initial` builds `orders` with foreign keys to
   tables it has not created yet: `relation "bunche_credentials" does not
   exist`), so the migration chain cannot provision anything from scratch.

2. This revision — so that a migration-based restore has the table too, and so
   the schema is described in the ledger rather than only in code.

## Idempotent, and it does not touch existing data

`CREATE TABLE IF NOT EXISTS` throughout, and the indexes/constraints are
created under `IF NOT EXISTS` guards too. Production already has this table
with 64 rows; re-running must be a no-op there and must never drop or rewrite
rows. `downgrade` deliberately does NOT drop the table — it only removes the
three indexes/constraint, because the application cannot run without the table
and a `DROP TABLE` in a rollback would destroy live catalog data.

## Schema is copied, not invented

Every column, type, default, constraint name and index name below was read off
the live production table (`\\d+ country_plan_types`), not guessed. That
matters for `cpt_unique` in particular: `routers/admin.py` upserts with a bare
`ON CONFLICT DO NOTHING`, which needs a unique constraint on
`(country_code, plan_type)` to resolve to.

Revision ID: 20261001_country_plan_types
Revises: 20261001_refund_gateway_evidence
Create Date: 2026-10-01 13:45:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20261001_country_plan_types"
down_revision = "20261001_refund_gateway_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS country_plan_types (
            id SERIAL PRIMARY KEY,
            country_code VARCHAR(2) NOT NULL,
            plan_type VARCHAR(20) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT false,
            price_per_ip NUMERIC(12, 2),
            price_per_gb NUMERIC(12, 2),
            provider_id INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            is_special BOOLEAN NOT NULL DEFAULT false,
            CONSTRAINT cpt_unique UNIQUE (country_code, plan_type)
        )
        """
    )
    # CREATE TABLE IF NOT EXISTS is a complete no-op when the table already
    # exists, so the constraints and indexes below are created independently.
    # `IF NOT EXISTS` makes re-running against production a no-op rather than
    # an error.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS cpt_unique "
        "ON country_plan_types (country_code, plan_type)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_cpt_enabled ON country_plan_types (enabled)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cpt_plan_type ON country_plan_types (plan_type)")


def downgrade() -> None:
    # Intentionally NOT `DROP TABLE`. Every catalog endpoint reads this table;
    # dropping it turns a rollback into an outage, and on production it would
    # destroy the 64 rows that define what is sellable. Remove only the
    # secondary indexes, and leave the table and its data in place.
    op.execute("DROP INDEX IF EXISTS idx_cpt_plan_type")
    op.execute("DROP INDEX IF EXISTS idx_cpt_enabled")