"""Charon A/B test router.

Endpoints:
  POST /internal/charon/ab/assign  - assign variant to session_id
  GET  /api/v1/admin/charon/ab-test/results - admin only, show variant stats
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import CharonAbAssignment, CharonAbOutcome
from app.services.permissions import require_permission

router = APIRouter(prefix="/internal/charon/ab", tags=["charon-ab"])


def _variant_for_session(session_id: str) -> str:
    """Deterministic 50/50 variant assignment via hash of session_id."""
    digest = hashlib.sha256(session_id.encode()).hexdigest()
    return "B" if int(digest, 16) % 2 == 0 else "A"


@router.post("/assign")
async def assign_variant(
    session_id: str,
) -> dict:
    """Assign a variant (A or B) to a session_id.

    Assignment is deterministic - same session_id always gets the same variant.
    Creates an outcome record with 'pending' status.
    """
    variant = _variant_for_session(session_id)

    async with async_session() as session:
        existing = await session.execute(
            select(CharonAbAssignment).where(CharonAbAssignment.session_id == session_id)
        )
        row = existing.scalar_one_or_none()
        if row is None:
            assignment = CharonAbAssignment(session_id=session_id, variant=variant)
            session.add(assignment)
            outcome = CharonAbOutcome(
                session_id=session_id,
                variant=variant,
                outcome="pending",
            )
            session.add(outcome)
        await session.commit()

    return {"session_id": session_id, "variant": variant}


@router.get("/outcome")
async def record_outcome(
    session_id: str,
    outcome: str,
    conversation_id: str | None = None,
) -> dict:
    """Record or update the outcome for a session's conversation."""
    if outcome not in ("resolution", "escalation"):
        raise HTTPException(status_code=400, detail="outcome must be resolution or escalation")

    async with async_session() as session:
        result = await session.execute(
            select(CharonAbOutcome).where(CharonAbOutcome.session_id == session_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.outcome = outcome
            row.concluded_at = datetime.now(timezone.utc)
            if conversation_id:
                row.conversation_id = conversation_id
        else:
            variant = _variant_for_session(session_id)
            row = CharonAbOutcome(
                session_id=session_id,
                variant=variant,
                outcome=outcome,
                conversation_id=conversation_id,
                concluded_at=datetime.now(timezone.utc),
            )
            session.add(row)
        await session.commit()

    return {"session_id": session_id, "outcome": outcome}


# Admin endpoint
admin_router = APIRouter(prefix="/api/v1/admin/charon", tags=["charon-ab-admin"])


@admin_router.get("/ab-test/results")
async def ab_test_results(
    current_admin: dict = Depends(require_permission("admin.system.audit_log.read")),
) -> dict:
    """Return A/B test results per variant."""
    async with async_session() as session:
        totals = await session.execute(
            select(
                CharonAbOutcome.variant,
                func.count(CharonAbOutcome.id).label("total"),
            ).group_by(CharonAbOutcome.variant)
        )
        total_map: dict[str, int] = {r.variant: r.total for r in totals}

        resolutions = await session.execute(
            select(
                CharonAbOutcome.variant,
                func.count(CharonAbOutcome.id).label("resolutions"),
            ).where(CharonAbOutcome.outcome == "resolution").group_by(CharonAbOutcome.variant)
        )
        res_map: dict[str, int] = {r.variant: r.resolutions for r in resolutions}

        escalations = await session.execute(
            select(
                CharonAbOutcome.variant,
                func.count(CharonAbOutcome.id).label("escalations"),
            ).where(CharonAbOutcome.outcome == "escalation").group_by(CharonAbOutcome.variant)
        )
        esc_map: dict[str, int] = {r.variant: r.escalations for r in escalations}

    variants = {}
    for v in ("A", "B"):
        total = total_map.get(v, 0)
        res = res_map.get(v, 0)
        esc = esc_map.get(v, 0)
        variants[v] = {
            "total": total,
            "resolutions": res,
            "escalations": esc,
            "pending": total - res - esc,
            "resolution_rate": round(res / total, 4) if total > 0 else None,
            "escalation_rate": round(esc / total, 4) if total > 0 else None,
        }

    return {"variants": variants}
