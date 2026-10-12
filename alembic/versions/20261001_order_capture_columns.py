"""Add a real payment-capture record to orders (gate item 2, t_c0b38088).

## Why

`orders.amount_paid_ngn` is an INVOICE amount, written when the order is
raised and populated on 100% of rows — including all 46 `refunded`, 54
`cancelled` and 110 `expired` production rows. It is never evidence that money
arrived. Until now the schema had NO column recording capture at all, so "did
this customer actually pay?" was unanswerable from our own database and
required a per-transaction gateway call — which is what makes bulk
reconciliation impractical.

## What this adds

    captured_at         timestamptz   when money actually arrived (NULL on pending)
    gateway_status      varchar(20)   pending / success / failed / refunded
    gateway_amount_ngn  numeric(12,2) amount the GATEWAY charged, in naira
    gateway_currency    varchar(3)    ISO code as the gateway reported it
    gateway_reference   varchar(100)  the reference the gateway itself echoed
    gateway_refund_id   varchar(100)  the gateway's refund id (gate item 3,
                                       card t_f765263b — carried here so the
                                       two cards do not produce conflicting
                                       migrations for the same table)

## Deliberately NOT backfilled

Every new column is nullable and is left NULL on all 238 existing rows. We do
not know what any of those orders actually captured: 46 `refunded` rows were
administrative status flips that never called the gateway, and all 19
`fulfilled` plus all 8 `active` rows have provider=NULL, meaning they were
written by hand or by test rather than by a webhook. Deriving a capture
value for them would be fabrication, and a fabricated capture record is worse
than a null one because it reads as evidence.

Affected historical rows are therefore correctly reported as "capture unknown"
by `app/services/capture.py::was_captured()`. That is the honest answer.

Revision ID: 20261001_order_capture_columns
Revises: 20260827_charon_conversations
Create Date: 2026-10-01 10:30:00.000000
"""

from alembic import op

# revision identifiers
revision = "20261001_order_capture_columns"
down_revision = "20260827_charon_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS throughout: app/main.py's lifespan runs the same additive
    # ALTERs on every boot (for deployments where alembic has not been run), so
    # a re-run of this migration must not explode on an existing column.
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS captured_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_status VARCHAR(20)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_amount_ngn NUMERIC(12, 2)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_currency VARCHAR(3)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_reference VARCHAR(100)")
    # Gate item 3 (t_f765263b). No CHECK constraint: the gateway vocabulary is
    # enforced in app/services/capture.py, which rejects unknown values at the
    # single write path rather than letting an out-of-vocabulary string land in
    # the DB via a direct SQL write and silently break "was money captured?".
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_refund_id VARCHAR(100)")

    # captured_at and gateway_status are the two columns reconciliation queries
    # filter and sort on ("what did we take in this period", "which orders are
    # unconfirmed"), so they get indexes. IF NOT EXISTS for the same reason as
    # the ALTERs above: this repo's convention is that every schema addition is
    # safely re-runnable.
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_captured_at ON orders (captured_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_gateway_status ON orders (gateway_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_gateway_refund_id ON orders (gateway_refund_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_orders_gateway_refund_id")
    op.execute("DROP INDEX IF EXISTS ix_orders_gateway_status")
    op.execute("DROP INDEX IF EXISTS ix_orders_captured_at")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_refund_id")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_reference")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_currency")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_amount_ngn")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_status")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS captured_at")
