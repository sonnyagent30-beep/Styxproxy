"""Refund retry cron — runs every 15 minutes via systemd timer.

Picks up orders stuck in 'failed_unfulfilled' and retries the Flutterwave refund.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("refund-retry-cron")

async def retry_failed_refunds():
    """Retry refunds for orders stuck in failed_unfulfilled."""
    import sys
    sys.path.insert(0, "/opt/styxproxy/backend")
    
    from sqlalchemy import text
    from app.database import async_session as AsyncSessionLocal
    from app.config import get_settings
    
    settings = get_settings()
    
    async with AsyncSessionLocal() as db:
        # Find orders stuck in failed_unfulfilled for more than 5 minutes
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = await db.execute(
            text("""
                SELECT order_id, payment_reference, amount_paid_ngn, customer_phone
                FROM orders 
                WHERE status = 'failed_unfulfilled'
                AND created_at < :cutoff
                LIMIT 10
            """),
            {"cutoff": cutoff}
        )
        stuck_orders = result.fetchall()
        
        if not stuck_orders:
            logger.debug("No stuck refunds to retry")
            return
        
        from app.services.flutterwave import _flutterwave_refund
        
        for order_id, tx_ref, amount, phone in stuck_orders:
            try:
                logger.info(f"Retrying refund for order {order_id}, tx_ref={tx_ref}")
                await _flutterwave_refund(tx_ref, float(amount), settings.flutterwave_secret_key)
                
                # Mark as refunded
                await db.execute(
                    text("""
                        UPDATE orders 
                        SET status = 'refunded', 
                            refund_requested = true,
                            refund_reason = 'Auto-refund: retry cron success'
                        WHERE order_id = :order_id
                    """),
                    {"order_id": order_id}
                )
                await db.commit()
                logger.info(f"Refund retry succeeded for {order_id}")
            except Exception as e:
                logger.error(f"Refund retry failed for {order_id}: {e}")
                await db.rollback()

if __name__ == "__main__":
    asyncio.run(retry_failed_refunds())
