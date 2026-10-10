#!/usr/bin/env python3
"""
Data usage refresh cron — runs every 15 minutes via systemd timer.

Polls data_remaining_gb for active residential/mobile orders from the
provider API and writes the value into orders.data_remaining_gb.

DC/ISP orders are skipped — they are per-IP products with no data cap.

If the provider API is unreachable or returns no value, the field is
set to NULL (unknown) — never a silent fallback number.

Schedule: every 15 minutes (OnUnitActiveSec=15min)
API budget: ~100 credentials × 1 call each = ~100 calls per run.
  At 15-min intervals = ~400 calls/hour = ~9,600 calls/day.
  Well within DataImpulse/Decodo rate limits (typically 100+ req/min).
"""
import asyncio
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data-usage-refresh")

# Plan types that have data caps (residential/mobile are per-GB)
DATA_PLAN_TYPES = {"residential", "mobile"}


async def refresh_data_usage():
    """Poll data_remaining_gb for active residential/mobile orders."""
    import sys
    sys.path.insert(0, "/opt/styxproxy/backend")

    from sqlalchemy import text
    from app.database import async_session as AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Find active orders that are residential/mobile
        result = await db.execute(
            text("""
                SELECT o.order_id, o.plan_type, o.data_remaining_gb,
                       c.provider_order_id, c.provider_name
                FROM orders o
                JOIN styxproxy_credentials c ON c.id = o.styxproxy_credential_id
                WHERE o.status IN ('fulfilled', 'active', 'fulfilling')
                  AND o.plan_type IN ('residential', 'mobile')
                  AND c.provider_order_id IS NOT NULL
                  AND c.provider_order_id != ''
                ORDER BY o.created_at DESC
                LIMIT 200
            """)
        )
        orders = result.fetchall()

        if not orders:
            logger.info("No active residential/mobile orders to refresh")
            return {"refreshed": 0, "failed": 0, "skipped": 0}

        logger.info("Found %d active residential/mobile orders to refresh", len(orders))

        refreshed = 0
        failed = 0
        skipped = 0

        for order in orders:
            order_id = order[0]
            plan_type = order[1]
            provider_order_id = order[3]
            provider_name = order[4]

            if not provider_order_id:
                skipped += 1
                continue

            try:
                # Poll the provider for current data_remaining_gb
                remaining_gb = await _poll_provider_data_remaining(
                    provider_name, provider_order_id
                )

                if remaining_gb is not None:
                    await db.execute(
                        text("""
                            UPDATE orders
                            SET data_remaining_gb = :remaining_gb
                            WHERE order_id = :order_id
                        """),
                        {"remaining_gb": remaining_gb, "order_id": order_id},
                    )
                    refreshed += 1
                    logger.debug(
                        "Order %s: data_remaining_gb = %s GB",
                        order_id,
                        remaining_gb,
                    )
                else:
                    # Provider returned no value — set to NULL (unknown)
                    await db.execute(
                        text("""
                            UPDATE orders
                            SET data_remaining_gb = NULL
                            WHERE order_id = :order_id
                        """),
                        {"order_id": order_id},
                    )
                    failed += 1
                    logger.warning(
                        "Order %s: provider returned no data_remaining_gb — set to NULL",
                        order_id,
                    )

            except Exception as e:
                failed += 1
                logger.error("Order %s: refresh failed: %s", order_id, e)

        await db.commit()
        logger.info(
            "Data usage refresh complete: %d refreshed, %d failed, %d skipped",
            refreshed,
            failed,
            skipped,
        )
        return {"refreshed": refreshed, "failed": failed, "skipped": skipped}


async def _poll_provider_data_remaining(
    provider_name: str, provider_order_id: str
) -> float | None:
    """Poll a single provider for data_remaining_gb.

    Returns the value in GB, or None if the provider has no data.
    """
    # In simulator mode, poll the simulator API
    if provider_name in ("proxy-seller", "simulator") or provider_order_id.startswith("SIM-"):
        return await _poll_simulator_data(provider_order_id)

    # Real provider polling would go here
    # For now, return None (unknown) for real providers
    # TODO: Implement DataImpulse/Decodo data polling when APIs are connected
    logger.debug(
        "No provider polling implemented for %s/%s — returning None",
        provider_name,
        provider_order_id,
    )
    return None


async def _poll_simulator_data(provider_order_id: str) -> float | None:
    """Poll the simulator for current data_remaining_gb.

    The simulator tracks data usage in its SQLite DB and returns
    a decreasing value based on elapsed time since order creation.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"http://127.0.0.1:8001/api/provider/credentials/{provider_order_id}"
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data_remaining_gb")
    except Exception as e:
        logger.warning("Simulator poll failed for %s: %s", provider_order_id, e)
    return None


if __name__ == "__main__":
    result = asyncio.run(refresh_data_usage())
    print(result)
