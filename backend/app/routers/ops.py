"""Monitor & Regulate API (S8) — internal ops service endpoints.

All endpoints require a service JWT with role: "ops-control".
Base URL: /_ops/v1/  (mounted at /ops/v1/ in main.py)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import (
    Customer,
    HealthSnapshot,
    Order,
    StyxproxyCredential,
)
from app.services.audit import write_audit_log
from app.services.ops_auth import require_ops_role
from app.services.refunds import GatewayRefundError, refund_at_gateway

settings = get_settings()

router = APIRouter(prefix="/_ops/v1", tags=["ops"])


# ─── Health ───────────────────────────────────────────────────────────────────


@router.get("/health")
async def ops_health(
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_ops_role("ops-control")),
) -> dict[str, Any]:
    """Deep health probe — DB + Redis + LiteLLM + Ollama + M2 cloud.

    Extends the /api/v1/health response with a history_summary showing
    last-24h uptime percentage from the health_snapshots table.
    """
    # Import helpers from health.py at call time to avoid circular imports
    from app.routers.health import _check_db, _check_litellm, _check_m2_cloud, _check_ollama, _check_redis

    db = await _check_db(session)
    redis = await _check_redis()
    litellm = await _check_litellm()
    ollama = await _check_ollama()
    m2 = await _check_m2_cloud()

    m2_ok = m2.get("status") == "connected"
    local_ok = litellm.get("status") == "connected" and ollama.get("status") == "connected"
    charon_available = m2_ok or local_ok

    if db != "connected":
        overall = "unhealthy"
    elif not charon_available:
        overall = "degraded"
    else:
        overall = "healthy"

    # Compute last-24h uptime from health_snapshots
    last_24h_uptime_pct: Optional[float] = None
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        total_snapshots = (
            await session.execute(
                select(func.count()).select_from(HealthSnapshot).where(HealthSnapshot.created_at >= cutoff)
            )
        ).scalar() or 0
        healthy_snapshots = (
            await session.execute(
                select(func.count())
                .select_from(HealthSnapshot)
                .where(HealthSnapshot.created_at >= cutoff)
                .where(HealthSnapshot.overall_status == "healthy")
            )
        ).scalar() or 0
        if total_snapshots > 0:
            last_24h_uptime_pct = round(healthy_snapshots / total_snapshots * 100, 2)
    except Exception:
        pass  # Non-fatal — leave uptime as null

    return {
        "services": {
            "db": db,
            "redis": redis,
            "m2": m2,
            "litellm": litellm,
            "ollama": ollama,
        },
        "status": overall,
        "history_summary": {
            "last_24h_uptime_pct": last_24h_uptime_pct,
        },
    }


# ─── Metrics ─────────────────────────────────────────────────────────────────


@router.get("/metrics")
async def ops_metrics(
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_ops_role("ops-control")),
) -> dict[str, Any]:
    """Platform metrics summary — all from async DB queries."""
    # Total customers
    total_customers = (await session.execute(select(func.count()).select_from(Customer))).scalar() or 0

    # Total orders
    total_orders = (await session.execute(select(func.count()).select_from(Order))).scalar() or 0

    # Order status counts
    paid_count = (
        await session.execute(select(func.count()).select_from(Order).where(Order.status == "paid"))
    ).scalar() or 0
    fulfilled_count = (
        await session.execute(select(func.count()).select_from(Order).where(Order.status == "fulfilled"))
    ).scalar() or 0
    refunded_count = (
        await session.execute(select(func.count()).select_from(Order).where(Order.status == "refunded"))
    ).scalar() or 0

    # Revenue (paid + fulfilled orders)
    revenue_ngn = (
        await session.execute(select(func.sum(Order.amount_paid_ngn)).where(Order.status.in_(["paid", "fulfilled"])))
    ).scalar() or 0.0

    # Active credentials
    active_credentials = (
        await session.execute(
            select(func.count()).select_from(StyxproxyCredential).where(StyxproxyCredential.status == "active")
        )
    ).scalar() or 0

    # Trial orders
    trial_count = (
        await session.execute(select(func.count()).select_from(Order).where(Order.status == "trial"))
    ).scalar() or 0

    return {
        "total_customers": total_customers,
        "total_orders": total_orders,
        "paid_count": paid_count,
        "fulfilled_count": fulfilled_count,
        "refunded_count": refunded_count,
        "revenue_ngn": float(revenue_ngn),
        "trial_count": trial_count,
        "active_credentials": active_credentials,
    }


# ─── Order operations ──────────────────────────────────────────────────────────


@router.post("/orders/{order_id}/refund")
async def ops_refund_order(
    order_id: str,
    request: Request,
    reason: str,
    session: AsyncSession = Depends(get_session),
    jwt_payload: dict = Depends(require_ops_role("ops-control")),
) -> dict[str, Any]:
    """Ops-triggered refund — calls Flutterwave and marks order refunded.

    Only refunds orders that are already paid or fulfilled.
    Logs action to admin_audit_log.
    """
    # Look up order
    result = await session.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ("paid", "fulfilled"):
        raise HTTPException(status_code=400, detail=f"Cannot refund order with status '{order.status}'")

    if order.status == "refunded":
        raise HTTPException(status_code=400, detail="Order already refunded")

    admin_email = jwt_payload.get("sub", "ops-service")

    # Refund AT THE GATEWAY and carry the gateway's response through. The old
    # code threw the result away (`_ = await _flutterwave_refund(...)`) and
    # flipped the status regardless of what the gateway actually said, so a
    # `refunded` order carried no evidence any money moved.
    try:
        refund = await refund_at_gateway(order, reason=reason or "Ops refund")
    except GatewayRefundError as e:
        # Log the failed attempt and re-raise so caller knows. The order is NOT
        # marked refunded and stays actionable.
        await write_audit_log(
            db_session=session,
            admin_email=admin_email,
            action="ops_refund_failed",
            resource_type="order",
            resource_id=order_id,
            details={
                "reason": reason,
                "error": str(e),
                "reference": order.tx_ref or order.payment_reference,
                "order_status_unchanged": order.status,
            },
            request=request,
        )
        raise HTTPException(status_code=502, detail=f"Gateway refund failed: {e}")

    # Mark order refunded — the gateway confirmed.
    order.status = "refunded"
    order.refund_requested = True
    order.refund_reason = reason
    order.gateway_refund_id = refund.gateway_refund_id
    order.gateway_refund_status = refund.gateway_status
    order.gateway_refund_amount = refund.amount_ngn
    order.gateway_refunded_at = datetime.now(timezone.utc)
    await session.commit()

    # Audit log
    await write_audit_log(
        db_session=session,
        admin_email=admin_email,
        action="ops_refund",
        resource_type="order",
        resource_id=order_id,
        details={
            "reason": reason,
            "tx_ref": refund.reference,
            "provider": refund.provider,
            "gateway_refund_id": refund.gateway_refund_id,
            "gateway_refund_status": refund.gateway_status,
            "amount": refund.amount_ngn,
        },
        request=request,
    )

    return {
        "status": "refunded",
        "tx_ref": refund.reference,
        "provider": refund.provider,
        "gateway_refund_id": refund.gateway_refund_id,
        "gateway_refund_status": refund.gateway_status,
        "amount": refund.amount_ngn,
    }


@router.post("/orders/{order_id}/reprocess")
async def ops_reprocess_order(
    order_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    jwt_payload: dict = Depends(require_ops_role("ops-control")),
) -> dict[str, Any]:
    """Re-trigger fulfillment for a paid order whose fulfillment failed.

    Re-runs create_credential() and marks order fulfilled on success.
    Marks order failed_unfulfilled again on error. Logs to admin_audit_log.

    Accepts BOTH terminal failure statuses. The previous guard was
    `if order.status != "failed_unfulfilled"`, which refused
    `failed_manual_review` — the status the webhook sets for a non-provider
    exception. So the endpoint refused the exact failure class it exists to
    recover, and a paid order in that state could not be requeued at all.
    """
    from app.services.credential import create_credential, resolve_country_for_credential

    # Look up order
    result = await session.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    REPROCESSABLE = {"failed_unfulfilled", "failed_manual_review"}
    if order.status not in REPROCESSABLE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot reprocess order with status '{order.status}'. "
                f"Reprocessable statuses: {sorted(REPROCESSABLE)}"
            ),
        )

    admin_email = jwt_payload.get("sub", "ops-service")

    try:
        credential, plaintext_password = await create_credential(
            db_session=session,
            order_id=order.order_id,
            customer_phone=order.customer_phone or "",
            plan_code=order.plan_code or "unknown",
            country=resolve_country_for_credential(order.country),
            proxy_type="isp",
            quantity=1,
            duration_days=30,
            protocol="socks5",
            pool_type="paid",
        )
        order.styxproxy_credential_id = credential.id
        order.status = "fulfilled"
        await session.commit()

        await write_audit_log(
            db_session=session,
            admin_email=admin_email,
            action="ops_reprocess_success",
            resource_type="order",
            resource_id=order_id,
            details={"credential_id": credential.id},
            request=request,
        )

        return {"status": "fulfilled", "order_id": order_id}

    except Exception as e:
        order.status = "failed_unfulfilled"
        await session.commit()

        await write_audit_log(
            db_session=session,
            admin_email=admin_email,
            action="ops_reprocess_failed",
            resource_type="order",
            resource_id=order_id,
            details={"error": str(e)},
            request=request,
        )

        raise HTTPException(status_code=500, detail=f"Reprocess failed: {e}")


# ─── Slow queries ─────────────────────────────────────────────────────────────


@router.get("/slow-queries")
async def ops_slow_queries(
    threshold_ms: int = Query(default=200, ge=1),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_ops_role("ops-control")),
) -> dict[str, Any]:
    """Query pg_stat_statements for slow queries.

    Falls back to empty list with note if pg_stat_statements is not available.
    threshold_ms filters queries exceeding the given latency threshold.
    """
    try:
        # pg_stat_statements must be enabled via shared_preload_libraries
        result = await session.execute(
            text(
                """
                SELECT query, calls, total_exec_time_ms, mean_exec_time_ms, max_exec_time_ms
                FROM pg_stat_statements
                WHERE total_exec_time_ms > :threshold
                ORDER BY total_exec_time_ms DESC
                LIMIT 50
                """
            ).bindparams(threshold=float(threshold_ms))
        )
        rows = result.fetchall()
        queries = [
            {
                "query": row[0][:500],  # truncate long queries
                "calls": row[1],
                "total_time_ms": round(float(row[2]), 2),
                "mean_time_ms": round(float(row[3]), 2),
                "max_time_ms": round(float(row[4]), 2),
            }
            for row in rows
        ]
        return {"queries": queries, "note": None}
    except Exception:
        return {
            "queries": [],
            "note": "pg_stat_statements not available or not enabled",
        }


# ─── Health history ───────────────────────────────────────────────────────────


@router.get("/health/history")
async def ops_health_history(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=500, ge=1, le=5000),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_ops_role("ops-control")),
) -> dict[str, Any]:
    """Read health_snapshots time-series.

    Requires role: ops-control (same as all other /_ops/v1/ endpoints).
    Reuses the same query logic as the admin health_history endpoint.
    """
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
