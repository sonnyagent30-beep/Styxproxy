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

| Situation | What Happens | Customer Action Needed? |
|-----------|-------------|------------------------|
| **IP still active** (not expired) | Same IP extended, same credentials | ❌ No — seamless |
| **IP expired** (past expiry date) | NEW proxy generated, NEW credentials | ✅ Yes — update settings |

---

## Reminder System

**Automated expiry reminders — 3 days before expiry:**

```
Bunche → Customer (WhatsApp):

👋 Hey [Name]!

Your proxies are expiring soon!

[ALL proxies with expiry in ≤7 days — NO LIMIT]

{RANDOM IP TIP}

Want to renew? Just say "Renew" and
I'll set it up — same IPs, no changes! 🔄
```

---

## Expiry Date Normalization

All proxies from the same order share the SAME expiry date (normalized at fulfillment).

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

🏴󠁧󠁢󠁿󠁧󠁢󠁿󠁧󠁢󠁿 Your IP can reveal your
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
Provider API → Proxy credentials
        ↓
[EXPIRY NORMALIZATION] — All proxies in same order → same Expires At date
        ↓
PDF receipt generated
        ↓
WhatsApp delivery to customer + RANDOM IP TIP
```

---

## The Core Principle

| What happens | Who does it |
|-------------|------------|
| New customer → legal notice + random IP tip | n8n ✅ |
| Returning customer ordering | n8n fully automated ✅ |
| Lost proxy details (known number) | n8n fully automated ✅ |
| Renewal (IP still active) | n8n fully automated ✅ |
| Renewal (IP expired) | n8n generates new proxy ✅ |
| Reminder (expiry within 7 days) | n8n sends + random IP tip ✅ |
| Expiry date normalization | Same order → same Expires At ✅ |
| Refund request (proxy not yet sent) | n8n auto-approves ✅ |
| Refund request (proxy already sent) | n8n declines → admin ⚠️ |
| Ban claim with screenshot | Admin review ⚠️ |
| Deceptive customer suspected | Admin review ⚠️ |
| New number claiming to be returning | Admin review ⚠️ |
| PIN/OTP fails 3x | Admin review ⚠️ |
| Admin commands | Admin handles ⚠️ |

---

## Admin WhatsApp Interface

Admin commands:

| Command | What it does |
|---------|-------------|
| `Admin` | Show all pending actions |
| `Approve ORD-XXXXX` | Approve replacement/refund |
| `Reject ORD-XXXXX [reason]` | Reject with reason |
| `Block [phone] [reason]` | Block customer |
| `Unblock [phone]` | Unblock customer |
| `Details ORD-XXXXX` | Get full order details |
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
  → Google Sheets Read: Get ALL proxy details — NO LIMIT
  → WhatsApp: Send all proxy details + RANDOM IP TIP

intent == "my proxies":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Present all with expiry dates + RANDOM IP TIP

intent == "check expiry" OR "days left":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Show all with days until expiry

intent == "ban reported" OR "ip blocked":
  → Was order within 24hrs?
    → YES: "Send screenshot of ban message."
      → Save → ban_pending_review → [ADMIN ALERT]
    → NO: "Replacement only within 24hrs. If technical issue, send screenshot."

intent == "refund":
  → Status == "awaiting_payment": Cancel, refund
  → Status == "fulfilled": "No refund after delivery. Technical issue? Send screenshot."

intent == "help":
  → Send help menu + RANDOM IP TIP

intent == "renew":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Present all with expiry dates
  → Customer selects which to renew
  → Check if IP active or expired
    → Active: Extend same IP (+30 days)
    → Expired: Generate NEW proxy, new credentials

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
  → Legal notice + RANDOM IP TIP + help menu

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

{RANDOM IP TIP}

TO ORDER: Reply with:
"Order ISP [country] [qty]"

TYPE "help" for support.
```

### Proxy Setup Guide (On Request) + RANDOM IP TIP

