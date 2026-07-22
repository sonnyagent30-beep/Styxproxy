"""Admin router."""
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_session
from app.models import Customer, Order, StyxproxyCredential, FreeTrial, CustomerAuditLog, ProcessedWebhook, FeatureFlag, Plan, ContactSubmission, CharonEscalation
from app.schemas import (
    AdminStatsResponse, AdminCustomerResponse, AdminCustomersResponse, AdminBlockRequest,
    AdminOrderResponse, AdminOrdersResponse, AdminOrderUpdateRequest, AdminRefundRequest,
    AdminCredentialResponse, AdminCredentialsResponse, AdminAuditLogsResponse, AdminAuditLogResponse,
    AdminWebhookLogsResponse, AdminWebhookLogResponse,
    LearnedFilesResponse, LearnedFileResponse, LearnContentResponse, 
    DeleteLearnedFileRequest, DeleteLearnedFileResponse,
    PlanResponse, PlansResponse, PlanCreateRequest, PlanUpdateRequest,
    ChannelFeatureFlagsResponse, ChannelFeatureFlagsUpdate, ChannelConfig,
    ContactSubmissionResponse, ContactSubmissionsResponse, ContactSubmissionReplyRequest,
    CharonEscalationResponse, EscalationsResponse, EscalationRespondRequest,
)
from app.auth import admin_only, admin_only_with_email
from app.services.audit import write_audit_log
from app.services.credential import replace_credential
from app.services.trial import get_trials_today_count
from app.services.audit import get_audit_logs
from app.services.email import send_refund_request_notification, send_refund_approved_notification, send_refund_processed_email
from pathlib import Path

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health", dependencies=[Depends(admin_only)])
async def admin_health():
    return {"status": "healthy", "admin": True}


@router.get("/stats", response_model=AdminStatsResponse, dependencies=[Depends(admin_only)])
async def get_stats(session: AsyncSession = Depends(get_session)):
    total_customers = (await session.execute(select(func.count()).select_from(Customer))).scalar() or 0
    active_orders = (await session.execute(select(func.count()).select_from(Order).where(Order.status == "active"))).scalar() or 0
    total_revenue = (await session.execute(select(func.sum(Order.amount_paid_ngn)).where(Order.status.in_(["active", "fulfilled"])))).scalar() or 0
    free_trials_today = await get_trials_today_count(session)
    active_credentials = (await session.execute(select(func.count()).select_from(StyxproxyCredential).where(StyxproxyCredential.status == "active"))).scalar() or 0
    return AdminStatsResponse(
        total_customers=total_customers,
        active_orders=active_orders,
        total_revenue_ngn=float(total_revenue or 0),
        free_trials_today=free_trials_today,
        active_credentials=active_credentials,
    )


