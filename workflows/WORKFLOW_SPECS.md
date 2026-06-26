# Bunche — n8n Workflow Specifications
*Zero-inventory, fully on-demand. Ollama + LiteLLM for natural language. No account creation — ever. Admin involved ONLY when human judgment is needed.*

---

## Refund Policy

**⚠️ STRICT: No refunds after proxy is generated and delivered.**

> Once a proxy IP is generated and sent to the customer, the sale is FINAL.
> Refunds are only considered in specific exempt cases listed below.

### Exemptions — Refunds ARE Allowed

| Case | Description | Who Approves |
|------|-------------|--------------|
| **Provider API failure** | Proxy never worked from the start | Admin — automatic |
| **Wrong IP delivered** | Wrong country/spec sent | Admin |
| **Fraudulent order** | Order placed with stolen payment | Admin |
| **Duplicate charge** | Same order charged twice | Admin — automatic |
| **Admin-approved exemption** | Exceptional circumstance | Admin only |

### Non-Exemptions — NO Refund

| Case | Reason |
|------|--------|
| "I changed my mind" | Proxy already generated and usable |
| "Platform banned my IP" | Outside our control — see replacement policy |
| "I don't need it anymore" | Service was delivered |
| "Found cheaper elsewhere" | Not our concern |
| Customer claims it doesn't work | Must prove it never worked from the start |
| Account banned by platform | Platform decision — not a proxy defect |

---

## Renewal Policy

| Proxy Type | Billing | Expiry | Rollover? |
|-----------|---------|--------|-----------|
| **ISP / DC** | Per month (time) | Yes — expiry date | ✅ Same IP kept if renewed before expiry |
| **Mobile** | Per GB (usage) | Yes — 30-day window | ❌ No rollover — fresh GB, old unused LOST |

### ISP / DC — Renewal

| Situation | What Happens | Customer Action Needed? |
|-----------|-------------|------------------------|
| **IP still active** (not expired) | Same IP extended, same credentials | ❌ No — seamless |
| **IP expired** (past expiry date) | NEW proxy generated, NEW credentials | ✅ Yes — update settings |

### Mobile — Renewal

| Situation | What Happens | Data |
|-----------|-------------|------|
| **Data remaining** | Fresh GB allocated — old unused GB LOST | ❌ Rollover: NO |
| **Data exhausted** | Proxy stops working — must top up or wait for expiry | Proxy inactive |
| **Expiry date passed** | New proxy generated — fresh GB allocation | Proxy inactive |

```
⚠️ MOBILE RENEWAL IMPORTANT:
Renewing your mobile proxy = fresh GB allocation.
Any UNUSED GB from your current plan is LOST.

Example:
→ You have 3GB left on your current plan
→ You renew early
→ New 5GB starts — old 3GB is GONE ❌

TIP: Renew AFTER data runs out
or on expiry day to avoid losing data!
```

---

## Mobile Proxy — Data Tracking

**Mobile proxies are tracked by DATA USED, not just time.**

### Google Sheets: Mobile Tracking Columns

| Column | Header | Notes |
|--------|--------|-------|
| Data Total (GB) | number | e.g., 5GB |
| Data Remaining (GB) | number | e.g., 2.3GB |
| Data Unit | text | "GB" |
| Expires At | datetime | 30-day window from purchase |

### Mobile Status Values

| Status | Meaning |
|--------|---------|
| `active` | Data remaining, proxy working ✅ |
| `data_low` | ≤1GB remaining, proxy working ⚠️ |
| `data_exhausted` | 0GB, proxy inactive ❌ |
| `expired` | Past expiry date |

---

## Reminder System

### ISP / DC — Time-Based Reminder

```
Daily cron checks:
  ↓
  [IF ISP or DC proxy]
    → Check: Expires At ≤ 7 days?
      → YES: Send expiry reminder with ALL proxies + RANDOM IP TIP
      → NO: Do nothing
```

### Mobile — Dual Reminder (Data + Time)

```
Daily cron checks:
  ↓
  [IF Mobile proxy]
    → Check: Data Remaining ≤ 1GB?
      → YES: Send data warning
    → Check: Data Remaining == 0GB?
      → YES: Send data exhausted + inactive notice
    → Check: Expires At ≤ 3 days AND Data Remaining > 0?
      → YES: Send expiry reminder
```

### Reminder Message Templates

