#!/usr/bin/env python3
"""Health snapshot cron — write a health probe to health_snapshots every minute.

Run via systemd timer or cron. Each invocation does its own probe + insert.

Exit codes:
  0 — snapshot written successfully (even if some components are down)
  1 — DB unavailable, could not write snapshot

Usage:
  /opt/styxproxy/backend/venv/bin/python3 /opt/styxproxy/backend/scripts/health_snapshot.py

Cron:
  * * * * * /opt/styxproxy/backend/venv/bin/python3 /opt/styxproxy/backend/scripts/health_snapshot.py >> /var/log/health_snapshot.log 2>&1
"""
import asyncio
import os
import sys
import time

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

# Force full model import so SQLAlchemy mapper registers
from app.models import HealthSnapshot  # noqa: E402
from app.database import async_session  # noqa: E402
from app.routers.health import (  # noqa: E402
    _check_db, _check_redis, _check_m2_cloud, _check_litellm, _check_ollama,
)


async def main():
    t0 = time.time()

    # Probe all components
    db_status = "unknown"
    redis_status = "unknown"
    m2_status = "unknown"
    litellm_status = "unknown"
    ollama_status = "unknown"
    errors = []

    try:
        async with async_session() as session:
            db_status = await _check_db(session)
    except Exception as e:
        errors.append(f"db: {e}")

    try:
        from app.services.observability import get_redis

        client = await get_redis()
        redis_status = "connected" if client is not None else "disconnected"
    except Exception as e:
        errors.append(f"redis: {e}")

    try:
        m2 = await _check_m2_cloud()
        m2_status = m2.get("status", "unknown")
    except Exception as e:
        errors.append(f"m2: {e}")

    try:
        litellm = await _check_litellm()
        litellm_status = litellm.get("status", "unknown")
    except Exception as e:
        errors.append(f"litellm: {e}")

    try:
        ollama = await _check_ollama()
        ollama_status = ollama.get("status", "unknown")
    except Exception as e:
        errors.append(f"ollama: {e}")

    db_connected = db_status == "connected"
    redis_connected = redis_status == "connected"
    m2_connected = m2_status == "connected"
    litellm_connected = litellm_status == "connected"
    ollama_connected = ollama_status == "connected"

    charon_available = m2_connected or (litellm_connected and ollama_connected)

    if db_connected and redis_connected and charon_available:
        overall_status = "healthy"
    elif db_connected:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    total_latency_ms = round((time.time() - t0) * 1000, 2)
    error_summary = "; ".join(errors)[:500] if errors else None

    # Write snapshot
    try:
        async with async_session() as session:
            snap = HealthSnapshot(
                db_connected=db_connected,
                redis_connected=redis_connected,
                m2_connected=m2_connected,
                litellm_connected=litellm_connected,
                ollama_connected=ollama_connected,
                overall_status=overall_status,
                charon_available=charon_available,
                total_latency_ms=total_latency_ms,
                error_summary=error_summary,
                source="cron",
            )
            session.add(snap)
            await session.commit()
            snap_id = snap.id
        print(
            f"OK snapshot id={snap_id} status={overall_status} latency={total_latency_ms}ms "
            f"db={db_status} redis={redis_status} m2={m2_status} "
            f"litellm={litellm_status} ollama={ollama_status}",
            flush=True,
        )
        return 0
    except Exception as e:
        print(f"FAIL: could not write snapshot: {e}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
