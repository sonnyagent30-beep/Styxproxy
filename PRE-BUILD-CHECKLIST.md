# Bunche — Pre-Build Checklist

**Purpose:** Everything that must be in place before writing the first line of code.
**Updated:** 2026-07-01

---

## Non-Negotiable Build Requirements

These are not preferences — they are enforced in every build decision:

| Requirement | Reason |
|---|---|
| **Frontend = display only** | Zero business logic in website. All operations go through backend API. |
| **10,000 concurrent customers** | Scale target at launch. Architecture must handle it. |
| **Stateless backend** | No in-memory session state. All state in PostgreSQL. |
| **Async webhook processing** | Webhooks queue work, not process synchronously. |
| **No secrets in frontend** | API keys, DB credentials never touch browser code. |
| **All webhooks verified** | HMAC on Flutterwave, token on Theorem Reach, before any processing. |

**Tech stack confirmed:**
- **Python + FastAPI** — async by default, Pydantic validation, same language as n8n scripts

---

## Phase 1: Accounts & Credentials

These are the real blockers. Nothing can be built or tested without them.

| # | What | Purpose | Link |
|---|---|---|---|
| 1 | Flutterwave merchant account | Accept payments in Naira | [dashboard.flutterwave.com](https://dashboard.flutterwave.com) |
| 2 | Flutterwave public + secret API keys | Webhook verification, transfers | Flutterwave Dashboard → Settings → API Keys |
| 3 | Telegram Bot token (@BotFather) | Telegram bot | [t.me/BotFather](https://t.me/BotFather) |
| 4 | WhatsApp Business API (Meta) | WhatsApp bot | [business.whatsapp.com](https://business.whatsapp.com) |
| 5 | WhatsApp Business Account ID | WhatsApp bot | Meta Business Dashboard |
| 6 | WhatsApp phone number (dedicated) | WhatsApp bot | Meta Business Dashboard |
| 7 | Theorem Reach account | Free trial survey tracking | [theoremreach.com](https://theoremreach.com) |
| 8 | Theorem Reach API key | Postback webhook | Theorem Reach dashboard |
| 9 | Proxy-Seller account | IP generation | Already have |
| 10 | DataImpulse account | Backup IP source | [dataimpulse.com](https://dataimpulse.com) |
| 11 | Cloudflare account | Tunnel for webhooks | [dash.cloudflare.com](https://dash.cloudflare.com) |
| 12 | Domain: styxproxy.com | Website + portal | Register at any registrar |
| 13 | Resend account (or SendGrid) | Transactional email | [resend.com](https://resend.com) |
| 14 | Resend API key | Send IP via email | Resend dashboard |

---

## Phase 2: VPS Setup (New Bunche VPS)

Buy VPS → install → configure. Do this before writing any backend code.

### Hardware Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disk | 50 GB SSD | 100 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Software to Install (in order)

```bash
# 1. System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git unzip ufw fail2ban certbot python3-certbot-nginx

# 2. PostgreSQL
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 3. Python 3.11+ (FastAPI requires 3.9+)
sudo apt install -y python3.11 python3.11-venv python3-pip
python3.11 --version  # confirm 3.11+

# 4. Redis (for async job queue)
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis

# 5. PM2 for process management
sudo npm install -g pm2  # or use supervisor for Python

# 6. Dante (SOCKS5 for paid proxies)
sudo apt install dante-server
sudo systemctl enable danted
# Verify
danted --version

# 7. 3proxy (for free trial proxies)
sudo apt install -y build-essential
cd /tmp
git clone https://github.com/3proxy/3proxy.git
cd 3proxy
make -f Makefile.Linux
sudo cp src/3proxy /usr/local/bin/
sudo cp scripts/rc.d/init.d.3proxy /etc/init.d/3proxy
sudo chmod 755 /etc/init.d/3proxy

# 8. nginx
sudo apt install -y nginx
sudo systemctl enable nginx
```

**Python project setup:**
```bash
cd /root/styxproxy-api
python3.11 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn[standard] pydantic python-dotenv
pip install asyncpg httpx slowapi
pip install psycopg2-binary  # sync fallback
pip install python-jose[cryptography]  # JWT if needed
```

### VPS Firewall (UFW)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh      # port 22
sudo ufw allow 80       # HTTP (Let's Encrypt)
sudo ufw allow 443      # HTTPS
sudo ufw allow 8080     # Backend API (nginx → backend)
sudo ufw enable
```

### DNS

Point `styxproxy.com` and `api.styxproxy.com` A records to the new VPS IP.

| Hostname | Points to |
|---|---|
| styxproxy.com | New VPS IP |
| api.styxproxy.com | New VPS IP |
| www.styxproxy.com | New VPS IP |

---

## Phase 3: Backend API Setup

### Environment Variables

Create `/root/styxproxy-api/.env`:

```bash
# Bunche Backend API
NODE_ENV=production
PORT=8080
DOMAIN=https://styxproxy.com

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bunche
POSTGRES_USER=bunche
POSTGRES_PASSWORD=<generate strong password>

# Flutterwave
FLUTTERWAVE_PUBLIC_KEY=<from Flutterwave dashboard>
FLUTTERWAVE_SECRET_KEY=<from Flutterwave dashboard>
FLUTTERWAVE_WEBHOOK_SECRET=<random 32-char string>

# Proxy Providers
PROXY_SELLER_API_KEY=<from Proxy-Seller>
PROXY_SELLER_API_URL=https://api.proxy-seller.com
DATAIMPULSE_API_KEY=<from DataImpulse>
DATAIMPULSE_API_URL=https://api.dataimpulse.com

# Email (Resend)
RESEND_API_KEY=<from Resend dashboard>
EMAIL_FROM=bunche@styxproxy.com

# 3proxy Management
THREEPROXY_CONFIG_PATH=/etc/3proxy/bunche-trial.cfg
THREEPROXY_PID_PATH=/var/run/3proxy-bunche.pid
TRIAL_PORT_START=8001
TRIAL_PORT_END=8100

# Theorem Reach
THEOREM_REACH_API_KEY=<from Theorem Reach>
THEOREM_REACH_WEBHOOK_SECRET=<random 32-char string>
```

### Start Backend

```bash
cd /root/styxproxy-api
npm install
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # enables auto-restart on reboot
```

---

## Phase 4: SSL Certificate

```bash
sudo certbot --nginx -d styxproxy.com -d www.styxproxy.com -d api.styxproxy.com
# Follow prompts — choose "Redirect" when asked
# Cert auto-renews after this
```

---

## Phase 5: n8n Setup (on Current VPS or New VPS?)

**Decision needed:** Should n8n live on the current VPS (84.247.132.12) or move to the new Bunche VPS?

| Option | Pros | Cons |
|---|---|---|
| Keep on current VPS | Already running, already has workflows | Telegram webhook needs tunnel to reach it |
| Move to new VPS | Everything in one place | Migration effort |

**Recommendation:** Keep on current VPS for now. n8n is working. Focus on building the new VPS infrastructure first.

### n8n Credentials to Wire (when ready)

| Credential | Where to get |
|---|---|
| PostgreSQL | Connect n8n to Bunche PostgreSQL on new VPS |
| Telegram Bot API | Use bot token from @BotFather |
| WhatsApp Business API | Use credentials from Meta |
| Theorem Reach | API key from Theorem Reach dashboard |

### Telegram Webhook Setup

```bash
# Set webhook on new VPS (or use cloudflared tunnel)
# Option A: Cloudflare Tunnel (no domain needed)
cloudflared tunnel --url http://localhost:5678
# Note the tunnel URL, use it as Telegram webhook URL

# Option B: Self-hosted tunnel with domain
# Set api.styxproxy.com → :5678 in nginx, then:
curl -F "url=https://api.styxproxy.com/telegram/webhook" \
     -H "Authorization: Bot <TELEGRAM_BOT_TOKEN>" \
     https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook
```

---

## Phase 6: Flutterwave Dashboard Configuration

### 1. Get API Keys

```
Flutterwave Dashboard → Settings → API Keys
Copy: Public Key (starts with FLW...)
Copy: Secret Key (starts with FLW...)
```

### 2. Set Webhook URL

```
Flutterwave Dashboard → Settings → Webhooks
Add URL: https://api.styxproxy.com/webhook/flutterwave
Events to listen for:
  ✓ payment.completed
  ✓ payment.failed
  ✓ transfer.completed
```

### 3. Generate HMAC Key for Webhook Verification

```
Flutterwave Dashboard → Settings → Webhooks
Click "Generate HMAC Key"
Copy the key → set as FLUTTERWAVE_WEBHOOK_SECRET in .env
```

### 4. Test Webhook Locally (during development)

```bash
# Use Flutterwave's test webhook tool
# Dashboard → Developers → Testing → Webhook Testing
```

---

## Phase 7: Telegram Bot Setup

### 1. Create Bot via @BotFather

```
Open: t.me/BotFather
Send: /newbot
Follow prompts → copy bot token
```

### 2. Configure Bot

```
BotFather → /setname → Bunche Support
BotFather → /setdescription → Your Bunche proxy assistant
BotFather → /setabouttext → Get ISP, datacenter, residential & mobile proxies
BotFather → /setcommands → Add: start, order, trial, help, manage
```

### 3. Get Chat ID (for testing)

```
Open your bot → send /start
Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
Copy: "chat": {"id": <YOUR_CHAT_ID>
```

### 4. Set Webhook

```
# Using cloudflared tunnel URL from Phase 5
curl -F "url=<CLOUDFLARED_TUNNEL_URL>/telegram/webhook" \
     -H "Authorization: Bot <BOT_TOKEN>" \
     https://api.telegram.org/bot<BOT_TOKEN>/setWebhook

# Verify
curl https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo
```

---

## Phase 8: WhatsApp Business API Setup

### This is the Most Complex Setup

WhatsApp Business API requires:
1. Meta Business account
2. WhatsApp Business app
3. Dedicated phone number (not used on regular WhatsApp)
4. Meta Business verification

**Step-by-step:**

```
1. Go to: developers.facebook.com
2. Create app → select "Business" type
3. Add "WhatsApp Messenger" product
4. Get: WhatsApp Business Account ID (starts with WABa...)
5. Get: Phone number ID (from WhatsApp → API Setup)
6. Get: Temporary access token (valid 24h, needs renewal)

# Set up webhook:
Meta Business Dashboard → WhatsApp → Configuration
Webhook URL: https://api.styxproxy.com/webhook/whatsapp
Verify Token: <random string you choose>
```

**Important:** WhatsApp Cloud API vs WhatsApp Business API (On-Premises)
- **Cloud API** (Meta's hosted) — easier setup, subscription-based pricing
- **On-Premises API** — self-hosted, more control, requires VPS

**Recommendation for Bunche:** WhatsApp Cloud API (simpler, no VPS needed for WhatsApp).

---

## Phase 9: Theorem Reach Setup

```
1. Create account at theoremreach.com
2. Get API Key from dashboard
3. Configure postback URL:
   https://api.styxproxy.com/webhook/theorem-reach

4. Postback parameters to expect:
   - sid (survey ID)
   - uid (user ID / unique identifier)
   - tid (transaction ID)
   - payout (amount earned)
   - event_type (survey_complete)

5. Set webhook secret in .env: THEOREM_REACH_WEBHOOK_SECRET
```

---

## Phase 10: Legal Pages (must be live before launch)

These must exist at launch:

| URL | What |
|---|---|
| styxproxy.com/terms | Terms of Service |
| styxproxy.com/privacy | Privacy Policy |
| styxproxy.com/aup | Acceptable Use Policy |
| styxproxy.com/refund | Refund Policy |

Templates exist in `docs/legal/` — review with a lawyer before publishing.

---

## Phase 11: Push All n8n Workflows to n8n

When n8n credentials are wired, import all workflows from `.n8n/workflows/`:

```
n8n → Settings → Import from JSON
Import each workflow in order:
1. admin-handler.json
2. ban-claim.json
3. channel-failover.json
4. error-alert.json
5. free-trial.json
6. order-handler.json
7. payment-confirmation.json
8. refund-handler.json
9. telegram-free-trial.json
10. telegram-order.json
11. theorem-reach-webhook.json
```

---

## Summary: What to Buy / Register First

Before writing any code, you need to buy/register these:

| Priority | What | Cost |
|---|---|---|
| 🔴 1 | Flutterwave merchant account | Free |
| 🔴 2 | Telegram Bot token | Free |
| 🟡 3 | WhatsApp Business API | Free to set up, usage costs |
| 🟡 4 | styxproxy.com domain | ~₦3,000–5,000/yr |
| 🟡 5 | Theorem Reach account | Free |
| 🟡 6 | Resend account | Free tier (100 emails/day) |
| 🟢 7 | New VPS | ~$10–20/month |
| 🟢 8 | DataImpulse account | Pay-as-you-go |

---

*Update this document as you complete each phase. Check off items as you go.*
