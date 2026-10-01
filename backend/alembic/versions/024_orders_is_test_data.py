"""Add orders.is_test_data — decidable real-vs-fixture marker.

Revision ID: 024_orders_is_test_data
Revises: 20260827_charon_conversations
Create Date: 2026-10-01

WHY THIS COLUMN IS NULLABLE, NOT ``NOT NULL DEFAULT false``
-----------------------------------------------------------
The obvious design is ``is_test_data boolean NOT NULL DEFAULT false``. That
design is wrong here, and wrong in exactly the way this column exists to fix.

With ``DEFAULT false``, every one of the 238 pre-existing rows silently becomes
``is_test_data = false`` — i.e. every historical row asserts "this is a real
customer order" — with no migration step having classified anything. QA then
writes ``WHERE is_test_data = false``, gets 238, and reports 238 real customers.
That is the same class of error as the one this column was created to stop: a
filter that looks authoritative and is answering a question nobody asked it.

So this column is deliberately nullable and NO backfill ships with it:

    is_test_data IS TRUE   -> known fixture / seeded / test row
    is_test_data IS FALSE  -> known real customer order
    is_test_data IS NULL   -> NOT YET CLASSIFIED

``NULL`` is the honest state for rows nobody has adjudicated. It makes
``COUNT(*) WHERE is_test_data IS NULL`` the standing "how much of the table is
still undecided" number, so the gap is visible instead of invisible.

Anyone writing an assertion MUST therefore filter explicitly. The safe idiom is
``WHERE is_test_data IS FALSE`` (counts only adjudicated-real rows).

Note on why, because the obvious explanation is wrong: ``NOT is_test_data`` does
NOT "sweep the NULLs in". SQL three-valued logic means ``NOT NULL`` evaluates to
NULL, and a NULL is not TRUE, so the row is EXCLUDED — the same rows as
``IS FALSE``. Verified on PostgreSQL 16 with all three states present:
``count(*) FILTER (WHERE NOT is_test_data)`` and
``count(*) FILTER (WHERE is_test_data IS FALSE)`` both returned 1, with 1 NULL
row excluded by both. So the two forms agree numerically here.

``IS FALSE`` is still the form to mandate, but for the defensible reasons:
it states the intent ("adjudicated real") instead of relying on three-valued
logic to do the right thing by accident, and it keeps meaning if a future
change ever gives the column a default or a fourth state. Write it explicitly
rather than trusting ``NOT`` to be safe.

Adding the column with no default also leaves the 238 existing rows untouched:
additive only, no rewrite of existing data, safe to run while other migrations
are in flight.

BACKFILL IS DELIBERATELY ABSENT
-------------------------------
The real-vs-fixture predicate proposed on t_9abad0e6 does not work against
production data — it selects 0 of 238 rows. See that card's comment thread for
the measured breakdown. Backfilling from a predicate that classifies nothing
would mark every row ``false`` and reintroduce the exact "confidently wrong
denominator" failure. Classification waits on a predicate verified against prod.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "024_orders_is_test_data"
down_revision = "20260827_charon_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, and deliberately WITHOUT server_default. See module docstring:
    # a default would classify all existing rows as "real" without evidence.
    op.add_column(
        "orders",
        sa.Column("is_test_data", sa.Boolean(), nullable=True),
    )

    # Partial index: the hot query is "adjudicated fixtures" and
    # "still unclassified". Both are sparse predicates over a boolean, where a
    # full btree on the raw column is nearly useless (it would index every
    # row's NULL and every false alike).
    op.create_index(
        "idx_orders_is_test_data_true",
        "orders",
        ["is_test_data"],
        postgresql_where=sa.text("is_test_data IS TRUE"),
    )
    op.create_index(
        "idx_orders_is_test_data_null",
        "orders",
        ["is_test_data"],
        postgresql_where=sa.text("is_test_data IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_orders_is_test_data_null", table_name="orders")
    op.drop_index("idx_orders_is_test_data_true", table_name="orders")
    op.drop_column("orders", "is_test_data")
