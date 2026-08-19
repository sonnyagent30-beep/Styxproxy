# Styxproxy Backend & DB Architecture Audit

**Audited:** 2026-08-19
**Scope:** Backend FastAPI + PostgreSQL + Docker + Frontend-Backend contract
**Severity scale:** CRITICAL / HIGH / MEDIUM / LOW / INFO

---

## 1. Backend — FastAPI Application

### 1.1 Application Structure

- **Entry point:** `backend/app/main.py` — FastAPI app with lifespan context manager
- **Routers (29 included):** `admin` (2014 lines), `orders` (1334), `blog` (967), `auth` (1221), `charon` (708), `superadmin` (799), `admin_support` (362), `health` (379), `ops` (410), `credentials`, `payments`, `webhooks`, `trials`, `inbound`, `maintenance`, `rls`, `analytics`, and others
- **ORM:** SQLAlchemy async (`asyncpg` driver) — `AsyncSession` throughout
- **Auth:** JWT (`python-jose`) + bcrypt (`passlib`) + TOTP (`pyotp`)
- **Rate limiting:** `slowapi` with Redis-backed moving-window strategy
- **Logging:** `structlog` with JSONRenderer + request_id context
- **Observability:** Sentry SDK (traces_sample_rate configurable), DeepSeek/w是一只鸭 for LLM observability

### 1.2 Connection Pooling

```python
# backend/app/database.py
engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    echo=False,
    pool_pre_ping=True,
)
```

**Finding [MEDIUM]:** Pool sizing is static. `pool_size=20` is reasonable for a medium VPS but has no runtime adaptation. Under burst load (e.g. a营销 campaign), 20 connections may be insufficient. No circuit breaker pattern is visible in the payment or credential paths.

### 1.3 Middleware Stack (in order)

| # | Middleware | Purpose |
|---|---|---|
| 1 | `SlowAPIMiddleware` | Rate limit enforcement |
| 2 | `CORSMiddleware` | `allow_credentials=True`, `allow_headers=["*"]` |
| 3 | `log_requests` (http) | Request logging with duration + request_id |
| 4 | `maintenance_block` (http) | 503 on public routes when `maintenance_mode` FeatureFlag is on |

**Finding [HIGH]:** `allow_credentials=True` with `allow_headers=["*"]` is a CORS misconfiguration. `allow_headers=["*"]` is not restricted by the CORS spec when credentials are present — in practice it means the server echoes back all headers including Authorization cookies. Combined with the broad `cors_origins` list, this is a moderate risk.

**Finding [INFO]:** Maintenance mode check runs on every non-exempt request. It executes a synchronous DB query (`select FeatureFlag...`) on the hot path for every public GET. This adds ~5-10ms per request. Consider caching with a 30s TTL.

### 1.4 Idempotent Schema Patches at Startup

`main.py` lifespan runs 13 `ALTER TABLE` statements on every startup:

```python
for stmt_sql in idempotent_patches:
    try:
        async with engine.begin() as conn:
            await conn.execute(text(stmt_sql))
    except Exception as patch_err:
        logger.warning("idempotent_patch_skipped", ...)
```

**Finding [HIGH]:** These patches run on every startup with bare `except Exception`. A failed migration (e.g. wrong column type, missing role) silently continues. If the alembic migration history diverges from what's expected, the app boots but the column is absent — queries fail at runtime rather than failing fast. The proper approach is versioned Alembic migrations applied once.

**Finding [HIGH]:** Column names in the patches reference `styxproxy_credentials.rotation_count`, `country_target`, etc. — but `models.py` also defines `rotation_mode`, `sticky_session_minutes`, `bandwidth_alert_pct` as ORM-mapped columns that must be present. If the `ALTER TABLE` fails silently, the ORM falls back to defaults but data is lost.

### 1.5 Credentials Encryption at Rest

`StyxproxyCredential.styxproxy_password` is stored as encrypted bytes (Fernet/AES-128-CBC). Encryption/decryption is handled by `app/services/crypto.py` via `get_password()` / `set_password()`.

```python
# Set on credential creation
ciphertext = encrypt_credential(plaintext)  # returns None if CRED_ENCRYPTION_KEY is not set
if ciphertext is None:
    logging.getLogger(__name__).error("Refusing to set styxproxy_password...")
    return
self.styxproxy_password = ciphertext
```

