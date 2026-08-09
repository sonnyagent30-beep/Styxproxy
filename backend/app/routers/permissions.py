"""Sprint 14 — RBAC + TOTP step-up endpoints.

- GET  /api/me/permissions         — current admin's effective codes
- GET  /api/admin/permissions      — list all permissions (admin can view)
- POST /api/admin/permissions/grant — grant code to admin (superadmin)
- POST /api/admin/permissions/revoke — revoke code from admin (superadmin)
- GET  /api/me/totp/status         — is TOTP enabled + is session step-upped?
- POST /api/me/totp/elevate        — re-prompt TOTP, refresh 5-min step-up

Permission Change Request Workflow (Sprint 15):
- POST /api/admin/permission-requests      — create a permission change request
- GET  /api/admin/permission-requests      — list requests (filtered by status)
- GET  /api/admin/permission-requests/{id} — get a specific request
- POST /api/admin/permission-requests/{id}/action — approve/reject a request (superadmin)
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    AdminAuth,
    AdminPermission,
    AdminTotpSession,
    AdminUserPermission,
    PermissionChangeRequest,
)

# Use require_viewer as the base for self-service endpoints
from app.routers.auth import require_superadmin, require_viewer
from app.schemas import (
    PermissionChangeRequestAction,
    PermissionChangeRequestCreate,
    PermissionChangeRequestListResponse,
    PermissionChangeRequestResponse,
)
from app.services.audit import write_audit_log
from app.services.email import send_admin_notification
from app.services.permissions import (
    TOTP_STEP_UP_WINDOW,
    get_effective_permissions_payload,
)

router = APIRouter(tags=["admin-permissions"])


# ============================================================
# /api/me/permissions — current admin's effective permissions
# ============================================================


@router.get("/api/me/permissions")
async def get_my_permissions(
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Return the current admin's effective permission codes grouped by category."""
    admin = current_admin["admin"]
    return await get_effective_permissions_payload(session, admin)


# ============================================================
# /api/admin/permissions — list all permissions (admin)
# ============================================================


