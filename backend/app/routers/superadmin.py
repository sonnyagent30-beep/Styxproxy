"""Superadmin router - administrative functions for system management."""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    AdminAuth,
    AdminInvite,
    AdminAuditLog,
    Order,
    StyxproxyCredential,
    Customer,
    SupportThread,
    ContactSubmission,
    CharonEscalation,
    FeatureFlag,
)
from app.schemas import (
    AdminAuditLogEntryResponse,
    AdminAuditLogListResponse,
    SuperadminAdminResponse,
    SuperadminAdminsListResponse,
    SuperadminCreateAdminRequest,
    SuperadminCreateAdminResponse,
    SuperadminUpdateRoleRequest,
    ProviderCostsResponse,
    ProviderCostResponse,
    SystemSettingsListResponse,
    SystemSettingResponse,
    SystemSettingUpdateRequest,
    GlobalSearchResponse,
    GlobalSearchCustomerResult,
    GlobalSearchOrderResult,
    GlobalSearchTicketResult,
    GlobalSearchContactResult,
    MetricsOverviewResponse,
)
from app.auth import get_password_hash
from app.routers.auth import require_superadmin
from app.services.audit import write_audit_log
from app.services.email import send_admin_invite_email

router = APIRouter(prefix="/api/admin", tags=["superadmin"])


def generate_temp_password(length: int = 16) -> str:
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ============== Audit Log Endpoints ==============