**ISP/DC — Expiry reminder:**
```
👋 Hey [Name]!

Your proxies are expiring soon!

[ALL ISP/DC proxies with ≤7 days — NO LIMIT]

💡 TIP: Renew before expiry to keep
the same IP!

Want to renew? Just say "Renew" 🔄
```

**Mobile — Data warning (≤1GB):**
```
📊 Data Alert — [Name]

Your Mobile Proxy:
🔗 IP: 5.6.7.8
📦 [X]GB remaining | Expires: [DATE]

⚠️ Running low on data!

{RANDOM IP TIP}

Top up now — say "Top up mobile" 📱
```

**Mobile — Data exhausted (0GB):**
```
⚠️ DATA EXHAUSTED — [Name]

Your Mobile Proxy:
🔗 IP: 5.6.7.8
📦 0GB remaining
⏰ Expires in [X] days

🔴 Your proxy is currently INACTIVE.

Top up now to restore access!
Say "Top up mobile" 📱
```

**Mobile — Data exhausted AND expiry approaching:**
```
⚠️ DATA EXHAUSTED + EXPIRY WARNING — [Name]

Your Mobile Proxy:
🔗 IP: 5.6.7.8
📦 0GB remaining
⏰ Expires in 3 days

🔴 Proxy is INACTIVE.

Two options:
1️⃣ Top up now — restore access for [X] days
2️⃣ Wait for expiry — renew with fresh GB

Which do you prefer? 📱
```

---

## Mobile Top-Up Flow

```
Customer: "Top up mobile"
  ↓
Bunche: Check customer has mobile proxy
  ↓
Bunche: "How much data do you want to add?

         5GB = ₦20,000
         10GB = ₦35,000
         
         ⚠️ Note: Any unused GB from
         your current plan will be lost
         when you top up!"
  ↓
Customer: "5GB"
  ↓
Bunche: "Sending payment link... 💳"

Payment confirmed
  ↓
Provider API: Add 5GB to existing order
  ↓
Google Sheets Update: Data Remaining = 5GB (new allocation)
  ↓
WhatsApp: "✅ Top up confirmed!

🔗 IP: 5.6.7.8
📦 5GB fresh allocation
⏰ Expires: [NEW DATE]

Your proxy is back online! 🔄

{RANDOM IP TIP}"
```

---

## Expiry Date Normalization (ISP/DC)

All ISP or DC proxies from the same order share the SAME expiry date (normalized at fulfillment).

---

## Random IP Tips Pool

**Rotate randomly — pick 1 per message. No repeat until all used.**

```
💡 DID YOU KNOW?

🌐 ISP proxies use real home/office IP
addresses — they look like a regular
internet user to websites and platforms.

📱 Mobile proxies use real 4G/5G
networks. They rotate through thousands
of real mobile carrier IPs.

🏢 Datacenter IPs come from servers —
fast and cheap, but some platforms
spot them more easily.

🔄 Residential proxies bounce your
traffic through real home devices.
Hardest to detect!

🕐 ISP proxies stay stable longer
than mobile proxies. Good for long
sessions.

🌍 Different countries have different
IP reputations. US and UK IPs are
among the most trusted globally.

📺 Some streaming platforms check
IP addresses against GPS data from
your phone — ISP proxies pass this.

💰 High-trust IPs (US/UK) cost more
because they're less likely to be
flagged by platforms.

🔒 Using a proxy hides your real
IP from websites — they only see
the proxy IP.

📡 Proxy speed depends on location.
A UK proxy in Nigeria is slower
than a Nigerian proxy. Choose wisely!

⚡ Datacenter proxies are fastest —
great for automation and bots.
But ISP proxies blend in better.

🌐 ISP = Internet Service Provider.
These are the IPs you get at home.
Most platforms trust them instantly.

🔁 Mobile proxies rotate IPs as you
use them — harder to track, great
for managing multiple accounts.

🏴󠁧󠁢󠁿󠁧󠁢󠁿 Your IP can reveal your
approximate location. A proxy hides
that from websites.

🎯 One IP per platform = cleaner
account history. Mixing platforms
on one IP can link your accounts.
```

---

## Legal Notice

**New customers only** — displayed once when a new phone number first messages Bunche.