**Finding [HIGH]:** `encrypt_credential()` returns `None` when the key is absent. The caller (`set_password()`) logs an error and returns without raising — the credential is silently not encrypted. The app continues to boot normally. If `CRED_ENCRYPTION_KEY` is not set in production, proxy passwords are written as `None` or plaintext and credentials fail.

**Finding [MEDIUM]:** No enforcement at startup. The config validator in `config.py` does not fail if `cred_encryption_key` is absent. This should be a FAIL condition for production (not just a WARNING).

### 1.6 Auth Endpoints

| Endpoint | Auth | Notes |
|---|---|---|
| `POST /api/admin/auth/login` | PIN (legacy) | Rate limited 10/5min |
| `POST /api/admin/auth/login/email` | email + password + optional TOTP | Primary login |
| `POST /api/admin/auth/setup` | invite code | Returns TOTP secret + backup codes |
| `POST /api/admin/auth/setup/complete` | temp_token + TOTP | Creates admin account |
| `POST /api/admin/auth/unlock/{email}` | `admin_token` in query param | Emergency unlock |
| `POST /api/admin/auth/password/forgot` | email | Rate limited 1/min |
| `POST /api/admin/auth/password/reset` | reset_token | Token hashed with bcrypt |

**Finding [MEDIUM]:** The `admin_token` for emergency unlock is passed as a **query parameter** (`secret` path param), not a header. Query params get logged in access logs, browser history, and can leak via referrer headers. This should use a header instead.

### 1.7 Ops Router

Mounted at `/_ops/v1/` (then exposed at `/ops/v1/`). Contains health probes, LLM metrics, DB metrics.

```python
router = APIRouter(prefix="/_ops/v1", tags=["ops"])
```

**Finding [CRITICAL]:** The `/_ops/v1/` prefix is a single path. There is no visible IP allowlisting or additional auth protecting it beyond the `require_ops_role` dependency. If `require_ops_role` only checks for a service JWT (no IP restriction), the ops endpoints are accessible to anyone who discovers the path.

---

## 2. Database Schema

### 2.1 Schema Drift — DOCUMENTED vs ACTUAL

The `docs/DATABASE_SCHEMA.md` (last updated 2026-07-01) describes a significantly different schema from what `models.py` implements:

| Element | Documented Schema | Actual ORM Model |
|---|---|---|
| `customers` PK | `id UUID` | `phone VARCHAR(20)` |
| `customers` lookup | `referral_code VARCHAR(20)` | No `referral_code` column |
| `platform_accounts.customer_id` | FK to `customers.id` (UUID) | FK to `customers.id` (UUID) — MATCHES |
| `styxproxy_credentials` username col | `bun_username VARCHAR(50)` | `styxproxy_username VARCHAR(50)` |
| `orders` PK | `order_id VARCHAR(20)` | `order_id VARCHAR(20)` — MATCHES |
| `orders` channel col | `channel_origin VARCHAR(20)` | No `channel_origin`; has `channel` FK via `platform_account` |
| `admin_auth` PK | `admin_phone VARCHAR(20)` | `email VARCHAR(255)` |
| `admin_auth` PIN | `pin_hash TEXT` | `pin_hash TEXT` — MATCHES |
| `admin_auth` TOTP | `totp_secret TEXT` | `totp_secret TEXT` — MATCHES |

**Finding [HIGH]:** Schema drift is severe for `customers`. The documented design uses a `referral_code` as the primary customer identifier; the actual model uses `phone` as the natural key. Any external tooling, documentation, or integrations built against the documented schema will break against the live DB.

**Finding [MEDIUM]:** `bun_username` → `styxproxy_username` mismatch. The documented column name was renamed. Code that queries by the old name (e.g. raw SQL in a script) will fail silently.

### 2.2 Key Tables

**`customers`** — Primary customer identity
- PK: `phone VARCHAR(20)` (not UUID — prevents phone number changes)
- No `referral_code` despite documented schema
- Fields: `pin_hash`, `blocked`, `free_trials_used_today`, `total_orders`, `lifetime_value_ngn`, `consent_given`, `support_notes`

