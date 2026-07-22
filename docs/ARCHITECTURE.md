# Styxproxy — Technical Architecture

**Last Updated:** 2026-07-01

---

## Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                          CUSTOMER                                 │
│                                                                  │
│   ┌────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│   │  styxproxy.com │   │  Telegram   │   │     WhatsApp        │   │
│   │  (Instant) │   │    Bot      │   │       Bot           │   │
│   └─────┬──────┘   └──────┬──────┘   └──────────┬──────────┘   │
│         │                  │                     │               │
│         │ Payment          │ Chat                 │ Chat         │
│         ▼                  ▼                     ▼               │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │                   FLUTTERWAVE                             │   │
│   │              (Payment Processing)                          │   │
│   └──────────────────────────┬───────────────────────────────┘   │
│                              │                                    │
│                    Payment Webhook                                │
│                              │                                    │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     NEW STYXPROXY VPS                               │
│                                                                  │
│   Port 80/443 (nginx reverse proxy)                              │
│                               │                                   │
│         ┌─────────────────────┼───────────────────────┐         │
│         │                     │                       │         │
│         ▼                     ▼                       ▼         │
│   ┌────────────┐       ┌──────────┐           ┌───────────┐     │
│   │   Website   │       │ Backend  │           │    n8n    │     │
│   │  (styxproxy.com)│       │   API   │           │(workflows)│     │
│   │   Static    │       │ :8080    │           │  :5678    │     │
│   └────────────┘       └────┬─────┘           └─────┬─────┘     │
│                              │                       │            │
│                              │  PostgreSQL :5432      │            │
│                              │  ┌─────────────────┐   │            │
│                              └──│  PostgreSQL     │───┘            │
│                                 │  bunche         │                 │
│                                 │  (all data)     │                 │
│                                 └─────────────────┘                 │
│                              │                                    │
│                              │  3proxy :8001–8100                │
│                              │  ┌─────────────────┐               │
│                              └──│  3proxy         │               │
│                                 │  (trial proxies)│               │
│                                 └─────────────────┘               │
└──────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Proxy-Seller │     │ DataImpulse  │     │ Theorem Reach│
│   (IPs)      │     │  (backup)   │     │  (surveys)   │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## Components

### 1. Website (styxproxy.com — Instant)

**Stack:** Static HTML/CSS/JS or Next.js (to be decided)
**Host:** New Styxproxy VPS
**SSL:** Let's Encrypt via certbot

**Pages:**

| Route | Purpose |
|---|---|
| `/` | Landing + product listing |
| `/order/<product>` | Checkout → Flutterwave |
| `/thank-you?tx_ref=` | Payment confirmation + IP display |
| `/manage` | Order management portal |
| `/manage/<tx_ref>` | Specific order details |
| `/terms` | Legal |
| `/privacy` | Legal |
| `/aup` | Legal |
| `/refund` | Legal |

**No backend on the website** — website calls the Backend API for:
- Creating payment invoices
- Checking order status
- Generating renewal links

---

### 2. Backend API

**Stack:** Python 3.11+ + FastAPI + Uvicorn + Pydantic + asyncpg
**Host:** New Styxproxy VPS (port 8080)
**Process manager:** Uvicorn (via PM2 or supervisor)
**Port exposed:** Via nginx reverse proxy on 443
**Async queue:** Redis + background tasks (FastAPI BackgroundTasks or Celery)

**Base URL:** `https://api.styxproxy.com`

**CRITICAL: n8n is NOT in the Instant (website) path.**

The website talks ONLY to the backend API. n8n is completely out of the path for website orders.

```
WEBSITE ORDER PATH (Instant):
Flutterwave → webhook to backend API → IP generated → DB updated
                         ↑
                         │
                   Website polls /order/:tx_ref → shows IP
                   (no n8n involved at all)

n8n IS involved ONLY in:
- Telegram chat orders (Telegram → n8n → backend)
- WhatsApp chat orders (WhatsApp → n8n → backend)
- Admin alert notifications (backend → n8n → admin Telegram/WhatsApp)
- Theorem Reach postbacks (Theorem Reach → backend → n8n records survey)
```

