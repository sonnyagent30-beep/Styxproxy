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
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_session
from app.schemas import HealthResponse
from app.config import get_settings

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
            return {"status": "degraded", "latency_ms": round(latency, 1), "error": f"HTTP {r.status_code}: {r.text[:100]}"}
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
    api_key = os.getenv("MINIMAX_API_KEY", "")
    if not api_key:
        return {"status": "not_configured", "latency_ms": None, "error": "MINIMAX_API_KEY not set"}
    base = settings.minimax_base_url.rstrip("/")
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
                return {"status": "auth_error", "latency_ms": round(latency, 1), "error": f"HTTP {r.status_code} (key invalid?)"}
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
    litellm = await _check_litellm()
    ollama = await _check_ollama()
    m2 = await _check_m2_cloud()

    # Charon availability: primary OR fallback must be reachable.
    # M2 priority, but local fallback as backup.
    m2_ok = m2["status"] == "connected"
    local_ok = litellm["status"] == "connected" and ollama["status"] == "connected"
    charon_available = m2_ok or local_ok

    # Compute top-level status:
    # - unhealthy: DB is down (api can't function)
    # - degraded: DB ok but Charon has NO working path (M2 + local both down)
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
            "litellm": litellm,
            "ollama": ollama,
            "m2_cloud": m2,
        },
        # Charon routing policy (P0-5):
        "charon_routing": {
            "primary": "m2-cloud",
            "fallback": "local-minicpm5",
        },
        # Hint for the frontend: when Charon is impaired, show a fallback
        # UI instead of a broken spinner. True means Charon can answer.
        "charon_available": charon_available,
    }
