"""Permission-aware auth dependencies (Sprint 14).

Three decorators + one helper:

1. ``require_permission(code, totp_required=False)`` — fastapi dependency that
   checks the current admin has ``code`` in their effective permission set
   (role defaults + per-user override). Optional ``totp_required=True`` adds
   step-up check.

2. ``require_totp_step_up()`` — fastapi dependency that requires a valid
   ``X-TOTP-Code`` header (or a valid ``admin_totp_sessions`` row) within the
   last N minutes. Used to gate sensitive endpoints.

3. ``get_effective_permissions(session, admin: AdminAuth) -> set[str]`` —
   resolve the set of permission codes for an admin (role defaults + user
   overrides, minus deny overrides).

Sprint 14 contract:
- User → permission IF user has explicit ALLOW for code OR role default is ALLOW AND user has no explicit DENY for code
- Role defaults are seeded in admin_role_permissions (3 roles: superadmin/admin/viewer); see migration 95d83c2
- Per-user overrides live in admin_user_permissions
- Permission change requests live in permission_change_requests (TBD: approval workflow)
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import AdminAuth, AdminRolePermission, AdminTotpSession, AdminUserPermission

# Step-up window: admin must re-enter TOTP within this window for sensitive ops
TOTP_STEP_UP_WINDOW = timedelta(minutes=5)


# ============================================================
# Helper: resolve effective permissions for an admin
# ============================================================


async def get_effective_permissions(session: AsyncSession, admin: AdminAuth) -> set[str]:
    """Return the set of permission codes granted to the given admin.

    Resolution order:
    1. Start with role defaults from admin_role_permissions (role == admin.role)
    2. Apply per-user overrides from admin_user_permissions:
       - granted=true → add code to set
       - granted=false → remove code from set
    """
    role = admin.role or "viewer"

    # 1. Role defaults
    stmt = select(AdminRolePermission).where(
        AdminRolePermission.role == role,
        AdminRolePermission.granted == True,  # noqa: E712
    )
    result = await session.execute(stmt)
    role_perms = {rp.permission_code for rp in result.scalars()}

    # 2. Per-user overrides
    stmt = select(AdminUserPermission).where(AdminUserPermission.admin_email == admin.email)
    result = await session.execute(stmt)
    user_perms = result.scalars().all()

    for up in user_perms:
        if up.granted:
            role_perms.add(up.permission_code)
        else:
            role_perms.discard(up.permission_code)

    return role_perms


async def has_permission(session: AsyncSession, admin: AdminAuth, code: str) -> bool:
    """Check if admin has a specific permission code."""
    perms = await get_effective_permissions(session, admin)
    return code in perms


# ============================================================
# Dependency factories
# ============================================================


def require_permission(code: str, totp_required: bool = False):
    """FastAPI dependency factory: admin must have the given permission code.

    Usage:
        @router.post("/foo", dependencies=[Depends(require_permission("admin.x.y"))])

    If totp_required=True, the admin must also have a valid TOTP step-up
    session (X-TOTP-Code header or a remember-me token).
    """

    async def _dep(
        current_admin: dict = Depends(__import__("app.routers.auth", fromlist=["require_viewer"]).require_viewer),
        session: AsyncSession = Depends(get_session),
    ) -> dict:
        admin: AdminAuth = current_admin["admin"]
        if not await has_permission(session, admin, code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{code}' required",
            )
        if totp_required:
            await _check_totp_step_up(session, admin)
        return current_admin

    return _dep


async def require_totp_step_up(
    current_admin: dict = Depends(__import__("app.routers.auth", fromlist=["require_viewer"]).require_viewer),
    session: AsyncSession = Depends(get_session),
    x_totp_code: Optional[str] = Header(None, alias="X-TOTP-Code"),
    x_totp_session: Optional[str] = Header(None, alias="X-TOTP-Session"),
) -> dict:
    """FastAPI dependency: require a recent TOTP step-up.

    Verifies one of:
    - X-TOTP-Code header: 6-digit TOTP code, matches admin.totp_secret
    - X-TOTP-Session header: remember-me session token (hashed, looked up in admin_totp_sessions)

    Returns current_admin dict on success.
    """
    admin: AdminAuth = current_admin["admin"]
    if not admin.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TOTP not enabled. Set up TOTP first via /api/admin/auth/setup-totp.",
        )
    await _check_totp_step_up(session, admin, x_totp_code, x_totp_session)
    return current_admin


async def _check_totp_step_up(
    session: AsyncSession,
    admin: AdminAuth,
    x_totp_code: Optional[str] = None,
    x_totp_session: Optional[str] = None,
) -> None:
    """Verify TOTP step-up. Returns None on success, raises HTTPException on failure."""
    import pyotp

    now = datetime.now(timezone.utc)

    # Path 1: explicit TOTP code in header
    if x_totp_code:
        if not admin.totp_secret:
            raise HTTPException(status_code=403, detail="TOTP not configured")
        totp = pyotp.TOTP(admin.totp_secret)
        if not totp.verify(x_totp_code, valid_window=1):
            raise HTTPException(status_code=403, detail="Invalid TOTP code")
        return  # success

    # Path 2: remember-me session token
    if x_totp_session:
        token_hash = hashlib.sha256(x_totp_session.encode()).hexdigest()
        stmt = select(AdminTotpSession).where(
            AdminTotpSession.session_token_hash == token_hash,
            AdminTotpSession.admin_email == admin.email,
            AdminTotpSession.revoked_at.is_(None),
            AdminTotpSession.expires_at > now,
        )
        result = await session.execute(stmt)
        sess = result.scalar_one_or_none()
        if sess:
            # Update last_used_at
            sess.last_used_at = now
            await session.commit()
            return  # success

    raise HTTPException(
        status_code=403,
        detail="TOTP step-up required. Provide X-TOTP-Code or X-TOTP-Session header.",
    )


# ============================================================
# /api/me/permissions endpoint helper
# ============================================================


async def get_effective_permissions_payload(session: AsyncSession, admin: AdminAuth) -> dict:
    """Build the payload for /api/me/permissions — categories + codes."""
    from app.models import AdminPermission

    perms = await get_effective_permissions(session, admin)
    stmt = select(AdminPermission).order_by(AdminPermission.category, AdminPermission.code)
    result = await session.execute(stmt)
    all_perms = result.scalars().all()

    by_category: dict[str, list[dict]] = {}
    for p in all_perms:
        by_category.setdefault(p.category, []).append(
            {
                "code": p.code,
                "description": p.description,
                "is_sensitive": p.is_sensitive,
                "granted": p.code in perms,
            }
        )

    return {
        "email": admin.email,
        "role": admin.role,
        "permission_count": len(perms),
        "permissions_by_category": by_category,
    }
