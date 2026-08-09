#!/usr/bin/env python3
"""Data retention: purge old analytics, health, webhooks, charon context."""

import os, sys, logging
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["JWT_SECRET"] = "retention-job"
os.environ["ADMIN_TOKEN"] = "retention-job"
os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://styxproxy_app:Ku3xHibr3qjcbGNSmQ5ZOAwNViCbm4lO@127.0.0.1:5432/styxproxy",
)

from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("retention")

# table: (retention_days, date_column)
RETENTION = [
    ("analytics_events", 30, "created_at"),
    ("health_snapshots", 30, "created_at"),
    ("charon_context", 7, "received_at"),
    ("charon_blog_chunks", 180, "created_at"),
    ("charon_ab_assignments", 90, "assigned_at"),
    ("charon_ab_outcomes", 90, "created_at"),
    ("charon_escalations", 90, "created_at"),
    ("processed_webhooks", 30, "processed_at"),
    ("idempotency_responses", 7, "created_at"),
]


async def purge_table(table: str, days: int, date_col: str) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"DELETE FROM {table} WHERE {date_col} < :cutoff"),
            {"cutoff": cutoff}
        )
    return result.rowcount


async def run():
    log.info("Starting data retention purge")
    total = 0
    for table, days, col in RETENTION:
        try:
            n = await purge_table(table, days, col)
            if n > 0:
                log.info(f"  Purged {n} rows from {table} (>{days} days)")
                total += n
            else:
                log.info(f"  {table}: nothing to purge")
        except Exception as e:
            log.error(f"  Error purging {table}: {e}")
    log.info(f"Retention complete. Total rows purged: {total}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
