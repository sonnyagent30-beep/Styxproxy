"""Add gateway refund EVIDENCE columns to orders (gate item 3, t_f765263b).

An admin refund used to flip `status='refunded'`, revoke the credential and
email the customer WITHOUT calling a gateway, so the customer was told their
money came back when it did not. All 46 legacy `refunded` rows are
administrative flips: every one carries a payment_reference but a NULL
tx_ref, i.e. the gateway was never consulted.

## Why this migration does NOT add gateway_refund_id

It is added here instead:

    20261001_order_capture_columns   (gate item 2, t_c0b38088)

That card landed the capture record (captured_at / gateway_status /
gateway_amount_ngn / gateway_currency / gateway_reference) and, by explicit
agreement on this thread, carried `gateway_refund_id` with it so the two cards
could not produce conflicting migrations for the same table. This file
therefore:

  * declares down_revision = "20261001_order_capture_columns", so the revision
    graph stays a single chain instead of forking a second alembic head off
    20260827_charon_conversations (two heads make `alembic upgrade head`
    refuse to run at all);
  * re-adds nothing for gateway_refund_id — not even idempotently. A second
    ADD COLUMN for a name another migration owns is exactly the collision that
    produced `ERROR: column "gateway_refund_id" of relation "orders" already
    exists`.

## What this adds

    gateway_refund_status   varchar(50)   status the gateway reported
    gateway_refund_amount   numeric(12,2) amount the gateway refunded, in naira
    gateway_refunded_at     timestamptz   when we recorded the confirmation

These complete the reconciliation handle: gateway_refund_id (item 2's column)
says WHICH refund, these say what the gateway said about it and when we heard.
Without them a refund row cannot answer "did the gateway confirm, for how much,
and when".

## Deliberately NOT backfilled

Additive, nullable, and no backfill, for the same reason as the capture columns:
for the 46 historical `refunded` rows we have no evidence any money was
refunded, so a fabricated value would be worse than NULL. A NULL
`gateway_refund_id` on a `refunded` row IS the finding — it marks an order
whose status was flipped administratively and whose real refund state is
unknown.

## Idempotency

IF NOT EXISTS throughout, matching item 2's style. app/main.py's lifespan runs
the same additive ALTERs on every boot (for deployments where alembic has not
been run), so this migration must be safely re-runnable.

Revision ID: 20261001_refund_gateway_evidence
Revises: 20261001_order_capture_columns
Create Date: 2026-10-01 11:05:00.000000
"""

from alembic import op

# revision identifiers
revision = "20261001_refund_gateway_evidence"
down_revision = "20261001_order_capture_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_refund_status VARCHAR(50)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_refund_amount NUMERIC(12, 2)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_refunded_at TIMESTAMP WITH TIME ZONE")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_refunded_at")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_refund_amount")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS gateway_refund_status")
