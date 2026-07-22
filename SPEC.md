# Styxproxy — Product SPEC
**Last Updated:** 2026-07-01
**Status:** Planning — Ready for Build

---

## The Three Channels

| Channel | Type | Purpose |
|---|---|---|
| **Instant** | Website (styxproxy.com) | Primary order path — anonymous, pay → get IP |
| **Telegram** | Chat bot | Support + ordering + free trial |
| **WhatsApp** | Chat bot | Support + ordering + free trial |

Customers choose. All three work independently — no linking required for any channel to function.

---

## Channel 1: Instant (Website — Primary Acquisition)

**Principle:** Zero friction. No registration. No data collection. Pay → get IP.

**Architecture rule (enforced):** Frontend is display only. Zero business logic in the website. Every action — invoice creation, IP generation, order status, renewals, complaints — goes through the backend API. The website never touches payment processing, credential generation, or database directly.

### Flow

```
Customer → styxproxy.com → Select product + country
    ↓
    Select payment method (Flutterwave Checkout)
    ↓
    Flutterwave generates tx_ref (= order number)
    ↓
    Customer completes payment
    ↓
    Flutterwave webhook → backend
    ↓
    IP generated → displayed on screen
    ↓
    "Thank you" page shows IP + order number
    ↓
    Email receipt sent (optional, just IP + order number)
```

