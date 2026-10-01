"""Charon A/B experiment framework.

Tracks which variant (A or B) a conversation is assigned to and records
resolution outcomes so we can measure whether page_context improves resolution.

Usage:
    from app.services.charon.ab_framework import get_variant, record_outcome

    variant = get_variant(conversation_id)        # 'control' or 'treatment'
    record_outcome(conversation_id, 'resolved')   # 'resolved' | 'escalated'
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class Variant(str, Enum):
    CONTROL = "control"     # A: no page context
    TREATMENT = "treatment"  # B: page context injected


# ── Experiment config ────────────────────────────────────────────────────────────

EXPERIMENT_ID = "page-context-v1"
TREATMENT_RATIO = 0.5  # 50% treatment, 50% control
MIN_CONVERSATION_LENGTH = 3  # only score conversations with 3+ messages


# ── Assignment ─────────────────────────────────────────────────────────────────

def get_variant(conversation_id: str) -> Variant:
    """Deterministically assign a conversation to a variant.

    Uses a hash so the same conversation_id always gets the same variant,
    and the split is consistent regardless of server restarts.
    """
    raw = f"{EXPERIMENT_ID}:{conversation_id}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    # Use first 8 hex chars as a large integer for ratio split
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return Variant.TREATMENT if bucket < TREATMENT_RATIO else Variant.CONTROL


def get_page_context_variant(
    conversation_id: str,
    page_context: dict | None,
) -> tuple[dict | None, Variant]:
    """Returns (actual_context, variant) for the agent to use.

    Control group: always returns (page_context, Variant.CONTROL) even if page_context exists.
    Treatment group: returns (page_context, Variant.TREATMENT).
    """
    variant = get_variant(conversation_id)
    if variant == Variant.CONTROL:
        return None, variant
    return page_context, variant


# ── Outcome recording ────────────────────────────────────────────────────────────

async def record_outcome(
    conversation_id: str,
    outcome: str,  # 'resolved' | 'escalated'
    resolution_time_seconds: float | None = None,
    messages_count: int | None = None,
) -> None:
    """Persist experiment outcome to DB (async, fire-and-forget on caller)."""
    try:
        import asyncpg, os
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://styxproxy_app:Ku3xHibr3qjcbGNSmQ5ZOAwNViCbm4lO@127.0.0.1:5432/styxproxy",
        )
        dsn = database_url.replace("postgresql+asyncpg://", "")
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2, command_timeout=10)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO charon_experiment_outcomes
                    (id, experiment_id, conversation_id, variant, outcome,
                     resolution_time_seconds, messages_count, created_at)
                VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (conversation_id, experiment_id) DO UPDATE
                    SET outcome = EXCLUDED.outcome,
                        resolution_time_seconds = EXCLUDED.resolution_time_seconds,
                        messages_count = EXCLUDED.messages_count
                """,
                EXPERIMENT_ID,
                conversation_id,
                get_variant(conversation_id).value,
                outcome,
                resolution_time_seconds,
                messages_count,
            )
        await pool.close()
    except Exception as e:
        logger.error(f"Failed to record experiment outcome: {e}")


# ── Stats ──────────────────────────────────────────────────────────────────────

async def get_experiment_stats() -> dict:
    """Return per-variant counts and resolution rates."""
    try:
        import asyncpg, os
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://styxproxy_app:Ku3xHibr3qjcbGNSmQ5ZOAwNViCbm4lO@127.0.0.1:5432/styxproxy",
        )
        dsn = database_url.replace("postgresql+asyncpg://", "")
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2, command_timeout=10)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    variant,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE outcome = 'resolved') as resolved,
                    COUNT(*) FILTER (WHERE outcome = 'escalated') as escalated,
                    ROUND(
                        COUNT(*) FILTER (WHERE outcome = 'resolved')::NUMERIC
                        / NULLIF(COUNT(*), 0) * 100, 1
                    ) as resolution_rate_pct,
                    AVG(resolution_time_seconds) FILTER (WHERE outcome = 'resolved')
                        as avg_resolution_seconds
                FROM charon_experiment_outcomes
                WHERE experiment_id = $1
                GROUP BY variant
                """,
                EXPERIMENT_ID,
            )
        await pool.close()
        return {
            "experiment_id": EXPERIMENT_ID,
            "treatment_ratio": TREATMENT_RATIO,
            "variants": [dict(r) for r in rows],
        }
    except Exception as e:
        logger.error(f"Failed to get experiment stats: {e}")
        return {"experiment_id": EXPERIMENT_ID, "error": str(e)}


# ── DB migration ────────────────────────────────────────────────────────────────

MIGRATION_SQL = """
-- Track A/B experiment outcomes
CREATE TABLE IF NOT EXISTS charon_experiment_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR(100) NOT NULL,
    conversation_id VARCHAR(200) NOT NULL,
    variant VARCHAR(20) NOT NULL,  -- 'control' or 'treatment'
    outcome VARCHAR(50) NOT NULL, -- 'resolved' or 'escalated'
    resolution_time_seconds NUMERIC,
    messages_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_experiment_conversation UNIQUE (conversation_id, experiment_id)
);

CREATE INDEX IF NOT EXISTS idx_experiment_experiment_id
    ON charon_experiment_outcomes (experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiment_variant
    ON charon_experiment_outcomes (variant);
CREATE INDEX IF NOT EXISTS idx_experiment_outcome
    ON charon_experiment_outcomes (outcome);
"""
