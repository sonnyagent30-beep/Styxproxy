"""Health check router.

Provides both an unauthenticated shallow health check (status only)
and a deep health check (DB + Redis + LiteLLM + Ollama + M2 cloud).

P0-5 (Jul 22 2026): the deep health endpoint surfaces BOTH Chataron
LLM paths (M2 cloud primary, MiniCPM5 local fallback) so the admin
status panel and the ChatWidget fallback can detect when the LLM
stack is down BEFORE users see a broken spinner. Charon itself
handles per-request failover in app/services/charon/llm.py.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import engine, get_session
from app.schemas import HealthResponse

settings = get_settings()

router = APIRouter(tags=["health"])


async def _check_db(session: AsyncSession) -> str:
    """Quick DB ping."""
    try:
        await session.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"


async def _check_redis() -> str:
    """Try Redis PING. Failure returns disconnected (not raises).

    P0-5: Redis is optional for the API core (rate limiting uses
    in-memory slowapi). Marking it disconnected is safe — the app
    keeps working. The redis library is intentionally not in
    requirements.txt yet; install it when we add Redis caching.
    """
    try:
        import redis.asyncio as redis_async

        client = redis_async.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        return "connected"
    except ImportError:
        return "not_installed"
    except Exception:
        return "disconnected"


async def _check_dante() -> dict[str, Any]:
    """Check if Dante SOCKS proxy is healthy on each configured server.

    P0-5 (Aug 08 2026): Dante runs on Interserver and Contabo as the
    DC/ISP proxy source + free trial provider. This check probes each
    server's SOCKS5 port and returns connection count + memory.
    """
    servers = getattr(
        settings,
        "dante_servers",
        [
            {"name": "us-interserver", "host": "162.35.184.69", "port": 1080},
            {"name": "uk-contabo", "host": "84.247.132.12", "port": 9000, "type": "control_api"},
        ],
    )
    results = []
    all_up = True

    for srv in servers:
        srv_type = srv.get("type", "socks5")
        name = srv.get("name", srv["host"])
        host = srv["host"]
        port = srv.get("port", 1080)

        try:
            if srv_type == "control_api":
                # HTTP health check against the Dante control API
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(f"http://{host}:{port}/health")
                    if r.status_code == 200:
                        data = r.json()
                        results.append(
                            {
                                "name": name,
                                "host": host,
                                "port": port,
                                "type": "control_api",
                                "status": "up",
                                "users": data.get("users"),
                                "version": data.get("version"),
                                "vps_label": data.get("vps_label"),
                                "error": None,
                            }
                        )
                    else:
                        all_up = False
                        results.append(
                            {
                                "name": name,
                                "host": host,
                                "port": port,
                                "type": "control_api",
                                "status": "degraded",
                                "error": f"HTTP {r.status_code}",
                            }
                        )
            else:
                import asyncio

                # SOCKS5 greeting
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=3.0,
                )
                writer.write(b"\x05\x01\x00")  # SOCKS5, no auth
                await writer.drain()
                resp = await asyncio.wait_for(reader.read(2), timeout=3.0)
                writer.close()
                await writer.wait_closed()

                if len(resp) == 2 and resp[0] == 5:
                    import subprocess

                    try:
                        cp = subprocess.run(
                            ["ss", "-tnp"],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        conns = sum(1 for line in cp.stdout.splitlines() if f":{port}" in line and "ESTAB" in line)
                    except Exception:
                        conns = None

                    results.append(
                        {
                            "name": name,
                            "host": host,
                            "port": port,
                            "type": "socks5",
                            "status": "up",
                            "connections": conns,
                            "error": None,
                        }
                    )
                else:
                    all_up = False
                    results.append(
                        {
                            "name": name,
                            "host": host,
                            "port": port,
                            "type": "socks5",
                            "status": "degraded",
                            "connections": None,
                            "error": "unexpected SOCKS response",
                        }
                    )
        except asyncio.TimeoutError:
            all_up = False
            results.append(
                {
                    "name": name,
                    "host": host,
                    "port": port,
                    "status": "down",
                    "connections": None,
                    "error": "connection timeout",
                }
            )
        except Exception as e:
            all_up = False
            results.append(
                {
                    "name": name,
                    "host": host,
                    "port": port,
                    "status": "down",
                    "connections": None,
                    "error": str(e)[:100],
                }
            )

    return {"status": "up" if all_up else "degraded", "servers": results}


async def _check_litellm() -> dict[str, Any]:
    """Check if LiteLLM proxy is alive on the expected port.

    Returns dict with status, latency_ms, and any error. Latency
    None if unreachable. This is the value the admin status panel
    reads to decide whether to alert.
    """
    base = settings.litellm_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            t0 = datetime.utcnow()
            r = await client.get(
                f"{base}/health/liveliness",
                headers={"Authorization": f"Bearer {settings.litellm_api_key}"},
            )
            latency = (datetime.utcnow() - t0).total_seconds() * 1000
            if r.status_code == 200 and "alive" in r.text.lower():
                return {"status": "connected", "latency_ms": round(latency, 1), "error": None}
            return {
                "status": "degraded",
                "latency_ms": round(latency, 1),
                "error": f"HTTP {r.status_code}: {r.text[:100]}",
            }
    except Exception as e:
        return {"status": "disconnected", "latency_ms": None, "error": str(e)[:200]}


async def _check_ollama() -> dict[str, Any]:
    """Check if Ollama is alive and has minicpm5 loaded."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://127.0.0.1:11434/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                return {"status": "connected", "models": models, "minicpm5_loaded": any("minicpm" in m for m in models)}
            return {"status": "degraded", "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)[:200]}


async def _check_m2_cloud() -> dict[str, Any]:
    """Check if MiniMax-M2 (cloud primary) is reachable.

    P0-5 (Jul 22 2026): M2 is the chat primary. We probe the /v1/models
    endpoint with the configured key. Network/auth failures register
    as 'disconnected'. The api itself isn't tied to M2 being up —
    the LLM client will fall back to MiniCPM5 — but the admin status
    panel watches this to alert on M2 outages.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return {"status": "not_configured", "latency_ms": None, "error": "GROQ_API_KEY not set"}
    base = settings.groq_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            t0 = datetime.utcnow()
            r = await client.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            latency = (datetime.utcnow() - t0).total_seconds() * 1000
            if r.status_code == 200:
                return {"status": "connected", "latency_ms": round(latency, 1), "error": None}
            if r.status_code in (401, 403):
                return {
                    "status": "auth_error",
                    "latency_ms": round(latency, 1),
                    "error": f"HTTP {r.status_code} (key invalid?)",
                }
            return {"status": "degraded", "latency_ms": round(latency, 1), "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "disconnected", "latency_ms": None, "error": str(e)[:200]}


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    """Shallow health check — DB only. Fast path for load balancers."""
    database_status = await _check_db(session)
    return HealthResponse(
        status="healthy" if database_status == "connected" else "degraded",
        version="1.0.0",
        database=database_status,
        timestamp=datetime.utcnow(),
    )


@router.get("/api/v1/health")
async def deep_health(session: AsyncSession = Depends(get_session)):
    """Deep health check — DB + Redis + LiteLLM + Ollama + M2 cloud.

    Use this for the admin status panel and the ChatWidget fallback
    check. The response is intentionally unauthenticated so the
    frontend can poll it cheaply. None of the checks leak secrets.

    Returns 200 even when services are down (so load balancers don't
    pull the api container just because LiteLLM is down — the api
    itself is fine). The status flags in the body indicate what is
    actually broken.

    P0-5 (Jul 22 2026): Charon_available is true when M2 cloud is
    reachable (the primary path). If M2 is down but local fallback
    is also down, charon_available is false. If only M2 is down,
    charon_available is STILL true (the local fallback covers it).
    """
    db = await _check_db(session)
    redis = await _check_redis()
    dante = await _check_dante()
    litellm = await _check_litellm()
    ollama = await _check_ollama()
    m2 = await _check_m2_cloud()

    # Charon availability: Groq must be reachable.
    charon_available = m2["status"] == "connected"

    # Compute top-level status:
    # - unhealthy: DB is down (api can't function)
    # - degraded: DB ok but Charon has NO working path
    # - healthy: DB ok and Charon has at least one working path
    if db != "connected":
        overall = "unhealthy"
    elif not charon_available:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "database": db,
            "redis": redis,
            "dante": dante,
            "groq": m2,
        },
        # Charon routing policy:
        "charon_routing": {
            "primary": "groq",
            "fallback": "none",
        },
        # Hint for the frontend: when Charon is impaired, show a fallback
        # UI instead of a broken spinner. True means Charon can answer.
        "charon_available": charon_available,
        # Theme C (Jul 28): DB connection pool stats so the admin panel
        # can alert at 80% utilization. Read from the SQLAlchemy engine's
        # pool — synchronous getters, safe to call from async.
        "db_pool": _pool_stats(),
    }


def _pool_stats() -> dict[str, Any]:
    """Return SQLAlchemy AsyncEngine pool stats: size, overflow, in-use, idle.

    pool_size=20 + max_overflow=10 → max 30 concurrent connections.
    Returns utilization = (in_use + overflow) / max for alert routing at 80%.
    The pool is shared across all workers (NOT per-process — asyncpg
    uses the same pool object per process, but uvicorn workers each
    have their own engine). Treat utilization as per-worker.
    """
    pool = engine.pool
    size = pool.size()
    checkedout = pool.checkedout()
    overflow = pool.overflow()
    # checkedin = size - checkedout (capped at 0)
    checkedin = pool.checkedin()
    max_conns = size + abs(min(overflow, 0)) + max(overflow, 0)
    # In-use = checkedout + overflow currently over the base size
    in_use = checkedout
    utilization = round(in_use / max(1, size), 3) if size else 0.0
    return {
        "size": size,
        "max_overflow": pool._max_overflow,
        "checked_out": checkedout,
        "checked_in": checkedin,
        "overflow": overflow,
        "max_connections": max_conns,
        "utilization": utilization,
    }


@router.get("/api/health/db")
async def db_pool_health(session: AsyncSession = Depends(get_session)):
    """Dedicated DB pool endpoint for the admin status panel.

    Theme C — surfaces pool stats in isolation so alerting can be
    wired to pool exhaustion without parsing the full /api/v1/health
    payload. Returns 200 always (status field indicates health).
    """
    db = await _check_db(session)
    pool = _pool_stats()
    # Alert threshold: 80% utilization OR any DB error
    utilization = pool["utilization"]
    pool_alert = utilization >= 0.8
    overall = "unhealthy" if db != "connected" else "warning" if pool_alert else "healthy"
    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": db,
        "pool": pool,
        "alert": {
            "pool_high_utilization": pool_alert,
            "threshold": 0.8,
        },
    }
