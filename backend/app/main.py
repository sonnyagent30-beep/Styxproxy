"""Styxproxy Backend FastAPI Application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.database import engine
from app.limiter import limiter
from app.models import Base
from app.routers import (
    admin,
    admin_support,
    analytics,
    auth,
    blog,
    catalog,
    charon,
    charon_ab,
    contact,
    costs,
    credentials,
    health,
    inbound,
    incident_notification,
    maintenance,
    ops,
    orders,
    payment_status,
    payments,
    permissions,
    platform,
    products,
    proxies,
    rls,
    session,
    superadmin,
    trials,
    unsubscribe,
    webhooks,
    admin_secrets,
)

settings = get_settings()

# Configure logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting Styxproxy Backend", version="1.0.0")

    # Create database tables (if they don't exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure all orders columns exist (idempotent, for migrations that may have failed)
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            columns_to_add = [
                ("platform_account_id", "UUID"),
                ("customer_phone", "VARCHAR(20)"),
                ("plan_type", "VARCHAR(20)"),
                ("plan_code", "VARCHAR(50)"),
                ("country", "VARCHAR(10)"),
                ("quantity", "INTEGER"),
                ("amount_paid_ngn", "NUMERIC(12, 2)"),
                ("payment_reference", "VARCHAR(100)"),
                ("tx_ref", "VARCHAR(100)"),
                ("provider", "VARCHAR(50)"),
                ("provider_order_id", "VARCHAR(100)"),
                ("styxproxy_credential_id", "INTEGER"),
                ("status", "VARCHAR(50) DEFAULT 'pending'"),
                ("ip_tested", "BOOLEAN DEFAULT false"),
                ("ip_test_result", "VARCHAR(10)"),
                ("data_total_gb", "NUMERIC(10, 2)"),
                ("data_remaining_gb", "NUMERIC(10, 2)"),
                ("data_expires", "TIMESTAMP WITH TIME ZONE"),
                ("expires_at", "TIMESTAMP WITH TIME ZONE"),
                ("ban_reported", "BOOLEAN DEFAULT false"),
                ("screenshot_url", "TEXT"),
                ("ban_verified", "VARCHAR(50)"),
                ("replacement_count", "INTEGER DEFAULT 0"),
                ("refund_requested", "BOOLEAN DEFAULT false"),
                ("refund_reason", "TEXT"),
                ("notes", "TEXT"),
                ("fulfilled_at", "TIMESTAMP WITH TIME ZONE"),
                ("cost_usd", "NUMERIC(10, 4)"),
                ("rotation_mode", "VARCHAR(20)"),
                ("city_id", "INTEGER"),
                ("city_name", "VARCHAR(100)"),
                ("referral_tx_ref", "VARCHAR(100)"),
                ("emails_sent", "INTEGER DEFAULT 0"),
                ("reminder_sent_at", "TIMESTAMP WITH TIME ZONE"),
            ]
            for col_name, col_type in columns_to_add:
                await conn.execute(
                    text(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                )
            logger.info("Orders table columns verified/updated")
    except Exception as e:
        logger.warning(f"Orders column migration skipped: {e}")

    # Seed initial trigger weights if they don't exist
    from sqlalchemy import text

    async with engine.connect() as conn:
        TRIGGERS = [
            "repeat_pricing",
            "pricing_dwell",
            "product_browse",
            "cart_abandon",
            "order_confusion",
            "session_stuck",
            "scroll_bottom",
            "exit_intent",
            "geo_question",
        ]
        for trigger_id in TRIGGERS:
            await conn.execute(
                text(
                    """
                    INSERT INTO trigger_weights
                        (trigger_id, weight, total_fires, total_opens, total_dismissed, total_converted, positive_rate)
                    VALUES (:tid, 1.0, 0, 0, 0, 0, 0)
                    ON CONFLICT (trigger_id) DO NOTHING
                    """
                ),
                {"tid": trigger_id},
            )
        await conn.commit()

    # Initialize Sentry if configured
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            environment="production" if settings.is_production else "development",
        )
        logger.info("Sentry initialized")

    yield

    # Shutdown: drain in-flight requests before closing connections.
    # Systemd sends SIGTERM on restart. Uvicorn's --timeout-graceful-shutdown
    # (30s) handles the HTTP drain. We add a small async sleep so the lifespan
    # shutdown handler completes cleanly before engine dispose.
    logger.info("Shutting down Styxproxy Backend — draining connections")
    import asyncio
    await asyncio.sleep(0.5)  # allow pending tasks to complete
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Styxproxy Backend API",
    description="Backend API for Styxproxy proxy reseller platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Initialize Sentry (no-op when SENTRY_DSN is not set)
from app.services import observability  # noqa: E402

observability.init_sentry()

# Add rate limiter to app state
app.state.limiter = limiter

# Sprint 5: Enable the limiter middleware so @limiter.limit decorators actually fire.
# Without this, all decorators are silent no-ops (we discovered this Jul 28 — Sprint 5).
# Also: SlowAPIMiddleware MUST be added BEFORE CORSMiddleware so it runs first in the chain.
app.add_middleware(SlowAPIMiddleware)


# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors.

    If the rate-limited path is Charon's public /reply (the only
    high-cost customer endpoint), bump the in-process CharonMetrics
    counter so the superadmin dashboard reflects the live flood state.
    Other endpoints (auth, etc.) keep their existing behavior.
    """
    if request.url.path.startswith("/api/v1/charon/"):
        from app.services.charon.stats import CharonMetrics

        CharonMetrics.mark_rate_limited()
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded: {exc.detail}",
            }
        },
        headers={"Retry-After": "60"},
    )


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware — adds request_id, logs completion with status + duration
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with request_id, status code, and elapsed time."""
    import time
    import uuid as uuid_lib

    request_id = request.headers.get("X-Request-ID") or str(uuid_lib.uuid4())[:8]

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.perf_counter()

    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    response = await call_next(request)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)

    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
    )

    response.headers["X-Request-ID"] = request_id
    return response


# HSTS middleware — enforces Strict-Transport-Security on HTTPS requests only.
# Without HSTS, browsers may opportunistically fall back to HTTP, enabling
# SSL-stripping attacks (HSTS-1 LOW, STYXv2-003-SEC).
@app.middleware("http")
async def hsts_middleware(request: Request, call_next):
    """Add HSTS header only for HTTPS requests."""
    response = await call_next(request)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Maintenance mode middleware — when enabled, blocks public routes with 503
# but lets admin/superadmin/health/webhooks/payment-processing routes through
# so the platform can keep processing payments, credentials, and admin
# operations even during a public-facing outage window.
MAINTENANCE_EXEMPT_PREFIXES = (
    # Admin / superadmin (and the maintenance state endpoint itself)
    "/api/admin",
    # Health + docs
    "/api/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    # Webhook receivers (Flutterwave, WhatsApp) — must keep accepting
    "/api/webhooks",
    # Payment + credential processing — keep in-flight orders alive
    "/api/payments",
    "/api/credentials",
    "/api/orders",
    # Support chat inbox / inbound messages
    "/api/inbound",
    # Charon runtime + public maintenance state (so admin UI can check)
    "/api/charon",
    "/api/public",
    # Session + trials (auth flows)
    "/api/session",
    "/api/trials",
)


@app.middleware("http")
async def maintenance_block(request: Request, call_next):
    """If maintenance mode is on, return 503 for public routes only.

    Admin/Superadmin routes and webhook/ingest endpoints are exempt so
    the platform can keep processing payments, credentials, and admin
    operations even during a public-facing outage window.
    """
    path = request.url.path

    # Static and the admin frontend itself are always available
    if any(path.startswith(p) for p in MAINTENANCE_EXEMPT_PREFIXES):
        return await call_next(request)

    # Only check on GET requests (POST/PUT/DELETE on public routes are
    # handled by the public read paths too — but the frontend is React,
    # not the API, so this is the right boundary)
    if request.method != "GET":
        return await call_next(request)

    # Check maintenance state
    try:
        from sqlalchemy import select

        from app.database import async_session
        from app.models import FeatureFlag

        async with async_session() as session:
            flag = (
                await session.execute(select(FeatureFlag).where(FeatureFlag.name == "maintenance_mode"))
            ).scalar_one_or_none()

            if flag and flag.enabled:
                # Read optional message + ready_at
                from app.models import FeatureFlag as FF

                ra = (await session.execute(select(FF).where(FF.name == "maintenance_ready_at"))).scalar_one_or_none()
                msg = (await session.execute(select(FF).where(FF.name == "maintenance_message"))).scalar_one_or_none()

                return JSONResponse(
                    status_code=503,
                    content={
                        "maintenance": True,
                        "ready_at": ra.description if ra else None,
                        "message": msg.description if msg else None,
                    },
                    headers={"Retry-After": "300"},
                )
    except Exception:
        # If the DB check itself fails, don't block traffic
        pass

    return await call_next(request)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions with request context."""
    import traceback
    logger.error(
        "Uncaught exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc(),
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "detail": str(exc),
                "request_id": structlog.contextvars.get_contextvars().get("request_id"),
            }
        },
    )


# Include routers
app.include_router(health)
app.include_router(platform)
app.include_router(proxies)
app.include_router(products)
app.include_router(orders)
app.include_router(payments)
app.include_router(webhooks)
app.include_router(admin_secrets.router)
app.include_router(credentials)
app.include_router(trials)
app.include_router(admin)
app.include_router(admin_support)
app.include_router(session)
app.include_router(charon)
app.include_router(contact)
app.include_router(auth)
app.include_router(catalog)
app.include_router(payment_status)
app.include_router(permissions)
app.include_router(rls)
app.include_router(blog)
app.include_router(inbound)
app.include_router(superadmin)
app.include_router(maintenance)
app.include_router(unsubscribe)
app.include_router(incident_notification)
app.include_router(costs)
app.include_router(analytics)
app.include_router(charon_ab)
app.include_router(ops, prefix="")
