#!/usr/bin/env python3
"""Reconciliation sweep for stuck pending orders.

Finds orders with status 'pending' older than 15 minutes, verifies payment
with Flutterwave, and if confirmed, marks as 'paid' and enqueues fulfillment.

This is the safety net for when a Flutterwave webhook fails signature
verification AND the gateway-verify fallback also fails (503 ~30% of the time).

Usage:
    python3 reconcile_pending_payments.py [--dry-run]

    --dry-run  Report what would be reconciled without mutating any orders.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/opt/styxproxy/backend")

from app.database import async_session as AsyncSessionLocal
from app.services.flutterwave import verify_flutterwave_payment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("reconcile-pending-payments")

# Only sweep orders older than this (past webhook delivery window)
PENDING_ORDER_MAX_AGE_MINUTES = 15

# Retry logic for Flutterwave verification
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds


async def verify_with_retry(tx_ref: str) -> dict | None:
    """Call verify_flutterwave_payment with retries on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await verify_flutterwave_payment(tx_ref)
            return result
        except Exception as e:
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_BASE ** attempt  # 2, 4, 8 seconds
                logger.warning(
                    f"Flutterwave verification attempt {attempt} failed for {tx_ref}: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Flutterwave verification failed after {MAX_RETRIES} attempts for {tx_ref}: {e}"
                )
                return None


async def reconcile_pending_payments(dry_run: bool = False) -> None:
    """Find stuck pending orders and reconcile them with Flutterwave."""
    from sqlalchemy import select, and_, update
    from app.models import Order
    from app.services.audit import log_audit_event

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=PENDING_ORDER_MAX_AGE_MINUTES)

    async with AsyncSessionLocal() as db:
        # Find pending orders older than the cutoff that have a payment_reference
        result = await db.execute(
            select(Order).where(
                and_(
                    Order.status == "pending",
                    Order.created_at < cutoff,
                    Order.payment_reference.isnot(None),
                )
            )
        )
        orders = result.scalars().all()

        if not orders:
            logger.info("No pending orders found for reconciliation")
            return

        logger.info(f"Found {len(orders)} pending orders to reconcile")
        if dry_run:
            logger.info("DRY-RUN MODE — no orders will be mutated")

        stats = {
            "verified_paid": 0,
            "verified_not_paid": 0,
            "verification_failed": 0,
            "enqueue_failed": 0,
            "skipped_race": 0,
        }

        for order in orders:
            tx_ref = order.payment_reference
            logger.info(f"Reconciling order {order.order_id} (tx_ref={tx_ref})")

            # Verify payment with Flutterwave (with retries)
            verification = await verify_with_retry(tx_ref)

            if verification is None:
                logger.warning(f"  -> Verification failed for {tx_ref}")
                stats["verification_failed"] += 1
                continue

            status = verification.get("status", "").lower()

            if status != "successful":
                logger.info(f"  -> Payment not successful: status={status}")
                stats["verified_not_paid"] += 1
                continue

            # Payment confirmed
            logger.info(f"  -> Payment confirmed! Amount={verification.get('amount')}")

            if dry_run:
                logger.info(
                    f"  [DRY-RUN] Would mark order {order.order_id} as paid "
                    f"and enqueue fulfillment"
                )
                stats["verified_paid"] += 1
                continue

            # Conditional status transition — the race guard.
            #
            # Instead of order.status = "paid"; await db.commit(), we use
            # UPDATE ... WHERE status="pending". This is atomic: exactly one
            # writer (this sweep or a concurrent webhook) can win the
            # transition. If rowcount is 0, someone else already transitioned
            # this order and we must NOT enqueue fulfillment.
            update_result = await db.execute(
                update(Order)
                .where(
                    Order.order_id == order.order_id,
                    Order.status == "pending",
                )
                .values(
                    status="paid",
                    amount_paid_ngn=verification.get("amount"),
                )
            )
            await db.commit()

            if update_result.rowcount == 0:
                logger.info(
                    f"  -> Order {order.order_id} already transitioned "
                    f"(concurrent webhook won) — skipping fulfilment enqueue"
                )
                stats["skipped_race"] += 1
                continue

            logger.info(f"  -> Order {order.order_id} marked as paid")

            # Enqueue fulfillment
            try:
                from app.routers._webhook_queue import enqueue_fulfillment

                payload = {
                    "event": "charge.completed",
                    "data": verification,
                }
                job_id = await enqueue_fulfillment(tx_ref, order.order_id, payload)
                logger.info(f"  -> Fulfillment enqueued: job_id={job_id}")
                stats["verified_paid"] += 1

                await log_audit_event(
                    db,
                    event_type="reconciliation_payment_confirmed",
                    phone=order.customer_phone,
                    order_id=order.order_id,
                    details={
                        "tx_ref": tx_ref,
                        "job_id": job_id,
                        "amount": verification.get("amount"),
                        "source": "reconciliation_sweep",
                    },
                )
            except Exception as e:
                logger.error(f"  -> Failed to enqueue fulfillment for {tx_ref}: {e}")
                stats["enqueue_failed"] += 1
                await log_audit_event(
                    db,
                    event_type="reconciliation_enqueue_failed",
                    phone=order.customer_phone,
                    order_id=order.order_id,
                    details={
                        "tx_ref": tx_ref,
                        "error": str(e),
                        "source": "reconciliation_sweep",
                    },
                )

        # Print summary
        logger.info("=" * 60)
        logger.info("RECONCILIATION SUMMARY")
        logger.info(f"  Total pending orders checked: {len(orders)}")
        logger.info(f"  Verified paid & fulfilled:     {stats['verified_paid']}")
        logger.info(f"  Verified not paid:             {stats['verified_not_paid']}")
        logger.info(f"  Verification failed:           {stats['verification_failed']}")
        logger.info(f"  Enqueue failed:                {stats['enqueue_failed']}")
        logger.info(f"  Skipped (race guard):          {stats['skipped_race']}")
        if dry_run:
            logger.info("  *** DRY-RUN — no changes were made ***")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Reconcile stuck pending orders with Flutterwave"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be reconciled without mutating any orders",
    )
    args = parser.parse_args()

    asyncio.run(reconcile_pending_payments(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