**`platform_accounts`** — Per-platform identity (Telegram/WhatsApp/web)
- FK to `customers.id`
- `device_id VARCHAR(64)` — anonymous web sessions (no PII, just a localStorage UUID)
- Unique constraint on `(platform, platform_user_id)`
- Added via idempotent startup patch: `device_id` column added if absent

**`orders`** — Proxy orders
- PK: `order_id VARCHAR(20)`
- FK to `platform_account_id` (nullable — some orders may predate platform_accounts)
- FK to `customers.phone` via `customer_phone` (legacy)
- Fields: `tx_ref` (Flutterwave reference, indexed), `provider`, `styxproxy_credential_id`, `ban_reported`, `replacement_count`, `city_id`, `city_name` (Sprint 13)

**`styxproxy_credentials`** — Proxy auth credentials
- `styxproxy_username VARCHAR(50)` UNIQUE
- `styxproxy_password` — **encrypted** `LargeBinary` (Fernet ciphertext), NULL if encryption not configured
- `customer_phone` FK (legacy, not UUID)
- `order_id` FK
- Fields added via patches: `rotation_count`, `country_target`, `sticky_session_minutes`, `bandwidth_alert_pct`, `password_rotated_at`, `last_ip_country`, `last_ip_address`, `session_id`, `session_expires_at`, `rotation_mode`, `assigned_static_ip`, `location_change_count`, `rotation_mode_change_count`

**`admin_auth`** — Admin accounts
- PK: `email VARCHAR(255)` (migrated from `admin_phone` in legacy accounts)
- `pin_hash TEXT` — bcrypt
- `totp_secret TEXT` — plaintext Base32 (sensitive!)
- `locked_until` — account lockout
- `reset_token_hash` + `reset_token_expires` — password reset tokens

**`admin_totp_sessions`** — "Remember this device" TOTP sessions
- `session_token_hash` — Argon2-hashed (via `pwd_context`)
- `expires_at` — TTL-based
- No revocation list visible

**`customer_audit_log`** — Immutable audit trail
- No `platform_account_id` — uses `customer_hash` (first 20 chars of sha256 of phone)
- This limits the ability to query by platform account directly

### 2.3 Indexes

All major tables have appropriate indexes. Notable:
- `processed_webhooks.webhook_id` — UNIQUE (idempotency)
- `orders.tx_ref` — indexed (Flutterwave lookups)
- `orders.customer_phone` — indexed (legacy phone-based lookups)
- `styxproxy_credentials.styxproxy_username` — unique index
- `styxproxy_credentials.status` + `pool_type` — composite index for pool queries

### 2.4 RLS (Row-Level Security)

**Status: ROLLED BACK** — documented in `RlsPolicy` model docstring.

```
RLS was rolled back in commit 0ba7241 (security review found the
policies too restrictive). This table tracks future RLS decisions.
```

RLS is currently **DISABLED** on all tables. The `rls_policy` table exists and tracks intended policy state. There is no `FORCE ROW LEVEL SECURITY` setting active.

**Finding [HIGH]:** With RLS disabled, any SQL injection vulnerability in application code or a compromised service account would have direct table access. The defense-in-depth RLS layer is not active.

**Finding [MEDIUM]:** `customer_audit_log` has no `platform_account_id` — audit events cannot be joined to platform accounts. The `customer_hash` (first 20 chars of phone sha256) is the only linkage, which is irreversible and loses information.

---

## 3. Frontend-Backend Contract

### 3.1 API Contract

`docs/API-CONTRACT.md` (generated 2026-07-23) is the single source of truth. Key rules:
- Field naming: snake_case throughout (BE Pydantic ↔ FE TypeScript)
- Money in **kobo** (integer, no floats)
- IDs: UUID strings
- Pagination: `page` (1-indexed) + `page_size` (default 20, max 100)
- Error format: `{"detail": "Human-readable message"}` or Pydantic 422 array
- Auth: `Authorization: Bearer <token>` on `/api/admin/*` and `/api/auth/*`

### 3.2 FE → BE Sync

**Backend authoritative:** `backend/app/schemas.py` (1825 lines of Pydantic models)
**Frontend mirror:** `frontend/src/types/index.ts`
**API calls:** `frontend/src/lib/api.ts` — `ApiClient` class with per-endpoint methods