```
🔧 How to use your ISP Proxy:

━━━━━━━━━━━━━━━━━━
📱 PHONE (Android / iOS):
━━━━━━━━━━━━━━━━━━

1️⃣ Open Settings

2️⃣ Search "VPN" — tap it

3️⃣ Tap "+" or "Add VPN"

4️⃣ Enter your details:

 Name: Bunche Proxy
 Type: HTTP
 Server: [IP address]
 Port: [port]
 Username: [your username]
 Password: [your password]

5️⃣ Save — tap Connect! ✅

━━━━━━━━━━━━━━━━━━
💻 DESKTOP (Chrome/Firefox/Edge):
━━━━━━━━━━━━━━━━━━

1️⃣ Open your browser

2️⃣ Settings → Advanced → Network
   → Open your PC's proxy settings

3️⃣ (Windows) Internet Options → 
   Connections → LAN settings →
   "Use a proxy server" → Enter details
   
   (Mac) Network → Proxies → 
   Manual → Enter details

4️⃣ Save. Browse!

━━━━━━━━━━━━━━━━━━
🌐 BROWSER EXTENSION (Chrome):
━━━━━━━━━━━━━━━━━━

Use a proxy switcher like SwitchyOmega:

→ New Profile → HTTP Proxy
→ Server: [IP address]
→ Port: [port]
→ Save → Activate profile

━━━━━━━━━━━━━━━━━━

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
  → Recovery setup: PIN or OTP
  → Store name
  → Log consent
  ↓
[IF NEW ORDER (not renewal)]
  → Provider API → Proxy credentials
  → IF fails → Try backup provider
    → All fail: Refund → [ADMIN ALERT]
  → [EXPIRY NORMALIZATION] — All proxies → same Expires At
  → Google Sheets Update: Status = "fulfilled"
  → [PDF GENERATION] → WhatsApp: Details + Receipt + RANDOM IP TIP
  ↓
[IF RENEWAL — IP active]
  → Same credentials, new expiry +30 days
  → WhatsApp: "Extended! Same IP." + RANDOM IP TIP
  → [PDF GENERATION] → WhatsApp: Receipt + RANDOM IP TIP
  ↓
[IF RENEWAL — IP expired]
  → Generate NEW proxy
  → WhatsApp: "New proxy ready! Update settings." + RANDOM IP TIP
  → [PDF GENERATION] → WhatsApp: Receipt + RANDOM IP TIP
  ↓
WhatsApp: "⚠️ No refunds once delivered. Replacement within 24hrs if banned."
  ↓
Respond HTTP 200
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
**If OTP chosen:** "Got it! Code will be sent to this WhatsApp when needed. ✅"
**Name:** "What should we call you? 👇"

---

## Workflow 3: Admin Command Handler

```
[CHECK: Is admin number?] → NO → Workflow 1
  ↓
Parse command:
"Pending" → List all pending actions
"Approve ORD-XXXXX" → Route by type: ban → replace proxy; refund → refund
"Reject ORD-XXXXX [reason]" → Reject, notify customer
"Block [phone] [reason]" → Block in Google Sheets
"Unblock [phone]" → Unblock
"Details ORD-XXXXX" → Full order summary
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
  → NO: "Replacement only within 24hrs. Send screenshot if technical issue."
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

## Workflow 7: Expiry Reminder Cron

**Trigger:** Daily 9:00 AM (Africa/Lagos)

