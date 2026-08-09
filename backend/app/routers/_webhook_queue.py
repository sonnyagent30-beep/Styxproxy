"""RQ webhook fulfillment queue for Styxproxy.

Enqueues slow work (credential creation, n8n webhook, auto-refund)
so the webhook endpoint returns 200 immediately without blocking.

Usage:
    from app.routers._webhook_queue import enqueue_fulfillment
    await enqueue_fulfillment(tx_ref, order_id, data_payload)
"""

import asyncio
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


async def enqueue_fulfillment(
    tx_ref: str,
    order_id: str,
    data_payload: dict,
) -> str:
    """
    Enqueue a fulfillment job for async processing.

    The webhook endpoint calls this to return 200 immediately.
    The RQ worker handles: create_credential + n8n webhook + auto-refund on failure.

    Args:
        tx_ref: Flutterwave transaction reference
        order_id: Internal order ID
        data_payload: Full webhook data dict

    Returns:
        job_id: The RQ job ID
    """
    job_id = f"fulfillment-{uuid.uuid4().hex[:12]}"

    # rq.Queue.enqueue() is sync — run in thread pool to avoid blocking the
    # async event loop. asyncio.to_thread() is available in Python 3.9+.
    def _do_enqueue():
        from rq import Queue
        from app.config import get_settings

        settings = get_settings()
        import redis as sync_redis
        conn = sync_redis.from_url(settings.redis_url, decode_responses=True)
        q = Queue("fulfillment", connection=conn)

        job = q.enqueue(
            "app.scripts.fulfillment_worker.fulfill_order_job",
            job_id=job_id,
            tx_ref=tx_ref,
            order_id=order_id,
            data_payload=data_payload,
            job_timeout=300,   # 5 min max
            result_ttl=86400,  # keep result 24h
        )
        return job.id

    try:
        result_job_id = await asyncio.to_thread(_do_enqueue)
        logger.info(
            "enqueued fulfillment job",
            job_id=result_job_id,
            tx_ref=tx_ref,
            order_id=order_id,
        )
        return result_job_id
    except Exception as exc:
        # Queue unavailable — let caller fall back to inline processing
        logger.warning(f"RQ enqueue failed: {exc}")
        raise
