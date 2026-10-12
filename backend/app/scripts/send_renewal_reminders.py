#!/usr/bin/env python3
"""S2.5 — Daily renewal reminder cron job.

Usage:
    python -m app.scripts.send_renewal_reminders

Run daily via cron or the Hermes cron system. Reads DATABASE_URL from
environment (defaults to the docker-compose value for local dev).

Each run scans all active orders expiring within 3 days and sends a
renewal reminder email to the customer if one has not already been sent today.
"""

import asyncio
import logging
import os
import sys

# Ensure the app package is importable (backend/ on the PYTHONPATH)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.database import get_session_context
from app.services.renewal import send_daily_renewal_reminders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("renewal_cron")


async def main() -> None:
    logger.info("Starting daily renewal reminder run")

    async with get_session_context() as session:
        summary = await send_daily_renewal_reminders(session)

    logger.info(
        "Daily renewal reminder run complete — sent=%d, skipped=%d, errors=%d",
        summary["sent"],
        summary["skipped"],
        summary["errors"],
    )


if __name__ == "__main__":
    asyncio.run(main())
