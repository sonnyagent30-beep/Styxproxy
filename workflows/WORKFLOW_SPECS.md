# Bunche — Workflow Specifications

**Last Updated:** 2026-06-27
**SHA:** Bunche-Auth-Layer-v1
**Status:** Ready for Implementation

---

## Table of Contents

1. [Products & Data Model](#products--data-model)
2. [Bunche Auth Layer](#bunche-auth-layer)
3. [Workflows](#workflows)
4. [Data Alert System](#data-alert-system)
5. [Referral System](#referral-system)
6. [Security](#security)
7. [Architecture](#architecture)
8. [Admin Authentication](#admin-authentication)
9. [PII Handling](#pii-handling)

---

## Products & Data Model

### Providers

| Provider | Products | Role |
|---------|---------|------|
| **Proxy-Seller** | ISP, Datacenter | Primary |
| **DataImpulse** | Residential, Mobile | Secondary |
| **Rayobyte** | DC Rotating | Future |
| **Self-hosted Dante** | ALL products (auth layer) | Bunche-branded auth |

### Products & Tracking

| Product | Provider | Billing | Tracking | Expiry |
|---------|----------|---------|----------|--------|
| ISP | Proxy-Seller | Per month | Time-based | Yes — expires on date |
| DC | Proxy-Seller | Per month | Time-based | Yes — expires on date |
| DC Rotating | Rayobyte | Per GB | GB-based | Varies |
| Residential | DataImpulse | Per GB | Data-based | **No time expiry — runs until GB is used** |
| Mobile | DataImpulse | Per GB | Data-based | 30-day window to use GB |
| **Free trial** | **Self-hosted Dante** | **Free (survey-paid)** | **2-hour TTL** | **Auto-expires via cron** |

---

## Bunche Auth Layer

### How It Works

All customers receive Bunche-branded proxy credentials. The actual proxy IPs are sourced from vetted infrastructure partners but customers interact only with Bunche.

```
Customer sees:   proxy1.bunche.ng:1080
                 username: bun_001
                 password: P@ssw0rd!
                        │
                        ▼
              Bunche Dante SOCKS5 Server (Hetzner)
                        │
              Maps Bunche username → Provider IP
                        │
                        ▼
            Vetted infrastructure partners
            (Proxy-Seller / DataImpulse)
```

### Credential Lifecycle

**Order Flow:**
1. Customer pays → Flutterwave webhook
2. n8n calls provider API → gets provider IP + credentials
3. n8n generates Bunche username/password
4. n8n calls `manage-bunche-credentials.sh add USERNAME PASSWORD`
5. n8n inserts row into `bunche_credentials` DB table
6. n8n sends Bunche-branded credentials via WhatsApp

**Refund Flow:**
1. Admin approves refund on Flutterwave dashboard
2. Flutterwave processes refund
3. n8n calls `manage-bunche-credentials.sh revoke USERNAME`
4. Dante reloads → old credentials instantly fail
5. n8n updates `bunche_credentials.status = 'revoked'`
6. Provider IP is NOT returned to provider (already paid for monthly)
7. Provider IP goes into free_trial pool with new temp password

**Free Trial Flow:**
1. Customer completes survey → verified via webhook
2. n8n picks an available IP from free_trial pool
3. n8n generates session password
4. n8n calls `manage-bunche-credentials.sh free_trial TRIALUSER SESSIONPASS`
5. Credentials sent to customer with 2hr expiry warning
6. Cron runs every 5 min → checks `bunche_credentials.expires_at`
7. Expired trials → `manage-bunche-credentials.sh revoke TRIALUSER`
8. IP returned to free_trial pool

### Credential Management

| Scenario | Action |
|---------|--------|
| New paying customer | Add Bunche credential → deliver → track in DB |
| Refund approved | Revoke Bunche credential → recycle IP to free_trial pool |
| Free trial starts | Assign from free_trial pool → send with 2hr TTL |
| Free trial expires | Revoke credential → IP stays in free_trial pool |
| Paid order expires | Revoke credential → no recycle (customer must renew) |
| Abuse detected | Revoke immediately → block customer |

---

## Workflows

### Workflow 1: Order Handler

**Trigger:** Incoming WhatsApp message
**Purpose:** Route customer message to appropriate action

```
[WhatsApp Webhook] → [Signature Verify] → [Idempotency] → [Rate Limit] → [Session Check]
        ↓
[LLM Intent Parser] → Extract intent + entities
        ↓
[Switch by Intent]
        ├── order → [Order Flow]
        ├── renewal → [Renewal Flow]
        ├── status → [Status Flow]
        ├── help → [Help Flow]
        ├── free_trial → [Free Trial Disclaimer]
        ├── recovery → [Recovery Flow]
        ├── how_to_use → [Setup Guide Flow]
        ├── check_data → [Data Status Flow]
        ├── referral_share → [Share Name Flow]
        └── unknown → [Fallback]
```

---

### Workflow 2: Payment Confirmation

**Trigger:** Flutterwave webhook (`payment.placed`, `transfer.completed`)
**Purpose:** Fulfill order after payment confirmed

```
[Flutterwave Webhook]
        ↓
[Signature Verify: HMAC-SHA256]
        ↓
[Idempotency Check: webhook_id in Redis → ignore if duplicate]
        ↓
[Parse tx_ref → extract customer_phone + plan_code]
        ↓
[Verify customer exists in DB]
        ↓
[Call Provider API: POST /order → get IP + provider credentials]
        ↓
[TEST IP: curl --proxy IP:PORT -U user:pass http://checkip.amazonaws.com]
        ├── FAIL → retry up to 3 times with new IP
        │        └── All fail → trigger refund automatically
        └── PASS → Continue
        ↓
[Generate Bunche credentials]
  bun_username = bun_{CUSTOMER_ID}
  bun_password = random 16-char
        ↓
[Call manage-bunche-credentials.sh add bun_USERNAME bun_PASSWORD]
        ↓
[INSERT into bunche_credentials table]
        ↓
[INSERT into orders table]
        ↓
[Send WhatsApp: Bunche-branded credentials]
  "✅ Payment confirmed!
  
  🌐 Your Proxy Details:
  
  IP/Host: proxy1.bunche.ng
  Port: 1080
  Username: bun_001
  Password: P@ssw0rd!2024
  
  Type: Residential
  Validity: 30 days
  Max GB: 5GB"
        ↓
[Return 200 OK to Flutterwave]
```

---

### Workflow 3: Admin Command Handler

(Same as before — unchanged)

---

### Workflow 4: Ban Claim

(Same as before — unchanged)

---

### Workflow 5: Provider APIs + Health Checks

(Same as before — unchanged)

---

### Workflow 6: Refund Handler

**Trigger:** Admin approves refund OR Flutterwave refund webhook
**Purpose:** Revoke Bunche credentials and recycle IP

```
[Refund Approved: flutterwave OR admin command]
        ↓
[Look up order in orders table]
        ↓
[Look up bunche_credentials record]
        ↓
[If not found → log error, skip credential revoke step]
        ↓
[Call manage-bunche-credentials.sh revoke bun_USERNAME]
        ↓
[Update bunche_credentials: status='revoked', revoke_reason='refund']
        ↓
[IF provider IP can be recycled (monthly IP, not GB-based)]
  → Insert new temp credential in free_trial pool
  → bun_username = temp_{TIMESTAMP}
  → bun_password = random
  → pool_type = 'refunded_recycled'
  → expires_at = NOW() + 2 hours
  → Bunche sends WhatsApp: "IP recycled to free trial pool"
        ↓
[Update orders: status='refunded']
        ↓
[Log in customer_audit_log]
        ↓
[Send WhatsApp to customer: refund confirmation]
```

---

### Workflow 7: Expiry + Data Reminder Cron

(Same as before — unchanged)

---

### Workflow 8: Free Trial (Self-Hosted Dante + Survey)

**Trigger:** Customer says "free trial" / "free plan" / "trial"
**Purpose:** Grant 2-hour trial via Survey + dynamic Bunche credentials

#### Part A: Customer-Facing Flow

```
[Customer asks for free trial]
        ↓
[Send WhatsApp: FULL DISCLAIMER + survey link]
        ↓
[Customer reads disclaimer, completes survey]
        ↓
[Customer replies DONE]
        ↓
[Wait for survey postback OR customer DONE reply]
        ↓
[Verify survey completion (HMAC + status=completed)]
        ↓
[Check daily limit: 3/3 used?]
        ↓
   ┌────────────────────────────────────────────┐
   │ Outcomes                                   │
   ├────────────────────────────────────────────┤
   │ ✅ Survey valid + limit OK → Grant trial    │
   │ ❌ Daily limit hit → "Try tomorrow"         │
   │ ❌ Invalid signature → log + admin alert     │
   │ ❌ All trial slots busy → "Try in 30m"       │
   └────────────────────────────────────────────┘
```

#### Part B: Backend Flow (when survey verified)

```
[Check free_trial_pool for available IP]
  → SELECT * FROM bunche_credentials 
    WHERE pool_type = 'free_trial' 
    AND status = 'available'
    LIMIT 1
        ↓
[If no available IP → check refunded_recycled pool]
        ↓
[Generate session password: Sess@2hr! + random]
        ↓
[Call manage-bunche-credentials.sh add trial_XXXX sess_PASS]
        ↓
[UPDATE bunche_credentials SET:
  customer_phone = phone,
  status = 'active',
  expires_at = NOW() + INTERVAL '2 hours',
  pool_type = 'free_trial']
        ↓
[INSERT into free_trials table]
        ↓
[Send WhatsApp to customer with credentials + 2hr expiry]
        ↓
[Return 200 OK to survey provider]
```

#### Part C: Free Trial Cron (Every 5 Minutes)

```
[Cron: every 5 minutes]
        ↓
[SELECT FROM bunche_credentials
  WHERE pool_type IN ('free_trial', 'refunded_recycled')
  AND status = 'active'
  AND expires_at < NOW()]
        ↓
[For each expired credential:]
  [Call manage-bunche-credentials.sh revoke TRIAL_USER]
  [UPDATE bunche_credentials SET:
    status = 'available',
    customer_phone = NULL,
    expires_at = NULL]
  [Log expiration in audit]
        ↓
[Send WhatsApp: "Your 2-hour trial has ended.
  Want unlimited access? Reply UPGRADE for pricing."]
```

---

### Workflow 9: Free Trial Follow-Up (Idle Cron)

(Same as before — adapted for Dante context)

---

### Workflow 10: Trial Reset (Daily Midnight)

(Same as before — also resets trial counters)

---

### Workflow 11: Bunche Logger

(Same as before — unchanged)

---

### Workflow 12: Provider Health Logger

(Same as before — unchanged)

---

### Workflow 13: Daily Summary

(Same as before — unchanged)

---

### Workflow 14: Data Alert Escalation Cron

(Same as before — unchanged)

---

### Workflow 15: Referral Credit Processor

(Same as before — unchanged)

---

## Data Alert System

(Same as before — unchanged)

---

## Referral System

(Same as before — unchanged)

---

## Security

### Webhook Signature Verification

All webhooks verified before processing:

| Webhook | Verification |
|---------|-------------|
| WhatsApp | HMAC-SHA256 (X-Hub-Signature-256) |
| Flutterwave | HMAC-SHA256 (verif-hash) |
| Survey Provider | HMAC-SHA256 (postback signature) |

### Credential Security

| Threat | Mitigation |
|--------|-----------|
| Credential brute force | Dante + fail2ban blocks after 3 failures |
| Credential theft | HTTPS-only, never in WhatsApp logs |
| Refund credential reuse | Credentials revoked before refund processed |
| Free trial credential sharing | Session password expires in 2hrs |

### Payment Idempotency

```
[Webhook received]
        ↓
[Extract webhook_id (tx_ref, message_id, etc.)]
        ↓
[Check Redis: webhook:processed:{provider}:{id}]
        ↓
[IF exists] → Return 200, ignore
[IF not exists] → Check PostgreSQL
        ↓
[IF in PostgreSQL] → Cache in Redis → Return 200, ignore
[IF not found] → Mark as processing → Continue
        ↓
[Process webhook]
        ↓
[Mark as processed in Redis + PostgreSQL]
```

---

## Architecture

### Complete Flow

```
Customer WhatsApp
        ↓
[Cloudflare — DDoS + rate limit]
        ↓
[Nginx — HTTPS + endpoint limits]
        ↓
[n8n webhook — signature + idempotency]
        ↓
[Redis — caching + sessions + rate limits]
        ↓
[PostgreSQL — customers, orders, audit logs, bunche_credentials]
        ↓
[MiniMax M2 API — LLM]
        ↓
[Provider APIs — Proxy-Seller, DataImpulse]
        ↓
[Dante SOCKS5 — Bunche credential auth]
        ↓
[WhatsApp reply]
```

### Bunche Credential Flow

```
n8n order workflow
        │
        ▼
Proxy-Seller / DataImpulse API
  ← returns: IP, Port, Provider Username, Provider Password
        │
        ▼
Generate Bunche credentials
  bun_username = bun_{customer_id}
  bun_password = random 16-char
        │
        ▼
Write to PostgreSQL: bunche_credentials table
  ← stores: bun_username, password_hash, provider details, status
        │
        ▼
Call manage-bunche-credentials.sh add USERNAME PASSWORD
        │
        ▼
Dante reloads → new user is valid
        │
        ▼
Customer connects: proxy1.bunche.ng:1080
  - Dante authenticates with bun_USERNAME + bun_PASSWORD
  - Dante routes to upstream provider IP
  - Customer sees Bunche-branded proxy
```

---

## Admin Authentication

(Same as before — unchanged)

---

## PII Handling

(Same as before — unchanged)

---

## Provider Health Endpoints

| Provider | Health Check | Order Endpoint | Data Status |
|----------|-------------|----------------|------------|
| Proxy-Seller | GET /balance | POST /api/v1/order/create | N/A (time-based) |
| DataImpulse | GET /account | POST /reseller/order/create | GET /reseller/order/{id} |
| **Dante** | `pgrep danted` | `manage-bunche-credentials.sh` | `bunche_credentials.expires_at` |

---

## Admin Commands

| Command | Risk | Description |
|---------|------|-------------|
| Trial stats | Low | Show today's trial count, active trials, slots used |
| Revoke trial USER | Medium | Force-remove a trial user (admin override) |
| List active trials | Low | Show all active trial user_ids + expiry times |
| Revoke credential USER | Medium | Revoke paying customer's Bunche credential |
| Check credential USER | Low | Show credential status in DB |

---

## Workflow Status Summary

| # | Workflow | Status |
|---|----------|--------|
| 1 | Order Handler | Ready |
| 2 | Payment Confirmation | Ready — updated for Dante credential creation |
| 3 | Admin Command Handler | Ready |
| 4 | Ban Claim | Ready |
| 5 | Provider APIs + Health | Ready |
| 6 | Refund Handler | Ready — updated for Dante credential revoke |
| 7 | Expiry + Data Reminder | Ready |
| 8 | **Free Trial (Dante + Survey)** | **Ready — updated for Dante auth** |
| 9 | Free Trial Follow-Up | Ready |
| 10 | Trial Reset | Ready |
| 11 | Bunche Logger | Ready |
| 12 | Provider Health Logger | Ready |
| 13 | Daily Summary | Ready |
| 14 | Data Alert Escalation | Ready |
| 15 | Referral Credit Processor | Ready |

---

## See Also

- `docs/REFERRAL_SYSTEM.md` — Full referral system specification
- `docs/DEAD_IP_REPLACEMENT_POLICY.md` — Dead IP retry flow
- `docs/DATABASE_SCHEMA.md` — PostgreSQL schema including `bunche_credentials`
- `docs/DANTE_SETUP.md` — Dante SOCKS5 installation and configuration
- `scripts/manage-bunche-credentials.sh` — Dante credential management script
- `scenarios/2026-06-26-free-trial.md` — Free trial scenario
- `scenarios/2026-06-26-first-time-order.md` — Paid first-time flow
- `scenarios/2026-06-26-refund-flow.md` — Refund scenario
- `docs/ARCHITECTURE_PLAN.md` — Full architecture plan
- `legal/TERMS_OF_SERVICE.md` — Legal terms (provider-neutral)
- `legal/PRIVACY_POLICY.md` — Privacy policy
- `legal/ACCEPTABLE_USE_POLICY.md` — Acceptable use