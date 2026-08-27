# Styxproxy — Comprehensive Project Audit Report

**Audit Date:** 2026-08-27  
**Scope:** Documentation, Backend, Frontend, n8n, Database, Infrastructure  
**Auditor:** Sonny (direct file review)

---

## 🔴 CRITICAL (Fix Immediately)

### 1. Dead Code: JavaScript Syntax in Python File
**File:** `backend/app/services/provider.py` (lines 111, 126)  
**Severity:** CRITICAL — Runtime crash  
```python
# This is JavaScript syntax, NOT Python
results = await Promise.all([
    decodo.check_health(),
    dataimpulse.check_health(),
])
```
`Promise.all` is JavaScript. Python uses `asyncio.gather()`. This will crash at import time.

### 2. Missing Function Import
**File:** `backend/app/routers/webhooks.py` (line 20)  
**Severity:** CRITICAL — Webhook processing broken  
```python
from app.services.flutterwave import (
    is_webhook_processed,
    mark_webhook_processed,
    process_payment_webhook,  # ← This function doesn't exist in flutterwave.py
    verify_flutterwave_signature,
)
```
`process_payment_webhook` is imported but never defined in `flutterwave.py`. All Flutterwave webhooks will 500.

### 3. Hardcoded Fallback Secrets in Config
**File:** `backend/app/config.py` (lines 23-35)  
**Severity:** CRITICAL — Auth bypass if .env not set  
```python
jwt_secret: str = "your-jwt-secret-key-change-in-production"
admin_token: str = "your-admin-token-change-in-production"
```
If `.env` is missing or vars are unset, the app starts with these defaults. An attacker can forge JWTs and access admin endpoints.

### 4. Hardcoded Product Prices (Single Source of Truth Violation)
**File:** `backend/app/routers/payments.py` (lines 20-28)  
**Severity:** CRITICAL — Pricing desync  
```python
PRODUCT_PRICES = {
    "ISP-NG-1": 5000,
    "ISP-NG-2": 9500,
    ...
}
```
Prices are hardcoded in two places: `payments.py` and `orders.py` (legacy fallback). The `plans` table is supposed to be the single source of truth. If admin updates a plan price, the payment endpoint still uses the stale hardcoded value.

### 5. n8n References Non-Existent Env Var
**File:** `.n8n/workflows/payment-confirmation.json` (line 19)  
**Severity:** CRITICAL — Payment webhooks fail  
```javascript
const secretHash = $env.FLUTTERWAVE_WEBHOOK_VERIF_HASH;
```
The actual env var is `FLUTTERWAVE_WEBHOOK_SECRET` (per `.env.production.example` and `config.py`). This workflow will always throw "Invalid Flutterwave signature."

---

## 🟠 HIGH (Fix This Week)

### 6. Homepage Blog Section Empty (Client-Side Fetch)
**File:** `frontend/src/components/LatestBlogPosts.tsx`  
**Severity:** HIGH — Broken UX, zero blog posts shown  
Component is `'use client'` with `useEffect` fetch. Server sends empty grid. If client fetch fails or is slow, user sees nothing. Other blog surfaces fetch server-side and pass as props.

### 7. ConsentGate Not Light/Dark Responsive
**File:** `frontend/src/components/ConsentGate.tsx`  
**Severity:** HIGH — Accessibility violation  
Uses CSS variables (`--card`, `--border`, etc.) but styles are hardcoded inline in a `<style>` tag. Doesn't respond to `prefers-color-scheme` media query.

### 8. n8n References Non-Existent Tables
**Files:** `.n8n/workflows/daily-summary.json`, `.n8n/workflows/free-trial.json`  
**Severity:** HIGH — Workflow runtime errors  
- `daily-summary.json` queries `error_log` and `free_trials` tables — neither exists in `models.py`
- `free-trial.json` queries `pending_trial_surveys` table — doesn't exist in models

### 9. n8n Order Handler References Dead Model
**File:** `.n8n/workflows/order-handler.json` (line 75)  
**Severity:** HIGH — LLM parse failures  
```json
"model": "MiniMax-M2"
```
The project migrated away from MiniMax. This model may not exist in the n8n execution environment.

