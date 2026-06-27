# Bunche — Workflow Specifications

**Last Updated:** 2026-06-27
**SHA:** data-alert-v1-referral + 3proxy-trial
**Status:** Planning Complete — Ready for Implementation

---

## Table of Contents

1. [Products & Data Model](#products--data-model)
2. [Workflows](#workflows)
3. [Data Alert System](#data-alert-system)
4. [Referral System](#referral-system)
5. [Security](#security)
6. [Architecture](#architecture)
7. [Admin Authentication](#admin-authentication)
8. [PII Handling](#pii-handling)

---

## Products & Data Model

### Providers

| Provider | Products | Role |
|----------|---------|------|
| **Proxy-Seller** | ISP, Datacenter | Primary |
| **DataImpulse** | Residential, Mobile | Secondary |
| **Self-hosted 3proxy** | Free trials only | Trial infrastructure |

### Products & Tracking

| Product | Provider | Billing | Tracking | Expiry |
|---------|----------|---------|----------|--------|
| ISP | Proxy-Seller | Per month | Time-based | Yes — expires on date |
| DC | Proxy-Seller | Per month | Time-based | Yes — expires on date |
| Residential | DataImpulse | Per GB | Data-based | **No time expiry — runs until GB is used up** |
| Mobile | DataImpulse | Per GB | Data-based | 30-day window to use GB |
| **Free trial** | **Self-hosted 3proxy** | **Free (survey-paid)** | **2-hour TTL** | **Auto-expires via cron** |

### Residential — No Time Expiry

Residential proxies from DataImpulse **do not expire by time**. They last until the allocated GB is fully used. There is no expiry date.

```
Residential 5GB purchased January 1
  → Works until 5GB is used up
  → No expiry date
  → Customer can track: "I've used X.X GB of 5GB"
```

### Mobile — 30-Day Window + Data Cap

Mobile proxies have both a **data cap** AND a **30-day window** to use it.

```
Mobile 5GB purchased January 1
  → 5GB of data to use
  → Must use it within 30 days (expires January 31)
  → If data runs out before day 30 → proxy stops
  → If day 30 arrives with data left → unused data is lost
```

### Free Trial — 2-Hour TTL (Locked)

Free trial uses Bunche's self-hosted 3proxy. Customers share the VPS public IP across all concurrent trials (max 100 at once). Trial credentials auto-expire after 2 hours via cron cleanup.

```
Trial granted at 14:00 Lagos
  → Works for 2 hours
  → Auto-expires at 16:00 (credentials removed from 3proxy)
  → Customer can re-request if more time needed (counts toward 3/day limit)
```

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

(Same as before — unchanged)

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

(Same as before — unchanged)

---

### Workflow 7: Expiry + Data Alert Cron

(Same as before — unchanged)

---

### Workflow 8: Free Trial (Self-Hosted 3proxy + Theorem Reach)

**Trigger:** Customer says "free trial" / "free plan" / "trial"
**Purpose:** Grant 2-hour trial via Theorem Reach survey + dynamic 3proxy credentials

> **Note:** Free trials use self-hosted 3proxy on the Bunche VPS (not paid provider IPs). Theorem Reach handles survey verification with HMAC-signed postbacks. Each trial costs ~$0.001 in VPS bandwidth and earns Bunche $1-4 in survey revenue.

#### Part A: Customer-Facing Flow

```
[Customer asks for free trial]
        ↓
[Send WhatsApp: FULL DISCLAIMER + survey link]
        ↓
[Customer reads disclaimer, completes Theorem Reach survey]
        ↓
[Customer replies DONE]
        ↓
[Wait for Theorem Reach postback OR customer DONE reply]
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
   │ ❌ All 100 trial slots busy → "Try in 30m"   │
   └────────────────────────────────────────────┘
```

#### Part B: Backend Flow (when survey verified)

```
[Generate unique user_id: trial_a7b9c2 (16 chars alphanumeric)]
[Generate random password: 16 chars]
[Find available port in 8001-8100 range]
        ↓
[Execute shell script: manage-3proxy-trial.sh add USER PASS PORT]
   └─→ Appends "users trial_a7b9c2:CL:hash" to /etc/3proxy/bunche-trial.cfg
   └─→ Sends SIGHUP to 3proxy (hot reload, no restart)
        ↓
[INSERT into free_trials table:
   - order_id = TRIAL-20260627-1042
   - phone_hash, user_id, password_hash
   - proxy_ip = VPS_PUBLIC_IP
   - proxy_port = 8001-8100
   - expires_at = NOW() + 2 hours
   - survey_transaction_id = from Theorem Reach (idempotency)
   - survey_payout_usd = 1.50 (recorded)
   - status = 'active']
        ↓
[Send WhatsApp to customer with credentials + 2hr expiry]
        ↓
[Return 200 OK to Theorem Reach]
```

#### Part C: Customer-Facing Disclaimer

```
🎁 FREE TRIAL — DISCLAIMER

Before we send your free IP, please read:

━━━━━━━━━━━━━━━━━━
⚠️ FREE TRIAL TERMS ⚠️
━━━━━━━━━━━━━━━━━━

This free trial uses a Bunche-hosted proxy
shared with other trial users. By accepting, you agree:

❌ NOT for production/critical use
❌ Not guaranteed private (shared with other trials)
❌ IP shared = if one user misbehaves, IP could get flagged
❌ No replacement if proxy dies or expires
❌ Used entirely at YOUR OWN RISK

✅ Bunche-hosted proxy — generally reliable
✅ Auto-expires after 2 hours
✅ For testing our service only
✅ Upgrade to paid plan for reliability + privacy

━━━━━━━━━━━━━━━━━━

Complete ONE survey to unlock your IP:

[SURVEY LINK]

After completing, reply DONE
```

#### Part D: Customer-Facing Success Message

```
✅ Survey verified! Trial ready.

━━━━━━━━━━━━━━━━━━
🌐 BUNCHE TRIAL PROXY — 2 HOURS
━━━━━━━━━━━━━━━━━━

🔗 IP: bunche.ng
🔌 Port: 8001
👤 User: trial_a7b9c2
🔑 Pass: Kx9mNp2qR8sT4wY7

⏰ Expires: [current time + 2hrs]

⚠️ Shared proxy — other trial users share this IP.
For private/production use, upgrade to a paid plan.

🛡️ You've used [X/3] free trials today.

💡 Want reliable private proxies? Reply menu to see paid plans.
```

#### Part E: Daily Limit Hit Message

```
🛡️ Daily limit reached — you've used 3/3 free trials today.

Come back tomorrow, or skip the wait with a paid plan:
• ISP UK/US: ₦6,500/mo (private, reliable)
• Residential 5GB: ₦5,000 (data never expires)
• Mobile 5GB: ₦20,000 (4G)

Reply menu to order, or wait until tomorrow for another free trial.
```

#### Part F: All Slots Busy Message

```
⚠️ All trial slots busy right now.

We'll ping you the moment one opens up (usually within 30 minutes).

🛡️ You've used [X/3] free trials today.

💡 Want reliable proxies now? Reply menu.
```

#### Why Theorem Reach + 3proxy (vs CPAGrip + Public Proxies)

| Reason | Detail |
|--------|--------|
| **Anti-bot** | Theorem Reach uses behavioral analysis (~95% bot block rate) — better than CPAGrip |
| **Revenue** | Theorem Reach pays us $1-4/trial — net positive economics |
| **Reliability** | Self-hosted 3proxy is Bunche-controlled, no flaky public proxy lists |
| **Cost** | $0.001/trial bandwidth vs public proxies that may not work at all |
| **Customer UX** | 2-hour TTL is generous vs no expiration (which causes confusion) |

---

### Workflow 9: Free Trial Follow-Up (Idle Cron)

(Same as before — adapted for 3proxy context)

---

### Workflow 10: Trial Reset (Daily Midnight)

(Same as before — also resets Theorem Reach postback counters)

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
| **Theorem Reach** | **HMAC-SHA256 (postback signature)** |
| Bitlock.ai | (DEPRECATED — removed in favor of Theorem Reach) |

### Rate Limiting (3 Layers)

| Layer | What It Catches |
|-------|----------------|
| Cloudflare | DDoS, bots, mass attacks |
| Nginx | Persistent attackers, per-endpoint limits |
| Redis in n8n | Customer spam, phone-based limits |
| **Free trial daily limit** | **Same phone can't request >3 trials/day** |

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

### Theorem Reach Idempotency

```
[Postback received with transaction_id]
        ↓
[INSERT INTO theorem_reach_postbacks (transaction_id, ...) ON CONFLICT DO NOTHING]
        ↓
[If inserted (new) → process trial]
[If conflict (already processed) → return 200, ignore]
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
[PostgreSQL — customers, orders, audit logs]
        ↓
[MiniMax M2 API — LLM]
        ↓
[Provider APIs — Proxy-Seller, DataImpulse]
        ↓
[3proxy shell script — add/remove trial users]
        ↓
[WhatsApp reply]
```

### Free Trial Sub-Flow

```
Customer: "free trial"
        ↓
[WhatsApp → n8n → Workflow 8]
        ↓
[Send disclaimer + Theorem Reach survey link]
        ↓
[Customer completes survey on Theorem Reach's domain]
        ↓
[Customer replies DONE on WhatsApp]
[OR Theorem Reach sends postback]
        ↓
[n8n workflow: verify HMAC, check status=completed]
        ↓
[Generate credentials, add to 3proxy via shell]
        ↓
[Send WhatsApp with trial credentials]
        ↓
[Cron every 5 min: clean expired credentials from 3proxy + DB]
```

---

## Admin Authentication

(Same as before — unchanged)

---

## PII Handling

(Same as before — unchanged)

---

## Error Workflow

(Same as before — unchanged)

---

## Products & Pricing

(Same as before — unchanged)

---

## Provider Health Endpoints

| Provider | Health Check | Order Endpoint | Data Status |
|----------|-------------|----------------|-------------|
| Proxy-Seller | GET /balance | POST /api/v1/order/create | N/A (time-based) |
| DataImpulse | GET /account | POST /reseller/order/create | GET /reseller/order/{id} — returns used_gb + remaining_gb |
| **Self-hosted 3proxy** | **ps aux \| grep 3proxy** | **shell script (manage-3proxy-trial.sh add USER PASS PORT)** | **DB table (free_trials.expires_at)** |

---

## Admin Commands

(Same as before — unchanged)

---

## Free Trial Admin Commands (New)

| Command | Risk | Description |
|---------|------|-------------|
| Trial stats | Low | Show today's trial count, active trials, slots used |
| Revoke trial USER | Medium | Force-remove a trial user (admin override) |
| List active trials | Low | Show all active trial user_ids + expiry times |

---

## Workflow Status Summary

| # | Workflow | Status |
|---|----------|--------|
| 1 | Order Handler | Planned |
| 2 | Payment Confirmation | Planned |
| 3 | Admin Command Handler | Planned |
| 4 | Ban Claim | Planned |
| 5 | Provider APIs + Health | Planned |
| 6 | Refund Handler | Planned |
| 7 | Expiry + Data Reminder | Planned |
| 8 | **Free Trial (3proxy + Theorem Reach)** | **Planned** |
| 9 | Free Trial Follow-Up | Planned |
| 10 | Trial Reset | Planned |
| 11 | Bunche Logger | Planned |
| 12 | Provider Health Logger | Planned |
| 13 | Daily Summary | Planned |
| 14 | Data Alert Escalation | Planned |
| 15 | Referral Credit Processor | Planned |

---

## See Also

- `docs/REFERRAL_SYSTEM.md` — Full referral system specification
- `docs/DEAD_IP_REPLACEMENT_POLICY.md` — Dead IP retry flow
- `scenarios/2026-06-26-free-trial.md` — Free trial scenario (canonical reference)
- `scenarios/2026-06-26-first-time-order.md` — Paid first-time flow
- `scenarios/2026-06-26-provider-down-recovery.md` — Provider failure path
- `scenarios/2026-06-26-new-number-recovery.md` — New phone recovery
- `scenarios/2026-06-26-forgot-pin-recovery.md` — Forgot PIN flow
- `docs/ARCHITECTURE_PLAN.md` — Full architecture plan
- `docs/SECURITY_PLAN.md` — Security implementation details
- `docs/DATABASE_SCHEMA.md` — PostgreSQL schema
- `legal/TERMS_OF_SERVICE.md` — Legal terms
- `legal/PRIVACY_POLICY.md` — Privacy policy
- `legal/ACCEPTABLE_USE_POLICY.md` — Acceptable use (includes trial abuse clause)