```
👋 Welcome to Bunche!

📄 By using Bunche, you agree to our
   Terms of Service, Privacy Policy,
   and Acceptable Use Policy.
   
   bunche.com/terms | bunche.com/privacy | bunche.com/aup

━━━━━━━━━━━━━━━━━━
PRICES:
🇬🇧🇺🇸🇩🇪 ISP proxies — ₦6,500/mo
🌏 JP, AU, BR, SG, KR — ₦7,500/mo
🌐 Residential 5GB — ₦5,000
📱 Mobile 4G 5GB — ₦20,000
💻 Datacenter — ₦2,500/mo
━━━━━━━━━━━━━━━━━━

💡 Mobile proxies are per GB —
30-day window. Unused GB does not
roll over on renewal.

{RANDOM IP TIP}

TO ORDER: Reply with:
"Order ISP [country] [qty]"

TYPE "help" for support.
```

---

## System Architecture

```
Customer WhatsApp Message
        ↓
[SECURITY LAYER] — Strip links, files, jailbreak attempts
        ↓
[CHECK: New customer?] → YES → Show legal notice first
                       → NO  → Skip legal notice
        ↓
[LLM PARSING] — Ollama via LiteLLM → structured order intent
        ↓
[CHECK: Is this an admin command?] → YES → Route to Admin Workflow
        ↓
[CHECK: Is this routine or exception?] → ROUTINE → n8n handles automatically
                                          → EXCEPTION → Route to Admin Workflow
        ↓
[IF MOBILE] → Data tracking enabled
[IF ISP/DC] → Time-based tracking enabled
        ↓
Provider API → Proxy credentials
        ↓
[EXPIRY NORMALIZATION] — ISP/DC: same order → same Expires At
        ↓
PDF receipt generated
        ↓
WhatsApp delivery + RANDOM IP TIP
```

---

## The Core Principle

| What happens | Who does it |
|-------------|------------|
| New customer → legal notice + mobile warning + IP tip | n8n ✅ |
| Mobile proxy → data tracking + data warnings | n8n ✅ |
| ISP/DC proxy → time-based expiry tracking | n8n ✅ |
| Returning customer ordering | n8n fully automated ✅ |
| Lost proxy details | n8n sends all — ISP/DC + Mobile ✅ |
| Renewal (ISP/DC — IP active) | Same IP extended ✅ |
| Renewal (ISP/DC — IP expired) | New proxy generated ✅ |
| Renewal (Mobile) | Fresh GB, old unused LOST ⚠️ |
| Top up (Mobile) | Add GB, reactivate proxy ✅ |
| Data warning (Mobile ≤1GB) | n8n sends warning ✅ |
| Data exhausted (Mobile 0GB) | n8n sends inactive notice ✅ |
| Expiry reminder (ISP/DC ≤7 days) | n8n sends reminder ✅ |
| Reminder shows ALL proxies | NO LIMIT ✅ |
| Expiry date normalization (ISP/DC) | Same order → same Expires At ✅ |
| Refund request (proxy not yet sent) | n8n auto-approves ✅ |
| Refund request (proxy already sent) | n8n declines → admin ⚠️ |
| Ban claim with screenshot | Admin review ⚠️ |
| Admin commands | Admin handles ⚠️ |

---

## Admin WhatsApp Interface

| Command | What it does |
|---------|-------------|
| `Admin` | Show all pending actions |
| `Approve ORD-XXXXX` | Approve replacement/refund |
| `Reject ORD-XXXXX [reason]` | Reject with reason |
| `Block [phone] [reason]` | Block customer |
| `Unblock [phone]` | Unblock customer |
| `Details ORD-XXXXX` | Full order details (data used, remaining for mobile) |
| `Refund ORD-XXXXX` | Initiate refund (exemption only) |
| `Force-Refund ORD-XXXXX` | Admin override |
| `Pending` | List all pending actions |

---

## Workflow 1: Order Handler (WhatsApp Incoming)

```
Webhook Trigger (WhatsApp POST)
  ↓
Edit Fields: Extract from, msg_body, msg_id, timestamp
  ↓
[SECURITY LAYER] — Strip links, files, injection
  ↓
[CHECK: Is admin number?] → YES → Admin Workflow
  ↓
[CHECK: Existing customer?] → YES → Workflow 1a
                           → NO  → Legal notice → Workflow 1b
```

### Workflow 1a: Returning Customer

