# Bunche — Security Hardening Checklist

**Last Updated:** 2026-07-01
**Purpose:** Security controls that must be implemented in code — not optional, not "later."

---

## Why This Document Exists

The architecture docs describe *what* to build. This document describes *how* to build it *securely*. Every item here must be implemented before launch. Not after.

---

## 1. Webhook Security

### 1.1 Flutterwave Webhook — HMAC Verification (CRITICAL)

**Threat:** Attacker crafts a fake webhook payload → backend thinks payment succeeded → free IP generated.

**Required implementation:**
```python
# Every Flutterwave webhook MUST verify HMAC before ANY processing
from Crypto.Hash import HMAC, SHA256

def verify_flutterwave_signature(payload: bytes, signature: str, secret: str) -> bool:
    computed = HMAC.new(secret.encode(), payload, SHA256).hexdigest()
    return computed == signature
```

**Rules:**
- Verify BEFORE reading any request body fields
- Reject with 401 if signature is invalid
- Never process payment data from unverified webhooks
- Log all verification failures with timestamp + IP

### 1.2 Flutterwave Webhook — Idempotency (CRITICAL)

**Threat:** Attacker replays a valid webhook after order is fulfilled → duplicate IP generation → free proxy.

**Required implementation:**
```python
async def process_flutterwave_webhook(payload: dict):
    tx_ref = payload["tx_ref"]

    # Check idempotency table FIRST
    existing = await db.fetchrow(
        "SELECT id FROM processed_webhooks WHERE event_id = $1",
        payload.get("id")
    )
    if existing:
        return {"status": "already_processed"}  # Return 200, don't reprocess

    # Process the payment...
    await db.execute(
        "INSERT INTO processed_webhooks (event_id, tx_ref, processed_at) VALUES ($1, $2, NOW())",
        payload["id"], tx_ref
    )
```

**Rules:**
- Store `flutterwave_event_id` in `processed_webhooks` before processing
- Return HTTP 200 for duplicate events (Flutterwave retries until it gets 200)
- Idempotency records never deleted
- Unique constraint on `event_id` in database

### 1.3 Theorem Reach Webhook — Token Verification

**Threat:** Fake survey completion postback → free trial issued without completing survey.

**Required implementation:**
```python
async def process_theorem_reach_webhook(request: Request):
    # Verify Bearer token matches THEOREM_REACH_WEBHOOK_SECRET
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {settings.THEOREM_REACH_WEBHOOK_SECRET}"

    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Then process postback...
```

### 1.4 All Webhooks — Rate Limiting

**Threat:** Attacker floods webhooks → causes excessive processing.

**Required implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/webhook/flutterwave")
@limiter.limit("30/minute")  # Per IP
async def flutterwave_webhook(request: Request):
    ...
```

---

## 2. Input Validation (Pydantic)

### 2.1 Every Request Body — Strict Pydantic Models

**Threat:** Malformed data causes crashes, wrong prices, or logic errors.

**Required implementation:**
```python
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

class CreateInvoiceRequest(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=50)
    country: str = Field(..., min_length=2, max_length=2)  # ISO code only
    email: str | None = Field(default=None, max_length=255)

    @field_validator("country")
    @classmethod
    def country_must_be_valid_iso(cls, v):
        valid_countries = {"NG", "UK", "US", "DE", "JP", "AU", "BR", "SG", "KR"}
        if v.upper() not in valid_countries:
            raise ValueError("Invalid country code")
        return v.upper()

    @field_validator("product_id")
    @classmethod
    def product_must_exist(cls, v):
        valid_products = {"ISP_UK", "ISP_US", "ISP_DE", "ISP_JP", "DC", "RES_5GB", "RES_10GB", "MOB_5GB", "MOB_10GB"}
        if v not in valid_products:
            raise ValueError("Invalid product")
        return v
```

**Rules:**
- Every endpoint has a Pydantic model
- No `dict` or raw `Body` parameters in route handlers
- All enums validated against known valid values
- Decimal fields for money (never float)

### 2.2 tx_ref — Strict Format

**Threat:** Injection attacks via tx_ref in SQL queries.

**Required implementation:**
```python
@router.get("/order/{tx_ref}")
async def get_order(tx_ref: str):
    # Strict format: Bunche tx_ref starts with "TXF-"
    if not tx_ref.startswith("TXF-"):
        raise HTTPException(status_code=400, detail="Invalid order reference")

    # Only alphanumeric after prefix
    if not re.match(r"^TXF-[A-Za-z0-9]{8,32}$", tx_ref):
        raise HTTPException(status_code=400, detail="Invalid order reference")

    order = await db.fetchrow(
        "SELECT * FROM instant_orders WHERE tx_ref = $1", tx_ref
    )
    ...
