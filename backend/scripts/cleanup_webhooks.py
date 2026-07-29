#!/usr/bin/env python3
"""Cleanup old processed_webhooks rows.

Theme C — preventive maintenance. Webhook payload data is only useful
for replay-debugging during the retention window. After 90 days the
duplicate-prevention protection is no longer needed (Stripe/PayPal will
have already sent the relevant notifications or the customer gave up).

Runs as a daily cron at 03:30 UTC (just after the daily pg_dump at 03:05
and the weekly pg_basebackup slot). Logs the deletion count to stderr
so the cron log captures it.

Safe to re-run: idempotent. Even if a deletion fails partway, the next
run will catch the remaining rows.

Safety: We DELETE (not TRUNCATE) and only the rows where processed_at
is older than 90 days. We never touch active webhooks.

Exit codes:
  0 — cleanup ran (even if no rows matched)
  1 — DB unavailable, could not perform cleanup
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

# Add backend to path so we can import app.*
sys.path.insert(0, "/opt/styxproxy/backend")

# Load env from /opt/styxproxy/.env (same as api)
_env_path = "/opt/styxproxy/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

from sqlalchemy import delete, func, select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import ProcessedWebhook  # noqa: E402

RETENTION_DAYS = 90


async def main() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    try:
        async with async_session() as session:
            # Count before delete (so we can log it without relying on rowcount)
            count_stmt = select(func.count()).select_from(ProcessedWebhook).where(
                ProcessedWebhook.processed_at < cutoff
            )
            count = (await session.execute(count_stmt)).scalar() or 0

            if count == 0:
                print(
                    f"[{datetime.now(timezone.utc).isoformat()}] "
                    f"no rows older than {cutoff.isoformat()} — skipping",
                    file=sys.stderr,
                )
                return 0

            # Delete only the old rows
            stmt = delete(ProcessedWebhook).where(ProcessedWebhook.processed_at < cutoff)
            result = await session.execute(stmt)
            await session.commit()
            deleted = result.rowcount

        print(
            f"[{datetime.now(timezone.utc).isoformat()}] "
            f"deleted {deleted} processed_webhooks rows older than {cutoff.isoformat()}",
            file=sys.stderr,
        )
        return 0
    except Exception as e:
        print(f"FAIL: cleanup error: {e}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
