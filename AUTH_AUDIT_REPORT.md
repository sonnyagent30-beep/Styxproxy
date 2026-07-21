# Styxproxy Admin Auth — Audit & Improvement Report

**Date:** 2026-07-20
**Status:** ✅ ALL IMPROVEMENTS COMPLETE

---

## ✅ Previously Fixed Issues (Pre-Audit)

| # | Issue | Fix |
|---|---|---|
| 1 | `api.ts` used cross-origin `api.styxproxy.com` — CORS failures | Changed to `/api-proxy` (same-origin) |
| 2 | TOTP secret regenerating every call (not persisted) | Moved to `system_settings` DB table |
| 3 | TOTP validation window ±30s too tight | Changed to `valid_window=2` (±60s) |
| 4 | Missing `/logout` endpoint | Added |
| 5 | Login page showed TOTP upfront (not two-step) | Split into step1 (PIN) + step2 (TOTP) |
| 6 | "Need an account?" link visible on login | Removed |
| 7 | Dashboard redirect loop ("feels like refresh") | Fixed auth check on mount only |
| 8 | Admin endpoints used `admin_only` (static ADMIN_TOKEN) | Replaced with `jwt_admin_required` |
| 9 | `/api/admin/*` paths missing Authorization header | Fixed `api.ts` to check both `/admin` and `/api/admin` |
| 10 | Blog pages failing static build (API calls during prerender) | Short-circuited to demo data during build |

---

## ✅ All 8 Improvements Implemented

### 1. Redis-based JWT Revocation — ✅ DONE
- `revoke_token()` + `is_token_revoked()` in `app/auth.py`
- Uses SHA256 hash of token as Redis key (avoids storing large tokens)
- TTL = remaining token lifetime
- `jwt_admin_required` checks revocation on every authenticated request
- `/logout` now **actually revokes** the token (not just client-side delete)

### 2. IP-based Rate Limiting — ✅ DONE
- Redis sliding window counter per IP
- Login endpoints: **10 req/min per IP**
- Default: 60 req/min per IP
- Returns `429 Too Many Requests` with `X-RateLimit-*` headers
- No rate limit on status, TOTP provision (public endpoints)

### 3. Audit Log Table — ✅ DONE
- `admin_audit_log` table with: `admin_phone`, `action`, `ip_address`, `user_agent`, `details`, `created_at`
- Indexed on `admin_phone` and `action` for fast lookups
- All admin actions logged: `login_success`, `login_failed`, `login_pin_verified`, `login_locked`, `logout`, `admin_setup`, `invite_create`, `password_change_success`, `password_change_failed`
- Never fails silently — exceptions are caught and rolled back

### 4. Signed Invite URLs — ✅ DONE
- HMAC-SHA256 signed URLs: `/admin/setup?invite=<code>&sig=<sig>&expires=<ts>`
- 7-day expiry embedded in URL
- `INVITE_SIGNING_KEY` env var (change in production!)
- `/setup` endpoint verifies signature before accepting invite
- Raw codes still work (backwards compatible)
- `POST /invites` response includes `signed_url` field

### 5. useAdminAuth() Hook — ✅ DONE
- `/frontend/src/hooks/useAdminAuth.ts`
- Centralized: admin state, loading, error, logout, refresh
- Replaces scattered localStorage + fetch calls in layout/pages

### 6. Error Boundary + Skeleton — ✅ DONE
- `/frontend/src/components/admin/ErrorBoundary.tsx` — catches JS errors, shows "Try Again"
- `/frontend/src/components/admin/Skeleton.tsx` — pulsing skeleton for dashboard loading
- Dashboard page uses both

### 7. Backend Auth Tests — ✅ DONE
- `/backend/tests/test_auth.py` — 11 test cases
- Tests: setup, invalid TOTP, duplicate admin, wrong PIN, locked account, expired step_token, logout revocation, signed invite verification

### 8. TOTP Secret in DB — ✅ DONE
- `system_settings` table stores `totp_secret` key
- `/totp/provision` reads from DB
- Setup reads/writes from DB
- No .env dependency for TOTP secret

---

## Architecture Notes

### Cookie Limitation (Vercel Serverless)
- HttpOnly cookies **cannot** be set through the Vercel proxy to the backend (Vercel strips `Secure` + `Set-Cookie` for cross-origin serverless responses)
- **Workaround:** Authorization header approach is used instead — Bearer token in `Authorization` header on every request
- The `api.ts` client stores token in `localStorage` and sends via `Authorization: Bearer <token>` header
- All admin endpoints accept both Authorization header AND `admin_token` cookie (cookie fallback for SSR)
- This is the correct pattern for Vercel-deployed frontends proxying to external backends

### Auth Token Flow
```
Browser → Vercel Frontend → /api-proxy → Backend (VPS Docker)
                              ↓
                    Authorization: Bearer <token>
                    (stored in localStorage by api.ts)
```

### Redis Usage
- JWT revocation: `revoked_token:<sha256(token)>` with TTL
- Rate limiting: `rate_limit:ip:<IP>:<window_timestamp>` with TTL

---

## Outstanding Recommendations (Lower Priority)

| Priority | Recommendation | Why |
|---|---|---|
| 🔴 High | Per-admin TOTP secrets | Currently shared — one secret compromises all admins |
| 🔴 High | INVITE_SIGNING_KEY env var | Must be set in production |
| 🟡 Med | CSRF tokens for state-changing requests | Protects against cross-site form submissions |
| 🟡 Med | Recovery codes for TOTP lockout | Admin loses phone = locked out |
| 🟡 Med | Per-role audit log filtering | Filter audit log by action type in UI |
| 🟢 Low | Backend test suite CI/CD | Run pytest on every PR |
| 🟢 Low | Two-step login (PIN first, then TOTP) | Already done with step1/step2 flow ✅ |

---

## DB Schema Additions

```sql
-- Admin audit log
CREATE TABLE admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_phone VARCHAR(20) NOT NULL,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_phone ON admin_audit_log(admin_phone);
CREATE INDEX idx_audit_action ON admin_audit_log(action);

-- System settings
CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO system_settings (key, value) VALUES ('totp_secret', '<current-secret>');
```

---

## Invite URL Format

**Raw code:** `1BLUnmY7gkUnnrh2rg13Ne7c-RgZjf1l` (bootstrap token — first admin only)

**Signed URL format:**
```
https://styxproxy.com/admin/setup?invite=<code>&sig=<hmac-sha256>&expires=<unix-timestamp>
```

The signed URL is generated by `POST /api/admin/auth/invites` and returned in the `signed_url` field.
