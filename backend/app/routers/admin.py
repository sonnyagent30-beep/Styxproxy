"""Admin router."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import admin_only, admin_only_with_email
from app.database import get_session
from app.models import (
    AdminAuditLog,
    CharonEscalation,
    ContactSubmission,
    Customer,
    FeatureFlag,
    Order,
    Plan,
    ProcessedWebhook,
    StyxproxyCredential,
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
    PlansResponse,
    PlanUpdateRequest,
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
from app.services.trial import get_trials_today_count

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health", dependencies=[Depends(admin_only)])
async def admin_health():
    return {"status": "healthy", "admin": True}


@router.get("/stats", response_model=AdminStatsResponse, dependencies=[Depends(admin_only)])
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
            "page": page,
            "limit": limit,
            "total_items": total,
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
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/email-delivery-log", dependencies=[Depends(admin_only)])
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
            "page": page,
            "limit": limit,
            "total_items": total,
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


@router.get("/charon/learned", response_model=LearnedFilesResponse, dependencies=[Depends(admin_only)])
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


@router.get("/charon/knowledge", response_model=AllKnowledgeFilesResponse, dependencies=[Depends(admin_only)])
async def list_all_knowledge_files():
    """List both knowledge/ (read-only seeded) and learned/ (admin-editable) files."""
    return AllKnowledgeFilesResponse(
        knowledge=_list_md_files(KNOWLEDGE_DIR, "knowledge", editable=False),
        learned=_list_md_files(LEARNED_DIR, "learned", editable=True),
    )


@router.get("/charon/knowledge/{filename}", response_model=LearnContentResponse, dependencies=[Depends(admin_only)])
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


@router.put("/charon/knowledge/{filename}", response_model=UpdateKnowledgeResponse, dependencies=[Depends(admin_only)])
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


@router.post("/charon/knowledge/{filename}", response_model=UpdateKnowledgeResponse, dependencies=[Depends(admin_only)])
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


@router.get("/charon/eval", response_model=EvalSetResponse, dependencies=[Depends(admin_only)])
async def get_eval_questions():
    """Return the Q/A eval set derived from Scenarios."""
    return get_eval_set()


@router.post("/charon/eval/run", response_model=EvalRunResponse, dependencies=[Depends(admin_only)])
async def run_eval_questions():
    """Run the eval set against the live Charon pipeline and report pass/fail per question."""
    return await run_eval_set()


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
            "page": page,
            "limit": limit,
            "total_items": total,
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
    query = query.offset((page - 1) * limit).limit(limit)
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
    result = await session.execute(select(ContactSubmission).where(ContactSubmission.id == submission_id))
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
    result = await session.execute(select(ContactSubmission).where(ContactSubmission.id == submission_id))
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

    query = query.offset((page - 1) * limit).limit(limit)
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
    result = await session.execute(select(CharonEscalation).where(CharonEscalation.id == escalation_id))
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
    result = await session.execute(select(CharonEscalation).where(CharonEscalation.id == escalation_id))
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    escalation.status = status
    await session.commit()
    return {"success": True}



@router.get("/n8n/failures", dependencies=[Depends(admin_only)])
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


@router.delete("/n8n/failures", dependencies=[Depends(admin_only)])
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


@router.get("/errors", dependencies=[Depends(admin_only)])
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


@router.get("/logs", dependencies=[Depends(admin_only)])
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


@router.get("/db/connections", dependencies=[Depends(admin_only)])
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


@router.get("/db/slow-queries", dependencies=[Depends(admin_only)])
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


@router.get("/cache/stats", dependencies=[Depends(admin_only)])
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


@router.get("/webhooks/health", dependencies=[Depends(admin_only)])
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


@router.get("/providers/health", dependencies=[Depends(admin_only)])
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


@router.get("/charon/health", dependencies=[Depends(admin_only)])
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
