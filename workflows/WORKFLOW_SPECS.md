# Bunche — Workflow Specifications

**Last Updated:** 2026-06-26
**SHA:** data-alert-v1
**Status:** Planning Complete — Ready for Implementation

---

## Table of Contents

1. [Products & Data Model](#products--data-model)
2. [Workflows](#workflows)
3. [Data Alert System](#data-alert-system)
4. [Security](#security)
5. [Architecture](#architecture)
6. [Admin Authentication](#admin-authentication)
7. [PII Handling](#pii-handling)

---

## Products & Data Model

### Providers

| Provider | Products | Role |
|----------|---------|------|
| **Proxy-Seller** | ISP, Datacenter | Primary |
| **DataImpulse** | Residential, Mobile | Secondary |

### Products & Tracking

| Product | Provider | Billing | Tracking | Expiry |
|---------|----------|---------|----------|--------|
| ISP | Proxy-Seller | Per month | Time-based | Yes — expires on date |
| DC | Proxy-Seller | Per month | Time-based | Yes — expires on date |
| Residential | DataImpulse | Per GB | Data-based | **No time expiry — runs until GB is used up** |
| Mobile | DataImpulse | Per GB | Data-based | 30-day window to use GB |

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
        ├── free_trial → [Free Trial Flow]
        ├── recovery → [Recovery Flow]
        ├── how_to_use → [Setup Guide Flow]
        ├── check_data → [Data Status Flow]
        └── unknown → [Fallback]
```

---

### Workflow 2: Payment Confirmation

**Trigger:** Flutterwave webhook
**Purpose:** Fulfill order after payment confirmed

```
[Flutterwave Webhook] → [Signature Verify] → [Idempotency] → [Rate Limit]
        ↓
[Extract tx_ref] → [Lookup order in PostgreSQL]
        ↓
[IF order exists AND status = 'paid'] → Return 200 (already processed)
[IF order exists AND status = 'pending'] → Continue
[IF order not found] → Log error → Return 200 (don't retry)
        ↓
[Call Provider API] → Generate proxy
        ↓
[Test proxy IP] → 5 second timeout
        ↓
[IF test PASS] → Save to PostgreSQL → Send to customer
[IF test FAIL] → Replace via API (max 2 attempts)
        ↓
[IF all replacements FAIL] → Auto-refund → Log to error_log
        ↓
[Send WhatsApp] → Proxy credentials + PDF receipt
        ↓
[Update PostgreSQL] → status = 'fulfilled', fulfilled_at = NOW()
```

---

### Workflow 3: Admin Command Handler

**Trigger:** Incoming WhatsApp message from admin number
**Purpose:** Execute admin commands with authentication

```
[WhatsApp Webhook] → [Signature Verify] → [Idempotency] → [Rate Limit]
        ↓
[Check: Is admin number?]
        ↓
[IF admin] → Check session
        ↓
[IF no session] → "Enter PIN"
[IF session expired (>30 min)] → "Session expired. Enter PIN."
[IF active session] → Continue
        ↓
[Parse command] → Determine risk level
        ↓
[IF low risk] → Execute immediately
[IF medium risk] → Require fresh PIN (2 min)
[IF high risk] → Require PIN + TOTP
        ↓
[Execute command] → Log to admin_commands_log
        ↓
[Send WhatsApp] → Result
```

**Risk Levels:**

| Level | Commands | Auth |
|-------|----------|------|
| Low | Pending, Provider Status, Errors, Daily Summary | Session |
| Medium | Block, Unblock, Resolve, Details | Fresh PIN |
| High | Refund, Force-Refund, Approve, Reject | PIN + TOTP |

---

### Workflow 4: Ban Claim

**Trigger:** Customer reports ban/screenshot
**Purpose:** Handle proxy ban replacement requests

```
[Customer sends screenshot]
        ↓
[Save image to R2] → Get URL
        ↓
[Update PostgreSQL] → orders.ban_reported = true, screenshot_url = url
        ↓
[Send to Admin] → "Ban claim for ORD-XXXXX"
        ↓
[Admin reviews] → Approve or Reject
        ↓
[IF approved] → Generate replacement proxy → Send to customer
[IF rejected] → Notify customer + reason
```

---

### Workflow 5: Provider APIs + Health Checks

**Purpose:** Proxy generation, testing, and health monitoring

**Pre-Order Health Check:**
```
[Customer selects product] → [Ping provider API] → [IF down] → "Try again later"
```

**IP Testing:**
```
[Generate proxy] → [Test: curl with 5s timeout]
        ↓
[IF PASS] → Deliver to customer
[IF FAIL] → Replace via API (max 2 attempts)
        ↓
[IF all FAIL] → Auto-refund + log to error_log
```

**Data Fetch (for Data Alert tracking):**
```
[Cron: Every 15 minutes]
        ↓
[For each active DataImpulse order]
  → GET /reseller/order/{id} or /status endpoint
  → Extract: data_used_gb, data_remaining_gb
  → Update PostgreSQL: data_used_gb, data_remaining_gb
  → IF data_remaining_gb changed → Log event
```

**Daily Health Cron:**
```
[Cron: Every 5 minutes]
        ↓
[Ping each provider API]
        ↓
[IF down] → Log to provider_log → [IF 3 consecutive failures] → Alert admin
```

---

### Workflow 6: Refund Handler

**Trigger:** Admin command or Flutterwave refund webhook
**Purpose:** Process refunds

```
[Admin: Refund ORD-XXXXX] → [Verify auth] → [Check eligibility]
        OR
[Flutterwave refund webhook] → [Verify signature] → [Verify idempotency]
        ↓
[IF eligible] → [Call Flutterwave Refund API]
        ↓
[IF success] → [Update PostgreSQL: status = 'refunded'] → [Notify customer]
[IF fail] → [Log error] → [Alert admin]
```

**Eligibility:** No refund after delivery. Exceptions: provider failure, wrong IP, fraud, duplicate charge, admin override.

---

### Workflow 7: Expiry + Data Alert Cron

**Trigger:** Daily cron at 9 AM (Africa/Lagos)
**Purpose:** Notify customers before ISP/DC expires. Data alerts handled by Workflow 14.

```
[Cron: Daily 09:00 Lagos]
        ↓
[Query PostgreSQL] → ISP and DC orders expiring in 3 days + active
        ↓
[For each ISP/DC order]
  → IF expires_at <= NOW + 3 days AND expires_at > NOW
  → Send expiry reminder
        ↓
[Query PostgreSQL] → Mobile orders expiring in 3 days + data remaining > 0
        ↓
[For each Mobile order]
  → IF data_expires <= NOW + 3 days AND data_remaining_gb > 0
  → Send expiry reminder
```

**ISP/DC Reminder:**

| Type | Trigger | Message |
|------|---------|---------|
| Expiry warning | 3 days before | "Your proxy expires in 3 days. Renew to keep [IP]." |

---

### Workflow 8: Free Trial (Opt-In)

**Trigger:** Customer types "free trial" or "give me trial"
**Purpose:** Deliver free proxy after survey completion

```
[Customer asks for free trial]
        ↓
[Check: Free trial offer sent today?]
        ↓
[IF yes] → "You've already received your trial offer today."
[IF no] → Continue
        ↓
[Check: Free trials used today >= 3?]
        ↓
[IF yes] → "Daily limit reached. Try again tomorrow."
[IF no] → Continue
        ↓
[Send disclaimer message]
        ↓
[Customer reads disclaimer] → [Customer replies "Done"]
        ↓
[Show CPAGrip survey link]
        ↓
[Customer completes survey] → [CPAGrip postback]
        ↓
[Verify postback signature]
        ↓
[Check idempotency] → [IF duplicate] → Return 200
        ↓
[Pull from Proxy-Seller or DataImpulse free allocation]
        ↓
[Test proxy] → 5s timeout
        ↓
[IF PASS] → Send proxy to customer + tip + upgrade nudge
[IF FAIL] → "Proxy unavailable. Try again."
        ↓
[Log to free_trials] → increment free_trials_used_today
```

---

### Workflow 9: Free Trial Follow-Up (15-min Idle Cron)

**Trigger:** Cron every 15 minutes
**Purpose:** Offer free trial to idle customers

```
[Cron: Every 15 minutes]
        ↓
[Query PostgreSQL] → Customers with:
  - last_message_at < NOW - 15 minutes
  - No active subscription
  - free_trial_offer_sent_today = false
  - free_trials_used_today < 3
        ↓
[For each customer]
        ↓
[Send free trial offer message]
        ↓
[Update: free_trial_offer_sent_today = true]
```

**Note:** Customer must ASK for free trial before we send proxy. This cron only OFFERS the trial.

---

### Workflow 10: Trial Reset (Daily Midnight)

**Trigger:** Cron at midnight Africa/Lagos
**Purpose:** Reset daily counters

```
[Cron: 00:00 Lagos]
        ↓
[UPDATE customers SET]
  free_trials_used_today = 0,
  free_trial_offer_sent_today = FALSE,
  free_trial_declined_today = FALSE
        ↓
[UPDATE free_trials SET status = 'dead' WHERE status = 'active']
```

---

### Workflow 11: Bunche Logger

**Purpose:** Persistent event logging with PII redaction

```
[Every workflow completion]
        ↓
[Extract: timestamp, request_id, customer_hash, event_type, order_id, workflow, status]
        ↓
[Hash any PII before logging]
        ↓
[Write to customer_audit_log]
```

**PII Redaction:**
```javascript
customer_hash = sha256(phone).substring(0, 20)  // Never log plain phone
ip_hash = sha256(ip).substring(0, 20)         // Never log plain IP
```

**Never log:**
- Plain phone number
- Plain IP address
- Plain names
- PIN or OTP codes
- Proxy credentials
- API keys

---

### Workflow 12: Provider Health Logger

**Trigger:** Cron every 5 minutes
**Purpose:** Track provider uptime and latency

```
[Cron: Every 5 minutes]
        ↓
[For each provider]
  → GET /health or /balance endpoint
  → Measure response time
  → Log to provider_log
        ↓
[IF failure] → Log error
  → [IF 3 consecutive failures] → Alert admin
```

---

### Workflow 13: Daily Summary

**Trigger:** Cron at 23:55 Africa/Lagos
**Purpose:** Aggregate daily metrics

```
[Cron: 23:55 Lagos]
        ↓
[Query PostgreSQL] → Calculate:
  - Total orders today
  - Total revenue today
  - Total errors today
  - Critical errors today
  - Total refunds today
  - New customers today
  - Free trials used today
        ↓
[INSERT INTO daily_summary]
        ↓
[IF errors > 5] → Alert admin
[IF revenue < ₦50,000] → Alert admin
```

---

### Workflow 14: Data Alert Escalation Cron

**Trigger:** Cron every 15 minutes
**Purpose:** Send escalating alerts as data runs low. Only for Residential and Mobile (DataImpulse).

```
[Cron: Every 15 minutes]
        ↓
[Query PostgreSQL] → All active Residential and Mobile orders
        ↓
[For each data order]
  → Fetch latest data_remaining_gb from PostgreSQL
  → Calculate: data_pct = (data_remaining_gb / data_total_gb) × 100
  → Check alert_history for last alert sent at this threshold
        ↓
[IF data_pct <= 20% AND no alert sent at 20%] → Send 20% alert
[IF data_pct <= 10% AND no alert sent at 10%] → Send 10% alert
[IF data_pct <= 5% AND no alert sent at 5%] → Send 5% alert
[IF data_remaining_gb == 0 AND no alert sent at 0%] → Send exhausted alert
        ↓
[Mark alert as sent in alert_history]
```

**Alert Escalation Schedule:**

| Threshold | Trigger | Message Type |
|-----------|---------|--------------|
| **20%** | `remaining_gb <= total_gb × 0.20` | First warning |
| **10%** | `remaining_gb <= total_gb × 0.10` | Second warning |
| **5%** | `remaining_gb <= total_gb × 0.05` | Final warning |
| **0GB** | `remaining_gb == 0` | Exhausted — proxy inactive |

**Each alert is sent only ONCE at each threshold.**

---

## Data Alert System

### Alert Message Templates

**20% — First Warning:**
```
📊 Data Running Low — [Name]

Your [PRODUCT] Proxy:
🔗 IP: [IP]
📦 [X.X]GB of [X]GB used (~[X]% left)
⏰ [Residential: "No expiry date" | Mobile: "Expires [DATE]"]

💡 You're using more data than expected.
Want to top up? Just say "Top up" 📱
```

**10% — Second Warning:**
```
⚠️ Data Running Very Low — [Name]

Your [PRODUCT] Proxy:
🔗 IP: [IP]
📦 Only [X.X]GB remaining (~[X]% left)
⏰ [Mobile: "Expires [DATE]"]

🚨 Time to top up!
Say "Top up" to add more data 📱
```

**5% — Final Warning:**
```
🚨 LAST WARNING — [Name]

Your [PRODUCT] Proxy:
🔗 IP: [IP]
📦 Just [X.X]GB left (~[X]%!)
🔴 Proxy stops when data runs out.

TOP UP NOW — say "Top up" 📱
```

**0GB — Exhausted:**
```
🔴 DATA EXHAUSTED — [Name]

Your [PRODUCT] Proxy:
🔗 IP: [IP]
📦 0GB remaining
⏰ [Mobile: "Expired [DATE]" | Residential: "No expiry"]

🔴 PROXY IS INACTIVE.

Say "Top up" to restore access 📱
```

**Mobile + Expiry Approaching (both at once):**
```
🔴⚠️ DATA LOW + EXPIRY SOON — [Name]

Your Mobile Proxy:
🔗 IP: [IP]
📦 [X.X]GB remaining
⏰ Expires in [X] days

Two problems:
1. Data running low
2. Proxy expires soon

Options:
1️⃣ Top up now — restore access + extend expiry
2️⃣ Wait for expiry — lose unused data

Which? 📱
```

### Top-Up Flow

```
Customer: "Top up"
  ↓
Bunche: "How much data?"

[Mobile options]
  5GB = ₦20,000
  10GB = ₦35,000

[Residential options]
  5GB = ₦5,000
  10GB = ₦9,000

⚠️ Mobile: Any unused GB from current plan will be LOST on top-up!
  ↓
Customer: "5GB"
  ↓
Bunche: "Sending payment link... 💳"
  ↓
Payment confirmed
  ↓
[IF Residential] → Add GB to existing proxy
[IF Mobile] → Add GB to existing proxy + extend to 30 days from today
  ↓
[PDF] → Receipt
  ↓
WhatsApp: "✅ Top up confirmed!

[PRODUCT] Proxy:
🔗 IP: [IP]
📦 [X]GB fresh allocation
⏰ [Mobile: "Expires [NEW DATE]"]

Your proxy is back online! 🔄"
```

### Data Status Check

```
Customer: "Check my data"
  ↓
[IF Residential found]
  → "📊 Your Residential Data

🔗 IP: [IP]
📦 [X.X]GB of [X]GB used
📌 Remaining: [X.X]GB
⏰ No time expiry — lasts until GB runs out"

[IF Mobile found]
  → "📊 Your Mobile Data

🔗 IP: [IP]
📦 [X.X]GB of [X]GB used
📌 Remaining: [X.X]GB
⏰ Expires: [DATE] ([X] days left)"

[IF both]
  → Show both

[IF neither]
  → "You don't have any data proxies yet.
      Want to order one? Reply 'Help' for options."
```

### Data Alert Tracking Table

```sql
CREATE TABLE data_alert_history (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(20) REFERENCES orders(order_id),
    threshold_pct INT,          -- 20, 10, 5, 0
    alert_sent_at TIMESTAMPTZ DEFAULT NOW(),
    message_type VARCHAR(20)     -- 'first_warning', 'second_warning', 'final_warning', 'exhausted'
);

CREATE INDEX idx_alert_history_order ON data_alert_history(order_id);
CREATE INDEX idx_alert_history_threshold ON data_alert_history(order_id, threshold_pct);
```

---

## Security

### Webhook Signature Verification

All webhooks verified before processing:

| Webhook | Verification |
|---------|-------------|
| WhatsApp | HMAC-SHA256 (X-Hub-Signature-256) |
| Flutterwave | HMAC-SHA256 (verif-hash) |
| CPAGrip | HMAC-SHA256 (signature param) |

---

### Rate Limiting (3 Layers)

| Layer | What It Catches |
|-------|----------------|
| Cloudflare | DDoS, bots, mass attacks |
| Nginx | Persistent attackers, per-endpoint limits |
| Redis in n8n | Customer spam, phone-based limits |

---

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
[PostgreSQL — customers, orders, audit logs]
        ↓
[MiniMax M2 API — LLM]
        ↓
[Provider APIs — Proxy-Seller, DataImpulse]
        ↓
[WhatsApp reply]
```

### Database: PostgreSQL

Self-hosted on VPS. Replaces Google Sheets.

**Schema:** See `docs/DATABASE_SCHEMA.md`

### Caching: Redis

| Type | TTL | Purpose |
|------|-----|---------|
| LLM response | 24h | 80% cache hit rate |
| Webhook idempotency | 24h | Prevent duplicates |
| Admin sessions | 30m | Session management |
| Fresh PIN | 2m | Medium-risk auth |
| Rate limits | Sliding | Anti-abuse |

### LLM: MiniMax M2 Cloud

Replaces Ollama. API-compatible with OpenAI.

```
Base URL: https://api.minimax.chat/v1
Model: MiniMax-M2
```

---

## Admin Authentication

### Session Flow

```
Admin sends message
        ↓
[No session] → "🔒 Enter PIN to access admin panel"
        ↓
[Admin enters PIN]
        ↓
[Verify PIN hash]
        ↓
[IF valid] → Create 30-min session → Execute command
[IF invalid] → Increment failed_attempts → Check lockout
        ↓
[IF 3 failed] → Lock for 15 min
[IF 5 failed] → Lock for 1 hour
[IF 10 failed] → Lock for 24 hours
```

### Session Rules

| Rule | Value |
|------|-------|
| Session timeout | 30 minutes inactivity |
| Timer reset | Every successful command |
| High-risk auth | PIN + TOTP (every time) |
| Alerts | Always delivered — admin must PIN to respond |

### TOTP Setup

```
[Admin: setup 2FA]
        ↓
[Generate TOTP secret] → [Encrypt with AES-256-GCM]
        ↓
[Generate QR code] → [Send to admin]
        ↓
[Admin scans + enters code] → [Verify] → [Store encrypted secret]
```

### Command Risk Levels

| Level | Commands | Auth |
|-------|----------|------|
| Low | Pending, Provider Status, Errors, Daily Summary | Active session |
| Medium | Block, Unblock, Resolve, Details | Fresh PIN (2 min) |
| High | Refund, Force-Refund, Approve, Reject | PIN + TOTP |

---

## PII Handling

**Rule: Never store plain PII in logs. Always hash first.**

| Data | How to Store |
|------|-------------|
| Phone | `sha256(phone).substring(0, 20)` |
| IP | `sha256(ip).substring(0, 20)` |
| Name | Do not store in logs |
| PIN | bcrypt hash only |
| TOTP secret | AES-256-GCM encrypted |
| Proxy credentials | Encrypted, never in logs |
| API keys | Environment variables only |

---

## Error Workflow

**Trigger:** Any workflow error
**Purpose:** Alert admin + log for investigation

```
[Workflow error]
        ↓
[Determine severity]
  - critical: payment processed, proxy not delivered
  - high: provider down, webhook failed
  - medium: timeout, rate limit hit
  - low: info, warning
        ↓
[Log to error_log]
        ↓
[IF critical OR high] → [Send WhatsApp to admin]
[IF medium OR low] → Log only
```

---

## Products & Pricing

| Product | Price | Provider | Tracking |
|---------|-------|----------|----------|
| ISP | ₦6,500/mo | Proxy-Seller | Time (expires on date) |
| Premium ISP | ₦7,500/mo | Proxy-Seller | Time |
| DC | ₦3,000/mo | Proxy-Seller | Time |
| Residential 5GB | ₦5,000 | DataImpulse | Data (no time expiry) |
| Residential 10GB | ₦9,000 | DataImpulse | Data |
| Mobile 4G 5GB | ₦20,000 | DataImpulse | Data + 30-day window |
| Mobile 4G 10GB | ₦35,000 | DataImpulse | Data + 30-day window |

**Exchange rate:** ₦1,380/$1

---

## Provider Health Endpoints

| Provider | Health Check | Order Endpoint | Data Status |
|----------|-------------|----------------|-------------|
| Proxy-Seller | GET /balance | POST /api/v1/order/create | N/A (time-based) |
| DataImpulse | GET /account | POST /reseller/order/create | GET /reseller/order/{id} — returns used_gb + remaining_gb |

---

## Admin Commands

| Command | Risk | Description |
|---------|------|-------------|
| Pending | Low | Show pending actions |
| Provider Status | Low | Show provider health |
| Errors | Low | Show recent errors |
| Daily Summary | Low | Show today's metrics |
| Block [phone] [reason] | Medium | Block customer |
| Unblock [phone] | Medium | Unblock customer |
| Resolve ERR-XXXXX | Medium | Mark error resolved |
| Details ORD-XXXXX | Medium | Show order details |
| Refund ORD-XXXXX | High | Process refund |
| Force-Refund ORD-XXXXX | High | Admin override refund |
| Approve ORD-XXXXX | High | Approve replacement |
| Reject ORD-XXXXX | High | Reject claim |
| Admin Status | Low | Show session info |
| Admin Logout | Low | End session |

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
| 8 | Free Trial (Opt-In) | Planned |
| 9 | Free Trial Follow-Up | Planned |
| 10 | Trial Reset | Planned |
| 11 | Bunche Logger | Planned |
| 12 | Provider Health Logger | Planned |
| 13 | Daily Summary | Planned |
| 14 | Data Alert Escalation | Planned |

---

## See Also

- `docs/ARCHITECTURE_PLAN.md` — Full architecture plan
- `docs/SECURITY_PLAN.md` — Security implementation details
- `docs/DATABASE_SCHEMA.md` — PostgreSQL schema
- `legal/TERMS_OF_SERVICE.md` — Legal terms
- `legal/PRIVACY_POLICY.md` — Privacy policy
- `legal/ACCEPTABLE_USE_POLICY.md` — Acceptable use
