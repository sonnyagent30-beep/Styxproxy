#!/usr/bin/env python3
"""Cleanup expired admin_totp_sessions.

Theme C — TOTP session tokens valid for 7 days by default. After
expires_at, the cookie no longer authenticates, so the row is dead
weight. Daily cleanup at 04:30 UTC keeps the table small.

Also deletes revoked sessions older than 30 days (audit trail only).
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/opt/styxproxy/backend")

_env_path = "/opt/styxproxy/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

from sqlalchemy import delete, func, or_, select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import AdminTotpSession  # noqa: E402


async def main() -> int:
    now = datetime.now(timezone.utc)
    revoked_cutoff = now - timedelta(days=30)

    try:
        async with async_session() as session:
            count_stmt = select(func.count()).select_from(AdminTotpSession).where(
                or_(
                    AdminTotpSession.expires_at < now,
                    (AdminTotpSession.revoked_at.is_not(None))
                    & (AdminTotpSession.revoked_at < revoked_cutoff),
                )
            )
            count = (await session.execute(count_stmt)).scalar() or 0

            if count == 0:
                print(f"[{now.isoformat()}] no expired/revoked rows — skipping", file=sys.stderr)
                return 0

            stmt = delete(AdminTotpSession).where(
                or_(
                    AdminTotpSession.expires_at < now,
                    (AdminTotpSession.revoked_at.is_not(None))
                    & (AdminTotpSession.revoked_at < revoked_cutoff),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            deleted = result.rowcount

        print(
            f"[{now.isoformat()}] deleted {deleted} admin_totp_sessions rows "
            f"(expired or revoked >30d ago)",
            file=sys.stderr,
        )
        return 0
    except Exception as e:
        print(f"FAIL: cleanup error: {e}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