```
intent == "order":
  → Google Sheets Read: Lookup price
  → HTTP Request → Flutterwave POST /payments
  → Google Sheets Append: Pending_Orders (awaiting_payment)
  → WhatsApp: "Payment link sent. ₦[price]"

intent == "lost proxy details":
  → Google Sheets Read: Get ALL proxies — ISP/DC + Mobile — NO LIMIT
  → WhatsApp: Send all proxy details + RANDOM IP TIP

intent == "my proxies" OR "check data":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → For Mobile: Show data remaining + expiry date
  → For ISP/DC: Show expiry date
  → WhatsApp: All proxies + status + RANDOM IP TIP

intent == "check expiry" OR "days left":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Show all with days until expiry (ISP/DC) or data remaining (Mobile)

intent == "ban reported" OR "ip blocked":
  → Was order within 24hrs?
    → YES: "Send screenshot of ban message." → Save → ban_pending_review → [ADMIN ALERT]
    → NO: "Replacement only within 24hrs."

intent == "refund":
  → Status == "awaiting_payment": Cancel, refund
  → Status == "fulfilled": "No refund after delivery."

intent == "help":
  → Send help menu + mobile data warning + RANDOM IP TIP

intent == "renew":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Present all with expiry/data status
  → Customer selects which to renew
  ↓
  [IF ISP/DC — IP active]: Extend same IP (+30 days)
  [IF ISP/DC — IP expired]: Generate NEW proxy
  [IF Mobile]: Fresh GB allocation, old unused LOST
  → WhatsApp: Confirmation + renewal warning (mobile) + RANDOM IP TIP

intent == "top up mobile" OR "buy more data":
  → Google Sheets Read: Find mobile proxy for customer
  → Present top-up options (5GB / 10GB)
  → "⚠️ Unused GB will be lost on top-up!"
  → Generate payment link
  → Payment confirmed → Add GB to existing order → Proxy reactivated
  → WhatsApp: "Top up confirmed!" + RANDOM IP TIP

intent == "how to use" OR "setup proxy" OR "configure":
  → Send proxy setup guide + RANDOM IP TIP

Default:
  → LLM reply
```

### Workflow 1b: New Customer

```
intent == "order":
  → Price check → Flutterwave payment link
  → WhatsApp: "Payment link sent."
  → Log consent (first interaction)

intent == "help":
  → Legal notice + mobile data warning + RANDOM IP TIP + help menu

intent == "lost proxy details":
  → WhatsApp: "Enter PIN or OTP"
    → PIN verify / OTP verify
      → Match: Send details + RANDOM IP TIP
      → Fail 3x: [ADMIN ALERT]

Default:
  → LLM reply
```

### Legal Notice (First Message Only)

```
👋 Welcome to Bunche!

📄 By using Bunche, you agree to our
   Terms of Service, Privacy Policy,
   and Acceptable Use Policy.
   
   bunche.com/terms | bunche.com/privacy | bunche.com/aup

━━━━━━━━━━━━━━━━━━
PRICES:
🇬🇧🇺🇸🇩🇪 ISP proxies — ₦6,500/mo
🌏 JP, AU, BR, SG, KR — ₦7,500/mo
🌐 Residential 5GB — ₦5,000
📱 Mobile 4G 5GB — ₦20,000
💻 Datacenter — ₦2,500/mo
━━━━━━━━━━━━━━━━━━

💡 Mobile proxies are per GB —
30-day window. Unused GB does not
roll over on renewal.

{RANDOM IP TIP}

TO ORDER: Reply with:
"Order ISP [country] [qty]"

TYPE "help" for support.
```

### Proxy Setup Guide (On Request) + RANDOM IP TIP

```
🔧 How to use your ISP Proxy:

📱 PHONE: Settings → Search "VPN" → Add VPN → Enter details
💻 DESKTOP: Browser network proxy settings or extension

🔧 How to use your Mobile Proxy:

📱 Same as ISP — Settings → VPN → Add VPN → Enter details
💻 Works on desktop too — same setup

━━━━━━━━━━━━━━━━━━
💡 IP TIPS — READ THIS:
━━━━━━━━━━━━━━━━━━

✅ One IP per device or per account.
   Risky to share 1 IP across many
   devices.

✅ Use different IPs for different
   platforms (UK IP for one platform,
   US IP for another).

🔄 ISP/DC: Renew BEFORE expiry to
   keep the same IP.

📱 Mobile: Renew AFTER data runs out
   or on expiry — unused GB does NOT
   roll over!

{RANDOM IP TIP}
```

