"""Order expiry cron — runs every 5 minutes via systemd timer.

Expires pending orders older than 30 minutes.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order-expiry-cron")

async def expire_old_orders():
    """Mark pending orders older than 30 minutes as expired."""
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
                RETURNING order_id
            """),
            {"cutoff": cutoff}
        )
        expired = result.fetchall()
        await db.commit()
        
        if expired:
            logger.info(f"Expired {len(expired)} pending orders: {[r[0] for r in expired]}")
        else:
            logger.debug("No pending orders to expire")

if __name__ == "__main__":
    asyncio.run(expire_old_orders())
