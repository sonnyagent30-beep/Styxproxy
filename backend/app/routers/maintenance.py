"""Maintenance mode router.

Public, superadmin, and admin routes all need to know if maintenance mode
is active. This router exposes:

  GET  /api/admin/maintenance         — read current state (any admin)
  POST /api/admin/maintenance/toggle  — superadmin flips the flag
  GET  /api/public/maintenance        — public read for the frontend

The maintenance page itself is rendered client-side; this router just
owns the boolean state.
"""

from typing import Optional

from fastapi import APIRouter, Depends
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
    return (await session.execute(select(FeatureFlag).where(FeatureFlag.name == name))).scalar_one_or_none()


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



# ─── Public status endpoint (Betterstack-compatible) ──────────────────────────
# Theme A: small public status endpoint that returns overall service health.
# Suitable for:
# - Betterstack / Atlassian Statuspage / Instatus webhooks (poll this URL)
# - A custom static status page that fetches this and renders a chart
# - Uptime monitoring (any HTTP client that wants a 200 from a healthy service)
#
# Response shape (Statuspage-compatible):
# {
#   "status": { "indicator": "none|minor|major|critical", "description": "..." },
#   "components": [
#     {"name": "API", "status": "operational|degraded|down"},
#     {"name": "Database", "status": "operational|degraded|down"},
#     ...
#   ],
#   "incidents": []
# }
#
# Caching: no cache headers by default. For Betterstack webhooks, the
# recommendation is to cache for ~60s to avoid hammering. Add
# Cache-Control header here if needed.

@router.get("/api/public/status")
async def public_status(session: AsyncSession = Depends(get_session)) -> dict:
    """Public service status (Betterstack-compatible).

    Returns the latest HealthSnapshot from the cron poller (M5) plus
    computed indicator. No auth — safe to expose to public monitors.

    Indicator logic:
    - "none" (operational): overall_status == healthy
    - "minor" (degraded): overall_status == degraded (some components
      down but core still works)
    - "major" (down): overall_status == unhealthy (DB down)
    """
    from sqlalchemy import select

    from app.models import HealthSnapshot

    # Read most recent snapshot (cron writes every minute)
    stmt = select(HealthSnapshot).order_by(HealthSnapshot.created_at.desc()).limit(1)
    result = await session.execute(stmt)
    snap = result.scalar_one_or_none()

    if snap is None:
        # No snapshot yet — likely fresh deploy before first cron ran
        return {
            "status": {
                "indicator": "unknown",
                "description": "No health data yet. Status will populate within 1 minute.",
            },
            "components": [],
            "incidents": [],
        }

    # Map component status
    def component_status(connected: bool, is_core: bool = False) -> str:
        if connected:
            return "operational"
        if is_core:
            return "down"
        return "degraded"

    components = [
        {"name": "API", "status": "operational"},  # We're responding, so API is up
        {"name": "Database", "status": component_status(snap.db_connected, is_core=True)},
        {"name": "Redis", "status": component_status(snap.redis_connected)},
        {"name": "M2 Cloud (Charon primary)", "status": component_status(snap.m2_connected)},
        {"name": "LiteLLM (Charon fallback)", "status": component_status(snap.litellm_connected)},
        {"name": "Ollama (Charon fallback)", "status": component_status(snap.ollama_connected)},
        {"name": "Charon (support bot)", "status": component_status(snap.charon_available)},
    ]

    # Map overall to statuspage indicator
    indicator_map = {
        "healthy": ("none", "All systems operational"),
        "degraded": ("minor", "Some non-core components are degraded"),
        "unhealthy": ("major", "Core systems are down — service degraded"),
    }
    indicator, description = indicator_map.get(
        snap.overall_status, ("unknown", f"Status: {snap.overall_status}")
    )

    return {
        "status": {"indicator": indicator, "description": description},
        "components": components,
        "incidents": [],
        "last_updated": snap.created_at.isoformat() if snap.created_at else None,
        "source": snap.source,
        "latency_ms": float(snap.total_latency_ms) if snap.total_latency_ms is not None else None,
    }