---

## Workflow 2: Payment Confirmation (Flutterwave Webhook)

```
Webhook Trigger (Flutterwave POST)
  ↓
Verify Flutterwave-Signature
  ↓
IF event !== "charge.completed" OR status !== "successful":
  → Respond 200 "ignored"
  ↓
Edit Fields: Extract tx_ref, amount, phone, meta
  ↓
Google Sheets: Find order by tx_ref
  ↓
IF Status !== "awaiting_payment":
  → Respond 200 "already processed"
  ↓
Google Sheets Update: Status = "paid_pending_fulfillment"
  ↓
Google Sheets: Check if customer exists
  ↓
[IF NEW CUSTOMER — First purchase]
  → Recovery setup: PIN or OTP → Store name → Log consent
  ↓
[IF NEW ORDER (not renewal)]
  → Provider API → Proxy credentials
  → IF fails → Try backup provider → All fail: Refund → [ADMIN ALERT]
  ↓
  [IF ISP or DC]:
    → [EXPIRY NORMALIZATION] — All → same Expires At
    → Google Sheets: Data Total = "unlimited", Data Remaining = "N/A"
    → Google Sheets Update: Status = "fulfilled"
    → [PDF] → WhatsApp: Details + Receipt + RANDOM IP TIP
  ↓
  [IF MOBILE]:
    → Google Sheets: Data Total = [X]GB, Data Remaining = [X]GB, Expires At = today + 30 days
    → Google Sheets Update: Status = "active"
    → [PDF] → WhatsApp: Details + Receipt + mobile data warning + RANDOM IP TIP
  ↓
[IF ISP/DC RENEWAL — IP active]:
  → Extend Expires At +30 days from today
  → Google Sheets Update: Status = "fulfilled"
  → [PDF] → WhatsApp: "Extended! Same IP." + RANDOM IP TIP
  ↓
[IF ISP/DC RENEWAL — IP expired]:
  → Generate NEW proxy
  → WhatsApp: "New proxy ready! Update settings." + RANDOM IP TIP
  → [PDF] → Receipt
  ↓
[IF MOBILE TOP-UP]:
  → Provider API: Add GB to existing order
  → Google Sheets Update: Data Remaining = [NEW GB], Expires At = today + 30 days
  → WhatsApp: "Top up confirmed! Proxy reactivated." + RANDOM IP TIP
  → [PDF] → Receipt
  ↓
WhatsApp: "⚠️ No refunds once delivered. Replacement within 24hrs if banned."
  ↓
Respond HTTP 200
```

### Mobile Delivery Message

```
🎉 Mobile Proxy Ready! 📱

━━━━━━━━━━━━━━━━━━
🔗 IP: [IP]
Port: [port]
Username: [user]
Password: [pass]
━━━━━━━━━━━━━━━━━━
📦 Data: [X]GB total
⏰ Expires: [DATE] (30 days)
━━━━━━━━━━━━━━━━━━

💡 IMPORTANT — MOBILE DATA:
→ Data is per GB — use it or lose it
→ 30-day window to use your data
→ Unused GB does NOT roll over on renewal
→ Renew AFTER data runs out to avoid losing it!

🔴 If your data runs to 0GB before
expiry — proxy stops working!

{RANDOM IP TIP}

📄 Receipt: [PDF ATTACHED]

⚠️ No refunds once delivered.
Replacement within 24hrs if banned.
```

### Recovery Setup Messages (First Purchase Only)

```
✅ Payment confirmed!

Before your proxy is delivered,
set up quick security for your next visit:

1️⃣ PIN — Set a 4-digit PIN
2️⃣ OTP — Get code via WhatsApp

Reply "1" or "2" 👇
```

**If PIN chosen:** "Reply with your 4-digit PIN 👇"
**If OTP chosen:** "Got it! Code will be sent when needed. ✅"
**Name:** "What should we call you? 👇"

---

## Workflow 3: Admin Command Handler