**Endpoints:**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/invoice/create` | Create Flutterwave invoice → return payment link |
| `POST` | `/webhook/flutterwave` | Receive Flutterwave payment → generate IP |
| `GET` | `/order/:tx_ref` | Get order status + IP |
| `POST` | `/order/:tx_ref/renew` | Create renewal invoice |
| `POST` | `/order/:tx_ref/complain` | Log ban complaint → return support links |
| `POST` | `/webhook/theorem-reach` | Receive survey postback |
| `POST` | `/webhook/telegram` | Telegram webhook (→ n8n) |
| `POST` | `/webhook/whatsapp` | WhatsApp webhook (→ n8n) |

**Security:**
- Flutterwave webhook: HMAC verification
- Telegram webhook: bot token verification
- WhatsApp webhook: verify token
- All endpoints: rate limiting (SlowAPI)
- CORS: restricted to styxproxy.com + admin.styxproxy.com domains
- Pydantic validation on all request bodies

### 3. PostgreSQL Database

**Host:** New Styxproxy VPS
**Port:** 5432
**Connection:** localhost only (no external access)

**Tables:**

| Table | Purpose |
|---|---|
| `instant_orders` | Anonymous website orders |
| `platform_accounts` | Telegram + WhatsApp customer accounts |
| `customers` | Unified customer profile (after merge) |
| `orders` | Chat-based orders |
| `bunche_credentials` | Styxproxy username → provider IP mapping |
| `free_trials` | Free trial sessions |
| `pending_trial_surveys` | Theorem Reach postbacks |
| `merge_requests` | Channel linking requests |
| `customer_audit_log` | Immutable audit trail |
| `error_log` | System errors |
| `provider_log` | Proxy provider API calls |
| `processed_webhooks` | Idempotency storage |
| `admin_auth` | Admin login |
| `admin_commands_log` | Admin command history |
| `rate_limit_log` | Rate limit tracking |
| `webhook_security_log` | Webhook verification failures |
| `daily_summary` | Daily metrics |
| `provider_log` | Provider health + costs |

---

### 4. Dante (Paid Proxy Auth Layer)

**Host:** New Styxproxy VPS
**Port:** 1080 (SOCKS5)
**Purpose:** Authenticate paid customers and route to upstream provider IPs

Dante is the SOCKS5 server that customers connect to. Customer provides their Styxproxy username + password. Dante verifies against the credentials table, then routes the connection through to the upstream provider IP.

```
Customer connects: proxy1.styxproxy.com:1080
  username: bun_001 / password: XxX
         │
         ▼
  Dante SOCKS5 Server
         │
  Looks up bun_001 → maps to upstream provider IP
         │
  Routes traffic to provider proxy
         │
  Response returned to customer
```

**Scripts:**
- `manage-bunche-credentials.sh add <username> <password>` → add to Dante userfile + SIGHUP
- `manage-bunche-credentials.sh revoke <username>` → remove from Dante userfile + SIGHUP

**Dante credential format:** `username:$apr1$<hash>` (apache2-utils htpasswd format)

**Security:** Bind Dante to Cloudflare IP ranges only. Never expose the upstream provider IPs directly to customers.

### 5. 3proxy (Free Trial Proxies)

**Host:** New Styxproxy VPS
**Ports:** 8001–8100 (100 concurrent trial proxies)
**Config:** `/etc/3proxy/bunche-trial.cfg`
**PID:** `/var/run/3proxy-bunche.pid`

3proxy handles free trial proxies separately from Dante. Each trial customer gets a port in the 8001–8100 range with their own username/password.

**How it works:**
- Trial credentials (user/pass) added to config when customer earns trial
- 3proxy authenticates trial users against this config
- Traffic routed through upstream (Proxy-Seller or DataImpulse)
- `cleanup-3proxy-trials.sh` runs every 5 minutes → removes expired trials

**Scripts:**

```bash
# Add trial user
manage-3proxy-trial.sh add <username> <password> <port>

# Remove trial user
manage-3proxy-trial.sh remove <username>

# List active
manage-3proxy-trial.sh list

# Count active
manage-3proxy-trial.sh count
```

---

### 5. n8n (Workflow Automation)

**Host:** Current VPS (84.247.132.12)
**Port:** 5678 (behind nginx, accessible via cloudflared tunnel)
**Database:** SQLite (n8n's own data) + PostgreSQL (Styxproxy data)

**Telegram webhook flow:**
```
Telegram → cloudflared tunnel → n8n :5678
                            (n8n workflows handle everything)
```

**WhatsApp webhook flow:**
```
WhatsApp Cloud API → POST https://api.styxproxy.com/webhook/whatsapp
                           ↓
                    nginx reverse proxy
                           ↓
                    n8n :5678
