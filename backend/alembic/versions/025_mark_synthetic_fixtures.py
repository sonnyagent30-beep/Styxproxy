"""Mark the 6 synthetic-phone fixture orders as is_test_data = true.

Revision ID: 025_mark_synthetic_fixtures
Revises: 024_orders_is_test_data
Create Date: 2026-10-01

WHY THIS IS ENUMERATED BY ID AND NOT DERIVED BY A PREDICATE
-------------------------------------------------------------
024 added the ``is_test_data`` column and deliberately shipped no backfill,
because the real-vs-fixture predicate proposed on t_9abad0e6 selects 0 of 238
rows against production data (it names a ``reference`` column that does not
exist on ``orders``, and its email clause NULL-propagates away 180 of 238 rows).

This migration therefore does NOT re-derive fixture membership. It marks an
explicit, human-adjudicated list of exactly 6 ``order_id`` values, confirmed by
a human (Manager, 2026-10-01) as unambiguously synthetic:

    ORD-8KUELV      ord_273ee9b3f9ba
    ORD-RSC0GX      ord_25ca80691b9f
    ord_586c3b03426d  ord_7f1b655633be

All 6 were created 2026-07-30 with masked phone values (``+234****0002`` /
``+234****0003``) and NULL ``customer_email``.

Enumerating IDs rather than matching on phone shape is deliberate. A predicate
here would silently re-mark every future order placed on a synthetic-looking
number — which is the same class of confidently-wrong denominator this column
exists to prevent, just pointed the other way.

SCOPE — WHAT IS DELIBERATELY NOT MARKED
---------------------------------------
* The 232 ``+anon*@styxproxy.local`` orders are NOT marked. ``customer.py``
  mints that address for the legitimate anonymous-checkout path (customers who
  never give a phone). They hold 69 ``tx_ref``s and 26 fulfilled credentials.
  Marking them ``true`` would hide every anonymous real customer.
* No row is ever set to ``is_test_data = false``. Absence of evidence is not
  evidence of a real customer. Per Manager ruling, ``false`` is only ever
  written when a human has positively adjudicated a specific order.
* The remaining 232 rows stay NULL, which is the truthful state: unclassified.

RESULTING SPLIT ON PRODUCTION (238 orders)
------------------------------------------
    fixture (TRUE)          6
    known real (FALSE)      0     <- by design, never written without evidence
    unclassified (NULL)   232

Safe to run more than once: the UPDATE is idempotent.
"""

from alembic import op

# revision identifiers
revision = "025_mark_synthetic_fixtures"
down_revision = "024_orders_is_test_data"
branch_labels = None
depends_on = None

# Human-adjudicated list. Do NOT convert this to a predicate.
SYNTHETIC_ORDER_IDS = (
    "ORD-8KUELV",
    "ORD-RSC0GX",
    "ord_25ca80691b9f",
    "ord_273ee9b3f9ba",
    "ord_586c3b03426d",
    "ord_7f1b655633be",
)

EXPECTED_COUNT = len(SYNTHETIC_ORDER_IDS)

# Named bind params, never string-interpolated values.
_ID_PARAMS = {f"id{i}": v for i, v in enumerate(SYNTHETIC_ORDER_IDS)}
_ID_LIST = "(" + ",".join(f":id{i}" for i in range(EXPECTED_COUNT)) + ")"


def upgrade() -> None:
    import sqlalchemy as sa

    bind = op.get_bind()

    # Guard first: if the table has drifted (rows deleted or IDs recycled),
    # stop loudly rather than silently marking fewer rows than the human
    # approved. A partial backfill is worse than none — it would leave the
    # table looking adjudicated when it is not.
    found = bind.execute(
        sa.text(f"SELECT count(*) FROM orders WHERE order_id IN {_ID_LIST}"),
        _ID_PARAMS,
    ).scalar()

    if found != EXPECTED_COUNT:
        raise RuntimeError(
            f"Refusing to backfill: expected {EXPECTED_COUNT} synthetic fixture "
            f"orders, found {found}. The approved list no longer matches the "
            f"table. Re-adjudicate the list before changing it."
        )

    bind.execute(
        sa.text(f"UPDATE orders SET is_test_data = TRUE WHERE order_id IN {_ID_LIST}"),
        _ID_PARAMS,
    )


def downgrade() -> None:
    import sqlalchemy as sa

    # Return these 6 to the unclassified state. Never set them to FALSE:
    # they were not adjudicated as real, they were unadjudicated.
    op.get_bind().execute(
        sa.text(f"UPDATE orders SET is_test_data = NULL WHERE order_id IN {_ID_LIST}"),
        _ID_PARAMS,
    )