"""Bunche Backend FastAPI Application."""
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import engine
from app.models import Base
from app.routers import (
    health,
    platform,
    products,
    orders,
    payments,
    webhooks,
    credentials,
    trials,
    admin,
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
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    ),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting Bunche Backend", version="1.0.0")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    # Shutdown
    logger.info("Shutting down Bunche Backend")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Bunche Backend API",
    description="Backend API for Bunche WhatsApp proxy reseller platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware — adds request_id, logs completion with status + duration
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with request_id, status code, and elapsed time."""
    import time
    import uuid as uuid_lib

    # Generate or extract request ID (allow upstream proxy to pass one via header)
    request_id = request.headers.get("X-Request-ID") or str(uuid_lib.uuid4())[:8]

    # Bind request_id to structlog context so every log line in this request includes it
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.perf_counter()

    # Log request start
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    # Call the endpoint
    response = await call_next(request)

    # Compute elapsed time
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)

    # Log request completion
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
    )

    # Add request_id to response headers so client can correlate logs
    response.headers["X-Request-ID"] = request_id

    return response


# Global exception handler — request_id already in structlog context
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions with request context."""
    logger.error(
        "Uncaught exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "request_id": structlog.contextvars.get_contextvars().get("request_id"),
            }
        },
    )


# Include routers
app.include_router(health.router)
app.include_router(platform.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
app.include_router(credentials.router)
app.include_router(trials.router)
app.include_router(admin.router)