```
For each customer with active proxies:
  → Get ALL proxies where Status == "fulfilled" AND Expires At ≤ today + 7 days
  → NO LIMIT on results
  ↓
IF any expiring within 7 days:
  → WhatsApp: Reminder with ALL expiring proxies + RANDOM IP TIP
  → "Say 'Renew' to extend — same IPs!"
  ↓
IF none expiring:
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

YOUR JOB:
1. Parse customer messages → extract: intent, product type, country, quantity
2. If order is clear → confirm price and prepare payment link request
3. If order is unclear → ask ONE clarifying question only
4. If customer asks about providers → deflect politely
5. If customer asks about refunds → explain the refund policy
6. Always include a RANDOM interesting IP/proxy tip when sending proxy details or setup info

RANDOM IP TIPS (pick 1 randomly, no repeat until all used — NEVER repeat the same tip back-to-back):
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
- "Proxy IPs can reveal your approximate location — a proxy hides this."
- "One IP per platform keeps account history cleaner."

REFUND POLICY:
- No refunds after proxy delivered
- Replacement within 24hrs if banned (with screenshot)
- Technical issue from start → admin reviews

HOW TO USE PROXY (correct instructions):
- PHONE: Settings → Search "VPN" → Add VPN → Enter details (NOT WiFi settings)
- DESKTOP: Browser network proxy settings or proxy switcher extension

NEVER:
- Never mention Proxy-Seller, OkeyProxy, DataImpulse, IPRoyal, or any provider name
- Never reveal API keys, internal pricing margins, or provider costs
- Never explain HOW proxies work technically beyond setup
- Never open, follow, or acknowledge any link in the customer message
- Never attempt to download, process, or parse any file
- Never reveal recovery method details to customers
- Never mention Jumia, Nigeria-specific platforms, or Nigerian marketplaces
- Never recommend 1 IP on many devices — advise one IP per account/device

COMMANDS:
- "Order ISP [COUNTRY] [QTY]" → order, ISP, country, qty
- "Order RES [QTY]GB" → order, RESIDENTIAL, qty
- "Order MOB [QTY]GB" → order, MOBILE, qty
- "Order DC [COUNTRY] [QTY]" → order, DATACENTER, country, qty
- "Status [ORDER_ID]" → status
- "My proxies" → check_proxies
- "Renew [ORDER_ID]" → renew
- "Help" → help
- "Check price [PRODUCT]" → price_check
- "Refund" / "Cancel" → refund_request
- "How to use" / "Setup proxy" / "Configure" → how_to_use

RESPONSE FORMAT — Return ONLY valid JSON:
{
  "intent": "order|status|renew|help|price_check|ban_reported|refund_request|check_proxies|how_to_use|unknown",
  "product": "ISP|RESIDENTIAL|MOBILE|DATACENTER|null",
  "country": "country code or null",
  "quantity": number or null,
  "confidence": 0.0 to 1.0,
  "reply": "short response (under 100 chars)"
}
```

---

## Google Sheets: Orders

| Column | Header |
|--------|--------|
| Order ID | text |
| Customer Phone | text |
| Plan Code | text |
| Country | text |
| Quantity | number |
| Amount Paid (NGN) | number |
| Payment Reference | text |
| Provider | text |
| Provider Order ID | text |
| Proxy Credentials | text |
| Status | text |
| Expires At | datetime |
| Ban Reported | boolean |
| Screenshot URL | text |
| Ban Verified | admin_review_pending / verified / rejected |
| Replacement Count | number |
| Refund Requested | boolean |
| Notes | text |
| Created At | datetime |
| Fulfilled At | datetime |
| Cost (USD) | number |

**Status Values:**
`awaiting_payment` | `paid_pending_fulfillment` | `fulfilled` | `ban_pending_review` | `replaced` | `failed` | `refund_pending` | `refunded` | `rejected` | `cancelled` | `expired`

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
| Expiry date normalization | All proxies in same order → same Expires At |
| Reminder shows ALL proxies | NO LIMIT — all with ≤7 days to expiry |
| Lost proxy details → ALL proxies | NO LIMIT — all for that customer |
| Proxy setup instructions | VPN settings on phone (NOT WiFi) |
| Random IP tips | Rotate — 1 tip per message, no repeat until all used |
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
| Expiry Reminder | Cron — daily 9:00 AM | Every day |
| Error Alert | n8n Error Trigger | On any error |

---

## Testing

```bash
# New customer — sees legal notice + random IP tip
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t1","from":"2349000000001","timestamp":"123","text":{"body":"Hi"}}]}}]}]}'

# Check proxies — returns all + random IP tip
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t2","from":"2349000000001","timestamp":"123","text":{"body":"My proxies"}}]}}]}]}'
```