```

**Workflows:**

| Workflow | Trigger | Purpose |
|---|---|---|
| `telegram-order.json` | Telegram message | New order via chat |
| `telegram-free-trial.json` | Telegram message | Free trial via chat |
| `free-trial.json` | WhatsApp message | Free trial via WhatsApp |
| `order-handler.json` | WhatsApp message | New order via WhatsApp |
| `payment-confirmation.json` | Flutterwave webhook | Process payment |
| `ban-claim.json` | Telegram/WhatsApp message | Ban complaint |
| `refund-handler.json` | Telegram/WhatsApp message | Refund request |
| `admin-handler.json` | Telegram/WhatsApp message | Admin commands |
| `error-alert.json` | Error event | Admin notification |
| `channel-failover.json` | System event | Channel redundancy |
| `theorem-reach-webhook.json` | Theorem Reach postback | Record survey |

---

## Data Flow Diagrams

### Instant (Website) Order Flow

```
1. Customer selects product on styxproxy.com
   → POST /invoice/create { product, country }
   (backend API creates record, calls Flutterwave → returns payment link)

2. Customer redirected to Flutterwave Checkout
   → Pays with card/bank/ussd
   → Flutterwave redirects to /thank-you?tx_ref=TXF-xxx

3. Flutterwave sends webhook to /webhook/flutterwave
   → HMAC verify ✓
   → Idempotency check ✓
   → Mark instant_orders.status = 'paid'
   → Call Proxy-Seller API → generate IP (async background task)
   → Update instant_orders: ip, port, username, status='fulfilled'

4. Customer's /thank-you page polls GET /order/:tx_ref
   → Returns { status, ip, port, username, password }
   → Page displays credentials immediately

n8n is NOT involved in this flow.
```

### Chat Order Flow (Telegram/WhatsApp)

```
1. Customer messages bot: "I want ISP UK"
   → Telegram/WhatsApp webhook → n8n workflow

2. n8n workflow:
   → Check if existing customer
   → POST /invoice/create { product } via backend API
   → Generate Flutterwave payment link
   → Send link in chat

3. Customer pays via Flutterwave link
   → Flutterwave webhook → backend API (n8n NOT in path)

4. n8n workflow receives order update via polling or trigger:
   → Generate IP via backend API
   → Send credentials in chat
   → Capture name + offer PIN
   → Fulfill order

n8n orchestrates the chat flow. Backend API handles payment and IP generation.
```

### Free Trial Flow

```
1. Customer: "free trial" on Telegram/WhatsApp
   → n8n workflow sends trial explanation + Theorem Reach link

2. Customer completes survey on Theorem Reach
   → Theorem Reach postback → /webhook/theorem-reach
   → Backend records in pending_trial_surveys
   → n8n workflow notified of new postback

3. Customer says "done" (12 surveys max)
   → n8n workflow:
     → Count surveys in pending_trial_surveys
     → Calculate time: surveys × 2hr (max 24hr)
     → POST /trial/create via backend API
     → Backend calls manage-3proxy-trial.sh add
     → Send credentials in chat
     → Create free_trials record

4. Every 5 minutes:
   → cleanup-3proxy-trials.sh checks expiry
   → Removes expired users from 3proxy config
   → Marks free_trials.status = 'expired'
```

---

## Security Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────┐
│  nginx (SSL termination)             │
│  - HTTPS only                       │
│  - Rate limiting                    │
│  - Gzip compression                 │
└──────────┬──────────────────────────┘
           │
    ┌──────┴───────┐
    │              │
    ▼              ▼
/webhook/*    /api/*
    │              │
    ▼              ▼
Backend API  Static Website
    │              │
    ▼              │
PostgreSQL        │
    │              │
    ▼              │
Proxy-Seller     │
DataImpulse       │
3proxy            │
```

**Critical security rules (enforced in every build decision):**
- Frontend (website) = display only. Zero business logic. Zero database access.
- All sensitive operations happen in the backend API — never in the browser
- API keys never in frontend code, never in environment variables accessible to the frontend
- Backend API: secrets in environment variables on the server only
- PostgreSQL: localhost only, no external access
- All webhooks: HMAC or token verification before any processing
- Rate limiting: every public endpoint
- No secrets in logs, no secrets in error messages

**Frontend security boundary:**
```
Website (browser)                  Backend API (server)
━━━━━━━━━━━━━━━━━━                 ━━━━━━━━━━━━━━━━━━━━
❌ No API keys                    ✅ All API keys
❌ No database access             ✅ PostgreSQL
❌ No payment processing          ✅ Flutterwave SDK
❌ No credential generation       ✅ Proxy-Seller SDK
❌ No webhook handling            ✅ Webhook handlers
✅ Can call /invoice/create       ❌ Cannot see server-side env
✅ Can call /order/:tx_ref       ❌ Cannot see DB credentials
✅ Can display IP + credentials   ❌ Cannot generate credentials
```