@router.get("/api/admin/permissions")
async def list_all_permissions(
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """List all 51 permission codes with categories, descriptions, and is_sensitive."""
    stmt = select(AdminPermission).order_by(AdminPermission.category, AdminPermission.code)
    result = await session.execute(stmt)
    perms = result.scalars().all()

    by_category: dict[str, list[dict]] = {}
    for p in perms:
        by_category.setdefault(p.category, []).append(
            {
                "code": p.code,
                "description": p.description,
                "is_sensitive": p.is_sensitive,
            }
        )

    return {
        "total": len(perms),
        "categories": list(by_category.keys()),
        "permissions_by_category": by_category,
    }


# ============================================================
# Grant / Revoke (superadmin only)
# ============================================================


class GrantPermissionRequest(BaseModel):
    admin_email: str
    permission_code: str


@router.post("/api/admin/permissions/grant")
async def grant_permission(
    body: GrantPermissionRequest,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Grant a permission code to an admin (creates user-level override)."""
    # Verify target admin exists
    stmt = select(AdminAuth).where(AdminAuth.email == body.admin_email)
    result = await session.execute(stmt)
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail=f"Admin '{body.admin_email}' not found")

    # Verify permission code exists
    stmt = select(AdminPermission).where(AdminPermission.code == body.permission_code)
    result = await session.execute(stmt)
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail=f"Permission '{body.permission_code}' not found")

    # Upsert user-level override
    stmt = select(AdminUserPermission).where(
        AdminUserPermission.admin_email == body.admin_email,
        AdminUserPermission.permission_code == body.permission_code,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        existing.granted = True
        existing.updated_at = datetime.now(timezone.utc)
    else:
        session.add(
            AdminUserPermission(
                admin_email=body.admin_email,
                permission_code=body.permission_code,
                granted=True,
                granted_by=current_admin["admin"].email,
            )
        )
    await session.commit()

    # Audit log
    await write_audit_log(
        db_session=session,
        admin_email=current_admin["admin"].email,
        action="permission.grant",
        resource_type="admin",
        resource_id=body.admin_email,
        details={"permission_code": body.permission_code},
    )

    return {
        "granted": True,
        "admin_email": body.admin_email,
        "permission_code": body.permission_code,
        "permission_is_sensitive": perm.is_sensitive,
    }


@router.post("/api/admin/permissions/revoke")
async def revoke_permission(
    body: GrantPermissionRequest,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Revoke a permission code from an admin (creates user-level deny override)."""
    # Verify target admin exists
    stmt = select(AdminAuth).where(AdminAuth.email == body.admin_email)
    result = await session.execute(stmt)
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail=f"Admin '{body.admin_email}' not found")

    # Upsert user-level deny override
    stmt = select(AdminUserPermission).where(
        AdminUserPermission.admin_email == body.admin_email,
        AdminUserPermission.permission_code == body.permission_code,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        existing.granted = False
        existing.updated_at = datetime.now(timezone.utc)
    else:
        session.add(
            AdminUserPermission(
                admin_email=body.admin_email,
                permission_code=body.permission_code,
                granted=False,
                granted_by=current_admin["admin"].email,
            )
        )
    await session.commit()

    # Audit log
    await write_audit_log(
        db_session=session,
        admin_email=current_admin["admin"].email,
        action="permission.revoke",
        resource_type="admin",
        resource_id=body.admin_email,
        details={"permission_code": body.permission_code},
    )

    return {"revoked": True, "admin_email": body.admin_email, "permission_code": body.permission_code}


# ============================================================
# TOTP step-up
# ============================================================


@router.get("/api/me/totp/status")
async def totp_status(
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Is TOTP enabled + is the current session step-upped?"""
    admin = current_admin["admin"]
    now = datetime.now(timezone.utc)

    # Find latest non-revoked session
    stmt = (
        select(AdminTotpSession)
        .where(
            AdminTotpSession.admin_email == admin.email,
            AdminTotpSession.revoked_at.is_(None),
            AdminTotpSession.expires_at > now,
        )
        .order_by(AdminTotpSession.granted_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    sess = result.scalar_one_or_none()

    step_upped = sess is not None
    expires_at = sess.expires_at if sess else None

    return {
        "totp_enabled": admin.totp_enabled,
        "step_upped": step_upped,
        "step_up_expires_at": expires_at.isoformat() if expires_at else None,
        "step_up_window_seconds": int(TOTP_STEP_UP_WINDOW.total_seconds()),
    }


class TOTPElevateRequest(BaseModel):
    totp_code: str
    remember_device: bool = False


@router.post("/api/me/totp/elevate")
async def totp_elevate(
    body: TOTPElevateRequest,
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Re-prompt TOTP, refresh 5-min step-up. Optional remember-device (30-day)."""
    import pyotp

    admin = current_admin["admin"]
    if not admin.totp_enabled or not admin.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not enabled. Set up TOTP first.")

    totp = pyotp.TOTP(admin.totp_secret)
    if not totp.verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=403, detail="Invalid TOTP code")

    now = datetime.now(timezone.utc)
    expires_at = now + TOTP_STEP_UP_WINDOW

    # If remember_device, create a longer-lived session token
    session_token = None
    session_token_hash = None
    if body.remember_device:
        session_token = secrets.token_urlsafe(48)
        session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()
        expires_at = now + timedelta(days=30)

    session.add(
        AdminTotpSession(
            admin_email=admin.email,
            session_token_hash=session_token_hash or "code-only",
            granted_at=now,
            expires_at=expires_at,
            last_used_at=now,
        )
    )
    await session.commit()

    # Audit log
    await write_audit_log(
        db_session=session,
        admin_email=admin.email,
        action="totp.stepup",
        resource_type="admin",
        resource_id=admin.email,
        details={"remember_device": body.remember_device},
    )

    response = {
        "elevated": True,
        "expires_at": expires_at.isoformat(),
        "window_seconds": int((expires_at - now).total_seconds()),
    }
    if session_token:
        response["session_token"] = session_token
        response["session_token_header"] = "X-TOTP-Session"
    return response


# ============================================================
# Permission Change Request Workflow (Sprint 15)
# ============================================================


@router.post("/api/admin/permission-requests", response_model=PermissionChangeRequestResponse)
async def create_permission_request(
    body: PermissionChangeRequestCreate,
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Create a permission change request.

    Admins can request:
    - Permission for themselves (target_email empty)
    - Permission for another admin (target_email specified)

    Requires justification (min 10 chars). Auto-expires in 7 days.
    """
    admin = current_admin["admin"]

    # Validate permission code exists
    stmt = select(AdminPermission).where(AdminPermission.code == body.permission_code)
    result = await session.execute(stmt)
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail=f"Permission '{body.permission_code}' not found")

    # Determine target email
    target_email = body.target_email if body.target_email else admin.email

    # If target is another admin, verify they exist
    if body.target_email:
        stmt = select(AdminAuth).where(AdminAuth.email == body.target_email)
        result = await session.execute(stmt)
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail=f"Admin '{body.target_email}' not found")

    # Create the request
    now = datetime.now(timezone.utc)
    pcr = PermissionChangeRequest(
        requested_by=admin.email,
        target_email=target_email,
        target_role=None,  # Will be set on approval
        permission_code=body.permission_code,
        desired_state=body.desired_state,
        justification=body.justification,
        status="pending",
        created_at=now,
        expires_at=now + timedelta(days=7),
    )
    session.add(pcr)
    await session.commit()
    await session.refresh(pcr)

    # Send admin notification to superadmins
    try:
        await send_admin_notification(
            title="Permission Change Request",
            details={
                "requested_by": admin.email,
                "target_email": target_email,
                "permission_code": body.permission_code,
                "desired_state": "grant" if body.desired_state else "revoke",
                "justification": body.justification[:100] + "..."
                if len(body.justification) > 100
                else body.justification,
                "request_id": str(pcr.id),
            },
            pill_type="yellow",
        )
    except Exception:
        pass  # Non-blocking

    return PermissionChangeRequestResponse.model_validate(pcr)


@router.get("/api/admin/permission-requests", response_model=PermissionChangeRequestListResponse)
async def list_permission_requests(
    status_filter: str = Query(None, description="Filter by status: pending, approved, rejected, expired"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """List permission change requests.

    Admins can see their own requests. Superadmins see all requests.
    """
    admin = current_admin["admin"]
    is_superadmin = admin.role == "superadmin"

    # Build conditions
    conditions = []
    if not is_superadmin:
        # Non-superadmins only see their own requests
        conditions.append(PermissionChangeRequest.requested_by == admin.email)

    if status_filter:
        conditions.append(PermissionChangeRequest.status == status_filter.lower())

    # Count total and pending
    count_stmt = select(func.count()).select_from(PermissionChangeRequest)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = (await session.execute(count_stmt)).scalar() or 0

    pending_stmt = (
        select(func.count()).select_from(PermissionChangeRequest).where(PermissionChangeRequest.status == "pending")
    )
    pending_count = (await session.execute(pending_stmt)).scalar() or 0

    # Paginated query
    offset = (page - 1) * limit
    stmt = (
        select(PermissionChangeRequest).order_by(PermissionChangeRequest.created_at.desc()).offset(offset).limit(limit)
    )
    if conditions:
        stmt = stmt.where(*conditions)

    result = await session.execute(stmt)
    requests = result.scalars().all()

    return PermissionChangeRequestListResponse(
        requests=[PermissionChangeRequestResponse.model_validate(r) for r in requests],
        total=total,
        pending_count=pending_count,
    )


@router.get("/api/admin/permission-requests/{request_id}", response_model=PermissionChangeRequestResponse)
async def get_permission_request(
    request_id: str,
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific permission change request."""
    from uuid import UUID

    try:
        uuid_id = UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format")

    admin = current_admin["admin"]
    is_superadmin = admin.role == "superadmin"

    stmt = select(PermissionChangeRequest).where(PermissionChangeRequest.id == uuid_id)
    result = await session.execute(stmt)
    pcr = result.scalar_one_or_none()

    if not pcr:
        raise HTTPException(status_code=404, detail="Request not found")

    # Non-superadmins can only see their own requests
    if not is_superadmin and pcr.requested_by != admin.email:
        raise HTTPException(status_code=403, detail="Not authorized to view this request")

    return PermissionChangeRequestResponse.model_validate(pcr)


@router.post("/api/admin/permission-requests/{request_id}/action")
async def act_on_permission_request(
    request_id: str,
    body: PermissionChangeRequestAction,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Approve or reject a permission change request (superadmin only).

    On approval, the permission is automatically granted/revoked.
    On rejection, the request is marked as rejected.
    """
    from uuid import UUID

    try:
        uuid_id = UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format")

    admin = current_admin["admin"]

    # Get the request
    stmt = select(PermissionChangeRequest).where(PermissionChangeRequest.id == uuid_id)
    result = await session.execute(stmt)
    pcr = result.scalar_one_or_none()

    if not pcr:
        raise HTTPException(status_code=404, detail="Request not found")

    if pcr.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {pcr.status}")

    now = datetime.now(timezone.utc)
    pcr.reviewed_by = admin.email
    pcr.reviewed_at = now
    pcr.reviewer_notes = body.reviewer_notes

    if body.action == "approve":
        pcr.status = "approved"

        # Apply the permission change
        target_email = pcr.target_email or pcr.requested_by

        # Upsert user-level override
        stmt = select(AdminUserPermission).where(
            AdminUserPermission.admin_email == target_email,
            AdminUserPermission.permission_code == pcr.permission_code,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.granted = pcr.desired_state
            existing.granted_at = now
        else:
            session.add(
                AdminUserPermission(
                    admin_email=target_email,
                    permission_code=pcr.permission_code,
                    granted=pcr.desired_state,
                    granted_by=admin.email,
                )
            )

        # Audit log
        await write_audit_log(
            db_session=session,
            admin_email=admin.email,
            action="permission.request.approve",
            resource_type="permission_request",
            resource_id=str(pcr.id),
            details={
                "target_email": target_email,
                "permission_code": pcr.permission_code,
                "desired_state": pcr.desired_state,
            },
        )

    else:  # reject
        pcr.status = "rejected"

        # Audit log
        await write_audit_log(
            db_session=session,
            admin_email=admin.email,
            action="permission.request.reject",
            resource_type="permission_request",
            resource_id=str(pcr.id),
            details={
                "requested_by": pcr.requested_by,
                "permission_code": pcr.permission_code,
                "reason": body.reviewer_notes,
            },
        )

    await session.commit()

    # Send notification to requester
    try:
        action_text = "approved" if body.action == "approve" else "rejected"
        await send_admin_notification(
            title=f"Permission Request {action_text.title()}",
            details={
                "request_id": str(pcr.id),
                "permission_code": pcr.permission_code,
                "status": pcr.status,
                "reviewed_by": admin.email,
                "reviewer_notes": body.reviewer_notes or "No notes provided",
            },
            pill_type="green" if body.action == "approve" else "red",
        )
    except Exception:
        pass  # Non-blocking

    return {
        "request_id": str(pcr.id),
        "status": pcr.status,
        "reviewed_by": admin.email,
        "reviewed_at": now.isoformat(),
    }