**What Styxproxy stores:**
- `tx_ref` (Flutterwave's transaction reference = order number)
- Product purchased
- Amount paid
- IP generated
- Timestamp

**What Styxproxy does NOT store:**
- Customer name
- Customer email (unless they enter it for receipt)
- Customer phone
- Customer IP address
- Any identifying data

### Management Portal

Customer goes to `styxproxy.com/manage` or `styxproxy.com/order/<tx_ref>`:

- **Check status** — enter tx_ref → see order details
- **Renew** — select new product → new Flutterwave payment → new IP
- **Complain (ban claim)** — enter tx_ref + screenshot → redirects to Telegram or WhatsApp of their choice

```
Complain flow:
  "How would you like to reach us?"
  → Telegram → opens Telegram chat with pre-filled message: "Ban claim for order [tx_ref]"
  → WhatsApp → opens WhatsApp chat with pre-filled message: "Ban claim for order [tx_ref]"
```

### Products on Website

| Product | Price |
|---|---|
| ISP UK | ₦6,500/mo |
| ISP US | ₦6,500/mo |
| ISP DE | ₦7,500/mo |
| ISP Japan | ₦7,500/mo |
| Datacenter | ₦2,500/mo |
| Residential 5GB | ₦5,000 |
| Residential 10GB | ₦9,000 |
| Mobile 4G 5GB | ₦20,000 |
| Mobile 4G 10GB | ₦35,000 |

---

## Channel 2 & 3: Telegram + WhatsApp

**Principle:** Full customer lifecycle. No anonymous ordering — chat requires identity (chat ID for Telegram, phone hash for WhatsApp).

### Capabilities (identical on both)

| Capability | Details |
|---|---|
| **Order** | Product → payment link → Flutterwave → IP delivered via chat |
| **Free Trial** | Survey-based accumulation → credentials delivered via chat |
| **Check Status** | By order ID |
| **Renew** | By order ID |
| **Ban Claim** | By order ID + screenshot |
| **Support** | Any question |
| **Account Recovery** | Phone hash (WhatsApp) / chat ID (Telegram) |

### Free Trial Flow (Telegram & WhatsApp only)

```
Customer → "I want free trial" / "free trial"
    ↓
    Styxproxy explains: complete surveys → earn time
    ↓
    Customer does surveys on Theorem Reach
    ↓
    Theorem Reach postback → Styxproxy webhook (records survey)
    ↓
    Survey count × 2hr = total trial time (max 24hr)
    ↓
    Customer says "done"
    ↓
    Trial credentials delivered via chat
    ↓
    Trial runs → auto-expires after earned time
```

**Rules:**
- 1 survey = 2 hours of trial
- Max 12 surveys = 24 hours
- Credentials sent once, after customer says "done"
- No daily limit
- No per-survey credential delivery

### How Chat Identity Works

**Telegram:**
- Customer identified by chat_id
- No phone number required
- Customer can use @username or anonymous
- Styxproxy stores: chat_id, username (if set), name (if shared)

**WhatsApp:**
- Customer identified by phone number hash
- Phone number required to have WhatsApp account
- Styxproxy stores: phone hash (not actual number), display name (if shared)

**No linking required** — Telegram and WhatsApp operate independently.
- Customer can use both without linking
- Linking is optional (for customers who want unified history)
- Either channel can fulfill an order independently

---

## Channel Priority

| Priority | Channel | Reason |
|---|---|---|
| **1st** | Instant (Website) | Fastest, most anonymous, no chat friction |
| **2nd** | Telegram | Free, anonymous-friendly, no phone required |
| **3rd** | WhatsApp | Widely used in Nigeria, phone required |

---

## The Management Portal

URL: `styxproxy.com/manage` or `styxproxy.com/order/<tx_ref>`

**Entry:** Order number (tx_ref from Flutterwave)

**Capabilities:**

| Action | Flow |
|---|---|
| Check status | Enter tx_ref → order details shown |
| Renew | Select product → Flutterwave payment → new IP |
| Complain / Ban claim | Enter tx_ref + upload screenshot → choose Telegram or WhatsApp → opens chat with pre-filled message |
| Contact support | Enter tx_ref → choose Telegram or WhatsApp → opens chat |

**No login. No password. Just order number.**

---

## Admin Dashboard

All admin operations move from Telegram to a dedicated web dashboard at `admin.styxproxy.com`.

**Telegram is no longer used for admin commands.** All admin staff log in via web only.

| Role | What they can do |
|---|---|
| **Admin** | View orders, issue refunds, process ban claims, view own credentials, view own audit actions |
| **SuperAdmin** | Everything Admin + create/delete admins, view all audit logs, view provider costs, change system settings |

**Login:** email + password + TOTP (6-digit code from authenticator app)

**All actions logged** to `admin_commands_log` — immutable, no DELETE allowed.

---

## What Stays the Same

- Flutterwave for all payments
- Proxy-Seller / DataImpulse for IP generation
- 3proxy for trial proxies (ports 8001–8100)
- Theorem Reach for free trial surveys
- PostgreSQL for all data storage

---

## Database Schema

Schema from `docs/DATABASE_SCHEMA.md` is unchanged. All three channels write to the same tables.

New table needed for Instant:

```sql
-- Instant orders (anonymous, no customer record)
CREATE TABLE instant_orders (
    tx_ref VARCHAR(100) PRIMARY KEY,  -- Flutterwave tx_ref = order number
    
    product VARCHAR(50) NOT NULL,
    country VARCHAR(10),
    amount_ngn DECIMAL(12,2),
    
    -- IP delivered
    ip_address INET,
    port INT,
    username VARCHAR(50),
    password_hash TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, paid, fulfilled, expired, refunded
    
    -- Payment
    flutterwave_payment_id VARCHAR(100),
    paid_at TIMESTAMPTZ,
    
    -- Optional receipt email
    receipt_email VARCHAR(200),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    fulfilled_at TIMESTAMPTZ
);

CREATE INDEX idx_instant_tx_ref ON instant_orders(tx_ref);
CREATE INDEX idx_instant_status ON instant_orders(status);
```

---

## Technical Architecture

```
                    Flutterwave Webhook
                           ↓
                    ┌──────────────┐
                    │  Backend API │
                    │  (Python +   │
                    │   FastAPI)   │
                    └──────┬───────┘
                           ↓
            ┌──────────────┼──────────────┐
            ↓              ↓              ↓
      Proxy-Seller    DataImpulse      3proxy
            ↓              ↓              ↓
      IP generated   IP generated   Trial proxies
            ↓              ↓              ↓
      Instant order  Instant order  Free trial
```

**Backend API responsibilities:**
- Receive Flutterwave webhooks → generate IP → store in instant_orders
- Receive Theorem Reach webhooks → record in pending_trial_surveys
- Expose management portal endpoints (check status, renew, complain redirect)
- All Styxproxy workflows run via n8n calling this backend

---

## Scale Target

**10,000 concurrent customers at launch.**

The architecture must handle 10,000 simultaneous active sessions, order processing, and webhook events without degradation.

Implications for the build:
- Stateless backend (no session state in memory — all in PostgreSQL)
- Connection pooling (PostgreSQL pool, Redis for ephemeral state if needed)
- Asynchronous processing (webhook → job queue → IP generation, not synchronous)
- CDN for all static assets
- Rate limiting at every public endpoint
- Database read replicas if needed at scale

## What NOT in This Spec

- **Email marketing** — no email collection except optional receipt
- **User accounts** — no login, no registration, no password
- **Referral system** — on Instant, there's no one to credit. Chat ordering keeps referrals.
- **Free trial on website** — trial is chat-only (Theorem Reach requires postback URL)
- **WhatsApp link from website** — Instant customers are anonymous. Support contact is opt-in via management portal.

---

## Order of Build

1. **Backend API** — Flutterwave webhook → IP generation → instant_orders table
2. **Instant website** — product pages → Flutterwave Checkout → thank-you page with IP
3. **Management portal** — styxproxy.com/manage
4. **Admin dashboard** — admin.styxproxy.com (SuperAdmin + Admin roles)
5. **Telegram bot** — full ordering + support (via n8n)
6. **WhatsApp bot** — full ordering + support (via n8n)
7. **Free trial** — Telegram + WhatsApp (after bots are working)
8. **Account linking** — optional (for customers who want unified history)

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend API | **Python 3.11+ + FastAPI** | Async by default, Pydantic validation, scale to 10k |
| Database | **PostgreSQL** | All Styxproxy data |
| Async queue | **Redis** | Background job processing for webhooks |
| Process manager | **Uvicorn** | ASGI server for FastAPI |
| Paid proxy auth | **Dante SOCKS5** | Customer connects to Dante → routed to upstream provider IP |
| Trial proxy auth | **3proxy** | Free trial proxies on ports 8001–8100 |
| Payments | **Flutterwave** | Naira payments |
| Email | **Resend** | Transactional emails |
| Website | **Static HTML/CSS/JS** | Display only, zero business logic |
| n8n | (existing) | Workflow automation |

**Rule:** Frontend (website) = display only. All business logic in FastAPI backend.

---

*This spec is the source of truth. Update this document before changing any workflow, channel, or product decision.*