**Finding [MEDIUM]:** Drift detection is manual ("PR reviewer checks"). No automated test verifies that every FE `request()` call has a matching BE route. A route added to the BE without updating FE types silently breaks at runtime.

**Finding [LOW]:** The `API_BASE_URL` in `api.ts` defaults to `'https://api.styxproxy.com'` (production). During local FE development against a local BE, `NEXT_PUBLIC_API_BASE_URL` must be set explicitly. The comment in the code documents this but it's easy to miss.

### 3.3 Public Endpoints (no auth required)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Basic health |
| `GET /products` | Plan catalog |
| `GET /catalog` | BE-driven plan templates |
| `GET /api/blog/posts` | Blog posts |
| `GET /api/public/checkout-status` | Checkout disabled flag |
| `POST /api/webhooks/flutterwave` | Flutterwave payment webhook |
| `POST /api/webhooks/theorem-reach` | TheoremReach survey webhook |
| `POST /api/orders/precheck` | Provider availability precheck |
| `POST /api/payments/initiate` | Initiate Flutterwave payment |
| `GET /api/blog/categories` | Blog categories |

**Finding [INFO]:** The public endpoint surface is reasonable. Flutterwave webhook is HMAC-verified. No IDOR-visible on precheck/initiate (order_id not yet assigned).

---

## 4. Staging vs Prod Deployment Parity

### 4.1 Current State

No separate `docker-compose.staging.yml` or `docker-compose.prod.yml` is present. Both staging and production use the same `docker-compose.yml`.

**Finding [MEDIUM]:** Deployment parity relies entirely on environment variable differences. If a new service or volume mount is added to `docker-compose.yml`, both staging and prod pick it up simultaneously. A breaking change to the compose file (e.g. removing a volume) would affect both environments without testing.

**Finding [MEDIUM]:** There is no visible CI/CD pipeline file (e.g. `.github/workflows/`). The `redeploy_trigger` file exists (empty), suggesting a file-based deploy trigger. The AGENTS.md references n8n workflows as the primary automation. Deploy process is not codified in a checked-in file.

### 4.2 Network Configuration

```yaml
api:
  network_mode: "host"  # Default: talks directly to 127.0.0.1
```

**Finding [MEDIUM]:** `network_mode: host` bypasses Docker's bridge network. The API container has full access to the host's network stack. In a shared-hosting environment (e.g. a VPS with other services), this gives the container broader network access than necessary. The `CHARON_LLM_HOST_NETWORK=0` flag can switch to bridge mode, but this is not the default.

### 4.3 is_production Detection

```python
@property
def is_production(self) -> bool:
    return self.log_level.upper() in ("WARNING", "ERROR", "CRITICAL")
```

**Finding [HIGH]:** `is_production` is derived from `log_level`. If `LOG_LEVEL=INFO` (a reasonable staging value), `is_production` evaluates to `False` — correct. But if `LOG_LEVEL=WARNING` (a valid INFO-level deploy), `is_production` becomes `True` and the Sentry initialization uses `environment="production"`. This is fragile and could cause staging events to be tagged as production in Sentry.

---

## 5. Security

### 5.1 Authentication

| Mechanism | Implementation | Notes |
|---|---|---|
| Customer JWT | `HS256`, 15-min expiry, `python-jose` | `sub` = platform_account UUID |
| Admin JWT | `HS256`, 15-min expiry (default) | `role` in payload |
| Admin password | bcrypt via `passlib` | Min 8 chars |
| Admin TOTP | pyotp, 6-digit, valid_window=1 | 30s clock sync |
| Webhook HMAC | `hmac.sha256` + `hmac.compare_digest` | Flutterwave only |
| Credential storage | Fernet (AES-128-CBC + HMAC-SHA256) | At rest |

### 5.2 Injection Risks

**Finding [LOW]:** The API-CONTRACT.md explicitly states: "All SQL queries use SQLAlchemy ORM or parameterized `text()` calls — no string concatenation with user input." Code review confirms ORM usage throughout. Raw SQL via `text()` is used in startup patches and ops endpoints but uses bound parameters.

### 5.3 RLS Bypass Vectors

