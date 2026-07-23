"""Maintenance mode router.

Public, superadmin, and admin routes all need to know if maintenance mode
is active. This router exposes:

  GET  /api/admin/maintenance         — read current state (any admin)
  POST /api/admin/maintenance/toggle  — superadmin flips the flag
  GET  /api/public/maintenance        — public read for the frontend

The maintenance page itself is rendered client-side; this router just
owns the boolean state.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import FeatureFlag
from app.routers.auth import require_admin, require_superadmin

router = APIRouter(tags=["maintenance"])

MAINTENANCE_FLAG = "maintenance_mode"
READY_AT_FLAG = "maintenance_ready_at"
MESSAGE_FLAG = "maintenance_message"


class MaintenanceState(BaseModel):
    enabled: bool
    ready_at: Optional[str] = None  # ISO 8601
    message: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    enabled: Optional[bool] = None
    ready_at: Optional[str] = None
    message: Optional[str] = None


async def _get_flag(session: AsyncSession, name: str) -> Optional[FeatureFlag]:
    return (
        await session.execute(select(FeatureFlag).where(FeatureFlag.name == name))
    ).scalar_one_or_none()


async def _ensure_flag(session: AsyncSession, name: str, default: bool = False) -> FeatureFlag:
    flag = await _get_flag(session, name)
    if flag is None:
        flag = FeatureFlag(name=name, enabled=default, description=f"auto-created: {name}")
        session.add(flag)
        await session.commit()
        await session.refresh(flag)
    return flag


@router.get("/api/admin/maintenance", response_model=MaintenanceState)
async def read_maintenance(
    session: AsyncSession = Depends(get_session),
    _admin: dict = Depends(require_admin),
):
    on = await _ensure_flag(session, MAINTENANCE_FLAG)
    ra = await _get_flag(session, READY_AT_FLAG)
    msg = await _get_flag(session, MESSAGE_FLAG)

    ready_at = None
    if ra and ra.description:
        ready_at = ra.description

    message = None
    if msg and msg.description:
        message = msg.description

    return MaintenanceState(
        enabled=on.enabled,
        ready_at=ready_at,
        message=message,
    )


@router.post("/api/admin/maintenance/toggle", response_model=MaintenanceState)
async def toggle_maintenance(
    body: MaintenanceUpdate,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_superadmin),
):
    """Superadmin sets maintenance state. Any field may be omitted to keep current value."""
    on = await _ensure_flag(session, MAINTENANCE_FLAG)

    if body.enabled is not None:
        on.enabled = body.enabled

    if body.ready_at is not None:
        ra = await _ensure_flag(session, READY_AT_FLAG)
        ra.description = body.ready_at

    if body.message is not None:
        msg = await _ensure_flag(session, MESSAGE_FLAG)
        msg.description = body.message

    await session.commit()

    # Audit log entry
    from app.models import AdminAuditLog

    audit = AdminAuditLog(
        admin_email=admin.get("email", "unknown"),
        action="maintenance_toggle",
        details={
            "enabled": on.enabled,
            "ready_at": body.ready_at,
            "message_set": body.message is not None,
        },
    )
    session.add(audit)
    await session.commit()

    return await read_maintenance(session, _admin=admin)


# Public endpoint — no auth, used by the maintenance page itself
@router.get("/api/public/maintenance", response_model=MaintenanceState)
async def public_maintenance(session: AsyncSession = Depends(get_session)):
    on = await _ensure_flag(session, MAINTENANCE_FLAG)
    ra = await _get_flag(session, READY_AT_FLAG)
    msg = await _get_flag(session, MESSAGE_FLAG)

    return MaintenanceState(
        enabled=on.enabled,
        ready_at=ra.description if ra else None,
        message=msg.description if msg else None,
    )
