"""Styxproxy Backend API"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.limiter import limiter

logger = logging.getLogger("app.main")

# ─── Observability ───────────────────────────────────────────────────────────
from app.services import observability  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    observability.init_sentry()

    # Add rate limiter to app state
    app.state.limiter = limiter

    # Sprint 5: Enable the limiter middleware so @limiter.limit decorators actually fire.
    # Without this, all decorators are silent no-ops (we discovered this Jul 28 — Sprint 5).
    # Also: SlowAPIMiddleware MUST be added BEFORE CORSMiddleware so it runs first in the chain.
    # DISABLED: SlowAPIMiddleware causes AttributeError on AuthenticationError in slowapi 0.1.10
    # https://github.com/numberoverzero/slowapi/issues/XXX
    # app.add_middleware(SlowAPIMiddleware)

    yield

    # Cleanup
    observability.sentry.finish()


settings = get_settings()
app = FastAPI(
    title="Styxproxy API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Called by fastapi when a rate limit is exceeded."""
    return JSONResponse(
        status_code=429,
        content={
            "error": f"Rate limit exceeded: {exc.detail}",
            "error_code": "RATE_LIMIT_EXCEEDED",
        },
    )


# ─── Middleware stack ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Routes ──────────────────────────────────────────────────────────────────
# Lazy import to avoid circular deps at module level
from app.routers import (  # noqa: E402
    admin_providers,
    admin_proxy_stats,
    admin_users,
    analytics,
    auth,
    charon,
    charon_ab,
    costs,
    health,
    metrics,
    orders,
    plan_settings,
    plans,
    platform_accounts,
    proxy_stats,
    providers,
    rotation,
    styxproxy_credentials,
    user_accounts,
    webhooks,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(plans.router)
app.include_router(plan_settings.router)
app.include_router(providers.router)
app.include_router(styxproxy_credentials.router)
app.include_router(user_accounts.router)
app.include_router(admin_users.router)
app.include_router(proxy_stats.router)
app.include_router(admin_proxy_stats.router)
app.include_router(webhooks.router)
app.include_router(analytics.router)
app.include_router(costs.router)
app.include_router(charon.router)
app.include_router(charon_ab.router)
app.include_router(rotation.router)
app.include_router(platform_accounts.router)
app.include_router(metrics.router)
app.include_router(admin_providers.router)


@app.get("/")
async def root():
    return {"message": "Styxproxy API", "version": "1.0.0"}
