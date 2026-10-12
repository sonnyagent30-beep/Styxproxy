"""Order expiry cron — runs every 5 minutes via systemd timer.

Two jobs:
1. Expire PENDING orders older than 30 minutes (unpaid, safe to expire).
2. Expire credentials on PAID orders whose expires_at has passed.

Paid orders are NEVER marked expired by this cron — only their credentials
are. A paid order whose fulfillment is stuck must remain recoverable
(re-queue or manual review), not be converted to a terminal 'expired'
state that blocks webhook retries.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order-expiry-cron")

async def expire_old_orders():
    """Expire old pending orders and enforce credential expiry on paid orders."""
    import sys
    sys.path.insert(0, "/opt/styxproxy/backend")

    from sqlalchemy import text
    from app.database import async_session as AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # ── Job 1: Expire pending orders older than 30 minutes ──
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
            logger.info(f"Expired {len(expired)} pending orders: {[(r[0], r[1]) for r in expired]}")
        else:
            logger.debug("No pending orders to expire")

        # ── Job 2: Expire credentials on paid orders past their expires_at ──
        now = datetime.now(timezone.utc)
        result2 = await db.execute(
            text("""
                UPDATE styxproxy_credentials
                SET status = 'expired'
                WHERE status = 'active'
                AND expires_at IS NOT NULL
                AND expires_at < :now
                RETURNING id, styxproxy_username, order_id
            """),
            {"now": now}
        )
        expired_creds = result2.fetchall()
        await db.commit()

        if expired_creds:
            logger.info(f"Expired {len(expired_creds)} credentials: {[(r[0], r[1], r[2]) for r in expired_creds]}")
        else:
            logger.debug("No credentials to expire")

if __name__ == "__main__":
    asyncio.run(expire_old_orders())