```

---

## 3. External API Calls

### 3.1 Timeouts on All External Calls

**Threat:** Proxy-Seller API hangs → request blocks → connection exhaustion → site goes down.

**Required implementation:**
```python
import httpx

# Every external API call MUST have timeouts
async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=2.0)) as client:
    response = await client.post(
        "https://api.proxy-seller.com/v1/create",
        json=payload,
        headers={"Authorization": f"Bearer {settings.PROXY_SELLER_API_KEY}"}
    )
```

**Rules:**
- Connect timeout: 2 seconds max
- Read timeout: 10 seconds max
- Never `httpx.AsyncClient()` without explicit timeout
- On timeout: log error, return 502 to client, do NOT retry silently

### 3.2 Retry with Circuit Breaker

**Threat:** Proxy provider is down → backend retries endlessly → accumulates bills or deadlocks.

**Required implementation:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def create_proxy_with_backoff(payload: dict) -> dict:
    response = await httpx.AsyncClient(timeout=10).post(
        "https://api.proxy-seller.com/v1/create",
        json=payload
    )
    if response.status_code >= 500:
        raise Exception("Provider error")  # Triggers retry
    return response.json()
```

**Circuit breaker:** After 5 consecutive failures to Proxy-Seller, stop trying for 60 seconds. Return "service temporarily unavailable" to customer.

---

## 4. SSRF Protection

**Threat:** Admin uploads a screenshot from a URL → backend fetches the URL → if URL is `http://localhost:5432` or `http://169.254.169.254/` (AWS metadata) → internal service exposure.

### 4.1 URL Validation for Admin Screenshots

```python
from urllib.parse import urlparse

BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "::1",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
    "metadata.azure.com",
}

def is_url_safe(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname.lower()

    # No private IP ranges
    if hostname in BLOCKED_HOSTS:
        return False

    # Check for private IP in resolved addresses
    try:
        import socket
        addrs = socket.getaddrinfo(hostname, None)
        for family, _, _, _, (ip, _) in addrs:
            if ip.startswith(("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                              "172.20.", "172.21.", "172.22.", "172.23.",
                              "172.24.", "172.25.", "172.26.", "172.27.",
                              "172.28.", "172.29.", "172.30.", "172.31.",
                              "192.168.", "127.")):
                return False
    except socket.gaierror:
        return False  # Can't resolve = likely invalid

    return True
```

### 4.2 Admin Cannot Upload Files from URLs

Ban claim screenshots must be uploaded directly (multipart/form-data), not from a URL. No `fetch()` from user-provided URLs in the backend.

---

## 5. Admin Authentication

### 5.1 Login Requires Email + Password + TOTP

```python
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str = Field(..., min_length=6, max_length=6)

async def admin_login(request: AdminLoginRequest):
    admin = await db.fetchrow(
        "SELECT * FROM admin_auth WHERE email = $1", request.email
    )

    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not bcrypt.checkpw(request.password.encode(), admin["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify TOTP
    if not verify_totp(admin["totp_secret"], request.totp_code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    # Generate session JWT
    token = create_jwt(admin_id=admin["id"], role=admin["role"])
    return {"token": token}
```

### 5.2 JWT Session Management

```python
# JWT payload — no secrets, only identifiers
class TokenPayload(BaseModel):
    sub: int  # admin_id
    role: Literal["admin", "superadmin"]
    exp: datetime

# Access token: 15 minutes expiry
# Refresh token: 7 days, stored in httpOnly cookie

# Every protected admin endpoint:
@router.get("/admin/orders")
async def list_orders(authorize: Authorize):
    if not authorize.is_authenticated:
        raise HTTPException(status_code=401)

    if authorize.role == "admin" and authorize.admin_id != order_admin_id:
        raise HTTPException(status_code=403)  # Admin can only see their orders
```

### 5.3 SuperAdmin-Only Endpoints

```python
def superadmin_required(authorize: Authorize):
    if authorize.role != "superadmin":
        raise HTTPException(status_code=403, detail="SuperAdmin access required")

@router.post("/admin/create")
async def create_admin(request: CreateAdminRequest, authorize: Authorize):
    superadmin_required(authorize)
    # Create new admin...
```

---

## 6. Secrets Management

### 6.1 Environment Variables — Server Only

