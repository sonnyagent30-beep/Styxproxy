"""Persist an escalation to the DB without needing the request session.

Called as a background task so it never blocks the response.
Uses the asyncpg pool directly — no ORM session needed.

After writing the charon_escalations row, this also creates a
SupportThread + SupportMessage so the escalation lands in /admin/support.
The Resend notification email is sent separately by the Charon router.
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
        dsn = database_url.replace("postgresql+asyncpg://", "postgresql://")
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
    """Insert a charon_escalations record and bridge to SupportThread.

    Returns the escalation ID or None on failure.
    """
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

            # --- Bridge to SupportThread ---
            # SupportThread requires customer_email (NOT NULL). Use a placeholder
            # when the customer didn't provide one so the thread still lands in the inbox.
            thread_email = customer_email or "unknown@styxproxy.com"
            thread_subject = f"Charon Escalation: {scenario_id}"
            if reason:
                thread_subject += f" — {reason}"

            thread_row = await conn.fetchrow(
                """
                INSERT INTO support_threads
                    (id, customer_email, customer_name, subject, status, order_id, created_at, last_message_at)
                VALUES
                    (gen_random_uuid(), $1, $2, $3, 'open', $4, NOW(), NOW())
                RETURNING id
                """,
                thread_email,
                None,  # customer_name — not available in escalation context
                thread_subject[:500],
                None,  # order_id — not available in escalation context
            )
            thread_id = thread_row["id"]
            logger.info(f"Created support thread {thread_id} for escalation {escalation_id}")

            # Create the inbound SupportMessage with the customer's original message
            await conn.execute(
                """
                INSERT INTO support_messages
                    (id, thread_id, direction, from_email, to_email, subject, body_text, body_html, created_at)
                VALUES
                    (gen_random_uuid(), $1, 'inbound', $2, $3, $4, $5, NULL, NOW())
                """,
                thread_id,
                thread_email,
                "support@styxproxy.com",
                thread_subject[:500],
                customer_message[:4000] if customer_message else "(no message)",
            )
            logger.info(f"Created inbound message in thread {thread_id}")

        # Note: the Resend notification email is already sent by the Charon router
        # (app/routers/charon.py) with a richer template. No need to duplicate it here.

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