```
[CHECK: Is admin number?] → NO → Workflow 1
  ↓
Parse command:
"Pending" → List all pending actions
"Approve ORD-XXXXX" → Route: ban → replace proxy; refund → refund
"Reject ORD-XXXXX [reason]" → Reject, notify customer
"Block [phone] [reason]" → Block in Google Sheets
"Unblock [phone]" → Unblock
"Details ORD-XXXXX" → Full summary (includes data used/remaining for mobile)
"Refund ORD-XXXXX" → Check status → refund or warn
"Force-Refund ORD-XXXXX" → Admin override, log as exemption
Default → "Unknown command. Type 'Pending'."
```

---

## Workflow 4: Ban Claim with Screenshot

```
Customer: "My IP was banned"
  ↓
Was order within 24hrs?
  → NO: "Replacement only within 24hrs."
  → YES: "Send screenshot of ban message."
    → Save → ban_pending_review
    → [ADMIN ALERT] → Admin approves/rejects
```

---

## Workflow 5: Provider APIs

### Proxy-Seller API (ISP + DC)

```
POST https://api.proxy-seller.com/v1/orders
Body: {"type": "isp", "country": "gb", "quantity": 1, "period": 30}
Response: {"order_id": "PS-12345", "status": "active", "proxies": [...]}
```

### OkeyProxy API (Residential)

```
POST https://api.okeyproxy.com/v1/order
Body: {"type": "residential", "country": "global", "traffic": "5GB"}
```

### DataImpulse API (Mobile)

```
POST https://api.dataimpulse.com/v1/order
Body: {"type": "mobile", "country": "us", "traffic": "5GB"}
Response: {"order_id": "DI-12345", "status": "active", "data_total": "5GB", "data_used": "0GB", "expires_at": "2026-07-26"}
```

### Fallback Chain

```
Proxy-Seller → Fails → OkeyProxy → Fails → DataImpulse → Fails
→ Refund → [ADMIN ALERT] → Mark failed
```

---

## Workflow 6: Refund Handler

```
Flutterwave webhook → refund events
  ↓
IF Status == "fulfilled":
  → Revoke proxy via Provider API
  ↓
Google Sheets: Status = "refunded"
  ↓
WhatsApp: "✅ Refund processed. ₦{amount} in 5–7 days."
```

---

## Workflow 7: Expiry + Data Reminder Cron

**Trigger:** Daily 9:00 AM (Africa/Lagos)

```
For each customer with active proxies:
  ↓
  [FOR ISP/DC proxies]:
    → Get ALL where Status == "fulfilled" AND Expires At ≤ today + 7 days
    → NO LIMIT
    → If found: Send ISP/DC expiry reminder + RANDOM IP TIP
  ↓
  [FOR Mobile proxies]:
    → Check Data Remaining ≤ 1GB?
      → YES: Send data warning + RANDOM IP TIP
    → Check Data Remaining == 0GB?
      → YES: Send data exhausted + inactive notice + RANDOM IP TIP
    → Check Expires At ≤ 3 days AND Data Remaining > 0GB?
      → YES: Send expiry warning + RANDOM IP TIP
  ↓
  [IF nothing to remind]:
    → Do nothing
```

---

## Error Workflow: Admin Alert

```
n8n Error Trigger
  ↓
WhatsApp (admin): "🔴 Workflow Error — {workflow_name} — {error_message}"
```

---