**Finding [HIGH]:** RLS is currently **disabled** on all tables. No bypass vectors exist because there is no RLS to bypass. However, the `styxproxy_app` role that would be used for RLS is mentioned in `rls_policy.using_clause` defaults. When RLS is re-enabled, the bypass role (`styxproxy_bypass`) must be verified as not having the `BYPASSRLS` attribute.

### 5.4 API Exposure

| Endpoint | Risk | Notes |
|---|---|---|
| `/_ops/v1/*` | CRITICAL | No visible IP allowlisting |
| `/api/webhooks/flutterwave` | LOW | HMAC verified, replay window enforced |
| `/api/webhooks/theorem-reach` | MEDIUM | No signature verification visible |
| `/api/admin/auth/unlock/{email}` | MEDIUM | `admin_token` in URL path parameter |
| `POST /api/admin/auth/password/forgot` | INFO | Generic response prevents enumeration |

### 5.5 TOTP Session Tokens

`admin_totp_sessions` issues "remember this device" tokens. The token is Argon2-hashed before storage. However:
- No visible revocation endpoint (tokens can only expire or be manually deleted in DB)
- `device_fingerprint` + `ip_address` + `user_agent` are stored but not verified on subsequent requests
- **Finding [MEDIUM]:** A stolen token (from localStorage/XSS) is valid until `expires_at`. No device binding or IP binding makes stolen tokens usable from any context.

---

## 6. Docker Configuration

### 6.1 Resource Limits

**Finding [CRITICAL]:** No service in `docker-compose.yml` has any `mem_limit`, `cpus`, or `nano_cpus` directive. All services can consume unlimited resources.

| Service | restart | healthcheck | mem_limit |
|---|---|---|---|
| `postgres` | `unless-stopped` | ✅ pg_isready | ❌ |
| `redis` | `unless-stopped` | ✅ redis-cli ping | ❌ |
| `api` | `unless-stopped` | ✅ curl /health | ❌ |
| `litellm` | `unless-stopped` | ❌ disabled | ❌ |

### 6.2 Healthchecks

**postgres:** `pg_isready` — standard, correct.
**redis:** `redis-cli ping` — standard, correct.
**api:** `curl -f http://localhost:8000/health` — correct, hits FastAPI's built-in health.

**litellm:** Healthcheck explicitly disabled in comments ("investigated in P1-1; the spawn-from-compose pattern triggers exit-code-1 from the python -c probe; uvicorn worker still comes up"). The recommendation is to monitor with `docker logs`.

**Finding [MEDIUM]:** No healthcheck on `litellm` means Docker will not restart it if it dies. The container will show `Up` even if the uvicorn process inside has exited.

### 6.3 Restart Policies

All services use `restart: unless-stopped`. This is appropriate for all services.

**Finding [INFO]:** `unless-stopped` does not restart containers on OOM kill or kernel panic. For a production database, `always` would be marginally safer.

### 6.4 Production Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
ENV PORT=8000
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Finding [MEDIUM]:** No `--workers` flag. Uvicorn runs with 1 worker by default. Under CPU-bound or I/O-bound load, a single worker limits throughput. The recommended approach for production is `--workers N` with N = `2 * cpu_cores + 1`.

**Finding [MEDIUM]:** No multi-stage build. The image contains the full Python build toolchain. A multi-stage build would reduce image size and attack surface.

**Finding [LOW]:** No `.dockerignore` visible. Without it, `backend/app`, `backend/tests`, `backend/scripts`, `backend/alembic` all get copied into the image. Only `app/` and `alembic/` should be needed at runtime.

---

## Findings Summary by Severity

### CRITICAL

| # | Finding | Location |
|---|---|---|
| C1 | No resource limits (`mem_limit`, `cpus`) on any Docker service | `docker-compose.yml` |
| C2 | `/_ops/v1/` router has no visible IP allowlisting; exposed as public path | `app/routers/ops.py` |
| C3 | Schema drift: documented `customers.id UUID` vs actual `phone VARCHAR(20)`; documented `bun_username` vs actual `styxproxy_username` | `docs/DATABASE_SCHEMA.md` vs `models.py` |

### HIGH

