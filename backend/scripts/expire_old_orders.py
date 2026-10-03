"""Order expiry cron — runs every 5 minutes via systemd timer.

Expires PENDING orders older than 30 minutes.

Pending: the customer never paid — safe to expire, nothing was charged.

Paid orders are NEVER touched by this cron. A `paid` order whose fulfilment is
stuck is a customer who WAS charged and has not received a credential. This job
used to run `WHERE status IN ('pending','paid')` and converted exactly those
orders into terminal `expired`, after which the webhook handler rejects every
retry with 400 "Order has expired" — the payment could never be completed and
the customer could never be fulfilled. Expiry is for abandoned checkouts, not
for failures in our own fulfilment path.

Stuck paid orders are surfaced instead of killed: they are logged and counted
so they can be re-queued (or handled manually), and they remain recoverable.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order-expiry-cron")

# A paid order older than this with no credential is stuck and needs attention.
STUCK_PAID_ALERT_MINUTES = 60


async def expire_old_orders():
    """Mark pending orders older than 30 minutes as expired.

    Paid orders are never modified. Stuck paid orders are reported for
    re-queue/manual review so they stay recoverable.
    """
    import sys
    sys.path.insert(0, "/opt/styxproxy/backend")

    from sqlalchemy import text
    from app.database import async_session as AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = await db.execute(
            text("""
                UPDATE orders
                SET status = 'expired'
                WHERE status = 'pending'
                AND created_at < :cutoff
                RETURNING order_id, status
            """),
            {"cutoff": cutoff}
        )
        expired = result.fetchall()
        await db.commit()

        if expired:
            logger.info(f"Expired {len(expired)} orders: {[(r[0], r[1]) for r in expired]}")
        else:
            logger.debug("No orders to expire")

        # ── Report stuck paid orders — NEVER expire them ────────────────────
        # These are charged customers with no credential. They must stay
        # actionable so a webhook retry or a manual re-queue can complete them.
        stuck_cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_PAID_ALERT_MINUTES)
        stuck = (await db.execute(
            text("""
                SELECT order_id, payment_reference, created_at
                FROM orders
                WHERE status = 'paid'
                AND created_at < :cutoff
                ORDER BY created_at
            """),
            {"cutoff": stuck_cutoff}
        )).fetchall()

        if stuck:
            logger.error(
                "STUCK PAID ORDERS (%d) — charged but not fulfilled. "
                "Left recoverable on purpose; re-queue fulfilment. ids=%s",
                len(stuck),
                [r[0] for r in stuck],
            )
        else:
            logger.debug("No stuck paid orders")


if __name__ == "__main__":
    asyncio.run(expire_old_orders())
