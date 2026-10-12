# Styxproxy — Security Plan

**Last Updated:** 2026-06-26
**Status:** Planning Complete — Ready for Implementation

---

## Overview

Security for Styxproxy is implemented in 7 layers. No single layer is sufficient — together they provide defense in depth.

| Layer | Name | Purpose |
|-------|------|---------|
| 1 | Cloudflare | Network edge protection |
| 2 | Nginx | TLS + per-endpoint rate limits |
| 3 | Webhook Signature Verification | Block forged webhooks |
| 4 | Payment Idempotency | Prevent duplicate processing |
| 5 | Redis Rate Limiting | Phone-based anti-abuse |
| 6 | Admin PIN + 2FA | Secure admin access |
| 7 | Monitoring + Alerting | Know when something breaks |

---

## Layer 1: Cloudflare Rate Limiting

**Setup:** Dashboard only (30 minutes)
**Cost:** $0 (free tier)

### Rules

**Rule 1: WhatsApp Webhook**
| Setting | Value |
|---------|-------|
| Field | Request URI |
| Operator | contains |
| Value | /webhook/whatsapp-incoming |
| Rate | 20 requests per minute |
| Counting | By IP address |
| Action | Challenge (CAPTCHA) |

**Rule 2: Flutterwave Webhook**
| Setting | Value |
|---------|-------|
| Field | Request URI |
| Operator | contains |
| Value | /webhook/flutterwave-payment |
| Rate | 100 requests per minute |
| Counting | By IP address |
| Action | Block |

**Rule 3: BitLabs Postback**
| Setting | Value |
|---------|-------|
| Field | Request URI |
| Operator | contains |
| Value | /webhook/bitlabs-postback |
| Rate | 50 requests per minute |
| Counting | By IP address |
| Action | Challenge (CAPTCHA) |

**Rule 4: Admin Area**
| Setting | Value |
|---------|-------|
| Field | Request URI |
| Operator | contains |
| Value | /admin/ |
| Rate | 30 requests per minute |
| Counting | By IP address |
| Action | Block |

**Also enable:** Bot Fight Mode (Security → Bots → On)

---

## Layer 2: Nginx HTTPS + Rate Limit Config