**Rule:** `.env` file never committed to GitHub. `POSTGRES_PASSWORD`, `FLUTTERWAVE_SECRET_KEY`, `PROXY_SELLER_API_KEY` are on the server only.

```bash
# .gitignore MUST contain:
.env
.env.*
*.pem
*.key
```

### 6.2 No Secrets in Logs

```python
import structlog
logger = structlog.get_logger()

# Bad:
logger.info("Creating proxy", api_key=settings.PROXY_SELLER_API_KEY)

# Good:
logger.info("Creating proxy", provider="proxy-seller")
# Secret excluded from all log output
```

### 6.3 Secrets Rotation Schedule

| Secret | Rotation frequency |
|---|---|
| `FLUTTERWAVE_WEBHOOK_SECRET` | Every 90 days |
| `POSTGRES_PASSWORD` | Every 90 days |
| `PROXY_SELLER_API_KEY` | Every 30 days (provider may rotate) |
| `RESEND_API_KEY` | Every 90 days |
| `JWT_SECRET` | Every 30 days |

**Rotation procedure:**
1. Generate new secret
2. Update `.env` on server
3. Restart backend
4. Verify all functions work
5. Old secret invalidated immediately

---

## 7. Rate Limiting (Per Endpoint)

All public endpoints must have rate limits:

| Endpoint | Limit | Window |
|---|---|---|
| `POST /invoice/create` | 10 requests | Per IP per minute |
| `GET /order/:tx_ref` | 30 requests | Per IP per minute |
| `POST /webhook/flutterwave` | 30 requests | Per IP per minute |
| `POST /webhook/theorem-reach` | 20 requests | Per IP per minute |
| `POST /admin/login` | 5 requests | Per IP per minute |
| `GET /admin/*` | 100 requests | Per admin per minute |
| `POST /admin/*` | 20 requests | Per admin per minute |

---

## 8. Audit Logging

### 8.1 Every Admin Action Logged

```python
async def log_admin_action(admin_id: int, action: str, details: dict, ip: str):
    await db.execute("""
        INSERT INTO admin_commands_log
        (admin_id, action, details, ip_address, created_at)
        VALUES ($1, $2, $3, $4, NOW())
    """, admin_id, action, json.dumps(details), ip)
```

**Logged actions:**
- Admin login / logout
- Order viewed (which tx_ref)
- Refund issued (which tx_ref, amount, reason)
- Ban claim reviewed (tx_ref, decision)
- New admin created / deleted
- System settings changed
- Credential manually issued / revoked

### 8.2 No Log Deletion

`admin_commands_log` table has NO `DELETE` operation. Audit logs are immutable. Only SuperAdmin can read them.

---

## 9. HTTPS and Transport Security

- **HSTS header** on all responses: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- **No HTTP** — port 80 redirects to 443 only
- **TLS 1.2 minimum** — reject TLS 1.0 and 1.1
- **Certificate renewal** — auto-renew via certbot 30 days before expiry

---

## 10. Error Handling

### 10.1 No Stack Traces in Production

```python
# FastAPI — disable verbose errors
app = FastAPI(docs_url=None, redoc_url=None, debug=False)

# Every handler:
@router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}  # Never expose traceback
    )
```

### 10.2 Structured Error Logging

```python
try:
    await process_order(tx_ref)
except Exception as e:
    logger.error(
        "order_processing_failed",
        tx_ref=tx_ref,
        error=str(e),
        error_type=type(e).__name__,
        request_id=request.state.request_id  # UUID per request
    )
    raise HTTPException(status_code=500, detail="Order processing failed")
```

Every request gets a `request_id` UUID generated at entry and logged with every subsequent log line.

---

## Pre-Launch Security Checklist

- [ ] All webhook HMAC verification implemented and tested
- [ ] Idempotency table created and tested with replay attack simulation
- [ ] Pydantic models on all endpoints
- [ ] All external API calls have timeouts
- [ ] Circuit breaker on Proxy-Seller and DataImpulse
- [ ] SSRF protection on all URL-fetching code
- [ ] Admin login requires email + password + TOTP
- [ ] JWT access token: 15-minute expiry
- [ ] All admin actions logged to `admin_commands_log`
- [ ] No secrets in logs (checked with `grep` before launch)
- [ ] Rate limiting on every public endpoint
- [ ] `.env` file confirmed NOT in GitHub
- [ ] HSTS header enabled
- [ ] Stack traces disabled in production
- [ ] Secrets rotation schedule documented
- [ ] UptimeRobot monitoring set up
- [ ] SSL certificate auto-renewal verified

---

*This checklist is the minimum security bar. Any item left unchecked = no launch.*