@router.get("/customers", response_model=AdminCustomersResponse, dependencies=[Depends(admin_only)])
async def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    blocked: Optional[bool] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    conditions = []
    if blocked is not None:
        conditions.append(Customer.blocked == blocked)
    if search:
        # Sanitise search term: escape LIKE/ILIKE special chars (% _ \)
        escaped = re.sub(r"([%_\\])", r"\\\1", search)
        conditions.append(
            (Customer.phone.ilike(f"%{escaped}%", escape="\\"))
            | (Customer.name.ilike(f"%{escaped}%", escape="\\"))
        )
    count_stmt = select(func.count()).select_from(Customer)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * limit
    stmt = select(Customer).order_by(Customer.created_at.desc()).offset(offset).limit(limit)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    customers = (await session.execute(stmt)).scalars().all()
    return AdminCustomersResponse(
        customers=[AdminCustomerResponse.model_validate(c) for c in customers],
        pagination={
            "page": page, "limit": limit, "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/customers/{customer_id}", response_model=AdminCustomerResponse, dependencies=[Depends(admin_only)])
async def get_customer(customer_id: UUID, session: AsyncSession = Depends(get_session)):
    customer = (await session.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return AdminCustomerResponse.model_validate(customer)


@router.post("/customers/{customer_id}/block", dependencies=[Depends(admin_only)])
async def block_customer(customer_id: UUID, request: AdminBlockRequest, session: AsyncSession = Depends(get_session)):
    customer = (await session.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    customer.blocked = True
    customer.blocked_reason = request.reason
    await session.commit()
    return {"status": "blocked", "customer_id": str(customer_id)}


@router.post("/customers/{customer_id}/unblock", dependencies=[Depends(admin_only)])
async def unblock_customer(customer_id: UUID, session: AsyncSession = Depends(get_session)):
    customer = (await session.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    customer.blocked = False
    customer.blocked_reason = None
    await session.commit()
    return {"status": "unblocked", "customer_id": str(customer_id)}


@router.get("/orders", response_model=AdminOrdersResponse, dependencies=[Depends(admin_only)])
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_phone: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
):
    conditions = []
    if status_filter:
        conditions.append(Order.status == status_filter)
    if customer_phone:
        conditions.append(Order.customer_phone == customer_phone)
    if date_from:
        conditions.append(Order.created_at >= date_from)
    if date_to:
        conditions.append(Order.created_at <= date_to)
    count_stmt = select(func.count()).select_from(Order)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * limit
    stmt = select(Order).order_by(Order.created_at.desc()).offset(offset).limit(limit)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    orders = (await session.execute(stmt)).scalars().all()
    return AdminOrdersResponse(
        orders=[AdminOrderResponse.model_validate(o) for o in orders],
        pagination={
            "page": page, "limit": limit, "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/orders/{order_id}", response_model=AdminOrderResponse, dependencies=[Depends(admin_only)])
async def get_order(order_id: str, session: AsyncSession = Depends(get_session)):
    order = (await session.execute(select(Order).where(Order.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return AdminOrderResponse.model_validate(order)


@router.patch("/orders/{order_id}")
async def update_order(
    order_id: str,
    body: AdminOrderUpdateRequest,
    http_request: Request,
    admin_email: str = Depends(admin_only_with_email),
    session: AsyncSession = Depends(get_session),
):
    order = (await session.execute(select(Order).where(Order.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    changes: dict = {}
    if body.status:
        changes["status"] = {"old": order.status, "new": body.status}
        order.status = body.status
        if body.status == "fulfilled":
            order.fulfilled_at = datetime.now(timezone.utc)
    if body.notes is not None:
        changes["notes_set"] = True
        order.notes = body.notes
    if body.ban_verified:
        changes["ban_verified"] = body.ban_verified
        order.ban_verified = body.ban_verified
    await session.commit()

    await write_audit_log(
        session,
        admin_email=admin_email,
        action="update_order",
        resource_type="order",
        resource_id=order_id,
        details={"changes": changes},
        request=http_request,
    )

    return {"status": "updated", "order_id": order_id}


@router.post("/orders/{order_id}/refund")
async def refund_order(
    order_id: str,
    body: AdminRefundRequest,
    http_request: Request,
    admin_email: str = Depends(admin_only_with_email),
    session: AsyncSession = Depends(get_session),
):
    order = (await session.execute(select(Order).where(Order.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status in ["refunded", "cancelled"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order already refunded or cancelled")
    order.status = "refunded"
    order.refund_requested = True
    order.refund_reason = body.reason
    if order.styxproxy_credential_id:
        cred = (await session.execute(select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id))).scalar_one_or_none()
        if cred:
            cred.status = "revoked"
    await session.commit()

    await write_audit_log(
        session,
        admin_email=admin_email,
        action="refund_order",
        resource_type="order",
        resource_id=order_id,
        details={"reason": body.reason, "full_refund": body.full_refund},
        request=http_request,
    )

    # Send admin notification
    await send_refund_approved_notification(
        order_id=order_id,
        customer_phone=order.customer_phone or "",
        amount=float(order.amount_paid_ngn or 0),
        currency="NGN",
    )
    
    # Send refund processed email to customer if email available
    customer = None
    if order.customer_phone:
        customer = (await session.execute(select(Customer).where(Customer.phone == order.customer_phone))).scalar_one_or_none()
    
    if customer:
        customer_email = getattr(customer, 'email', None)
        if customer_email:
            try:
                await send_refund_processed_email(
                    customer_email=customer_email,
                    customer_name=customer.name if customer.name else "Customer",
                    order_id=order_id,
                    amount=float(order.amount_paid_ngn or 0),
                    currency="NGN",
                    reason=request.reason or "Refund processed",
                )
            except Exception:
                pass
    
    return {"status": "refunded", "order_id": order_id, "refund_amount": float(order.amount_paid_ngn or 0)}


@router.post("/credentials/{credential_id}/replace", dependencies=[Depends(admin_only)])
async def replace_credential_endpoint(credential_id: int, session: AsyncSession = Depends(get_session)):
    new_credential = await replace_credential(session, credential_id, "admin_replacement")
    if not new_credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return {"status": "replaced", "old_credential_id": credential_id, "new_credential_id": new_credential.id}


@router.get("/credentials", response_model=AdminCredentialsResponse, dependencies=[Depends(admin_only)])
async def list_credentials(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    pool_type: Optional[str] = None,
    customer_phone: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    conditions = []
    if status_filter:
        conditions.append(StyxproxyCredential.status == status_filter)
    if pool_type:
        conditions.append(StyxproxyCredential.pool_type == pool_type)
    if customer_phone:
        conditions.append(StyxproxyCredential.customer_phone == customer_phone)
    count_stmt = select(func.count()).select_from(StyxproxyCredential)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * limit
    stmt = select(StyxproxyCredential).order_by(StyxproxyCredential.created_at.desc()).offset(offset).limit(limit)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    credentials = (await session.execute(stmt)).scalars().all()
    return AdminCredentialsResponse(
        credentials=[AdminCredentialResponse.model_validate(c) for c in credentials],
        pagination={
            "page": page, "limit": limit, "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/audit", response_model=AdminAuditLogsResponse, dependencies=[Depends(admin_only)])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    customer_hash: Optional[str] = None,
    event_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
):
    logs, total = await get_audit_logs(
        session,
        customer_hash=customer_hash,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    return AdminAuditLogsResponse(
        logs=[AdminAuditLogResponse.model_validate(log) for log in logs],
        pagination={
            "page": page, "limit": limit, "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/webhooks", response_model=AdminWebhookLogsResponse, dependencies=[Depends(admin_only)])
async def list_webhook_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    total = (await session.execute(select(func.count()).select_from(ProcessedWebhook))).scalar() or 0
    offset = (page - 1) * limit
    stmt = select(ProcessedWebhook).order_by(ProcessedWebhook.processed_at.desc()).offset(offset).limit(limit)
    webhooks = (await session.execute(stmt)).scalars().all()
    return AdminWebhookLogsResponse(
        webhooks=[AdminWebhookLogResponse.model_validate(w) for w in webhooks],
        pagination={
            "page": page, "limit": limit, "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


# Charon Learned Files Management
LEARNED_DIR = Path(__file__).parents[3] / "data" / "charon" / "learned"


@router.get("/charon/learned", response_model=LearnedFilesResponse, dependencies=[Depends(admin_only)])
async def list_learned_files():
    """List all learned files in the RAG knowledge base."""
    if not LEARNED_DIR.exists():
        return LearnedFilesResponse(files=[])
    
    files = []
    for path in sorted(LEARNED_DIR.rglob("*.md")):
        stat = path.stat()
        files.append(LearnedFileResponse(
            name=path.name,
            path=str(path.relative_to(LEARNED_DIR.parent.parent)),
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        ))
    return LearnedFilesResponse(files=files)


@router.get("/charon/learned/{filename}", response_model=LearnContentResponse, dependencies=[Depends(admin_only)])
async def get_learned_file_content(filename: str):
    """Get the content of a specific learned file."""
    # Security: prevent path traversal
    filename = filename.replace("..", "").replace("/", "")
    filepath = LEARNED_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    if not filepath.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a file")
    
    content = filepath.read_text(encoding="utf-8")
    return LearnContentResponse(
        name=filepath.name,
        path=str(filepath.relative_to(LEARNED_DIR.parent.parent)),
        content=content,
    )


@router.delete("/charon/learned", response_model=DeleteLearnedFileResponse, dependencies=[Depends(admin_only)])
async def delete_learned_file(request: DeleteLearnedFileRequest):
    """Delete a learned file from the RAG knowledge base."""
    # Security: prevent path traversal
    filename = request.filename.replace("..", "").replace("/", "")
    filepath = LEARNED_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    if not filepath.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a file")
    
    filepath.unlink()
    
    # Invalidate cache after deletion
    from app.services.charon.knowledge import invalidate_cache
    invalidate_cache()
    
    return DeleteLearnedFileResponse(
        ok=True,
        message=f"Deleted {filename}",
    )


# ============== Plans CRUD ==============

@router.get("/plans", response_model=PlansResponse, dependencies=[Depends(admin_only)])
async def list_plans(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    plan_type: Optional[str] = None,
    country: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
):
    """List all plans with pagination and filters."""
    conditions = []
    if plan_type:
        conditions.append(Plan.plan_type == plan_type.upper())
    if country:
        conditions.append(Plan.country == country.upper())
    if is_active is not None:
        conditions.append(Plan.is_active == is_active)
    
    count_stmt = select(func.count()).select_from(Plan)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    
    offset = (page - 1) * limit
    stmt = select(Plan).order_by(Plan.sort_order, Plan.plan_code).offset(offset).limit(limit)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    plans = (await session.execute(stmt)).scalars().all()
    
    return PlansResponse(
        plans=[PlanResponse.model_validate(p) for p in plans],
        pagination={
            "page": page, "limit": limit, "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse, dependencies=[Depends(admin_only)])
async def get_plan(plan_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single plan by ID."""
    plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return PlanResponse.model_validate(plan)


@router.post("/plans", response_model=PlanResponse, dependencies=[Depends(admin_only)])
async def create_plan(request: PlanCreateRequest, session: AsyncSession = Depends(get_session)):
    """Create a new plan."""
    # Check for duplicate plan_code
    existing = (await session.execute(select(Plan).where(Plan.plan_code == request.plan_code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan code already exists")
    
    plan = Plan(
        plan_code=request.plan_code,
        plan_type=request.plan_type.upper(),
        country=request.country.upper(),
        price_ngn=request.price_ngn,
        quantity=request.quantity,
        duration_days=request.duration_days,
        features=request.features,
        is_active=request.is_active,
        sort_order=request.sort_order,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return PlanResponse.model_validate(plan)


@router.patch("/plans/{plan_id}", response_model=PlanResponse, dependencies=[Depends(admin_only)])
async def update_plan(plan_id: int, request: PlanUpdateRequest, session: AsyncSession = Depends(get_session)):
    """Update a plan."""
    plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    
    if request.price_ngn is not None:
        plan.price_ngn = request.price_ngn
    if request.quantity is not None:
        plan.quantity = request.quantity
    if request.duration_days is not None:
        plan.duration_days = request.duration_days
    if request.features is not None:
        plan.features = request.features
    if request.is_active is not None:
        plan.is_active = request.is_active
    if request.sort_order is not None:
        plan.sort_order = request.sort_order
    
    await session.commit()
    await session.refresh(plan)
    return PlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", dependencies=[Depends(admin_only)])
async def delete_plan(plan_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a plan."""
    plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    
    await session.delete(plan)
    await session.commit()
    return {"status": "deleted", "plan_id": plan_id}


# ============== Channel Feature Flags ==============

async def get_or_create_feature_flag(session: AsyncSession, name: str, default_url: str = "") -> FeatureFlag:
    """Get or create a feature flag for a channel."""
    flag = (await session.execute(select(FeatureFlag).where(FeatureFlag.name == name))).scalar_one_or_none()
    if not flag:
        flag = FeatureFlag(
            name=name,
            description=f"Channel configuration for {name}",
            enabled=False,
        )
        session.add(flag)
        await session.commit()
        await session.refresh(flag)
    return flag


@router.get("/features/channels", response_model=ChannelFeatureFlagsResponse)
async def get_channel_feature_flags(session: AsyncSession = Depends(get_session)):
    """Get channel feature flags (Telegram, WhatsApp) - public endpoint."""
    # Get or create Telegram flag
    telegram_flag = await get_or_create_feature_flag(session, "telegram")
    # Get or create WhatsApp flag
    whatsapp_flag = await get_or_create_feature_flag(session, "whatsapp")
    
    # Parse admin_overrides (JSON) for URLs - using {"url": "..."} format
    telegram_url = telegram_flag.admin_overrides.get("url", "") if telegram_flag.admin_overrides else ""
    whatsapp_url = whatsapp_flag.admin_overrides.get("url", "") if whatsapp_flag.admin_overrides else ""
    
    return ChannelFeatureFlagsResponse(
        telegram=ChannelConfig(enabled=telegram_flag.enabled, url=telegram_url),
        whatsapp=ChannelConfig(enabled=whatsapp_flag.enabled, url=whatsapp_url),
    )


@router.put("/features/channels", response_model=ChannelFeatureFlagsResponse, dependencies=[Depends(admin_only)])
async def update_channel_feature_flags(
    request: ChannelFeatureFlagsUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update channel feature flags (admin only)."""
    # Update Telegram
    telegram_flag = await get_or_create_feature_flag(session, "telegram")
    telegram_flag.enabled = request.telegram.enabled
    telegram_flag.admin_overrides = {"url": request.telegram.url}
    
    # Update WhatsApp
    whatsapp_flag = await get_or_create_feature_flag(session, "whatsapp")
    whatsapp_flag.enabled = request.whatsapp.enabled
    whatsapp_flag.admin_overrides = {"url": request.whatsapp.url}
    
    await session.commit()
    await session.refresh(telegram_flag)
    await session.refresh(whatsapp_flag)
    
    return ChannelFeatureFlagsResponse(
        telegram=ChannelConfig(
            enabled=telegram_flag.enabled,
            url=telegram_flag.admin_overrides.get("url", "") if telegram_flag.admin_overrides else "",
        ),
        whatsapp=ChannelConfig(
            enabled=whatsapp_flag.enabled,
            url=whatsapp_flag.admin_overrides.get("url", "") if whatsapp_flag.admin_overrides else "",
        ),
    )


# ============== Contact Submissions ==============

@router.get("/contact-submissions", response_model=ContactSubmissionsResponse, dependencies=[Depends(admin_only)])
async def list_contact_submissions(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List all contact submissions with optional status filter."""
    query = select(ContactSubmission).order_by(ContactSubmission.created_at.desc())
    if status:
        query = query.where(ContactSubmission.status == status)
    
    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()
    
    # Paginate
    query = query.offset((page-1)*limit).limit(limit)
    rows = (await session.execute(query)).scalars().all()
    
    return ContactSubmissionsResponse(
        data=[ContactSubmissionResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.post("/contact-submissions/{submission_id}/reply", dependencies=[Depends(admin_only)])
async def reply_contact_submission(
    submission_id: UUID,
    request: ContactSubmissionReplyRequest,
    session: AsyncSession = Depends(get_session),
):
    """Reply to a contact submission."""
    result = await session.execute(
        select(ContactSubmission).where(ContactSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission.status = "replied"
    submission.admin_notes = request.admin_notes
    await session.commit()
    return {"success": True}


@router.patch("/contact-submissions/{submission_id}", dependencies=[Depends(admin_only)])
async def update_contact_submission(
    submission_id: UUID,
    status: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Update contact submission status."""
    result = await session.execute(
        select(ContactSubmission).where(ContactSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission.status = status
    await session.commit()
    return {"success": True}


# ============== Charon Escalations ==============

@router.get("/escalations", response_model=EscalationsResponse, dependencies=[Depends(admin_only)])
async def list_escalations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List all Charon escalations with optional status filter."""
    query = select(CharonEscalation).order_by(CharonEscalation.created_at.desc())
    if status:
        query = query.where(CharonEscalation.status == status)
    
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()
    
    query = query.offset((page-1)*limit).limit(limit)
    rows = (await session.execute(query)).scalars().all()
    
    return EscalationsResponse(
        data=[CharonEscalationResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.post("/escalations/{escalation_id}/respond", dependencies=[Depends(admin_only)])
async def respond_escalation(
    escalation_id: UUID,
    request: EscalationRespondRequest,
    session: AsyncSession = Depends(get_session),
):
    """Respond to a Charon escalation."""
    result = await session.execute(
        select(CharonEscalation).where(CharonEscalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    escalation.status = "reviewed"
    escalation.admin_notes = request.admin_notes
    await session.commit()
    return {"success": True}


@router.patch("/escalations/{escalation_id}", dependencies=[Depends(admin_only)])
async def update_escalation(
    escalation_id: UUID,
    status: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Update escalation status."""
    result = await session.execute(
        select(CharonEscalation).where(CharonEscalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    escalation.status = status
    await session.commit()
    return {"success": True}