**Firewall rules (UFW):**
- Port 22: SSH (your IP only — use fail2ban)
- Port 80: HTTP (Let's Encrypt only)
- Port 443: HTTPS (world)
- All other ports: blocked

**No ports exposed to public except 80/443.**

---

## Environment Variables Reference

```bash
# ======================
# Backend API (.env)
# ======================

NODE_ENV=production
PORT=8080
DOMAIN=https://styxproxy.com
API_BASE=https://api.styxproxy.com

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bunche
POSTGRES_USER=bunche
POSTGRES_PASSWORD=<strong-password>

# Redis (async queue)
REDIS_URL=redis://localhost:6379

# Flutterwave
FLUTTERWAVE_PUBLIC_KEY=FLWPUBK-xxxx
FLUTTERWAVE_SECRET_KEY=FLWSECK-xxxx
FLUTTERWAVE_WEBHOOK_SECRET=<32-char-random>

# Proxy Providers
PROXY_SELLER_API_KEY=xxx
PROXY_SELLER_API_URL=https://api.proxy-seller.com
DATAIMPULSE_API_KEY=xxx
DATAIMPULSE_API_URL=https://api.dataimpulse.com

# Email (Resend)
RESEND_API_KEY=re_xxxx
EMAIL_FROM=bunche@styxproxy.com

# 3proxy
THREEPROXY_CONFIG_PATH=/etc/3proxy/bunche-trial.cfg
THREEPROXY_PID_PATH=/var/run/3proxy-bunche.pid
TRIAL_PORT_START=8001
TRIAL_PORT_END=8100

# Theorem Reach
THEOREM_REACH_API_KEY=xxx
THEOREM_REACH_WEBHOOK_SECRET=<random>

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## Directory Structure (New Styxproxy VPS)

```
/root/
├── bunche-api/               # Backend API (Python + FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Environment variables + Pydantic settings
│   │   ├── database.py        # asyncpg connection pool
│   │   ├── models/            # Pydantic models (request/response shapes)
│   │   │   ├── __init__.py
│   │   │   ├── invoice.py
│   │   │   ├── order.py
│   │   │   └── webhook.py
│   │   ├── routes/            # FastAPI routers
│   │   │   ├── __init__.py
│   │   │   ├── invoice.py     # POST /invoice/create
│   │   │   ├── order.py       # GET /order/:tx_ref, renew, complain
│   │   │   └── webhook.py     # POST /webhook/flutterwave, /theorem-reach
│   │   ├── services/          # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── flutterwave.py # Invoice creation, HMAC verification
│   │   │   ├── proxy_provider.py # Proxy-Seller / DataImpulse calls
│   │   │   ├── email.py      # Resend transactional email
│   │   │   └── trial.py      # 3proxy trial management
│   │   └── middleware/       # Rate limiting, CORS, error handling
│   │       ├── __init__.py
│   │       └── rate_limit.py
│   ├── venv/                  # Python virtual environment
│   ├── requirements.txt
│   └── ecosystem.config.js     # PM2 config (uvicorn)
│
├── bunche-website/           # Static website (HTML/CSS/JS)
│   ├── index.html
│   ├── thankyou.html
│   ├── manage.html
│   ├── css/
│   ├── js/
│   └── assets/
│
├── scripts/
│   ├── manage-bunche-credentials.sh  # Dante (paid proxy) credentials
│   ├── manage-3proxy-trial.sh        # 3proxy (free trial) credentials
│   └── cleanup-3proxy-trials.sh      # Expire old trial proxies
│
├── /etc/3proxy/
│   └── bunche-trial.cfg      # 3proxy config
│
├── /var/run/
│   └── 3proxy-bunche.pid
│
└── /var/log/
    └── bunche-trial-cleanup.log
```

---

## Deployment Checklist

Before going live:

- [ ] SSL certificate active on styxproxy.com + api.styxproxy.com
- [ ] PostgreSQL schema created + indexes
- [ ] Backend API running via PM2 + auto-restart enabled
- [ ] nginx reverse proxy configured
- [ ] Flutterwave webhook verified (test payment)
- [ ] Telegram bot webhook set
- [ ] WhatsApp Cloud API webhook verified
- [ ] Theorem Reach postback URL configured
- [ ] 3proxy installed + running + test user added
- [ ] Email sending verified (Resend test)
- [ ] All legal pages live
- [ ] Management portal accessible
- [ ] Thank-you page IP display tested
