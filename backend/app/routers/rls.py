"""Sprint 15 — RLS admin router.

Endpoints:
  GET   /api/admin/rls/policies        List all rls_policy rows + counts
  GET   /api/admin/rls/status          Snapshot: count + bypass role + running role
  GET   /api/admin/rls/rollout-plan    Phase 2a-2h plan with completion flags
  POST  /api/admin/rls/policies/toggle Enable / disable RLS on a single table
  POST  /api/admin/rls/policies/refresh Backfill rls_policy rows from pg_class

All endpoints require permission code 'admin.system.maintenance.read' — the
existing superadmin permission — since Sprint 15 hasn't introduced new RLS-specific
codes yet. SuperAdmins / admins / superadmins-by-role can all toggle.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas_rls import (
    RlsPolicyListResponse,
    RlsPolicyResponse,
    RlsPolicyToggleRequest,
    RlsPolicyToggleResponse,
    RlsRolloutPhase,
    RlsRolloutPlanResponse,
    RlsSafeStatus,
)
from app.services.audit import write_audit_log
from app.services.permissions import require_permission
from app.services.rls import (
    get_bypass_role_status,
    get_pg_rls_state,
    get_rollout_plan,
    list_policies,
    toggle_policy,
)

router = APIRouter(prefix="/api/admin/rls", tags=["rls"])


@router.get("/policies", response_model=RlsPolicyListResponse)
async def list_policies_endpoint(
    current_admin: dict = Depends(require_permission("admin.system.maintenance.read")),
    session: AsyncSession = Depends(get_session),
) -> RlsPolicyListResponse:
    """List all rls_policy rows + enable / not-started counts."""
    policies, enabled, not_started = await list_policies(session)
    items = [RlsPolicyResponse.model_validate(p) for p in policies]
    return RlsPolicyListResponse(
        policies=items,
        total=len(items),
        enabled_count=enabled,
        not_started_count=not_started,
    )


@router.get("/status", response_model=RlsSafeStatus)
async def status_endpoint(
    current_admin: dict = Depends(require_permission("admin.monitor.health.read")),
    session: AsyncSession = Depends(get_session),
) -> RlsSafeStatus:
    """Snapshot of RLS + role state for the safety UI."""
    policies, enabled, not_started = await list_policies(session)
    items = [RlsPolicyResponse.model_validate(p) for p in policies]
    role_state = await get_bypass_role_status(session)

    return RlsSafeStatus(
        total_tables=len(items),
        rls_enabled_count=enabled,
        rls_disabled_count=len(items) - enabled,
        policies=items,
        bypass_role_exists=role_state["bypass_role_exists"],
        current_user_role=role_state["current_user_role"],
        bypass_role_attr_present=role_state["bypass_role_attr_present"],
    )


@router.get("/rollout-plan", response_model=RlsRolloutPlanResponse)
async def rollout_plan_endpoint(
    current_admin: dict = Depends(require_permission("admin.system.maintenance.read")),
    session: AsyncSession = Depends(get_session),
) -> RlsRolloutPlanResponse:
    """Return the Phase 2a-2h rollout plan with completion flags."""
    phases, next_phase, conn_pinned = await get_rollout_plan(session)
    phase_models = [RlsRolloutPhase(**p) for p in phases]
    return RlsRolloutPlanResponse(
        phases=phase_models,
        next_phase=next_phase,
        connection_string_pinned=conn_pinned,
    )


# HIGH_RISK tables — toggling RLS on these requires TOTP step-up
HIGH_RISK_TABLES = {"orders", "styxproxy_credentials", "customers", "admin_auth"}


def _toggle_auth() -> Depends:
    """RLS toggle always requires TOTP step-up (security-critical operation)."""
    from app.services.permissions import require_permission

    return Depends(require_permission("admin.system.maintenance.read", totp_required=True))


@router.post("/policies/toggle", response_model=RlsPolicyToggleResponse)
async def toggle_policy_endpoint(
    body: RlsPolicyToggleRequest,
    current_admin: dict = _toggle_auth(),
    session: AsyncSession = Depends(get_session),
) -> RlsPolicyToggleResponse:
    """Enable or disable RLS on a single table.

    SuperAdmin / admin only. TOTP step-up always required for this operation.
    Idempotent. Audit-logged.
    """
    admin_email = current_admin["admin"].email

    # Sanity-check table exists
    check = (
        await session.execute(
            __import__("sqlalchemy").text("SELECT 1 FROM pg_class WHERE relname = :t AND relkind = 'r'"),
            {"t": body.table_name},
        )
    ).fetchone()
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"table '{body.table_name}' not found in public schema",
        )

    result = await toggle_policy(
        session,
        table_name=body.table_name,
        enable=body.enable,
        using_clause=body.using_clause,
        with_check=body.with_check,
        notes=body.notes,
        admin_email=admin_email,
    )

    # Audit log
    await write_audit_log(
        db_session=session,
        admin_email=admin_email,
        action="rls.toggle",
        resource_type="database.table",
        resource_id=body.table_name,
        details={
            "enable": body.enable,
            "pg_rls_state": result["pg_rls_state"],
            "pg_policy_count": result["pg_policy_count"],
            "policy_status": result["policy_status"],
            "using_clause": body.using_clause or "true",
            "with_check": body.with_check or "true",
            "notes": body.notes,
        },
    )

    return RlsPolicyToggleResponse(**result)


@router.post("/policies/refresh")
async def refresh_policies_endpoint(
    current_admin: dict = Depends(require_permission("admin.system.maintenance.read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Re-backfill rls_policy rows from pg_class for tables that don't have one yet.

    Useful after /api/admin/rls/policies/toggle creates state on a fresh table
    that wasn't pre-backfilled. No destructive ops.
    """
    admin_email = current_admin["admin"].email

    # Find all public tables not yet represented in rls_policy
    missing = (
        await session.execute(
            __import__("sqlalchemy").text("""
            SELECT c.relname
            FROM pg_class c
            WHERE c.relkind = 'r'
              AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
              AND NOT EXISTS (SELECT 1 FROM rls_policy rp WHERE rp.table_name = c.relname)
        """)
        )
    ).fetchall()
    added = []
    for (table_name,) in missing:
        pg_state, pg_count = await get_pg_rls_state(session, table_name)
        await toggle_policy(
            session,
            table_name=table_name,
            enable=pg_state == "enabled",
            using_clause="true",
            with_check="true",
            notes="backfilled via /policies/refresh",
            admin_email=admin_email,
        )
        added.append({"table": table_name, "now_enabled": pg_state == "enabled"})

    await write_audit_log(
        db_session=session,
        admin_email=admin_email,
        action="rls.refresh",
        resource_type="rls_policy",
        resource_id=None,
        details={"added": added},
    )

    return {"added": added, "count_added": len(added)}