### 10. Hardcoded Stub Proxy IPs Including Private Range
**File:** `backend/app/services/credential.py` (lines 34-38)  
**Severity:** HIGH — Customer-facing failure  
```python
STUB_PROXY_POOL = {
    "NG": [{"ip": "185.199.228.45", "port": 1080}],
    ...
    "DEFAULT": [{"ip": "192.168.1.1", "port": 1080}],  # Private IP!
}
```
If provider API is down, customers get `192.168.1.1` — a private IP that routes nowhere.

### 11. Massive Router Files (Maintainability)
**Files:** `backend/app/routers/admin.py` (2264 lines), `backend/app/services/email.py` (2638 lines), `backend/app/routers/orders.py` (1332 lines)  
**Severity:** HIGH — Code maintainability  
These files are too large. `admin.py` alone is 2264 lines covering plans, customers, orders, credentials, analytics, etc. Should be split into sub-routers.

### 12. Frontend Type Files Too Large
**Files:** `frontend/src/lib/api.ts` (1247 lines), `frontend/src/types/index.ts` (1082 lines)  
**Severity:** HIGH — Code maintainability  
Single files for all API functions and all types. Difficult to navigate and maintain.

### 13. Checkout Page Cart State Duplication
**File:** `frontend/src/app/(public)/order/checkout/page.tsx` (lines 52-63)  
**Severity:** HIGH — State desync  
```typescript
const stored =
  sessionStorage.getItem('styxproxy_cart') ||
  localStorage.getItem('styxproxy_cart');
```
Cart is read from sessionStorage OR localStorage with fallback. If they diverge (e.g., user has two tabs open), checkout shows stale data. The Zustand cart-store is the source of truth but checkout bypasses it.

### 14. Database Schema Doc Stale
**File:** `docs/DATABASE_SCHEMA.md`  
**Severity:** HIGH — Developer confusion  
Last updated 2026-08-19, claims "reflects models.py and Alembic migrations 001-021." But `models.py` has tables not documented (e.g., `trigger_weights`, `feature_flags`, `plan_settings`, `admins`, `support_threads`, etc.). Doc says "all 10 tables" but there are 20+.

---

## 🟡 MEDIUM (Fix This Month)

### 15. README.md Wrong Next.js Version
**File:** `README.md` (line 7)  
```
- Frontend: Next.js 16
```
Actual: Next.js 15.

### 16. TODO.md References Non-Existent Repo
**File:** `TODO.md` (line 25)  
```
1. Build static website (styxproxy-web repo)
```
There is no `styxproxy-web` repo. The frontend is in this repo at `frontend/`.

### 17. TODO.md References Wrong VPS Provider
**File:** `TODO.md` (line 26)  
```
2. Provision VPS (Hetzner CX21)
```
Actual production is Interserver `162.35.184.69`.

### 18. SPEC.md Status Stale
**File:** `SPEC.md` (line 3)  
```
**Status:** Planning — Ready for Build
```
The project is live at styxproxy.com. Status should be "Production."

### 19. AGENTS.md Last Updated June
**File:** `AGENTS.md` (line 3)  
```
**Last Updated:** 2026-06-26
```
References workflows that have since been modified. Stale agent documentation.

### 20. RUNBOOKS.md References Non-Existent Services
**File:** `RUNBOOKS.md` (lines 35-40)  
```json
"m2_cloud": "connected",
"litellm": "disconnected",
"ollama": "disconnected"
```
These services don't exist in the actual health endpoint response.

### 21. DEPLOYMENT.md References Wrong Provider
**File:** `DEPLOYMENT.md` (lines 14, 61)  
```
VPS (Ubuntu 22.04) | Hetzner / DigitalOcean | ~$15–20/mo
```
Actual: Interserver VPS.

### 22. DEPLOYMENT.md References 3proxy (Not Used)
**File:** `DEPLOYMENT.md` (line 45)  
```
└── 3proxy — self-hosted free trial proxy (Step 12)
```
The actual free trial implementation doesn't use 3proxy.

### 23. ROLE_MODEL.md Redacted Role Names
**File:** `ROLE_MODEL.md` (lines 7-9)  
```
|  | Initial cluster | SUPERUSER, CREATEDB, CREATEROLE, BYPASSRLL | Emergency repair only |
```
Role names are empty (redacted?). The table is unreadable.

