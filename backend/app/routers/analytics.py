"""Analytics router for tracking and reporting funnel events."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
    AnalyticsEventsListResponse,
    AnalyticsFunnelResponse,
    FunnelStage,
)
from app.services.permissions import require_permission

router = APIRouter(prefix="/api/v1/admin/analytics", tags=["admin-analytics"])


# Funnel stages in order
FUNNEL_STAGES = [
    "page_view",
    "plan_viewed",
    "cart_added",
    "checkout_started",
    "payment_completed",
]


async def get_current_admin(authorization: str = Query(...)) -> bool:
    """Dependency to verify admin authorization."""
    if not verify_admin_token(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    return True


@router.get("/funnel", response_model=AnalyticsFunnelResponse)
async def get_funnel_analytics(
    from_date: Optional[datetime] = Query(
        None, description="Start date for analytics (defaults to 30 days ago)"
    ),
    to_date: Optional[datetime] = Query(
        None, description="End date for analytics (defaults to now)"
    ),
    admin: bool = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Get funnel analytics with conversion rates between stages.
    
    Returns counts for each funnel stage and conversion rates relative to the previous stage.
    """
    # Default date range: last 30 days
    if from_date is None:
        from_date = datetime.now(timezone.utc) - timedelta(days=30)
    if to_date is None:
        to_date = datetime.now(timezone.utc)

    # Ensure timezone-aware
    if from_date.tzinfo is None:
        from_date = from_date.replace(tzinfo=timezone.utc)
    if to_date.tzinfo is None:
        to_date = to_date.replace(tzinfo=timezone.utc)

    stages = []
    previous_count = None
    total_events = 0

    for event_name in FUNNEL_STAGES:
        # Query count for this event in the date range
        stmt = text("""
            SELECT COUNT(*) as cnt 
            FROM analytics_events 
            WHERE event_name = :event_name 
            AND created_at >= :from_date 
            AND created_at <= :to_date
        """)
        
        result = await session.execute(stmt, {
            "event_name": event_name,
            "from_date": from_date,
            "to_date": to_date
        })
        count = result.scalar() or 0
        
        # Calculate conversion rate
        conversion_rate = None
        if previous_count is not None and previous_count > 0:
            conversion_rate = round((count / previous_count) * 100, 2)
        
        stages.append(FunnelStage(
            event_name=event_name,
            count=count,
            conversion_rate=conversion_rate
        ))
        
        previous_count = count
        total_events += count

    return AnalyticsFunnelResponse(
        stages=stages,
        total_events=total_events,
        period_start=from_date,
        period_end=to_date
    )


@router.get("/events", response_model=AnalyticsEventsListResponse)
async def list_analytics_events(
    event_name: Optional[str] = Query(None, description="Filter by event name"),
    from_date: Optional[datetime] = Query(None, description="Start date filter"),
    to_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(50, ge=1, le=500, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    admin: bool = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    List analytics events with optional filters.
    
    Supports filtering by event_name, date range, and supports pagination.
    """
    # Build WHERE clause
    conditions = []
    params = {}
    
    if event_name:
        conditions.append("event_name = :event_name")
        params["event_name"] = event_name
    
    if from_date:
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        conditions.append("created_at >= :from_date")
        params["from_date"] = from_date
    
    if to_date:
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)
        conditions.append("created_at <= :to_date")
        params["to_date"] = to_date
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Get total count
    count_stmt = text(f"SELECT COUNT(*) FROM analytics_events WHERE {where_clause}")
    total_result = await session.execute(count_stmt, params)
    total = total_result.scalar() or 0
    
    # Get paginated events
    query_stmt = text(f"""
        SELECT id, event_name, session_id, customer_phone, tx_ref, 
               country, plan_code, channel, meta, created_at
        FROM analytics_events 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    params["limit"] = limit
    params["offset"] = offset
    
    result = await session.execute(query_stmt, params)
    rows = result.fetchall()
    
    events = [
        AnalyticsEventResponse(
            id=row.id,
            event_name=row.event_name,
            session_id=row.session_id,
            customer_phone=row.customer_phone,
            tx_ref=row.tx_ref,
            country=row.country,
            plan_code=row.plan_code,
            channel=row.channel,
            meta=row.meta if isinstance(row.meta, dict) else {},
            created_at=row.created_at
        )
        for row in rows
    ]
    
    return AnalyticsEventsListResponse(
        events=events,
        total=total,
        page=(offset // limit) + 1,
        page_size=limit
    )


@router.post("/events", response_model=AnalyticsEventResponse, status_code=201)
async def create_analytics_event(
    event: AnalyticsEventCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new analytics event.
    
    This endpoint is public (no admin auth required) for tracking from frontend.
    """
    stmt = text("""
        INSERT INTO analytics_events 
        (event_name, session_id, customer_phone, tx_ref, country, plan_code, channel, meta, created_at)
        VALUES (:event_name, :session_id, :customer_phone, :tx_ref, :country, :plan_code, :channel, :meta::jsonb, NOW())
        RETURNING id, event_name, session_id, customer_phone, tx_ref, country, plan_code, channel, meta, created_at
    """)
    
    result = await session.execute(stmt, {
        "event_name": event.event_name,
        "session_id": event.session_id,
        "customer_phone": event.customer_phone,
        "tx_ref": event.tx_ref,
        "country": event.country,
        "plan_code": event.plan_code,
        "channel": event.channel,
        "meta": event.meta
    })
    
    await session.commit()
    
    row = result.fetchone()
    
    return AnalyticsEventResponse(
        id=row.id,
        event_name=row.event_name,
        session_id=row.session_id,
        customer_phone=row.customer_phone,
        tx_ref=row.tx_ref,
        country=row.country,
        plan_code=row.plan_code,
        channel=row.channel,
        meta=row.meta if isinstance(row.meta, dict) else {},
        created_at=row.created_at
    )