**Setup:** Config file deployment
**Cost:** $0 (Let's Encrypt free)

### Rate Limit Zones

| Zone | Limit | Burst |
|------|-------|-------|
| whatsapp_ip | 20 req/min | 10 |
| flutterwave_ip | 100 req/min | 20 |
| bitlabs_ip | 50 req/min | 10 |
| general_ip | 60 req/min | 20 |
| conn_limit | 10 concurrent per IP | — |

### Endpoints

| Endpoint | Rate Zone | Limit | Burst |
|---------|----------|-------|-------|
| /webhook/whatsapp-incoming | whatsapp_ip | 20/min | 10 |
| /webhook/flutterwave-payment | flutterwave_ip | 100/min | 20 |
| /webhook/bitlabs-postback | bitlabs_ip | 50/min | 10 |
| /health | general_ip | 300/min | 50 |
| /admin/* | general_ip | 30/min | 5 + Basic auth |

### SSL Settings
- Protocol: TLS 1.2 + 1.3 only
- Ciphers: Modern suite (ECDHE)
- Certificate: Let's Encrypt (auto-renew)
- HSTS header: Enabled

### Security Headers
```
Strict-Transport-Security: max-age=31536000
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

---

## Layer 3: Webhook Signature Verification

**Purpose:** Verify webhooks actually come from the claimed provider.

### Providers & Algorithms

| Webhook | Algorithm | Header/Param | Confirmed |
|---------|-----------|--------------|-----------|
| WhatsApp | HMAC-SHA256 | X-Hub-Signature-256 | ✅ Meta docs |
| Flutterwave | HMAC-SHA256 | verif-hash | ✅ Flutterwave docs |
| BitLabs | HMAC-SHA1 | signature param | ✅ BitLabs docs |

### Verification Flow
```
Webhook arrives
        ↓
Extract signature from header
        ↓
Calculate expected signature using:
  - Your secret (stored in env var)
  - The raw request body
  - Algorithm (SHA256 or SHA1)
        ↓
Compare signatures (constant-time)
        ↓
Valid → Continue to workflow
Invalid → Return 401, log attempt
```

### Response on Failure
```
HTTP 401 Unauthorized
{
  "error": "Invalid signature"
}
```

### Anti-Replay Check
Reject webhooks older than 30 minutes.

### Admin Alert
Trigger alert if >10 failed verifications in 5 minutes from same IP.

---

## Layer 4: Payment Idempotency

**Purpose:** Prevent duplicate processing when same webhook is received multiple times.

### Storage
- **Redis:** Fast lookup (TTL: 24 hours)
- **PostgreSQL:** Permanent record (retention: 90 days)

### Redis Key Pattern
```
webhook:processed:{provider}:{webhook_id}
```

### Webhook ID Mapping

| Provider | ID Used |
|----------|---------|
| Flutterwave | tx_ref |
| BitLabs | transaction_id |

### Flow
```
Webhook arrives
        ↓
Extract webhook ID
        ↓
Check Redis
        ↓
Already exists → Return 200, ignore
Not in Redis → Check PostgreSQL
        ↓
Already in PostgreSQL → Cache in Redis → Return 200, ignore
Not found → Continue processing
        ↓
Process webhook
        ↓
Mark as processed in Redis (24h) + PostgreSQL (permanent)
```

### Race Condition Protection
Redis SETNX (atomic check-and-set) prevents concurrent processing.

---

## Layer 5: Redis Rate Limiting (Escalating)

**Purpose:** Limit customer message frequency with escalating penalties.

### Limits
| Endpoint | Limit | Window |
|----------|-------|--------|
| Customer WhatsApp | 20 per minute | 60 seconds |
| BitLabs postback | 10 per minute | 60 seconds |

### Escalation Pattern

| Step | Violation | Action | Reset |
|------|-----------|--------|-------|
| 1 | 1st | 1 min block | — |
| 2 | 2nd | 5 min block | — |
| 3 | 3rd | 15 min block | — |
| 4 | 4th | 30 min block | — |
| 5 | 5th | 1 hr block | — |
| 6 | 6th | 2 hr block | — |
| 7 | 7th | 24 hr ban | — |
| 8 | 8th (within 3 days of 7th) | **PERMANENT BLACKLIST** | Appeal to admin |

### Reset Conditions
| Event | What Resets |
|-------|-------------|
| 24 hours with no violations | Violation counter resets to 0 |
| 3 days after 24hr ban ends | No blacklist (if no more violations) |
| Permanent blacklist | Admin can unblacklist via appeal |

### Customer Messages
**1-6 min blocks:**
```
You're sending too quickly. Wait [X] minutes.
```

**7th (24hr ban):**
```
You've been temporarily banned for 24 hours due to repeated abuse. Contact support if you believe this is a mistake.
```

**8th (permanent blacklist):**
```
Your account has been permanently blacklisted. Contact support if you believe this is a mistake.
```

### Tracking
Redis key: `ratelimit:violations:{phone_hash}` with 24-hour TTL.

---

## Layer 6: Admin PIN + 2FA

**Purpose:** Secure admin commands with two-factor authentication.

### Two Parts
1. **PIN:** 4-6 digits, starts 30-min session
2. **TOTP:** 6-digit code from authenticator app, required for high-risk commands

### Session Flow
```
Admin sends message
        ↓
No active session → "Enter PIN"
        ↓
PIN entered → Verify hash → 30-min session starts
        ↓
Session active → Can run LOW risk commands
        ↓
MEDIUM risk command → Require fresh PIN (2 min window)
        ↓
HIGH risk command → Require PIN + TOTP every time
        ↓
30 min inactivity → Session expires
```

### Command Risk Levels

| Level | Commands | Auth Required |
|-------|----------|---------------|
| Low | Pending, Provider Status, Errors, Daily Summary, Admin Status, Admin Logout | Active session |
| Medium | Block, Unblock, Resolve ERR-XXXXX, Details ORD-XXXXX | Fresh PIN (2 min) |
| High | Refund, Force-Refund, Approve, Reject, Remove Blacklist | PIN + TOTP |

### Full Admin Commands

| Command | Risk | Auth |
|---------|------|------|
| Pending | Low | Session |
| Provider Status | Low | Session |
| Errors | Low | Session |
| Daily Summary | Low | Session |
| Admin Status | Low | Session |
| Admin Logout | Low | Session |
| Block [phone] [reason] | Medium | Fresh PIN |
| Unblock [phone] | Medium | Fresh PIN |
| Resolve ERR-XXXXX | Medium | Fresh PIN |
| Details ORD-XXXXX | Medium | Fresh PIN |
| Refund ORD-XXXXX | High | PIN + TOTP |
| Force-Refund ORD-XXXXX | High | PIN + TOTP |
| Approve ORD-XXXXX | High | PIN + TOTP |
| Reject ORD-XXXXX | High | PIN + TOTP |
| Remove Blacklist [phone] | High | PIN + TOTP |

### Lockout Policy
| Failed Attempts | Lockout |
|----------------|---------|
| 3 in 10 minutes | 15 minutes |
| 5 in 1 hour | 1 hour |
| 10 in 24 hours | 24 hours |

### Setup Flow
1. Admin enters PIN (stored as bcrypt hash)
2. Admin scans QR code with authenticator app
3. Admin enters TOTP code to verify
4. TOTP secret stored encrypted (AES-256-GCM)

---

## Layer 7: Monitoring + Alerting

**Purpose:** Know when something needs attention.

### Alert Levels

| Level | Action |
|-------|--------|
| Critical | Immediate WhatsApp to admin |
| Warning | Log + notify if repeated |
| Info | Log only |

### Critical Alerts (Immediate)

| Event |
|-------|
| Provider down |
| Payment webhook attack |
| Database connection failed |
| Multiple refund failures |
| Admin PIN failures (3x) |
| VPS disk space low (<20%) |
| Backup failure |

### Warning Alerts (Log + Alert if Repeated)

| Event | Trigger |
|-------|---------|
| Rate limit violations | >10 in 5 minutes |
| Signature verification failures | >10 in 5 minutes |
| High error rate | >5 in 1 hour |
| Revenue below threshold | <₦50,000/day |
| Admin login from new IP | First time |
| Blacklist event | Customer blacklisted |
| Proxy delivery failure | >3 consecutive |
| Free trial abuse | >3 trials/day per customer |
| High ban rate | >20% proxies banned |
| Redis memory | >80% used |
| PostgreSQL connections | >80% of max |
| Refund rate spike | >10% of orders |
| Webhook from unknown IP | IP not on allowlist |

### Info Alerts (Log Only)

| Event |
|-------|
| New order |
| New customer |
| Successful refund |
| Provider health check passed |
| Data depleted |
| Revenue spike |

---

## Security Checklist

| Item | Status |
|------|--------|
| Cloudflare rate limiting | Required |
| Nginx HTTPS + rate limits | Required |
| Webhook signature verification | Required |
| Payment idempotency | Required |
| Redis rate limiting (escalating) | Required |
| Admin PIN + TOTP | Required |
| Monitoring + alerting | Required |
| PostgreSQL SSL | Required |
| Redis password | Required |
| TOTP secrets encrypted | Required |
| API keys in env vars | Required |
| Certificate auto-renewal | Required |
| Daily backups | Required |

---

## Implementation Effort

| Layer | Time |
|-------|------|
| Cloudflare setup | 30 min |
| Nginx + HTTPS | 2 hours |
| Webhook verification | 4 hours |
| Payment idempotency | 4 hours |
| Redis rate limiting | 4 hours |
| Admin auth (PIN + 2FA) | 8 hours |
| Monitoring + alerting | 4 hours |
| Testing | 4 hours |
| **Total** | **~30 hours** |

---

## Cost

| Component | Cost |
|-----------|------|
| Cloudflare free tier | $0 |
| Let's Encrypt | $0 |
| Redis | $0 |
| Monitoring | $0 |
| **Total** | **$0** |
