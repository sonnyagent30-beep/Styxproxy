"""
Global idempotency for Styxproxy — dependency-based approach.

Apply to any POST handler with:
    idempotency_key: str = Depends(check_idempotency)

How it works:
- Client sends header: Idempotency-Key: <uuid>
- No key → proceed (legacy clients work normally)
- Key + same request within 24h → return cached response
- Key + new request → process, store result, return it

Store: PostgreSQL table idempotency_responses (key_hash PK)
Cleanup: cron DELETE WHERE created_at < NOW() - INTERVAL '25 hours'
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import Header, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.models import IdempotencyResponse


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def check_idempotency(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Optional[str]:
    """
    FastAPI dependency for idempotent POST endpoints.

    Returns the idempotency key if the request should proceed.
    Raises HTTPException(409) if a cached response exists.
    Skips entirely if no Idempotency-Key header is present.

    Usage:
        @router.post("/orders/create")
        async def create_order(
            order_data: OrderCreate,
            idempotency_key: Optional[str] = Depends(check_idempotency),
            ...
        ):
    """
    if not idempotency_key:
        return None  # No key = no protection

    key_hash = _hash(idempotency_key)
    now = datetime.now(timezone.utc)
    ttl = datetime.fromtimestamp(now.timestamp() + 86400, tz=timezone.utc)

    async with AsyncSession(engine) as session:
        # Find existing record — uses ORM select with bindparams, NO raw text() f-strings
        row = await session.execute(
            select(IdempotencyResponse).where(
                IdempotencyResponse.key_hash == key_hash,
                IdempotencyResponse.expires_at > now,
            )
        )
        existing = row.scalar_one_or_none()

        if existing:
            if existing.status_code is not None:
                # Completed cached response
                body = json.loads(existing.response_body) if existing.response_body else {}
                hdrs = json.loads(existing.response_headers) if existing.response_headers else {}
                raise HTTPException(
                    status_code=existing.status_code,
                    detail=body,
                    headers=hdrs,
                )
            else:
                # In-flight
                raise HTTPException(status_code=409, detail={"error": {"code": "IN_PROGRESS", "message": "Request already in progress"}})

        # New key — insert in-flight record
        await session.execute(
            text("""
                INSERT INTO idempotency_responses (key_hash, created_at, expires_at)
                VALUES (:kh, :ca, :ea)
                ON CONFLICT (key_hash) DO NOTHING
            """),
            {"kh": key_hash, "ca": now.isoformat(), "ea": ttl.isoformat()},
        )
        await session.commit()

    return idempotency_key


async def store_idempotent_response(
    idempotency_key: Optional[str],
    status_code: int,
    response_body: dict,
    headers: Optional[dict] = None,
):
    """Call after a successful POST to cache the response."""
    if not idempotency_key:
        return

    key_hash = _hash(idempotency_key)
    now = datetime.now(timezone.utc)

    async with AsyncSession(engine) as session:
        await session.execute(
            text("""
                UPDATE idempotency_responses
                SET status_code = :sc,
                    response_body = :rb,
                    response_headers = :rh
                WHERE key_hash = :kh
            """),
            {
                "sc": status_code,
                "rb": json.dumps(response_body),
                "rh": json.dumps(headers or {}),
                "kh": key_hash,
            },
        )
        await session.commit()