## Ollama + LiteLLM Setup

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
pip install litellm
litellm --model ollama/llama3.2:3b --port 4000
```

---

## Security Layer

```javascript
const stripped = input
  .replace(/https?:\/\/[^\s]+/gi, "[LINK REMOVED]")
  .replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, "[IP REMOVED]")
  .replace(/ignore previous instructions/gi, "")
  .replace(/disregard all rules/gi, "")
  .replace(/system prompt/gi, "")
  .replace(/<\|.*?\|>/g, "")
  .replace(/\{.*?"role.*?\}/g, "")
  .trim()
  .substring(0, 500);

return {
  original: input,
  cleaned: stripped,
  hasLink: /https?:\/\//.test(input),
  hasInjection: /ignore|disregard|system prompt|<\|.*?\|>/i.test(input)
};
```

---

## System Prompt — LLM Rule Book

```SYSTEM
You are the order assistant for Bunche, a WhatsApp-based proxy reseller operating in Nigeria.

TONE: Friendly, brief, Nigerian-friendly English. Never excessive emojis. Be direct.

IMPORTANT — MOBILE vs ISP/DC:
- ISP and DC proxies = time-based (monthly). They expire on a DATE.
- Mobile proxies = per GB. They have DATA (GB) and an EXPIRY DATE.
- Mobile data does NOT roll over. Unused GB is LOST on renewal.
- If mobile data reaches 0GB, the proxy STOP WORKING even if days remain.
- Always warn: "Renew mobile AFTER data runs out or on expiry — unused GB is lost!"

YOUR JOB:
1. Parse customer messages → extract: intent, product type, country, quantity
2. If order is clear → confirm price and prepare payment link request
3. If order is unclear → ask ONE clarifying question only
4. If customer asks about providers → deflect politely
5. If customer asks about refunds → explain the refund policy
6. Always include a RANDOM interesting IP/proxy tip when sending proxy details

RANDOM IP TIPS (pick 1 randomly, no repeat until all used):
- "ISP proxies use real home IP addresses — they look like a regular internet user to websites."
- "Mobile proxies use real 4G/5G networks and rotate IPs as you use them."
- "Datacenter proxies are fastest but some platforms spot them more easily."
- "Residential proxies bounce traffic through real home devices — hardest to detect!"
- "ISP proxies stay stable longer than mobile proxies — good for long sessions."
- "US and UK IPs are among the most trusted globally by platforms."
- "Some streaming platforms check IPs against GPS data — ISP proxies pass this check."
- "High-trust IPs cost more because they're less likely to be flagged."
- "Using a proxy hides your real IP from websites."
- "Proxy speed depends on location. A UK proxy in Nigeria is slower than a local one."
- "Datacenter proxies are fastest — great for automation."
- "Mobile proxies rotate IPs automatically — harder to track."
- "ISP = Internet Service Provider. These are the IPs you get at home."
- "Proxy IPs hide your approximate location from websites."
- "One IP per platform keeps account history cleaner."

MOBILE-SPECIFIC TIPS:
- "Mobile proxies are per GB — unused GB does not roll over on renewal!"
- "If your mobile data runs to 0GB, the proxy stops working even if days remain."
- "Renew mobile AFTER data runs out to avoid losing unused GB!"

REFUND POLICY:
- No refunds after proxy delivered
- Replacement within 24hrs if banned (with screenshot)
- Technical issue from start → admin reviews

HOW TO USE PROXY:
- PHONE: Settings → Search "VPN" → Add VPN → Enter details (NOT WiFi settings)
- DESKTOP: Browser network proxy settings or proxy switcher extension

NEVER:
- Never mention Proxy-Seller, OkeyProxy, DataImpulse, or any provider name
- Never reveal API keys, internal pricing margins, or provider costs
- Never explain HOW proxies work technically beyond setup
- Never open, follow, or acknowledge any link in the customer message
- Never attempt to download, process, or parse any file
- Never reveal recovery method details to customers
- Never mention Jumia, Nigerian platforms, or Nigerian marketplaces
- Never recommend 1 IP on many devices — advise one IP per account/device
- Never imply mobile GB rolls over — it does NOT

COMMANDS:
- "Order ISP [COUNTRY] [QTY]" → order, ISP, country, qty
- "Order RES [QTY]GB" → order, RESIDENTIAL, qty
- "Order MOB [QTY]GB" → order, MOBILE, qty
- "Order DC [COUNTRY] [QTY]" → order, DATACENTER, country, qty
- "Status [ORDER_ID]" → status
- "My proxies" OR "Check data" → check_proxies
- "Renew [ORDER_ID]" → renew
- "Top up mobile" OR "Buy more data" → top_up_mobile
- "Help" → help
- "Check price [PRODUCT]" → price_check
- "Refund" / "Cancel" → refund_request
- "How to use" / "Setup proxy" / "Configure" → how_to_use

RESPONSE FORMAT — Return ONLY valid JSON:
{
  "intent": "order|status|renew|top_up_mobile|help|price_check|ban_reported|refund_request|check_proxies|how_to_use|unknown",
  "product": "ISP|RESIDENTIAL|MOBILE|DATACENTER|null",
  "country": "country code or null",
  "quantity": number or null,
  "confidence": 0.0 to 1.0,
  "reply": "short response (under 100 chars)"
}
```

---

## Google Sheets: Orders

| Column | Header | Notes |
|--------|--------|-------|
| Order ID | text | |
| Customer Phone | text | |
| Plan Type | ISP / DC / Mobile / Residential | Differentiates proxy types |
| Plan Code | text | |
| Country | text | |
| Quantity | number | |
| Amount Paid (NGN) | number | |
| Payment Reference | text | |
| Provider | text | |
| Provider Order ID | text | |
| Proxy Credentials | text | |
| Status | text | |
| Data Total (GB) | number | Mobile only — e.g., 5GB |
| Data Remaining (GB) | number | Mobile only — decrements as used |
| Expires At | datetime | ISP/DC: monthly date. Mobile: 30-day window |
| Ban Reported | boolean | |
| Screenshot URL | text | |
| Ban Verified | admin_review_pending / verified / rejected | |
| Replacement Count | number | |
| Refund Requested | boolean | |
| Notes | text | |
| Created At | datetime | |
| Fulfilled At | datetime | |
| Cost (USD) | number | |

**Status Values:**
`awaiting_payment` | `paid_pending_fulfillment` | `fulfilled` | `data_low` | `data_exhausted` | `ban_pending_review` | `replaced` | `failed` | `refund_pending` | `refunded` | `rejected` | `cancelled` | `expired`

**Mobile Status Logic:**
- `data_low` → Data Remaining ≤ 1GB
- `data_exhausted` → Data Remaining == 0GB
- `expired` → Past expiry date

---

## Google Sheets: Customers

| Column | Header |
|--------|--------|
| Phone | text (primary key) |
| Name | text |
| Recovery Method | PIN or OTP |
| PIN Hash | text (bcrypt) |
| Total Orders | number |
| Lifetime Value (NGN) | number |
| Replacement Count | number |
| Last Order At | datetime |
| Support Notes | text |
| Blocked | boolean |
| Blocked Reason | text |
| Consent Given | boolean |
| Consent Version | text |
| Consent At | datetime |
| Created At | datetime |

---

## Security Checklist

| Rule | Enforced Where |
|------|---------------|
| No URLs in customer messages | Security Stripper |
| No links opened by LLM | System prompt + n8n pre-check |
| No file downloads | System prompt + n8n pre-check |
| No provider names revealed | System prompt (LLM) |
| No injection prompts processed | Security Stripper + system prompt |
| LLM output validated as JSON | n8n validation node |
| LLM cannot execute actions | n8n acts on structured output only |
| Message length limited to 500 chars | Security Stripper |
| PIN stored hashed | bcrypt hash in Google Sheets |
| OTP expires in 5 minutes | Timestamp checked |
| Max 3 verification attempts | Counted before admin escalation |
| Admin only on exception | Admin Workflow triggered only on exception |
| No refund after delivery | Workflow enforces — admin override only |
| Legal notice only on first interaction | Workflow checks new vs returning |
| Mobile: No GB rollover on renewal | Explicit warning in every mobile message |
| Mobile: Data exhaustion tracked | data_low / data_exhausted statuses |
| Mobile: Proxy stops at 0GB | Workflow handles as inactive |
| Expiry date normalization (ISP/DC) | Same order → same Expires At |
| Reminder shows ALL proxies | NO LIMIT |
| Random IP tips | Rotate — 1 per message, no repeat until all used |
| No Nigerian platforms | Never mention Jumia, Nigerian marketplaces |

---

## Workflow Activation Checklist

| Workflow | Trigger | When |
|----------|---------|------|
| Order Handler | WhatsApp Webhook | Always |
| Payment Confirmation | Flutterwave Webhook | On payment |
| Admin Command Handler | WhatsApp Webhook (admin number) | On admin message |
| Ban Claim | WhatsApp Webhook (within Order Handler) | On ban claim |
| Refund Handler | Flutterwave Webhook | On refund event |
| Expiry + Data Reminder | Cron — daily 9:00 AM | Every day |
| Error Alert | n8n Error Trigger | On any error |

---

## Testing

```bash
# New customer — legal notice + mobile warning
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t1","from":"2349000000001","timestamp":"123","text":{"body":"Hi"}}]}}]}]}'

# Mobile order — shows data warning
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t2","from":"2349000000001","timestamp":"123","text":{"body":"Order mobile 5GB"}}]}}]}]}'

# Check proxies — shows data remaining for mobile
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t3","from":"2349000000001","timestamp":"123","text":{"body":"My proxies"}}]}}]}]}'

# Top up mobile
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t4","from":"2349000000001","timestamp":"123","text":{"body":"Top up mobile"}}]}}]}]}'
```