@router.get("/audit-log", response_model=AdminAuditLogListResponse)
async def get_admin_audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    admin_email: Optional[str] = None,
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get paginated admin audit log entries (superadmin only).

    Filters by action, admin_email (matched against admin_phone column where
    we store the email), and date range. The details column is JSON-encoded
    so we surface admin_email/resource_type/resource_id/dict from it.
    """
    import json

    # Build filters
    conditions = []
    if action:
        conditions.append(AdminAuditLog.action == action)
    if from_date:
        conditions.append(AdminAuditLog.created_at >= from_date)
    if to_date:
        conditions.append(AdminAuditLog.created_at <= to_date)
    if admin_email:
        # admin_email lives in the details blob (admin_phone column carries
        # the email in practice). We'll filter after fetching below.
        pass

    # Count query
    count_stmt = select(func.count()).select_from(AdminAuditLog)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0

    # Data query
    offset = (page - 1) * limit
    stmt = (
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))
    logs = (await session.execute(stmt)).scalars().all()

    entries = []
    for log in logs:
        parsed_details: dict = {}
        if log.details:
            try:
                parsed_details = json.loads(log.details)
            except (TypeError, ValueError):
                parsed_details = {}

        if admin_email and parsed_details.get("admin_email") != admin_email:
            continue

        entries.append(
            AdminAuditLogEntryResponse(
                id=log.id,
                admin_email=parsed_details.get("admin_email") or log.admin_phone,
                admin_phone=log.admin_phone,
                action=log.action,
                resource_type=parsed_details.get("resource_type"),
                resource_id=parsed_details.get("resource_id"),
                details=parsed_details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
        )

    return AdminAuditLogListResponse(
        logs=entries,
        pagination={
            "page": page,
            "limit": limit,
            "total_items": len(entries),
            "total_pages": (len(entries) + limit - 1) // limit if entries else 0,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


# ============== Admin Management Endpoints ==============

@router.get("/admins", response_model=SuperadminAdminsListResponse)
async def list_admins(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """List all admins with role from AdminAuth (not invite lookup)."""
    # Get total count
    count_stmt = select(func.count()).select_from(AdminAuth)
    total = (await session.execute(count_stmt)).scalar() or 0

    # Get superadmin count
    superadmin_stmt = select(func.count()).select_from(AdminAuth).where(AdminAuth.role == "superadmin")
    superadmins_count = (await session.execute(superadmin_stmt)).scalar() or 0

    # Paginated query
    offset = (page - 1) * limit
    stmt = (
        select(AdminAuth)
        .order_by(AdminAuth.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    admins = (await session.execute(stmt)).scalars().all()

    return SuperadminAdminsListResponse(
        admins=[
            SuperadminAdminResponse(
                email=admin.email or "",
                role=admin.role,
                totp_enabled=admin.totp_enabled,
                failed_attempts=admin.failed_attempts,
                locked_until=admin.locked_until,
                created_at=admin.created_at,
                last_used=admin.last_used,
            )
            for admin in admins
        ],
        stats={
            "total_admins": total,
            "superadmins_count": superadmins_count,
        },
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.post("/admins", response_model=SuperadminCreateAdminResponse)
async def create_admin(
    request: SuperadminCreateAdminRequest,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
    http_request: Request = None,
):
    """Create a new admin (superadmin only)."""
    # Check if admin already exists
    stmt = select(AdminAuth).where(AdminAuth.email == request.email)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this email already exists",
        )

    # Create admin with role
    admin = AdminAuth(
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=request.role,
    )
    session.add(admin)

    # Also create an invite record for tracking
    invite = AdminInvite(
        invite_code=secrets.token_urlsafe(16),
        email=request.email,
        role=request.role,
        created_by=current_admin["email"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        max_uses=1,
        uses_count=1,
        used_at=datetime.now(timezone.utc),
        used_by=request.email,
    )
    session.add(invite)
    await session.commit()

    # Write audit log
    await write_audit_log(
        session,
        admin_email=current_admin["email"],
        action="create_admin",
        resource_type="admin",
        resource_id=request.email,
        details={"role": request.role},
        request=http_request,
    )

    return SuperadminCreateAdminResponse(
        email=request.email,
        role=request.role,
        message=f"Admin created with role '{request.role}'",
    )


@router.patch("/admins/{admin_email}/role", response_model=dict)
async def update_admin_role(
    admin_email: str,
    request: SuperadminUpdateRoleRequest,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
    http_request: Request = None,
):
    """Update an admin's role (superadmin only)."""
    # Find admin
    stmt = select(AdminAuth).where(AdminAuth.email == admin_email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    old_role = admin.role
    admin.role = request.role

    # Also update invite table if exists
    stmt = select(AdminInvite).where(AdminInvite.used_by == admin_email)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()
    if invite:
        invite.role = request.role

    await session.commit()

    # Write audit log
    await write_audit_log(
        session,
        admin_email=current_admin["email"],
        action="update_role",
        resource_type="admin",
        resource_id=admin_email,
        details={"old_role": old_role, "new_role": request.role},
        request=http_request,
    )

    return {
        "email": admin_email,
        "role": request.role,
        "message": f"Role updated from '{old_role}' to '{request.role}'",
    }


@router.delete("/admins/{admin_email}")
async def delete_admin(
    admin_email: str,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
    http_request: Request = None,
):
    """Soft-delete an admin by setting role to viewer and locking (superadmin only)."""
    # Find admin
    stmt = select(AdminAuth).where(AdminAuth.email == admin_email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    # Cannot delete yourself
    if admin_email == current_admin["email"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    old_role = admin.role

    # Set role to viewer and lock account
    admin.role = "viewer"
    admin.locked_until = datetime.now(timezone.utc) + timedelta(days=365 * 10)  # Lock for 10 years

    # Also update invite table
    stmt = select(AdminInvite).where(AdminInvite.used_by == admin_email)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()
    if invite:
        invite.role = "viewer"

    await session.commit()

    # Write audit log
    await write_audit_log(
        session,
        admin_email=current_admin["email"],
        action="delete_admin",
        resource_type="admin",
        resource_id=admin_email,
        details={"old_role": old_role},
        request=http_request,
    )

    return {
        "message": f"Admin '{admin_email}' has been deactivated (role set to viewer, account locked)",
    }


@router.post("/admins/{admin_email}/lock", response_model=dict)
async def lock_admin(
    admin_email: str,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
    http_request: Request = None,
):
    """Lock an admin account (superadmin only)."""
    stmt = select(AdminAuth).where(AdminAuth.email == admin_email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    admin.locked_until = datetime.now(timezone.utc) + timedelta(days=365)
    await session.commit()

    # Write audit log
    await write_audit_log(
        session,
        admin_email=current_admin["email"],
        action="lock_account",
        resource_type="admin",
        resource_id=admin_email,
        request=http_request,
    )

    return {
        "email": admin_email,
        "locked": True,
        "message": f"Admin '{admin_email}' has been locked",
    }


@router.post("/admins/{admin_email}/unlock", response_model=dict)
async def unlock_admin(
    admin_email: str,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
    http_request: Request = None,
):
    """Unlock an admin account (superadmin only)."""
    stmt = select(AdminAuth).where(AdminAuth.email == admin_email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    admin.locked_until = None
    admin.failed_attempts = 0
    await session.commit()

    # Write audit log
    await write_audit_log(
        session,
        admin_email=current_admin["email"],
        action="unlock_account",
        resource_type="admin",
        resource_id=admin_email,
        request=http_request,
    )

    return {
        "email": admin_email,
        "locked": False,
        "message": f"Admin '{admin_email}' has been unlocked",
    }


# ============== Provider Costs Endpoint ==============

@router.get("/providers/costs", response_model=ProviderCostsResponse)
async def get_provider_costs(
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregated provider cost data."""
    # Try to get provider costs from orders
    stmt = (
        select(
            Order.provider,
            func.count(Order.order_id).label("total_orders"),
            func.sum(Order.cost_usd).label("total_cost_usd"),
        )
        .where(Order.provider.isnot(None))
        .group_by(Order.provider)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return ProviderCostsResponse(
            providers=[],
            note="No provider cost data available",
        )

    providers = [
        ProviderCostResponse(
            name=row.provider or "unknown",
            total_orders=row.total_orders,
            total_cost_usd=float(row.total_cost_usd or 0),
        )
        for row in rows
    ]

    return ProviderCostsResponse(providers=providers)


# ============== System Settings Endpoints ==============

@router.get("/settings", response_model=SystemSettingsListResponse)
async def list_settings(
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """List system settings (superadmin only)."""
    # Check if feature_flags table has system settings
    # For now, return empty list as there's no dedicated system_settings table
    return SystemSettingsListResponse(
        settings=[],
        note="System settings not yet implemented. Use feature flags for configuration.",
    )


@router.patch("/settings/{key}", response_model=dict)
async def update_setting(
    key: str,
    request: SystemSettingUpdateRequest,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
    http_request: Request = None,
):
    """Update a system setting (superadmin only)."""
    # Check if feature flag exists
    stmt = select(FeatureFlag).where(FeatureFlag.name == key)
    result = await session.execute(stmt)
    flag = result.scalar_one_or_none()

    if flag:
        # Update existing feature flag
        flag.enabled = request.value if isinstance(request.value, bool) else flag.enabled
        await session.commit()

    # Write audit log
    await write_audit_log(
        session,
        admin_email=current_admin["email"],
        action="update_settings",
        resource_type="settings",
        resource_id=key,
        details={"value": str(request.value)},
        request=http_request,
    )

    return {
        "key": key,
        "value": request.value,
        "message": f"Setting '{key}' updated",
    }


# ============== Global Search Endpoint ==============

@router.get("/search", response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, description="Search query"),
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Global search across customers, orders, support threads, and contact submissions."""
    customers = []
    orders = []
    tickets = []
    contacts = []

    # Search customers (phone or name)
    customer_stmt = (
        select(Customer)
        .where(
            (Customer.phone.ilike(f"%{q}%")) | (Customer.name.ilike(f"%{q}%"))
        )
        .limit(10)
    )
    customer_results = (await session.execute(customer_stmt)).scalars().all()
    for c in customer_results:
        customers.append(
            GlobalSearchCustomerResult(
                id=str(c.id),
                phone=c.phone,
                name=c.name,
            )
        )

    # Search orders (order_id)
    order_stmt = (
        select(Order)
        .where(Order.order_id.ilike(f"%{q}%"))
        .limit(10)
    )
    order_results = (await session.execute(order_stmt)).scalars().all()
    for o in order_results:
        orders.append(
            GlobalSearchOrderResult(
                order_id=o.order_id,
                customer_phone=o.customer_phone,
                status=o.status,
                amount_paid_ngn=o.amount_paid_ngn,
            )
        )

    # Search support threads (subject or from_email)
    thread_stmt = (
        select(SupportThread)
        .where(
            (SupportThread.subject.ilike(f"%{q}%"))
            | (SupportThread.customer_email.ilike(f"%{q}%"))
        )
        .limit(10)
    )
    thread_results = (await session.execute(thread_stmt)).scalars().all()
    for t in thread_results:
        tickets.append(
            GlobalSearchTicketResult(
                id=str(t.id),
                subject=t.subject,
                customer_email=t.customer_email,
                status=t.status,
            )
        )

    # Search contact submissions (subject or from_email)
    contact_stmt = (
        select(ContactSubmission)
        .where(
            (ContactSubmission.subject.ilike(f"%{q}%"))
            | (ContactSubmission.from_email.ilike(f"%{q}%"))
        )
        .limit(10)
    )
    contact_results = (await session.execute(contact_stmt)).scalars().all()
    for c in contact_results:
        contacts.append(
            GlobalSearchContactResult(
                id=str(c.id),
                from_email=c.from_email,
                subject=c.subject,
                status=c.status,
            )
        )

    total = len(customers) + len(orders) + len(tickets) + len(contacts)

    return GlobalSearchResponse(
        results={
            "customers": [c.model_dump() for c in customers],
            "orders": [o.model_dump() for o in orders],
            "tickets": [t.model_dump() for t in tickets],
            "contacts": [c.model_dump() for c in contacts],
        },
        total=total,
    )


# ============== Metrics Overview Endpoint ==============

@router.get("/metrics/overview", response_model=MetricsOverviewResponse)
async def get_metrics_overview(
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get system metrics overview."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Orders today
    orders_today = (
        await session.execute(
            select(func.count()).select_from(Order).where(Order.created_at >= today_start)
        )
    ).scalar() or 0

    # Orders this week
    orders_this_week = (
        await session.execute(
            select(func.count()).select_from(Order).where(Order.created_at >= week_start)
        )
    ).scalar() or 0

    # Revenue today (in NGN)
    revenue_today_stmt = (
        select(func.sum(Order.amount_paid_ngn))
        .where(
            and_(
                Order.created_at >= today_start,
                Order.status.in_(["active", "fulfilled"]),
            )
        )
    )
    revenue_today_ngn = float((await session.execute(revenue_today_stmt)).scalar() or 0)

    # Revenue this week
    revenue_week_stmt = (
        select(func.sum(Order.amount_paid_ngn))
        .where(
            and_(
                Order.created_at >= week_start,
                Order.status.in_(["active", "fulfilled"]),
            )
        )
    )
    revenue_this_week_ngn = float((await session.execute(revenue_week_stmt)).scalar() or 0)

    # Revenue this month
    revenue_month_stmt = (
        select(func.sum(Order.amount_paid_ngn))
        .where(
            and_(
                Order.created_at >= month_start,
                Order.status.in_(["active", "fulfilled"]),
            )
        )
    )
    revenue_this_month_ngn = float((await session.execute(revenue_month_stmt)).scalar() or 0)

    # Active proxies (credentials)
    active_proxies = (
        await session.execute(
            select(func.count()).select_from(StyxproxyCredential).where(StyxproxyCredential.status == "active")
        )
    ).scalar() or 0

    # Churned today (orders that expired today)
    churned_today = (
        await session.execute(
            select(func.count()).select_from(Order).where(Order.expires_at >= today_start)
        )
    ).scalar() or 0

    # Open escalations
    escalations_open = (
        await session.execute(
            select(func.count()).select_from(CharonEscalation).where(CharonEscalation.status == "open")
        )
    ).scalar() or 0

    # Open support threads
    support_threads_open = (
        await session.execute(
            select(func.count()).select_from(SupportThread).where(SupportThread.status == "open")
        )
    ).scalar() or 0

    # Pending contact submissions
    contact_submissions_open = (
        await session.execute(
            select(func.count()).select_from(ContactSubmission).where(ContactSubmission.status == "pending")
        )
    ).scalar() or 0

    return MetricsOverviewResponse(
        orders_today=orders_today,
        orders_this_week=orders_this_week,
        revenue_today_ngn=revenue_today_ngn,
        revenue_this_week_ngn=revenue_this_week_ngn,
        revenue_this_month_ngn=revenue_this_month_ngn,
        active_proxies=active_proxies,
        churned_today=churned_today,
        escalations_open=escalations_open,
        support_threads_open=support_threads_open,
        contact_submissions_open=contact_submissions_open,
        charon_llm_status=_charon_llm_status(),
        charon_total_requests=_charon_stats().total_requests,
        charon_escalated_replies=_charon_stats().escalated_replies,
        charon_llm_errors=_charon_stats().llm_errors,
        charon_tokens_used_total=_charon_stats().tokens_used_total,
    )


def _charon_stats():
    """Lazy import so a missing Charon module doesn't break metrics."""
    try:
        from app.services.charon.stats import CharonMetrics
        return CharonMetrics.get()
    except Exception:
        # Return a zero-shaped stub so the response model always validates.
        from app.services.charon.stats import CharonStats
        return CharonStats()


def _charon_llm_status() -> str:
    """Best-effort 'up' / 'degraded' / 'down' indicator for the dashboard."""
    try:
        import os
        # P0-5 (Jul 22 2026): primary is M2 cloud. Always check the
        # cloud key — local-only is no longer a configuration.
        if not os.getenv("MINIMAX_API_KEY"):
            # No M2 key configured — degraded even if local is up
            pass
        s = _charon_stats()
        if not getattr(s, "llm_configured", False):
            # Probe by checking Ollama reachability? Keep simple: report based on counters.
            return "unknown"
        if s.llm_errors > 0 and (s.llm_last_error_at and (s.llm_last_success_at is None or s.llm_last_error_at > s.llm_last_success_at)):
            return "degraded"
        if s.llm_last_success_at is None and s.total_requests > 0:
            return "degraded"
        return "up"
    except Exception:
        return "unknown"


# ============== Charon Stats ==============

@router.get("/charon/stats")
async def get_charon_stats(
    current_admin: dict = Depends(require_superadmin),
):
    """Detailed Charon runtime stats (superadmin only).

    Returns counters + recent errors + latency aggregates. Backed by the
    in-process stats singleton in services/charon/stats.py. Useful for
    diagnosing "is Charon actually responding?" issues.
    """
    # Imported lazily so a missing / non-functional charon module
    # doesn't break superadmin startup.
    try:
        from app.services.charon.stats import CharonMetrics
        return CharonMetrics.get().to_dict()
    except Exception as e:
        return {
            "error": f"stats module unavailable: {e}",
            "uptime_seconds": 0,
        }


@router.post("/charon/reset")
async def reset_charon_stats(
    current_admin: dict = Depends(require_superadmin),
):
    """Reset Charon counters to zero. Useful after deploying a config fix."""
    try:
        from app.services.charon.stats import CharonMetrics
        CharonMetrics.reset()
        return {"ok": True, "reset_at": "now"}
    except Exception as e:
        return {"ok": False, "error": str(e)}