| # | Finding | Location |
|---|---|---|
| H1 | Idempotent startup patches swallow all exceptions — schema inconsistency fails silently | `main.py` lifespan |
| H2 | Credential encryption degrades silently when `CRED_ENCRYPTION_KEY` absent; not enforced at startup | `crypto.py`, `config.py` |
| H3 | RLS is disabled on all tables (rolled back in commit 0ba7241); no active row-level security | DB / `models.py` |
| H4 | `is_production` derived from `log_level` — misclassification risk | `config.py` |
| H5 | `allow_credentials=True` + `allow_headers=["*"]` in CORS config | `main.py` CORS setup |
| H6 | `styxproxy_password` can be written as NULL when encryption key absent (not refused) | `StyxproxyCredential.set_password()` |

### MEDIUM

| # | Finding | Location |
|---|---|---|
| M1 | No `--workers` flag in production Dockerfile; single uvicorn worker | `Dockerfile` |
| M2 | No multi-stage build in Dockerfile; full build toolchain in runtime image | `Dockerfile` |
| M3 | No healthcheck on `litellm` sidecar | `docker-compose.yml` |
| M4 | `admin_token` for emergency unlock passed as URL path parameter (logged in access logs) | `app/routers/auth.py` |
| M5 | TOTP "remember device" tokens have no revocation mechanism and no device/IP binding | `AdminTotpSession` model |
| M6 | Staging and prod share identical `docker-compose.yml`; no separate override | `docker-compose.yml` |
| M7 | Maintenance mode DB query runs on every public request hot path (~5-10ms overhead) | `maintenance_block` middleware |
| M8 | Password reset token uses bcrypt for hashing (appropriate) but no token blacklist for JWTs post-reset | `app/routers/auth.py` |
| M9 | Connection pool is static (pool_size=20); no circuit breaker visible | `database.py` |
| M10 | FE ↔ BE type drift detection is manual; no automated contract test | `docs/API-CONTRACT.md` |
| M11 | `customer_audit_log` uses `customer_hash` (irreversible sha256 truncation) — cannot join to platform accounts | `models.py` |

### LOW

| # | Finding | Location |
|---|---|---|
| L1 | `TheoremReach` webhook has no signature verification | `app/routers/webhooks.py` |
| L2 | `api.ts` `API_BASE_URL` defaults to production URL; local dev needs env override | `frontend/src/lib/api.ts` |
| L3 | No `.dockerignore`; tests/scripts/alembic copied into runtime image | `Dockerfile` / project |
| L4 | `admin_totp_sessions.device_fingerprint` stored but not verified on use | `app/routers/auth.py` |

### INFO

| # | Finding | Location |
|---|---|---|
| I1 | `verify_admin_token` in `auth.py` has redacted content visible in the function signature | `app/auth.py` |
| I2 | Rate limiter key function uses `get_remote_address` — not reliable without trusted proxy headers | `limiter.py` |
| I3 | JWT expiry is 15 minutes (default) — reasonable; but refresh token flow not implemented | `auth.py` |

---

## Recommendations (Priority Order)

1. **Add Docker resource limits immediately** — at minimum `mem_limit` for postgres (512MB) and api (256MB). Add `cpus` constraint for all services.
2. **Add healthcheck to litellm** — or implement an external monitor via the ops health endpoint.
3. **Fail fast when `CRED_ENCRYPTION_KEY` is absent** in production — add to `Settings.validate_environment()` failures.
4. **Restrict CORS** — change `allow_headers` to explicit list instead of `["*"]` or remove `allow_credentials=True`.
5. **Protect `/_ops/v1/`** — add IP allowlist middleware or move behind an internal network annotation.
6. **Migrate startup patches to proper Alembic migrations** — apply once, not on every boot. Remove the try/except patch loop from `main.py`.
7. **Update `docs/DATABASE_SCHEMA.md`** — reflect the actual `phone`-based `customers` PK, `styxproxy_username` column name, and `admin_auth.email` primary key.
8. **Add `--workers` to production Dockerfile** — `2 * cpu_cores + 1` uvicorn workers.
9. **Implement multi-stage Dockerfile** — build stage + slim runtime stage.
10. **Fix `is_production` detection** — use an explicit `ENVIRONMENT=production` env var instead of deriving from log level.
11. **Add TOTP session token revocation** — or bind sessions to device fingerprint + IP and verify on each use.
12. **Add automated FE↔BE contract test** — generate OpenAPI spec from FastAPI and diff against FE TypeScript types in CI.
