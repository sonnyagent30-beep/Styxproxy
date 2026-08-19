"""Admin router."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    AdminAuditLog,
    CharonEscalation,
    ContactSubmission,
    Customer,
    FeatureFlag,
    Order,
    Plan,
    PlanSettings,
    ProcessedWebhook,
    ReferralCredit,
    StyxproxyCredential,
    TrialSession,
)
from app.schemas import (
    AdminAuditLogResponse,
    AdminAuditLogsResponse,
    AdminBlockRequest,
    AdminCredentialResponse,
    AdminCredentialsResponse,
    AdminCustomerResponse,
    AdminCustomersResponse,
    AdminOrderResponse,
    AdminOrdersResponse,
    AdminOrderUpdateRequest,
    AdminRefundRequest,
    AdminStatsResponse,
    AdminWebhookLogResponse,
    AdminWebhookLogsResponse,
    AllKnowledgeFilesResponse,
    ChannelConfig,
    ChannelFeatureFlagsResponse,
    ChannelFeatureFlagsUpdate,
    CharonEscalationResponse,
    ContactSubmissionReplyRequest,
    ContactSubmissionResponse,
    ContactSubmissionsResponse,
    DeleteLearnedFileRequest,
    DeleteLearnedFileResponse,
    EscalationRespondRequest,
    EscalationsResponse,
    EvalRunResponse,
    EvalSetResponse,
    KnowledgeFileResponse,
    LearnContentResponse,
    LearnedFileResponse,
    LearnedFilesResponse,
    PlanCreateRequest,
    PlanResponse,
    PlanSettingBasePricing,
    PlanSettingsDisplay,
    PlanSettingsResponse,
    PlanSettingsUpdateRequest,
    PlansResponse,
    PlanUpdateRequest,
    ReferralCreditResponse,
    ReferralStatsResponse,
    TrialConversionStatsResponse,
    UpdateKnowledgeRequest,
    UpdateKnowledgeResponse,
)
from app.services.audit import get_audit_logs, write_audit_log
from app.services.credential import replace_credential
from app.services.email import (
    send_refund_approved_notification,
    send_refund_processed_email,
)
from app.services.n8n import clear_failures, get_failure_stats, get_failures
from app.services.permissions import require_permission
from app.services.referral import (
    backfill_referral_codes,
    get_referral_stats_for_customer,
)
from app.services.trial import get_trials_today_count

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health", dependencies=[Depends(require_permission("admin.monitor.health.read"))])
async def admin_health():
    return {"status": "healthy", "admin": True}


@router.get(
    "/stats", response_model=AdminStatsResponse, 
    dependencies=[Depends(require_permission("admin.monitor.metrics.read"))]
)
async def get_stats(session: AsyncSession = Depends(get_session)):
    total_customers = (await session.execute(select(func.count()).select_from(Customer))).scalar() or 0
    active_orders = (
        await session.execute(select(func.count()).select_from(Order).where(Order.status == "active"))
    ).scalar() or 0
    total_revenue = (
        await session.execute(select(func.sum(Order.amount_paid_ngn)).where(Order.status.in_(["active", "fulfilled"])))
    ).scalar() or 0
    free_trials_today = await get_trials_today_count(session)
    active_credentials = (
        await session.execute(
            select(func.count()).select_from(StyxproxyCredential).where(StyxproxyCredential.status == "active")
        )
    ).scalar() or 0

    # Count plans per type
    plan_counts: dict[str, int] = {}
    for plan_type in ["ISP", "DC", "MOBILE", "RESIDENTIAL"]:
        count = (
            await session.execute(
                select(func.count()).select_from(Plan).where(Plan.plan_type == plan_type)
            )
        ).scalar() or 0
        plan_counts[plan_type] = count

    return AdminStatsResponse(
        total_customers=total_customers,
        active_orders=active_orders,
        total_revenue_ngn=float(total_revenue or 0),
        free_trials_today=free_trials_today,
        active_credentials=active_credentials,
        plan_counts=plan_counts,
    )


@router.get(
    "/customers", response_model=AdminCustomersResponse, 
    dependencies=[Depends(require_permission("admin.customers.list"))]
)
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
            (Customer.phone.ilike(f"%{escaped}%", escape="\\")) | (Customer.name.ilike(f"%{escaped}%", escape="\\"))
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
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get(
    "/customers/{customer_id}", response_model=AdminCustomerResponse, 
    dependencies=[Depends(require_permission("admin.customers.list"))]
)
async def get_customer(customer_id: UUID, session: AsyncSession = Depends(get_session)):
    customer = (await session.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return AdminCustomerResponse.model_validate(customer)


@router.post(
    "/customers/{customer_id}/block", dependencies=[Depends(require_permission("admin.customers.escalations.handle", totp_required=True))]
)
async def block_customer(customer_id: UUID, request: AdminBlockRequest, session: AsyncSession = Depends(get_session)):
    customer = (await session.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    customer.blocked = True
    customer.blocked_reason = request.reason
    await session.commit()
    return {"status": "blocked", "customer_id": str(customer_id)}


@router.post(
    "/customers/{customer_id}/unblock", dependencies=[Depends(require_permission("admin.customers.escalations.handle", totp_required=True))]
)
async def unblock_customer(customer_id: UUID, session: AsyncSession = Depends(get_session)):
    customer = (await session.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    customer.blocked = False
    customer.blocked_reason = None
    await session.commit()
    return {"status": "unblocked", "customer_id": str(customer_id)}


@router.get(
    "/orders", response_model=AdminOrdersResponse, dependencies=[Depends(require_permission("admin.orders.list"))]
)
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
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get(
    "/orders/{order_id}", response_model=AdminOrderResponse, 
    dependencies=[Depends(require_permission("admin.orders.list"))]
)
async def get_order(order_id: str, session: AsyncSession = Depends(get_session)):
    order = (await session.execute(select(Order).where(Order.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return AdminOrderResponse.model_validate(order)


@router.post(
    "/orders/lookup", response_model=AdminOrderResponse,
    dependencies=[Depends(require_permission("admin.orders.list"))]
)
async def lookup_order(
    order_id: Optional[str] = Body(None),
    tx_ref: Optional[str] = Body(None),
    phone: Optional[str] = Body(None),
    session: AsyncSession = Depends(get_session),
):
    """Look up an order by order_id, tx_ref, or customer phone."""
    conditions = []
    if order_id:
        conditions.append(Order.order_id == order_id)
    if tx_ref:
        conditions.append(Order.tx_ref == tx_ref)
    if phone:
        conditions.append(Order.customer_phone.ilike(f"%{phone}%"))
    if not conditions:
        raise HTTPException(status_code=400, detail="Provide order_id, tx_ref, or phone")
    stmt = select(Order).where(or_(*conditions)).limit(1)
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return AdminOrderResponse.model_validate(order)


@router.patch("/orders/{order_id}", dependencies=[Depends(require_permission("admin.orders.refund", totp_required=True))])
async def update_order(
    order_id: str,
    body: AdminOrderUpdateRequest,
    http_request: Request,
    current_admin: dict = Depends(require_permission("admin.orders.refund", totp_required=True)),
    session: AsyncSession = Depends(get_session),
):
    admin_email = current_admin["admin"].email
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


@router.post("/orders/{order_id}/refund", dependencies=[Depends(require_permission("admin.orders.refund", totp_required=True))])
async def refund_order(
    order_id: str,
    body: AdminRefundRequest,
    http_request: Request,
    current_admin: dict = Depends(require_permission("admin.orders.refund", totp_required=True)),
    session: AsyncSession = Depends(get_session),
):
    admin_email = current_admin["admin"].email
    order = (await session.execute(select(Order).where(Order.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status in ["refunded", "cancelled"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order already refunded or cancelled")
    order.status = "refunded"
    order.refund_requested = True
    order.refund_reason = body.reason
    if order.styxproxy_credential_id:
        cred = (
            await session.execute(
                select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
            )
        ).scalar_one_or_none()
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
        customer = (
            await session.execute(select(Customer).where(Customer.phone == order.customer_phone))
        ).scalar_one_or_none()

    if customer:
        customer_email = getattr(customer, "email", None)
        if customer_email:
            try:
                await send_refund_processed_email(
                    customer_email=customer_email,
                    customer_name=customer.name if customer.name else "Customer",
                    order_id=order_id,
                    original_amount=float(order.amount_paid_ngn or 0),
                    refund_amount=float(order.amount_paid_ngn or 0),
                    currency="NGN",
                    reason=body.reason or "Refund processed",
                )
            except Exception:
                pass

    return {"status": "refunded", "order_id": order_id, "refund_amount": float(order.amount_paid_ngn or 0)}


@router.post(
    "/credentials/{credential_id}/replace", dependencies=[Depends(require_permission("admin.monitor.providers.read", totp_required=True))]
)
async def replace_credential_endpoint(credential_id: int, session: AsyncSession = Depends(get_session)):
    new_credential = await replace_credential(session, credential_id, "admin_replacement")
    if not new_credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return {"status": "replaced", "old_credential_id": credential_id, "new_credential_id": new_credential.id}


@router.get(
    "/credentials", response_model=AdminCredentialsResponse, 
    dependencies=[Depends(require_permission("admin.monitor.providers.read"))]
)
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
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/email-delivery-log", dependencies=[Depends(require_permission("admin.monitor.logs.read"))])
async def get_email_delivery_log(
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(
        None, description="Filter by status: queued, api_error, http_error, unexpected_error, skipped_no_key"
    ),
):
    """Return recent email delivery events from the persistent JSON-lines log.

    Useful for diagnosing delivery failures without grepping docker logs.
    """
    from app.services.email import _DELIVERY_LOG_PATH  # noqa: PLC0415

    log_path = Path(_DELIVERY_LOG_PATH)
    if not log_path.exists():
        return {"total": 0, "entries": [], "log_path": str(log_path)}

    lines = log_path.read_text(encoding="utf-8").splitlines()
    entries: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if status_filter:
        entries = [e for e in entries if e.get("status") == status_filter]
    entries.reverse()  # newest first
    entries = entries[:limit]

    return {
        "total": len(entries),
        "entries": entries,
        "log_path": str(log_path),
    }


@router.get(
    "/audit", response_model=AdminAuditLogsResponse, 
    dependencies=[Depends(require_permission("admin.system.audit_log.read"))]
)
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
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get(
    "/webhooks", response_model=AdminWebhookLogsResponse, 
    dependencies=[Depends(require_permission("admin.monitor.webhooks.read"))]
)
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
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


# Charon Learned Files Management
LEARNED_DIR = Path(__file__).parents[3] / "data" / "charon" / "learned"


@router.get(
    "/charon/learned", response_model=LearnedFilesResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read"))]
)
async def list_learned_files():
    """List all learned files in the RAG knowledge base."""
    if not LEARNED_DIR.exists():
        return LearnedFilesResponse(files=[])

    files = []
    for path in sorted(LEARNED_DIR.rglob("*.md")):
        stat = path.stat()
        files.append(
            LearnedFileResponse(
                name=path.name,
                path=str(path.relative_to(LEARNED_DIR.parent.parent)),
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return LearnedFilesResponse(files=files)


@router.get(
    "/charon/learned/{filename}", response_model=LearnContentResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read"))]
)
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


@router.delete(
    "/charon/learned", response_model=DeleteLearnedFileResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read", totp_required=True))]
)
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


# ============== Charon Knowledge (admin can read/edit ALL knowledge files) ==============

KNOWLEDGE_DIR = Path("/root/styxproxy/backend/data/charon/knowledge")


def _list_md_files(directory: Path, source_label: str, editable: bool) -> list:
    """List .md files in a directory as KnowledgeFileResponse."""
    if not directory.exists():
        return []
    items = []
    for path in sorted(directory.rglob("*.md")):
        stat = path.stat()
        items.append(
            KnowledgeFileResponse(
                name=path.name,
                path=str(path.relative_to(directory.parent.parent)),
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                editable=editable,
            )
        )
    return items


@router.get(
    "/charon/knowledge", response_model=AllKnowledgeFilesResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read"))]
)
async def list_all_knowledge_files():
    """List both knowledge/ (read-only seeded) and learned/ (admin-editable) files."""
    return AllKnowledgeFilesResponse(
        knowledge=_list_md_files(KNOWLEDGE_DIR, "knowledge", editable=False),
        learned=_list_md_files(LEARNED_DIR, "learned", editable=True),
    )


@router.get(
    "/charon/knowledge/{filename}", response_model=LearnContentResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read"))]
)
async def get_knowledge_file_content(filename: str):
    """Read the content of a knowledge/ file (read-only seeded knowledge)."""
    # Security: prevent path traversal
    filename = filename.replace("..", "").replace("/", "")
    filepath = KNOWLEDGE_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if not filepath.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a file")
    content = filepath.read_text(encoding="utf-8")
    return LearnContentResponse(
        name=filepath.name,
        path=str(filepath.relative_to(filepath.parent.parent.parent)),
        content=content,
    )


@router.put(
    "/charon/knowledge/{filename}", response_model=UpdateKnowledgeResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read", totp_required=True))]
)
async def update_knowledge_file(filename: str, payload: UpdateKnowledgeRequest):
    """Update an existing knowledge/ file (replaces content with title + body as markdown)."""
    filename = filename.replace("..", "").replace("/", "")
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    filepath = KNOWLEDGE_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    full_content = f"# {payload.title.strip()}\n\n{payload.content.strip()}\n"
    filepath.write_text(full_content, encoding="utf-8")
    stat = filepath.stat()

    # Invalidate RAG cache so the new content is picked up immediately
    from app.services.charon.knowledge import invalidate_cache

    invalidate_cache()

    return UpdateKnowledgeResponse(
        ok=True,
        message=f"Updated {filename}",
        name=filename,
        path=str(filepath.relative_to(filepath.parent.parent.parent)),
        size=stat.st_size,
    )


@router.post(
    "/charon/knowledge/{filename}", response_model=UpdateKnowledgeResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read", totp_required=True))]
)
async def create_knowledge_file(filename: str, payload: UpdateKnowledgeRequest):
    """Create a new file in knowledge/."""
    filename = filename.replace("..", "").replace("/", "")
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    filepath = KNOWLEDGE_DIR / filename
    if filepath.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File already exists")

    full_content = f"# {payload.title.strip()}\n\n{payload.content.strip()}\n"
    filepath.write_text(full_content, encoding="utf-8")
    stat = filepath.stat()

    from app.services.charon.knowledge import invalidate_cache

    invalidate_cache()

    return UpdateKnowledgeResponse(
        ok=True,
        message=f"Created {filename}",
        name=filename,
        path=str(filepath.relative_to(filepath.parent.parent.parent)),
        size=stat.st_size,
    )


# ============== Charon Q/A Evaluation ==============

from app.services.charon.eval import get_eval_set, run_eval_set  # noqa: E402


@router.get(
    "/charon/eval", response_model=EvalSetResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read"))]
)
async def get_eval_questions():
    """Return the Q/A eval set derived from Scenarios."""
    return get_eval_set()


@router.post(
    "/charon/eval/run", response_model=EvalRunResponse, 
    dependencies=[Depends(require_permission("admin.monitor.logs.read"))]
)
async def run_eval_questions():
    """Run the eval set against the live Charon pipeline and report pass/fail per question."""
    return await run_eval_set()


# ============== Plans CRUD ==============


@router.get(
    "/plans", response_model=PlansResponse, dependencies=[Depends(require_permission("admin.system.maintenance.read"))]
)
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
        data=[PlanResponse.model_validate(p) for p in plans],
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get(
    "/plans/{plan_id}", response_model=PlanResponse, 
    dependencies=[Depends(require_permission("admin.system.maintenance.read"))]
)
async def get_plan(plan_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single plan by ID."""
    plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return PlanResponse.model_validate(plan)


