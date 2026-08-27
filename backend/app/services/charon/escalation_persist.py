"""Persist an escalation to the DB without needing the request session.

Called as a background task so it never blocks the response.
Uses the asyncpg pool directly — no ORM session needed.
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

logger = logging.getLogger(__name__)

_pool = None


async def _get_pool():
    global _pool
    if _pool is None:
        import asyncpg
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url:
            logger.warning("DATABASE_URL not set, skipping escalation persistence")
            return None
        dsn = database_url.replace("postgresql+asyncpg://", "")
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2, command_timeout=10)
    return _pool


async def persist_escalation(
    conversation_id: str,
    customer_email: str | None,
    customer_phone: str | None,
    customer_message: str,
    history_summary: str,
    scenario_id: str,
    reason: str | None = None,
) -> UUID | None:
    """Insert a charon_escalations record. Returns the created ID or None on failure."""
    try:
        pool = await _get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO charon_escalations
                    (id, conversation_id, customer_email, customer_phone,
                     customer_message, history_summary, status, sla_deadline, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), $1, $2, $3, $4, $5, 'pending', NOW() + INTERVAL '2 hours', NOW(), NOW())
                RETURNING id
                """,
                conversation_id,
                customer_email,
                customer_phone,
                customer_message[:2000],
                history_summary[:500],
            )
            escalation_id = row["id"]
            logger.info(f"Persisted escalation {escalation_id} for scenario={scenario_id}")
            return escalation_id
    except Exception as e:
        logger.error(f"Failed to persist escalation: {e}")
        return None


def persist_escalation_sync(
    conversation_id: str,
    customer_email: str | None,
    customer_phone: str | None,
    customer_message: str,
    history_summary: str,
    scenario_id: str,
    reason: str | None = None,
) -> None:
    """Fire-and-forget wrapper — schedules persist_escalation in a thread pool.

    Use this when you are inside an async function and don't want to await.
    """
    import threading

    def _bg():
        asyncio.run(
            persist_escalation(
                conversation_id=conversation_id,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_message=customer_message,
                history_summary=history_summary,
                scenario_id=scenario_id,
                reason=reason,
            )
        )

    threading.Thread(target=_bg, daemon=True).start()