### 24. Missing Indexes on Frequently Queried Columns
**File:** `backend/app/models.py`  
**Severity:** MEDIUM — Performance  
- `orders` table: no index on `customer_id`, `status`, `tx_ref`, `created_at`
- `styxproxy_credentials` table: no index on `order_id`, `status`, `customer_id`
- `processed_webhooks` table: no index on `created_at` (for cleanup)

### 25. Post.tags JSON Column (Not JSONB)
**File:** `backend/app/models.py` (line 909)  
```python
tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```
Plain `JSON` column. `.contains()` compiles to `LIKE` which Postgres rejects. Requires `func.cast(Post.tags, JSONB).contains(...)` workaround. Should be `JSONB` natively.

### 26. Frontend Uses fetch() Instead of api Module
**File:** `frontend/src/components/PaymentStatusPoller.tsx` (line 67)  
```typescript
const res = await fetch(`/api/orders/by-payment-reference/${txRef}`);
```
Bypasses the centralized `api` module. No error handling, no auth headers, no type safety.

### 27. Duplicate Cart Item Interface
**Files:** `frontend/src/app/(public)/thank-you/page.tsx` (lines 16-25), `frontend/src/types/index.ts`  
**Severity:** MEDIUM — Type drift  
`CartItem` is redefined locally in `thank-you/page.tsx` instead of importing from `@/types`.

### 28. n8n Referral Credit References Missing Column
**File:** `.n8n/workflows/referral-credit.json` (line 82)  
```
"values": "referral_credit_ngn = referral_credit_ngn + {{$json.referral_credit}}"
```
The `customers` table doesn't have a `referral_credit_ngn` column in `models.py`.

### 29. Docker Compose No Explicit Backup Volume
**File:** `infrastructure/docker-compose.yml`  
**Severity:** MEDIUM — Data loss risk  
Postgres data volume (`postgres_data`) is a Docker named volume. No explicit host mount or backup verification. The backup script exists but isn't wired to a cron job in the compose file.

### 30. .env.production.example Mismatch with Code
**File:** `infrastructure/.env.production.example` (line 20)  
```
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-xxxxxxxxxxxxx
```
Code expects `flutterwave_secret_key` (per `config.py`). Env var name mismatch.

---

## 🟢 LOW (Nice to Have)

### 31. ESLint Disables in Checkout
**File:** `frontend/src/app/(public)/order/checkout/page.tsx` (line 2)  
```typescript
/* eslint-disable react-hooks/set-state-in-effect */
```
Indicates a known anti-pattern was left in.

### 32. Magic Numbers in PaymentStatusPoller
**File:** `frontend/src/components/PaymentStatusPoller.tsx` (lines 34-35)  
```typescript
const POLL_INTERVAL_MS = 3500;
const MAX_ATTEMPTS = 60; // ~3.5 minutes
```
Should be configurable or at least documented.

### 33. console.log in Production Code
**Files:** Multiple frontend components  
**Severity:** LOW — Debug output in production  
Several components have `console.log` / `console.error` statements.

### 34. Missing Test Files
**Files:** `backend/tests/`  
**Severity:** LOW — Quality gate  
Test coverage appears minimal. No tests for critical paths (payments, webhooks, credential generation).

### 35. Hardcoded Webhook Age Constant
**File:** `backend/app/routers/webhooks.py` (line 30)  
```python
FLUTTERWAVE_MAX_PAYLOAD_AGE_SECONDS = 300
```
Should be configurable via settings.

---

## Summary

| Severity | Count | Key Themes |
|----------|-------|------------|
| 🔴 CRITICAL | 5 | Dead code (JS in Python), missing function, hardcoded secrets, price desync, wrong env var |
| 🟠 HIGH | 9 | Broken blog section, broken n8n tables, dead LLM model, stub IPs, massive files |
| 🟡 MEDIUM | 16 | Stale docs, missing indexes, JSON vs JSONB, type duplication, backup gaps |
| 🟢 LOW | 5 | ESLint disables, magic numbers, console.log, missing tests |

**Top 3 priorities:**
1. Fix `provider.py` `Promise.all` → `asyncio.gather()` (crash at import)
2. Add `process_payment_webhook` to `flutterwave.py` (webhooks broken)
3. Remove hardcoded `PRODUCT_PRICES` from `payments.py` (pricing desync)
