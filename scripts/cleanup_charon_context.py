#!/usr/bin/env python3
"""Cleanup expired CharonContext rows.

Theme C — Charon's per-conversation rolling summary is only useful for
the in-flight 24h window. After expires_at, the row is dead weight and
the agent should start fresh anyway. Daily cleanup at 04:00 UTC keeps
the table small and the agent's context-bundle-loader fast.

Runs as a daily cron. Logs deletions to stderr.

Safe to re-run: idempotent. The DELETE filter is on expires_at, so
already-deleted rows do nothing.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

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
from app.models import CharonContext  # noqa: E402


async def main() -> int:
    now = datetime.now(timezone.utc)

    try:
        async with async_session() as session:
            # Count first so we can log without relying on rowcount
            count_stmt = select(func.count()).select_from(CharonContext).where(
                CharonContext.expires_at < now
            )
            count = (await session.execute(count_stmt)).scalar() or 0

            if count == 0:
                print(
                    f"[{now.isoformat()}] no expired rows — skipping",
                    file=sys.stderr,
                )
                return 0

            stmt = delete(CharonContext).where(CharonContext.expires_at < now)
            result = await session.execute(stmt)
            await session.commit()
            deleted = result.rowcount

        print(
            f"[{now.isoformat()}] deleted {deleted} charon_context rows older than {now.isoformat()}",
            file=sys.stderr,
        )
        return 0
    except Exception as e:
        print(f"FAIL: cleanup error: {e}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
