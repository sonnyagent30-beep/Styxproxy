"""Order expiry cron — runs every 5 minutes via systemd timer.

Expires PENDING orders older than 30 minutes.
Pending: customer never paid — safe to expire.

Paid orders are NEVER touched by this cron. A paid order whose fulfillment
is stuck must remain recoverable (re-queue or manual review), not be converted
to a terminal 'expired' state that blocks webhook retries.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order-expiry-cron")

async def expire_old_orders():
    """Mark pending orders older than 30 minutes as expired. Paid orders are never touched."""
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

if __name__ == "__main__":
    asyncio.run(expire_old_orders())
