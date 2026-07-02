"""Audit service for immutable audit logging."""
import hashlib
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CustomerAuditLog

async def log_audit_event(db_session: Optional[AsyncSession], event_type: str, customer_hash: Optional[str] = None,
    phone: Optional[str] = None, order_id: Optional[str] = None, workflow: Optional[str] = None,
    status: Optional[str] = None, details: Optional[dict[str, Any]] = None, request_id: Optional[str] = None) -> None:
    if db_session is None: return
    if phone and not customer_hash:
        customer_hash = hashlib.sha256(phone.encode()).hexdigest()[:20]
    audit_entry = CustomerAuditLog(request_id=request_id, customer_hash=customer_hash, event_type=event_type,
        order_id=order_id, workflow=workflow, status=status, details=details)
    db_session.add(audit_entry)
    await db_session.commit()

async def get_audit_logs(db_session: AsyncSession, customer_hash: Optional[str] = None, event_type: Optional[str] = None,
    date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, page: int = 1, limit: int = 20) -> tuple:
    from sqlalchemy import select, func, and_
    base_conditions = []
    if customer_hash: base_conditions.append(CustomerAuditLog.customer_hash == customer_hash)
    if event_type: base_conditions.append(CustomerAuditLog.event_type == event_type)
    if date_from: base_conditions.append(CustomerAuditLog.timestamp >= date_from)
    if date_to: base_conditions.append(CustomerAuditLog.timestamp <= date_to)
    count_stmt = select(func.count()).select_from(CustomerAuditLog)
    if base_conditions: count_stmt = count_stmt.where(and_(*base_conditions))
    total = (await db_session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * limit
    stmt = select(CustomerAuditLog).order_by(CustomerAuditLog.timestamp.desc()).offset(offset).limit(limit)
    if base_conditions: stmt = stmt.where(and_(*base_conditions))
    result = await db_session.execute(stmt)
    logs = result.scalars().all()
    return list(logs), total
