"""Audit service for immutable audit logging."""
import hashlib
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models import CustomerAuditLog, AdminAuditLog


async def log_audit_event(db_session: Optional[AsyncSession], event_type: str, customer_hash: Optional[str] = None, phone: Optional[str] = None, order_id: Optional[str] = None, workflow: Optional[str] = None, status: Optional[str] = None, details: Optional[dict[str, Any]] = None, request_id: Optional[str] = None) -> None:
    if db_session is None:
        return
    if phone and not customer_hash:
        customer_hash = hashlib.sha256(phone.encode()).hexdigest()[:20]
    audit_entry = CustomerAuditLog(request_id=request_id, customer_hash=customer_hash, event_type=event_type, order_id=order_id, workflow=workflow, status=status, details=details)
    db_session.add(audit_entry)
    await db_session.commit()

async def get_audit_logs(db_session: AsyncSession, customer_hash: Optional[str] = None, event_type: Optional[str] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, page: int = 1, limit: int = 20) -> tuple[list[CustomerAuditLog], int]:
    from sqlalchemy import select, func, and_
    base_conditions = []
    if customer_hash:
        base_conditions.append(CustomerAuditLog.customer_hash == customer_hash)
    if event_type:
        base_conditions.append(CustomerAuditLog.event_type == event_type)
    if date_from:
        base_conditions.append(CustomerAuditLog.timestamp >= date_from)
    if date_to:
        base_conditions.append(CustomerAuditLog.timestamp <= date_to)
    count_stmt = select(func.count()).select_from(CustomerAuditLog)
    if base_conditions:
        count_stmt = count_stmt.where(and_(*base_conditions))
    total = (await db_session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * limit
    stmt = select(CustomerAuditLog).order_by(CustomerAuditLog.timestamp.desc()).offset(offset).limit(limit)
    if base_conditions:
        stmt = stmt.where(and_(*base_conditions))
    result = await db_session.execute(stmt)
    logs = result.scalars().all()
    return list(logs), total


async def write_audit_log(
    db_session: AsyncSession,
    *,
    admin_email: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Any] = None,
    request: Optional[Request] = None,
) -> AdminAuditLog:
    """Write an admin audit log entry.

    Mirrors the live AdminAuditLog schema (id, admin_phone, action,
    ip_address, user_agent, details-as-text, created_at). The admin_email
    and resource_type/resource_id values are folded into the details blob so
    nothing is lost, then everything is JSON-serialized.

    Args:
        db_session: The database session
        admin_email: The admin's email who performed the action
        action: The action performed (e.g., "create_admin", "update_role")
        resource_type: Optional resource type (folded into details)
        resource_id: Optional resource id (folded into details)
        details: Optional additional details about the action (dict or scalar)
        request: Optional FastAPI Request object to extract IP address from
    """
    import json

    # Extract IP address from request headers
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    if request:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host
        user_agent = request.headers.get("user-agent")

    merged_details: dict[str, Any] = {"resource_type": resource_type}
    if isinstance(details, dict):
        merged_details.update(details)
    elif details is not None:
        merged_details["extra"] = details
    merged_details["resource_id"] = resource_id
    merged_details["admin_email"] = admin_email

    details_text = json.dumps(merged_details, default=str)

    audit_entry = AdminAuditLog(
        admin_phone=admin_email,  # column reused for email identity
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details_text,
    )
    db_session.add(audit_entry)
    await db_session.commit()
    await db_session.refresh(audit_entry)
    return audit_entry
