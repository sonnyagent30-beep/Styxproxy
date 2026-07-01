# Bunche — Database Schema Review & Reconciliation

**Document Type:** Technical Review
**Date:** July 1, 2026
**Status:** Planning Complete — Build Decision Required

---

## Executive Summary

**Critical finding:** The `infrastructure/postgres/init/01-schema.sql` and the `docs/DATABASE_SCHEMA.md` are **two completely different schemas** for the same project. One must be chosen as source of truth.

| Aspect | `01-schema.sql` | `DATABASE_SCHEMA.md` |
|--------|---------------|---------------------|
| **Design approach** | Simplified, phone-centric | Multi-account with platform_accounts + merge |
| **Authentication** | Phone-based (`phone PK`) | Platform-based (`platform_user_id` per channel) |
| **Account merging** | ❌ Not supported | ✅ Explicit merge flow |
| **Credentials table** | `proxy_credentials` (simple) | `bunche_credentials` (with Dante mapping) |
| **Free trials** | ❌ Not in schema | ✅ `free_trials` + `pending_trial_surveys` |
| **Webhook idempotency** | ✅ `flutterwave_ref UNIQUE` | ✅ `processed_webhooks` table |
| **Admin auth** | ❌ Not in schema | ✅ `admin_auth` + `admin_commands_log` |

**Recommendation:** Adopt `DATABASE_SCHEMA.md` as canonical. Rewrite `01-schema.sql` to match.

---

## Issue 1: Critical — Two Incompatible Schemas

The `01-schema.sql` uses **phone-centric design** — `customers.phone VARCHAR(20) PRIMARY KEY`. This means:

1. Each customer has exactly ONE phone number as identity
2. A customer with both Telegram AND WhatsApp = TWO rows in `customers`
3. No way to link them without a separate merge table that doesn't exist
4. No `referral_code` column — just `referrer_id`

The `DATABASE_SCHEMA.md` uses `platform_accounts` as the core identity layer:
- A `customer` can have multiple `platform_accounts` (Telegram + WhatsApp)
- `customers` is created when the FIRST account is created, or when two accounts merge

**Action required:** CHOOSE one schema. Recommend `DATABASE_SCHEMA.md`.

---

## Issue 2: Missing Tables in `01-schema.sql`

| Missing Table | Purpose | Priority |
|-------------|---------|----------|
| `platform_accounts` | Per-channel identity (Telegram/WhatsApp) | 🔴 Critical |
| `merge_requests` | OTP-based account merging | 🔴 Critical |
| `bunche_credentials` | Dante SOCKS5 username ↔ provider IP mapping | 🔴 Critical |
| `free_trials` | Free trial tracking (surveys → proxy) | 🟡 Medium |
| `pending_trial_surveys` | Theorem Reach postback records | 🟡 Medium |
| `customer_audit_log` | Immutable per-platform-account audit trail | 🟡 Medium |
| `error_log` | Workflow error tracking | 🟡 Medium |
| `admin_auth` | Admin PIN + TOTP authentication | 🟡 Medium |
| `rate_limit_log` | Rate limit hits for abuse detection | 🟢 Low |
| `webhook_security_log` | Webhook signature verification failures | 🟢 Low |

---

## Issue 3: Scale Problems at 10K Concurrent

### Problem 1: PostgreSQL Connection Exhaustion

At 10K concurrent, PostgreSQL default `max_connections=100` exhausts immediately.

**Fix:** FastAPI uses `asyncpg` + SQLAlchemy async sessions. Each request borrows a connection from the async pool, returns it immediately after the query — no connection held while waiting on I/O. Configure:

```python
# FastAPI database config
DATABASE_URL = "postgresql+asyncpg://bunche:password@postgres:5432/bunche"

# SQLAlchemy async engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # base connections
    max_overflow=30,      # extra connections under load (20+30=50 concurrent)
    pool_timeout=30,
    pool_recycle=3600,
)
```

For n8n (separate process), PostgreSQL directly handles ~20-30 n8n connections — well within defaults.

### Problem 2: `orders` Table — No Partitioning

At 10K customers with monthly subscriptions, orders grows to ~120K+ rows/year. Without partitioning, monthly reports require full scans.

**Fix:** Partition `orders` by `created_at` (monthly range).

### Problem 3: No Composite Index for Customer Dashboard

Most common query:
```sql
SELECT * FROM orders 
WHERE customer_id = $1 
AND status NOT IN ('cancelled', 'refunded')
ORDER BY created_at DESC
LIMIT 10;
```

**Fix:** Add `CREATE INDEX idx_orders_customer_status ON orders(customer_id, status);`

---

## Issue 4: Dangerous Query Patterns

### `proxy_credentials` Doesn't Track Dante Mapping

The `proxy_credentials` table is just an IP/port tracker. It doesn't track the **Dante SOCKS5 username** that Bunche issues to customers.

**Fix:** Use `bunche_credentials` from `DATABASE_SCHEMA.md`:
- `bun_username` — what customer uses to auth to Dante
- `password_hash` — bcrypt
- `dante_port` — which Dante port this credential maps to
- `upstream_proxy_ip` — actual provider IP

---

## Migration Strategy

Since the two schemas are completely different, this is a **big bang migration**:

1. **Freeze writes** to old system
2. **Export** all data from old `customers` and `orders`
3. **Create new schema** (DATABASE_SCHEMA.md implementation)
4. **Map old data** to new schema
5. **Load and validate**
6. **Cut over** — point application to new database

---

## Decision Required from Dannion

> **Which schema do we use as canonical?**

**Option A:** Adopt `DATABASE_SCHEMA.md` fully. Rewrite `01-schema.sql`. Multi-channel account model, Dante mapping, free trials, account merging. ~350 lines of SQL.

**Option B:** Simplify `DATABASE_SCHEMA.md` to match `01-schema.sql`. Remove multi-channel account model. Faster to build but loses Telegram/WhatsApp account merging.

**Recommendation for launch velocity:** Start with Option B (simplified schema). Add `platform_accounts` + account merging in Month 2 when customer count grows.
