"""
Data Usage Refresh Service

Polls the provider simulator for data_remaining_gb on active residential/mobile
orders and writes the value to orders.data_remaining_gb.

This is the scheduled refresh that keeps the "GB remaining" display honest.
Before this service, data_remaining_gb was written once at order creation and
never updated — customers saw a number that never moved.

Schedule: every 15 minutes via cron
API budget: 1 request per active residential/mobile order per run
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure the app package is importable
sys.path.insert(0, "/opt/styxproxy/backend")

# Load env from /opt/styxproxy/.env (same as api)
_env_path = "/opt/styxproxy/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#"):
                continue
            if "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ[_key.strip()] = _val.strip()

from app.config import get_settings
from app.database import async_session as AsyncSessionLocal
from app.models import Order

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("data_usage_refresh")

# Provider simulator base URL
SIMULATOR_BASE_URL = os.getenv("SIMULATOR_BASE_URL", "http://127.0.0.1:8001")

# Maximum number of orders to refresh per run (safety cap)
MAX_ORDERS_PER_RUN = int(os.getenv("DATA_REFRESH_MAX_ORDERS", "100"))

# Timeout for each provider API call
API_TIMEOUT = float(os.getenv("DATA_REFRESH_TIMEOUT", "10"))


async def _fetch_data_remaining(provider_order_id: str) -> Optional[float]:
    """Fetch data_remaining_gb from the provider simulator.

    Returns None if the provider is unreachable or the order is not found.
    """
    url = f"{SIMULATOR_BASE_URL}/api/provider/data_remaining/{provider_order_id}"
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                remaining = data.get("data_remaining_gb")
                if remaining is not None:
                    return float(remaining)
            elif resp.status_code == 404:
                logger.warning(
                    "Order %s not found on provider — skipping", provider_order_id
                )
            else:
                logger.warning(
                    "Provider returned %d for order %s",
                    resp.status_code,
                    provider_order_id,
                )
    except httpx.TimeoutException:
        logger.warning(
            "Timeout fetching data for order %s", provider_order_id
        )
    except Exception as e:
        logger.warning(
            "Error fetching data for order %s: %s", provider_order_id, e
        )
    return None


async def refresh_data_usage() -> dict:
    """Refresh data_remaining_gb for all active residential/mobile orders.

    Returns a summary dict: {"refreshed": N, "skipped": M, "errors": K}
    """
    refreshed = 0
    skipped = 0
    errors = 0

    async with AsyncSessionLocal() as db:
        # Find active residential/mobile orders that have a provider_order_id
        stmt = (
            select(Order)
            .where(
                Order.status.in_(["active", "fulfilled"]),
                Order.plan_type.in_(["residential", "mobile"]),
                Order.provider_order_id.isnot(None),
            )
            .order_by(Order.created_at.desc())
            .limit(MAX_ORDERS_PER_RUN)
        )
        result = await db.execute(stmt)
        orders = result.scalars().all()

        logger.info(
            "Found %d active residential/mobile orders to refresh", len(orders)
        )

        for order in orders:
            try:
                remaining = await _fetch_data_remaining(order.provider_order_id)
                if remaining is not None:
                    # Update the order with the fresh value
                    await db.execute(
                        update(Order)
                        .where(Order.order_id == order.order_id)
                        .values(
                            data_remaining_gb=remaining,
                            data_expires=order.data_expires,  # keep existing expiry
                        )
                    )
                    refreshed += 1
                    logger.debug(
                        "Order %s: data_remaining_gb=%.2f GB",
                        order.order_id,
                        remaining,
                    )
                else:
                    skipped += 1
                    logger.debug(
                        "Order %s: no data from provider — skipping",
                        order.order_id,
                    )
            except Exception as e:
                errors += 1
                logger.error(
                    "Error refreshing order %s: %s", order.order_id, e
                )

        await db.commit()

    summary = {"refreshed": refreshed, "skipped": skipped, "errors": errors}
    logger.info(
        "Data usage refresh complete — refreshed=%d skipped=%d errors=%d",
        refreshed,
        skipped,
        errors,
    )
    return summary


async def main():
    logger.info("Starting data usage refresh run")
    summary = await refresh_data_usage()
    logger.info("Run complete: %s", summary)


if __name__ == "__main__":
    asyncio.run(main())