@router.post(
    "/plans", response_model=PlanResponse, dependencies=[Depends(require_permission("admin.system.maintenance.read"))]
)
async def create_plan(request: PlanCreateRequest, session: AsyncSession = Depends(get_session)):
    """Create a new plan.

    Pricing model (Sprint 13):
    - residential/mobile: price_per_gb required, price_ngn optional (computed)
    - datacenter/isp:     price_ngn required (per-IP)
    """
    # Check for duplicate plan_code
    existing = (await session.execute(select(Plan).where(Plan.plan_code == request.plan_code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan code already exists")

    # Validate pricing per plan_type
    pt = request.plan_type.upper()
    if pt in ("RESIDENTIAL", "MOBILE"):
        if request.price_per_gb is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="price_per_gb is required for residential/mobile plans",
            )
    elif pt in ("DATACENTER", "ISP", "DC"):
        if request.price_ngn is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="price_ngn is required for datacenter/ISP plans (per-IP pricing)",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan_type: {pt}",
        )

    plan = Plan(
        plan_code=request.plan_code,
        plan_type=pt,
        country=request.country.upper(),
        price_ngn=request.price_ngn or 0,
        price_per_gb=request.price_per_gb,
        quantity=request.quantity,
        duration_days=request.duration_days,
        features=request.features,
        is_active=request.is_active,
        sort_order=request.sort_order,
        min_gb=request.min_gb,
        max_gb=request.max_gb,
        gb_tiers=request.gb_tiers,
        supports_city=request.supports_city,
        rotation_mode=request.rotation_mode,
        static_price_multiplier=request.static_price_multiplier,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return PlanResponse.model_validate(plan)


@router.patch(
    "/plans/{plan_id}", response_model=PlanResponse, 
    dependencies=[Depends(require_permission("admin.system.maintenance.read"))]
)
async def update_plan(plan_id: int, request: PlanUpdateRequest, session: AsyncSession = Depends(get_session)):
    """Update a plan. Admin can edit price_per_gb, gb_tiers, min/max_gb,
    supports_city, rotation_mode, static_price_multiplier (Sprint 13)."""
    plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    if request.price_ngn is not None:
        plan.price_ngn = request.price_ngn
    if request.price_per_gb is not None:
        plan.price_per_gb = request.price_per_gb
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
    if request.min_gb is not None:
        plan.min_gb = request.min_gb
    if request.max_gb is not None:
        plan.max_gb = request.max_gb
    if request.gb_tiers is not None:
        plan.gb_tiers = request.gb_tiers
    if request.supports_city is not None:
        plan.supports_city = request.supports_city
    if request.rotation_mode is not None:
        plan.rotation_mode = request.rotation_mode
    if request.static_price_multiplier is not None:
        plan.static_price_multiplier = request.static_price_multiplier

    await session.commit()
    await session.refresh(plan)
    return PlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", dependencies=[Depends(require_permission("admin.system.maintenance.read", totp_required=True))])
async def delete_plan(plan_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a plan."""
    plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    await session.delete(plan)
    await session.commit()
    return {"status": "deleted", "plan_id": plan_id}

# ============== Plan Settings (plan-type level pricing) =============

@router.get(
    "/plan-settings",
    response_model=list[PlanSettingsDisplay],
    dependencies=[Depends(require_permission("admin.plans.manage"))],
)
async def list_plan_settings(
    session: AsyncSession = Depends(get_session),
):
    """List all plan settings grouped by plan_type with base_pricing and country_overrides."""
    # Get all base_pricing settings
    base_result = await session.execute(
        select(PlanSettings)
        .where(PlanSettings.setting_key == "base_pricing")
        .order_by(PlanSettings.plan_type)
    )
    base_settings = base_result.scalars().all()
    
    # Get all country_override settings
    override_result = await session.execute(
        select(PlanSettings)
        .where(PlanSettings.setting_key == "country_override")
        .order_by(PlanSettings.plan_type, PlanSettings.country)
    )
    override_settings = override_result.scalars().all()
    
    # Build result
    result: list[PlanSettingsDisplay] = []
    
    for base in base_settings:
        plan_type = base.plan_type
        
        # Find overrides for this plan_type
        overrides = {
            o.country: o.setting_value.get("price_per_ip", 0)
            for o in override_settings
            if o.plan_type == plan_type
        }
        
        # Build base_pricing
        base_pricing = PlanSettingBasePricing(
            price_per_ip=base.setting_value.get("price_per_ip"),
            price_per_gb=base.setting_value.get("price_per_gb"),
            pricing_model=base.setting_value.get("pricing_model", "per_IP"),
            gb_tiers=base.setting_value.get("gb_tiers"),
        )
        
        result.append(PlanSettingsDisplay(
            plan_type=plan_type,
            base_pricing=base_pricing,
            country_overrides=overrides,
        ))
    
    return result


@router.patch(
    "/plan-settings/{plan_type}",
    response_model=PlanSettingsResponse,
    dependencies=[Depends(require_permission("admin.plans.manage"))],
)
async def update_plan_setting(
    plan_type: str,
    request: PlanSettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update a plan setting by plan_type (ISP, DC, RESIDENTIAL, MOBILE)."""
    setting = (
        await session.execute(
            select(PlanSettings).where(
                func.lower(PlanSettings.plan_type) == plan_type.lower(),
                PlanSettings.setting_key == "pricing",
            )
        )
    ).scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail=f"No plan setting found for plan_type: {plan_type}")

    if request.setting_value is not None:
        setting.setting_value = request.setting_value
    if request.description is not None:
        setting.description = request.description
    if request.is_active is not None:
        setting.is_active = request.is_active
    if request.priority is not None:
        setting.priority = request.priority

    await session.commit()
    await session.refresh(setting)
    return PlanSettingsResponse.model_validate(setting)


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


@router.put(
    "/features/channels", response_model=ChannelFeatureFlagsResponse, 
    dependencies=[Depends(require_permission("admin.feature_flags.update"))]
)
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


# ============== Generic Feature Flags ==============


class FeatureFlagUpdate(BaseModel):
    enabled: Optional[bool] = None


class FeatureFlagResponse(BaseModel):
    name: str
    enabled: bool
    description: Optional[str] = None


@router.get(
    "/features/flags/{flag_name}",
    response_model=FeatureFlagResponse,
    dependencies=[Depends(require_permission("admin.feature_flags.read"))]
)
async def get_feature_flag(
    flag_name: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a feature flag by name."""
    flag = (await session.execute(select(FeatureFlag).where(FeatureFlag.name == flag_name))).scalar_one_or_none()
    if not flag:
        # Auto-create with default values
        flag = FeatureFlag(
            name=flag_name,
            description=f"auto-created: {flag_name}",
            enabled=False,
        )
        session.add(flag)
        await session.commit()
        await session.refresh(flag)
    return FeatureFlagResponse(name=flag.name, enabled=flag.enabled, description=flag.description)


@router.patch(
    "/features/flags/{flag_name}",
    response_model=FeatureFlagResponse,
    dependencies=[Depends(require_permission("admin.feature_flags.update"))]
)
async def update_feature_flag(
    flag_name: str,
    request: FeatureFlagUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a feature flag (enable/disable). Used for checkout_disabled, etc."""
    flag = (await session.execute(select(FeatureFlag).where(FeatureFlag.name == flag_name))).scalar_one_or_none()
    if not flag:
        # Auto-create if doesn't exist
        flag = FeatureFlag(
            name=flag_name,
            description=f"auto-created: {flag_name}",
            enabled=request.enabled if request.enabled is not None else False,
        )
        session.add(flag)
    else:
        if request.enabled is not None:
            flag.enabled = request.enabled

    await session.commit()
    await session.refresh(flag)

    # Audit log
    from app.models import AdminAuditLog
    audit = AdminAuditLog(
        admin_email="unknown",  # Will be filled by auth dependency
        action=f"feature_flag_update_{flag_name}",
        details={"enabled": flag.enabled},
    )
    session.add(audit)
    await session.commit()

    return FeatureFlagResponse(name=flag.name, enabled=flag.enabled, description=flag.description)


# ============== Contact Submissions ==============


@router.get(
    "/contact-submissions", response_model=ContactSubmissionsResponse, 
    dependencies=[Depends(require_permission("admin.customers.support.respond"))]
)
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
    query = query.offset((page - 1) * limit).limit(limit)
    rows = (await session.execute(query)).scalars().all()

    return ContactSubmissionsResponse(
        data=[ContactSubmissionResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.post(
    "/contact-submissions/{submission_id}/reply", 
    dependencies=[Depends(require_permission("admin.customers.support.respond"))]
)
async def reply_contact_submission(
    submission_id: UUID,
    request: ContactSubmissionReplyRequest,
    session: AsyncSession = Depends(get_session),
):
    """Reply to a contact submission."""
    result = await session.execute(select(ContactSubmission).where(ContactSubmission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.status = "replied"
    submission.admin_notes = request.admin_notes
    await session.commit()
    return {"success": True}


@router.patch(
    "/contact-submissions/{submission_id}", 
    dependencies=[Depends(require_permission("admin.customers.support.respond"))]
)
async def update_contact_submission(
    submission_id: UUID,
    status: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Update contact submission status."""
    result = await session.execute(select(ContactSubmission).where(ContactSubmission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.status = status
    await session.commit()
    return {"success": True}


# ============== Charon Escalations ==============


@router.get(
    "/escalations", response_model=EscalationsResponse, 
    dependencies=[Depends(require_permission("admin.customers.escalations.handle"))]
)
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

    query = query.offset((page - 1) * limit).limit(limit)
    rows = (await session.execute(query)).scalars().all()

    return EscalationsResponse(
        data=[CharonEscalationResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.post(
    "/escalations/{escalation_id}/respond", 
    dependencies=[Depends(require_permission("admin.customers.escalations.handle"))]
)
async def respond_escalation(
    escalation_id: UUID,
    request: EscalationRespondRequest,
    session: AsyncSession = Depends(get_session),
):
    """Respond to a Charon escalation."""
    result = await session.execute(select(CharonEscalation).where(CharonEscalation.id == escalation_id))
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    escalation.status = "reviewed"
    escalation.admin_notes = request.admin_notes
    await session.commit()
    return {"success": True}


@router.patch(
    "/escalations/{escalation_id}", dependencies=[Depends(require_permission("admin.customers.escalations.handle"))]
)
async def update_escalation(
    escalation_id: UUID,
    status: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Update escalation status."""
    result = await session.execute(select(CharonEscalation).where(CharonEscalation.id == escalation_id))
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    escalation.status = status
    await session.commit()
    return {"success": True}



@router.get("/n8n/failures", dependencies=[Depends(require_permission("admin.monitor.webhooks.read"))])
async def list_n8n_webhook_failures(limit: int = Query(default=50, le=200)) -> dict:
    """List recent n8n webhook delivery failures (admin only).

    Bug walk theme-B fix: previously failed webhook deliveries were only
    logged to stdout and lost. Now persisted to Redis (capped at 100) so
    admin can review which customers never got their n8n-driven delivery
    (WhatsApp message, Telegram notification, etc.) and trigger manual
    recovery.

    Query params:
        limit: Max number of failures to return (default 50, max 200).

    Returns:
        {
            "stats": {"buffer_size": int, "last_48h_count": int},
            "failures": [
                {"order_id", "tx_ref", "timestamp", "error", "payload_summary"},
                ...
            ]
        }
    """
    failures = await get_failures(limit=limit)
    stats = await get_failure_stats()
    return {"stats": stats, "failures": failures}


@router.delete("/n8n/failures", dependencies=[Depends(require_permission("admin.monitor.webhooks.read"))])
async def clear_n8n_webhook_failures() -> dict:
    """Clear the n8n webhook failures buffer (admin only).

    Use after handling each failure manually (resending the webhook,
    refunding, etc.). Returns the number of failures cleared.
    """
    cleared = await clear_failures()
    return {"cleared": cleared}



# ─── §14 Monitor & Regulate API — M2/M3 endpoints ────────────────────────────
# Theme A: small admin monitoring endpoints (5 M2 + 3 M3). Each is small
# but together they close the admin observability gap. All admin_only.
# See Notion §14 spec for the rationale.


@router.get("/errors", dependencies=[Depends(require_permission("admin.monitor.logs.read"))])
async def list_recent_errors(
    limit: int = Query(default=50, le=500),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List recent error events from admin_audit_log.

    Filters action column for entries containing 'error' or 'fail'.
    Theme A M2 endpoint: admin uses this to spot systemic issues
    (e.g. payment_initiate_failed spiking after a Flutterwave outage).
    """
    stmt = (
        select(AdminAuditLog)
        .where(AdminAuditLog.action.ilike("%error%") | AdminAuditLog.action.ilike("%fail%"))
        .order_by(AdminAuditLog.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {
        "errors": [
            {
                "id": r.id,
                "admin_phone": r.admin_phone,
                "action": r.action,
                "ip_address": r.ip_address,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "limit": limit,
    }


@router.get("/logs", dependencies=[Depends(require_permission("admin.monitor.logs.read"))])
async def list_admin_logs(
    limit: int = Query(default=100, le=500),
    action_filter: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List recent admin actions from admin_audit_log.

    Theme A M2 endpoint: full admin action log. Use action_filter to
    narrow (e.g. 'maintenance_toggle', 'feature_flag_update',
    'login_success', etc.).
    """
    stmt = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit)
    if action_filter:
        stmt = stmt.where(AdminAuditLog.action.ilike(f"%{action_filter}%"))
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {
        "logs": [
            {
                "id": r.id,
                "admin_phone": r.admin_phone,
                "action": r.action,
                "ip_address": r.ip_address,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "limit": limit,
        "filter": action_filter,
    }


@router.get("/db/connections", dependencies=[Depends(require_permission("admin.monitor.db.read"))])
async def db_connection_stats(session: AsyncSession = Depends(get_session)) -> dict:
    """PostgreSQL connection stats from pg_stat_activity.

    Theme A M2 endpoint: shows active vs idle connections, plus the
    server-side max_connections setting. Useful for spotting connection
    leaks (active >> expected) before they crash the pool.
    """
    active_q = text("""
        SELECT
          count(*) FILTER (WHERE state = 'active') AS active,
          count(*) FILTER (WHERE state = 'idle') AS idle,
          count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_txn,
          count(*) AS total,
          (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_conn
        FROM pg_stat_activity
        WHERE datname = current_database()
    """)
    by_app = text("""
        SELECT application_name, count(*) AS count
        FROM pg_stat_activity
        WHERE datname = current_database()
        GROUP BY application_name
        ORDER BY count DESC
        LIMIT 10
    """)
    active_result = await session.execute(active_q)
    active_row = active_result.mappings().one()
    by_app_result = await session.execute(by_app)
    by_app_rows = by_app_result.mappings().all()

    return {
        "active": active_row["active"],
        "idle": active_row["idle"],
        "idle_in_transaction": active_row["idle_in_txn"],
        "total": active_row["total"],
        "max_connections": active_row["max_conn"],
        "by_application": [{"application_name": r["application_name"], "count": r["count"]} for r in by_app_rows],
    }


@router.get("/db/slow-queries", dependencies=[Depends(require_permission("admin.monitor.db.read"))])
async def db_slow_queries(
    threshold_ms: int = Query(default=200, ge=50, le=10000),
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Recent slow queries from pg_stat_statements.

    Theme A M2 endpoint: surfaces queries above the threshold. Requires
    pg_stat_statements extension (often enabled by default). Returns
    empty list if extension isn't loaded — caller should fall back to
    reading the empty result and not raise.

    Note: pg_stat_statements requires superuser to enable. If the
    styxproxy role can't query it, this returns 403 from PG.
    """
    try:
        q = text("""
            SELECT
              round((mean_exec_time)::numeric, 2) AS avg_ms,
              calls,
              round((total_exec_time)::numeric, 0) AS total_ms,
              query
            FROM pg_stat_statements
            WHERE mean_exec_time > :threshold
            ORDER BY mean_exec_time DESC
            LIMIT :limit
        """)
        result = await session.execute(q, {"threshold": threshold_ms, "limit": limit})
        rows = result.mappings().all()
        return {
            "slow_queries": [
                {"avg_ms": r["avg_ms"], "calls": r["calls"], "total_ms": r["total_ms"], "query": r["query"][:500]}
                for r in rows
            ],
            "threshold_ms": threshold_ms,
            "extension_available": True,
        }
    except Exception as e:
        return {
            "slow_queries": [],
            "threshold_ms": threshold_ms,
            "extension_available": False,
            "error": str(e)[:200],
        }


@router.get("/cache/stats", dependencies=[Depends(require_permission("admin.monitor.cache.read"))])
async def cache_stats() -> dict:
    """Redis cache statistics (if available).

    Theme A M2 endpoint: returns Redis keyspace info (hits, misses,
    memory, key count by db). Returns empty stats if Redis isn't
    configured or reachable.
    """
    try:
        from app.services.observability import get_redis

        client = await get_redis()
        if client is None:
            return {"available": False, "reason": "redis_unavailable"}
        info = await client.info("stats")
        keyspace = await client.info("keyspace")
        return {
            "available": True,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0)
                / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            ),
            "total_keys": sum(int(v.get("keys", 0)) for v in keyspace.values() if isinstance(v, dict)),
            "memory_used_bytes": info.get("used_memory", 0),
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:200]}


# ─── M3 endpoints ────────────────────────────────────────────────────────────


@router.get("/webhooks/health", dependencies=[Depends(require_permission("admin.monitor.webhooks.read"))])
async def webhook_health(session: AsyncSession = Depends(get_session)) -> dict:
    """Webhook delivery health from processed_webhooks table.

    Theme A M3 endpoint: shows recent webhook activity, separated by
    provider (Flutterwave, etc.). The /api/admin/n8n/failures endpoint
    covers outbound n8n delivery; this covers inbound webhook processing.
    """
    q = text("""
        SELECT
          provider,
          count(*) FILTER (WHERE created_at > now() - interval '1 hour') AS last_1h,
          count(*) FILTER (WHERE created_at > now() - interval '24 hours') AS last_24h,
          count(*) AS total
        FROM processed_webhooks
        GROUP BY provider
    """)
    try:
        result = await session.execute(q)
        rows = result.mappings().all()
        return {
            "providers": [dict(r) for r in rows],
            "note": "Counts of processed (not necessarily successful) webhooks.",
        }
    except Exception as e:
        return {"providers": [], "error": str(e)[:200]}


@router.get("/providers/health", dependencies=[Depends(require_permission("admin.monitor.providers.read"))])
async def providers_health() -> dict:
    """Provider availability summary from in-memory cache.

    Theme A M3 endpoint: reports configured providers. The full
    provider_test.py benchmarks (separate sprint) cover deeper
    analysis; this is a quick at-a-glance summary for the admin
    dashboard.
    """
    from app.services.providers import PROVIDER_COSTS
    return {
        "providers_configured": list(PROVIDER_COSTS.keys()),
        "note": "For live availability benchmarks use /api/admin/providers/test (Theme B+).",
    }


@router.post("/providers/test", dependencies=[Depends(require_permission("admin.monitor.providers.read"))])
async def test_provider_proxy(
    ip: str,
    port: int,
    http: bool = True,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Run full Speed + Strength + Quality benchmark on a single proxy IP.

    Returns ProxyTestResult with speed/strength/quality grades + PASS/FAIL verdict.
    Requires: ip (string) and port (int) query params.
    """
    from app.services.provider import ProviderProxy
    from app.services.provider_test import benchmark_tiers, test_proxy_full

    proxy = ProviderProxy(
        provider_order_id=f"manual-test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        ip=ip,
        port=port,
        username="",
        password="",
        protocol="http" if http else "socks5",
        expires_at=datetime.now(timezone.utc),
        country="",
        isp="",
        asn="",
    )

    result = await test_proxy_full(proxy)
    return {
        "benchmark": result.to_dict(),
        "tiers": benchmark_tiers(),
    }


@router.get("/charon/health", dependencies=[Depends(require_permission("admin.monitor.logs.read"))])
async def charon_health() -> dict:
    """Charon support bot health summary.

    Theme A M3 endpoint: aggregates M2 cloud + LiteLLM + Ollama
    reachability + computed charon_available flag (matches the logic
    in /api/v1/health). Useful for the admin dashboard.

    Reuses the existing /api/v1/health probe logic by calling that
    endpoint internally rather than importing private helpers.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://127.0.0.1:8000/api/v1/health")
            if r.status_code == 200:
                data = r.json()
                services = data.get("services", {})
                m2 = services.get("m2_cloud", {})
                litellm = services.get("litellm", {})
                ollama = services.get("ollama", {})
                m2_ok = m2.get("status") == "connected"
                local_ok = litellm.get("status") == "connected" and ollama.get("status") == "connected"
                return {
                    "charon_available": m2_ok or local_ok,
                    "m2_cloud": m2,
                    "litellm": litellm,
                    "ollama": ollama,
                    "source": "delegated_to_/api/v1/health",
                }
        return {"charon_available": False, "error": "health_endpoint_unreachable"}
    except Exception as e:
        return {"charon_available": False, "error": str(e)[:200]}



# ─── §14 Monitor & Regulate API — M4 endpoints ────────────────────────────────
# Theme A: operational tools that let admin recover from stuck orders and
# diagnose pipeline failures. Both admin_only with email audit trail.


@router.post("/orders/{order_id}/re-fulfill", dependencies=[Depends(require_permission("admin.orders.re_fulfill"))])
async def re_fulfill_order(
    order_id: str,
    http_request: Request,
    current_admin: dict = Depends(require_permission("admin.orders.re_fulfill")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    admin_email = current_admin["admin"].email
    """Re-run credential creation for an order.

    Theme A M4 endpoint: when a paid order is stuck (status=paid but no
    credential, or customer reports dead proxy), admin can manually
    trigger create_credential again. Useful for:
    - Orders where the original webhook failed mid-pipeline
    - Orders where credentials expired prematurely
    - Manual recovery from a provider outage

    Safety:
    - Refuses if order is already refunded or cancelled
    - Revokes existing credential before creating new one
    - Audit-logs the action with admin_email + IP

    Returns the new credential brief + new order status.
    """
    from app.services.credential import create_credential

    order = (
        await session.execute(select(Order).where(Order.order_id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status in ("refunded", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is {order.status}; cannot re-fulfill",
        )

    try:
        # Revoke existing credential if any (avoid duplicates)
        if order.styxproxy_credential_id:
            old_cred = (
                await session.execute(
                    select(StyxproxyCredential).where(
                        StyxproxyCredential.id == order.styxproxy_credential_id
                    )
                )
            ).scalar_one_or_none()
            if old_cred:
                old_cred.status = "revoked"

        # Re-run credential creation
        credential, plaintext_password = await create_credential(
            db_session=session,
            order_id=order.order_id,
            customer_phone=order.customer_phone or "",
            plan_code=order.plan_code or "unknown",
            country=order.country or "NG",
            proxy_type="isp",
            quantity=1,
            duration_days=30,
            protocol="socks5",
            pool_type="paid",
        )
        order.styxproxy_credential_id = credential.id
        order.status = "active"
        order.replacement_count = (order.replacement_count or 0) + 1
        await session.commit()
        await session.refresh(credential)
        await session.refresh(order)
    except Exception as e:
        await session.rollback()
        await write_audit_log(
            session,
            admin_email=admin_email,
            action="re_fulfill_failed",
            resource_type="order",
            resource_id=order.order_id,
            details={"error": str(e)[:500]},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-fulfill failed: {str(e)[:200]}",
        )

    await write_audit_log(
        session,
        admin_email=admin_email,
        action="re_fulfill_order",
        resource_type="order",
        resource_id=order.order_id,
        details={
            "new_credential_id": credential.id,
            "new_status": order.status,
            "replacement_count": order.replacement_count,
        },
    )

    return {
        "success": True,
        "order_id": order.order_id,
        "status": order.status,
        "credential_id": credential.id,
        "bun_username": credential.bun_username,
        "upstream_proxy_ip": credential.upstream_proxy_ip,
        "upstream_proxy_port": credential.upstream_proxy_port,
        "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
        "replacement_count": order.replacement_count,
        "note": "plaintext password not returned; check webhook/email delivery",
    }


@router.post("/self-test", dependencies=[Depends(require_permission("admin.monitor.self_test.run"))])
async def self_test(
    http_request: Request,
    current_admin: dict = Depends(require_permission("admin.monitor.self_test.run")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    admin_email = current_admin["admin"].email
    """Run a full pipeline self-test without creating real orders.

    Theme A M4 endpoint: validates that every component of the order
    pipeline is reachable. Specifically checks:
    - Database: SELECT 1 + counts on critical tables
    - Redis: PING
    - Provider availability: calls check_availability for the cheapest
      ISP-NG-1 plan + quantity=1 (dry-run, no real cost)
    - Stripe/Flutterwave: configured (env var present) but does NOT
      hit their API
    - Feature flag infra: can read a known flag
    - n8n: configured (URL present) but does NOT call webhook

    Returns one entry per check with pass/fail + reason + latency_ms.
    Audit-logged as 'self_test_run' for compliance.

    If any check fails, the response is still 200 — caller inspects
    results. This endpoint is informational, not a fail-fast gate.
    """
    import time

    from app.config import get_settings
    from app.services.observability import get_redis

    results = []
    settings = get_settings()

    # DB check
    t0 = time.time()
    try:
        await session.execute(text("SELECT 1"))
        customers = (await session.execute(text("SELECT count(*) FROM customers"))).scalar() or 0
        orders = (await session.execute(text("SELECT count(*) FROM orders"))).scalar() or 0
        results.append({
            "check": "database",
            "pass": True,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "details": {"customers": customers, "orders": orders},
        })
    except Exception as e:
        results.append({
            "check": "database",
            "pass": False,
            "error": str(e)[:200],
        })

    # Redis check
    t0 = time.time()
    try:
        client = await get_redis()
        if client is None:
            results.append({"check": "redis", "pass": False, "error": "redis_unavailable"})
        else:
            await client.ping()
            results.append({
                "check": "redis",
                "pass": True,
                "latency_ms": round((time.time() - t0) * 1000, 1),
            })
    except Exception as e:
        results.append({"check": "redis", "pass": False, "error": str(e)[:200]})

    # Provider availability check (dry-run; no real proxy order)
    t0 = time.time()
    try:
        from app.services.availability import check_availability

        result = await check_availability(
            plan_code="ISP-NG-1",
            country="Nigeria",
            proxy_type="isp",
            quantity=1,
        )
        results.append({
            "check": "provider_availability",
            "pass": bool(result.get("available")),
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "details": result,
        })
    except Exception as e:
        results.append({"check": "provider_availability", "pass": False, "error": str(e)[:200]})

    # Flutterwave configured (env var present, no API call)
    results.append({
        "check": "flutterwave_configured",
        "pass": bool(settings.flutterwave_secret_key),
        "details": {
            "secret_key_set": bool(settings.flutterwave_secret_key),
            "public_key_set": bool(getattr(settings, "flutterwave_public_key", "")),
        },
    })

    # n8n webhook configured (URL present, no API call)
    results.append({
        "check": "n8n_configured",
        "pass": bool(settings.n8n_webhook_url),
        "details": {"url_set": bool(settings.n8n_webhook_url)},
    })

    # Feature flag infra check
    t0 = time.time()
    try:
        flag = (
            await session.execute(
                select(FeatureFlag).where(FeatureFlag.name == "maintenance_mode")
            )
        ).scalar_one_or_none()
        results.append({
            "check": "feature_flags",
            "pass": flag is not None,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "details": {"maintenance_mode_flag_exists": flag is not None},
        })
    except Exception as e:
        results.append({"check": "feature_flags", "pass": False, "error": str(e)[:200]})

    overall_pass = all(r["pass"] for r in results)

    await write_audit_log(
        session,
        admin_email=admin_email,
        action="self_test_run",
        resource_type="system",
        details={
            "overall_pass": overall_pass,
            "checks_run": len(results),
            "checks_failed": sum(1 for r in results if not r["pass"]),
        },
    )

    return {
        "overall_pass": overall_pass,
        "checks": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["pass"]),
            "failed": sum(1 for r in results if not r["pass"]),
        },
    }



@router.get("/health/history", dependencies=[Depends(require_permission("admin.monitor.health.read"))])
async def health_history(
    hours: int = Query(default=24, ge=1, le=168),  # max 7 days
    limit: int = Query(default=500, le=5000),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Read health_snapshots time-series for the admin dashboard.

    Theme A M5 endpoint: returns the last N snapshots within the time
    window, newest first. Suitable for rendering time-series charts
    (overall_status line, component availability bars, latency trend).

    Query params:
        hours: how far back to look (default 24, max 168 = 7 days)
        limit: max snapshots to return (default 500, max 5000)

    Returns:
        {
            "snapshots": [{timestamp, status, components, latency}, ...],
            "summary": {total, healthy_count, degraded_count, unhealthy_count}
        }
    """
    from datetime import datetime, timedelta, timezone

    from app.models import HealthSnapshot

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(HealthSnapshot)
        .where(HealthSnapshot.created_at >= cutoff)
        .order_by(HealthSnapshot.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    snapshots = [
        {
            "id": r.id,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
            "overall_status": r.overall_status,
            "components": {
                "db": r.db_connected,
                "redis": r.redis_connected,
                "m2": r.m2_connected,
                "litellm": r.litellm_connected,
                "ollama": r.ollama_connected,
                "charon": r.charon_available,
            },
            "latency_ms": float(r.total_latency_ms) if r.total_latency_ms is not None else None,
            "error": r.error_summary,
            "source": r.source,
        }
        for r in rows
    ]

    summary = {
        "total": len(snapshots),
        "healthy": sum(1 for s in snapshots if s["overall_status"] == "healthy"),
        "degraded": sum(1 for s in snapshots if s["overall_status"] == "degraded"),
        "unhealthy": sum(1 for s in snapshots if s["overall_status"] == "unhealthy"),
    }

    return {
        "snapshots": snapshots,
        "summary": summary,
        "window_hours": hours,
        "limit": limit,
    }


# ─── Referral system endpoints (Sprint 2) ─────────────────────────────────────


@router.get(
    "/referrals/stats",
    response_model=ReferralStatsResponse,
    dependencies=[Depends(require_permission("admin.referrals.read"))],
)
async def get_platform_referral_stats(
    session: AsyncSession = Depends(get_session),
):
    """Platform-wide referral statistics for the admin dashboard."""
    # All applied credits
    applied_stmt = select(ReferralCredit).where(ReferralCredit.applied_at.isnot(None))
    applied_credits = (await session.execute(applied_stmt)).scalars().all()

    # All pending credits
    pending_stmt = select(ReferralCredit).where(ReferralCredit.applied_at.is_(None))
    pending_credits = (await session.execute(pending_stmt)).scalars().all()

    total_earned_ngn = sum(c.credit_amount_nGN for c in applied_credits) / 1_000_000
    total_pending_ngn = sum(c.credit_amount_nGN for c in pending_credits) / 1_000_000

    # Count unique referrers and referees
    referrer_ids = {c.referrer_customer_id for c in applied_credits}
    referee_ids = {c.referee_customer_id for c in applied_credits}

    return ReferralStatsResponse(
        total_referrals=len(applied_credits),
        pending_referrals=len(pending_credits),
        total_credit_earned_ngn=total_earned_ngn,
        total_credits_available_ngn=total_pending_ngn,
        referrer_count=len(referrer_ids),
        referee_count=len(referee_ids),
    )


@router.get(
    "/referrals/credits",
    response_model=list[ReferralCreditResponse],
    dependencies=[Depends(require_permission("admin.referrals.read"))],
)
async def list_referral_credits(
    session: AsyncSession = Depends(get_session),
    applied: Optional[bool] = Query(
        None,
        description="Filter by applied status: true=applied, false=pending, omitted=all",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all referral credit records, newest first."""
    stmt = select(ReferralCredit).order_by(ReferralCredit.created_at.desc()).limit(limit).offset(offset)
    if applied is True:
        stmt = stmt.where(ReferralCredit.applied_at.isnot(None))
    elif applied is False:
        stmt = stmt.where(ReferralCredit.applied_at.is_(None))
    rows = (await session.execute(stmt)).scalars().all()
    return [ReferralCreditResponse.model_validate(r) for r in rows]


@router.get(
    "/referrals/by-customer/{customer_id}",
    response_model=ReferralStatsResponse,
    dependencies=[Depends(require_permission("admin.referrals.read"))],
)
async def get_customer_referral_stats(
    customer_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Referral stats for a specific customer (as referrer)."""
    customer = (
        await session.execute(select(Customer).where(Customer.id == customer_id))
    ).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    stats = await get_referral_stats_for_customer(session, customer_id=customer.id)
    return ReferralStatsResponse(**stats)


@router.post(
    "/referrals/backfill-codes",
    dependencies=[Depends(require_permission("admin.referrals.manage"))],
)
async def admin_backfill_referral_codes(
    session: AsyncSession = Depends(get_session),
):
    """Generate referral codes for existing customers who don't have one.

    Safe to re-run — only affects rows where referral_code IS NULL.
    Returns the count of codes generated.
    """
    count = await backfill_referral_codes(session)
    return {"codes_generated": count, "detail": f"Generated {count} referral codes."}
