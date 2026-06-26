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

## Pre-Payment Health Check — Overview

**We NEVER let a customer pay unless we know we can deliver.**

---

## IP Testing — Overview

**We test every IP before sending it to a customer.**

---

## Free Trial — Systematic Approach

**Free trial is OFFERED SYSTEMATICALLY, not advertised upfront.**

### Rules

| Rule | Detail |
|------|--------|
| **Trial duration** | TEMPORARY — until proxy dies |
| **Daily limit** | 3 IPs per phone number per DAY |
| **Task** | ONE survey per IP (verified via postback) |
| **Free proxy source** | Geonode Free API |
| **No replacement** | Dead proxy = complete another survey |
| **Reset** | Daily midnight (Africa/Lagos) |

### When to Offer Free Trial (The Trigger System)

| Customer State | Offer Free Trial? |
|----------------|-------------------|
| New customer, first message, no active subscription | ❌ NO (wait for browsing) |
| Customer browsed (asked prices), no order, idle 15+ min | ✅ YES |
| Customer has active subscription | ❌ NO |
| Customer bought today | ❌ NO |
| Customer already used 3 trials today | ❌ NO |
| Customer explicitly declined trial today | ❌ NO |
| Customer on ban_pending_review | ❌ NO |

### When Customer ASKS About Free Trial

**If customer asks "Do you have free trial?" / "Is there free trial?":**

Reply:
"Yes! We have a free trial 🎁

Here's how it works:
→ Complete ONE short survey
→ We send you 1 free proxy IP
→ Up to 3 trials per day

Free trial uses public proxies
(not as reliable as paid) — best
for testing our service quality.

To skip the trial and order now,
just say 'Order ISP UK 1' or
similar.

Type 'help' anytime."

**Then:** Wait for customer to either order or ask for the trial.

- If customer orders → normal order flow
- If customer says "Free trial" / "Trial" / "Free proxy" / "YES" / "Give me the free trial" / "I want the free trial" / "Send me free trial" → Route to Workflow 8

### Why 15-Minute Delay (For Auto-Offer)

| Reason | Benefit |
|--------|---------|
| Customer isn't pushed on first message | Better experience |
| Only offered when relevant | Less spammy |
| Targets "browsing but not buying" segment | Higher conversion |
| 15-min delay feels natural | Not desperate |

### The Full Flow

**Step 1: First Message**
```
Customer: "Hi"
  ↓
Bunche: Legal notice ONLY (no free trial mention)
```

**Step 2: Customer Browses**
```
Customer: "How much is UK ISP?"
  ↓
Bunche: "🇬🇧 UK ISP — ₦6,500/mo"
  ↓
Customer: "What about Residential?"
  ↓
Bunche: "🌐 Residential 5GB — ₦9,500 (data never expires!)"
  ↓
[Customer goes silent — no order placed]
```

**Step 3: 15-Minute Follow-Up (Workflow 9 — Cron Trigger)**
```
[15 minutes after last customer message]
  ↓
Bunche checks:
  - No order placed after last message
  - No active subscription
  - Free trial not offered today
  - Free trial not declined today
  ↓
If eligible:
  "👋 Hey! Still thinking about it?

  Not ready to commit? Try our FREE TRIAL!

  Complete a short survey, get 1 free proxy IP.
  3 free trials per day.

  ⚠️ Note: Free trial uses public proxies —
  not as reliable as our paid plans. Used at
  your own risk. For testing only.

  Want to try? Reply YES

  Type NO to skip."
  ↓
Log: Free Trial Offer Sent = today, timestamp
```

**Step 4: Customer Says YES / Free trial / Trial / Free proxy / Give me the free trial**
```
Customer: "YES" or "Free trial" or "Give me the free trial"
  ↓
Bunche: "🎁 FREE TRIAL — DISCLAIMER

  Before we send your free IP, please read:

  ━━━━━━━━━━━━━━━━━━
  ⚠️ FREE TRIAL TERMS ⚠️
  ━━━━━━━━━━━━━━━━━━

  This free trial uses PUBLIC PROXIES from
  external sources. By accepting, you agree:

  ❌ NOT guaranteed to work
  ❌ NOT guaranteed stable
  ❌ May stop working at any moment
  ❌ Not for production/critical use
  ❌ No replacement if proxy dies
  ❌ Used entirely at YOUR OWN RISK

  ✅ Bunche is NOT responsible for proxy
     performance during free trial
  ✅ For testing our service only
  ✅ Upgrade to paid plan for reliability

  ━━━━━━━━━━━━━━━━━━

  Complete ONE survey to unlock your IP:

  [CPAGRIP SURVEY LINK]

  After completing, reply DONE"
  ↓
Log: Disclaimer Accepted = true, timestamp
```

**Step 5: Customer Says NO**
```
Customer: "NO"
  ↓
Bunche: "👍 No problem! We're here whenever you're ready.

Type 'help' anytime for our services."
  ↓
Log: Free Trial Declined Today = true
```

**Step 6: Customer Completes Survey**
```
Customer completes survey
  ↓
Survey postback → Bunche webhook (auto-verified)
  ↓
Bunche: Pull Geonode Free proxy → Test (5s) → Send
  ↓
WhatsApp:
"✅ SURVEY VERIFIED!

🔍 Verification:
→ Survey ID: [SRV-XXXXX]
→ Verified: [timestamp]

━━━━━━━━━━━━━━━━━━
🎁 FREE TRIAL PROXY — TEMPORARY
━━━━━━━━━━━━━━━━━━

🔗 Proxy: [IP]:[PORT]
📍 Location: [location]
🔓 Type: Open proxy (NO username/password)
⏰ TEMPORARY — lasts until it dies

━━━━━━━━━━━━━━━━━━
⚠️ REMINDER — FREE TRIAL TERMS
━━━━━━━━━━━━━━━━━━

This is a PUBLIC open proxy.

❌ NOT guaranteed to work
❌ May stop working anytime
❌ Open proxy = anyone can use it
❌ Not for sensitive/private activity
❌ Used at YOUR OWN RISK

🔧 How to use:
📱 Phone: Settings → Search VPN → Add VPN
   → Host: [IP] | Port: [PORT]
💻 Desktop: Browser proxy settings → HTTP
   → Host: [IP] | Port: [PORT]

📊 Today's trial usage: 1 of 3 used

🚀 Want RELIABLE proxies with username/password?
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo (with auth)
💻 Datacenter — ₦3,000/mo (with auth)
🌐 Residential 5GB — ₦9,500 (with auth)
📱 Mobile 4G 5GB — ₦20,000 (with auth)

{RANDOM IP TIP}
━━━━━━━━━━━━━━━━━━"
  ↓
Log: Free Trials Used Today += 1
```

---

## Pricing (₦1,380/$1)

| Product | Price | Provider | Data | Expiry | Rollover |
|---------|-------|---------|------|--------|---------|
| 🇬🇧🇺🇸🇩🇪 ISP | **₦6,500/mo** | Proxy-Seller | Unlimited | Monthly date | ✅ Same IP on renewal |
| 🌏 Premium ISP (JP, AU, BR, SG, KR) | **₦7,500/mo** | Proxy-Seller | Unlimited | Monthly date | ✅ Same IP on renewal |
| 💻 Datacenter | **₦3,000/mo** | Proxy-Seller | Unlimited | Monthly date | ✅ Same IP on renewal |
| 🌐 Residential 5GB | **₦9,500** | DataImpulse | 5GB (data never expires) | No expiry | ✅ Unlimited rollover |
| 📱 Mobile 4G 5GB | **₦20,000** | DataImpulse | 5GB | 30-day window | ❌ No rollover |

---

## Cost Analysis (₦1,380/$1)

| Product | Provider Cost ($) | Provider Cost (₦) | Sell (₦) | Margin (₦) | Margin (%) |
|---------|-----------------|-----------------|---------|-----------|-----------|
| ISP | $3.50 | ₦4,830 | ₦6,500 | ₦1,670 | 34.5% |
| DC | $1.50 | ₦2,070 | ₦3,000 | ₦930 | 44.9% |
| Residential 5GB | $5.00 | ₦6,900 | ₦9,500 | ₦2,600 | 37.7% |
| Mobile 4G 5GB | $10.00 | ₦13,800 | ₦20,000 | ₦6,200 | 44.9% |

---

## Renewal Policy

| Proxy Type | What Happens | Unused Data/Time |
|-----------|-------------|-----------------|
| **ISP / DC** | Same IP extended | Rollover: YES |
| **Residential** | Fresh GB added to pool | Rollover: YES — data never expires |
| **Mobile** | Fresh GB allocated | Rollover: NO — old unused GB LOST |

---

## Data Tracking

### Google Sheets: Orders — Tracking Columns

| Column | ISP / DC | Residential | Mobile |
|--------|----------|------------|--------|
| Data Total (GB) | N/A | ✅ | ✅ |
| Data Remaining (GB) | N/A | ✅ | ✅ |
| Data Expires | N/A | ❌ Never | ✅ 30-day window |

### Status Values

| Status | Used For | Meaning |
|--------|---------|---------|
| `active` | All | Working ✅ |
| `data_low` | RES / Mobile | ≤1GB remaining ⚠️ |
| `data_exhausted` | RES / Mobile | 0GB — proxy inactive ❌ |
| `expired` | ISP / DC / Mobile | Past expiry date |

---

## Reminder System

### ISP / DC — Time-Based

```
Daily cron: Check Expires At ≤ 7 days → Send reminder
```

### Residential — Data-Based (No Expiry!)

```
Daily cron: Check Data Remaining ≤ 1GB → Send data warning
No expiry reminder (data never expires!)
```

### Mobile — Dual (Data + Time)

```
Daily cron:
→ Data Remaining ≤ 1GB → Send warning
→ Data Remaining == 0GB → Send exhausted notice
→ Expires At ≤ 3 days AND Data Remaining > 0GB → Send expiry reminder
```

---

## Random IP Tips Pool

**Rotate randomly — pick 1 per message. No repeat until all used.**

```
💡 DID YOU KNOW?

🌐 ISP proxies use real home/office IP addresses.

📱 Mobile proxies use real 4G/5G networks.

🏢 Datacenter IPs come from servers — fast and cheap.

🔄 Residential proxies bounce through real home devices.

🕐 ISP proxies stay stable longer than mobile.

🌍 US and UK IPs are among the most trusted.

📺 Some platforms check IPs against GPS data.

💰 High-trust IPs cost more because they're less likely flagged.

🔒 Using a proxy hides your real IP.

📡 Proxy speed depends on location.

⚡ Datacenter proxies are fastest — great for automation.

🌐 ISP = Internet Service Provider.

🔁 Mobile proxies rotate IPs as you use them.

🏴󠁧󠁢󠁿󠁧󠁢󠁿 Proxy IPs hide your location.

🎯 One IP per platform = cleaner account history.
```

---

## Legal Notice (First Message Only — NO Free Trial Mention)

```
👋 Welcome to Bunche!

📄 By using Bunche, you agree to our
   Terms of Service, Privacy Policy,
   and Acceptable Use Policy.
   
   bunche.com/terms | bunche.com/privacy | bunche.com/aup

━━━━━━━━━━━━━━━━━━
PRICES:
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo
🌏 Premium ISP — ₦7,500/mo
💻 Datacenter — ₦3,000/mo
🌐 Residential 5GB — ₦9,500
📱 Mobile 4G 5GB — ₦20,000
━━━━━━━━━━━━━━━━━━

💡 IMPORTANT — RESIDENTIAL vs MOBILE:
→ Residential: Data NEVER expires!
→ Mobile: 30-day window, unused GB lost!

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
[LOG: Customer_Audit_Log entry — msg_received]
[Correlation ID: msg_id from webhook]
        ↓
[CHECK: New customer?] → YES → Legal notice → Workflow 1b
                       → NO  → Workflow 1a
        ↓
[LLM PARSING] — Ollama via LiteLLM → structured intent
        ↓
[IF INTENT == "order"] → Pre-payment health check → Payment
[IF INTENT == "renew/top_up/help/etc"] → Handle normally
[IF INTENT == "free_trial_request"] → Workflow 8 (disclaimer + survey)
        ↓
[Cron Workflow 9: Every 1 minute]
  → Find customers idle 15+ min, no order, no active sub
  → Offer free trial (NOT advertised upfront)
```

---

## The Core Principle

| What happens | Who does it |
|-------------|------------|
| Free trial offered AFTER 15-min idle | Workflow 9 (cron) ✅ |
| Free trial: customer asks → confirm + explain | LLM responds ✅ |
| Free trial: customer opts in → disclaimer | n8n ✅ |
| Free trial: survey completion verified | Survey postback ✅ |
| Pre-payment health check | n8n checks provider before payment link ✅ |
| Provider down → No payment link | n8n tells customer, no charge ✅ |
| IP testing before delivery | n8n tests every IP (5s timeout) ✅ |
| IP fails → replacement | n8n requests new IP ✅ |
| Replacement also fails → refund | n8n refunds automatically ✅ |
| ISP/DC → time-based tracking | n8n ✅ |
| Residential → data never expires | n8n ✅ |
| Mobile → 30-day, no rollover | n8n ✅ |
| Refund request (not our fault) | n8n auto-approves ✅ |
| Refund request (our fault) | n8n declines → admin ⚠️ |
| Ban claim with screenshot | Admin review ⚠️ |
| Admin commands | Admin handles ⚠️ |
| **All events logged to Customer_Audit_Log** | **Workflow 11** ✅ |
| **All errors logged to Error_Log** | **Workflow 11** ✅ |
| **Provider health monitored** | **Workflow 12** ✅ |
| **Daily summary generated** | **Workflow 13** ✅ |

---

## Admin WhatsApp Interface

| Command | What it does |
|---------|-------------|
| `Admin` | Show all pending actions |
| `Approve ORD-XXXXX` | Approve replacement/refund |
| `Reject ORD-XXXXX [reason]` | Reject with reason |
| `Block [phone] [reason]` | Block customer |
| `Unblock [phone]` | Unblock customer |
| `Details ORD-XXXXX` | Full order details |
| `Refund ORD-XXXXX` | Initiate refund (exemption only) |
| `Force-Refund ORD-XXXXX` | Admin override |
| `Pending` | List all pending actions |
| `Provider Status` | Check health of all providers |
| `Errors` | List open errors |
| `Errors critical` | List critical errors |
| `Resolve ERR-XXXXX` | Mark error as resolved |
| `Ignore ERR-XXXXX` | Mark as ignored |
| `Logs [phone]` | Show customer audit log (hashed) |
| `Provider log` | Recent provider health checks |
| `Daily summary` | Today's metrics |

---

## Workflow 1: Order Handler (WhatsApp Incoming)

```
Webhook Trigger (WhatsApp POST)
  ↓
Edit Fields: Extract from, msg_body, msg_id, timestamp
[LOG: msg_received — correlation_id = msg_id]
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
  → Google Sheets Read: Lookup price + country
  → [PRE-PAYMENT HEALTH CHECK]
    → Call Proxy-Seller / DataImpulse API
    → Check: Is country/provider available?
      → ❌ UNAVAILABLE or DOWN:
        → WhatsApp: "Sorry, [product] for [country] is
           temporarily unavailable right now."
        → [LOG: order_failed — provider_unavailable]
        → END
      → ✅ AVAILABLE:
        → Continue ↓
  → HTTP Request → Flutterwave POST /payments
  → Google Sheets Append: Pending_Orders (awaiting_payment)
  → [LOG: order_created]
  → WhatsApp: "Payment link sent! ₦[price] 💳"

intent == "lost proxy details":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → WhatsApp: Send all proxy details + RANDOM IP TIP
  → [LOG: details_sent]

intent == "my proxies" OR "check data":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → WhatsApp: All proxies + status + RANDOM IP TIP
  → [LOG: check_proxies]

intent == "check expiry" OR "days left":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Show all with days / data remaining
  → [LOG: check_expiry]

intent == "ban reported" OR "ip blocked":
  → Was order within 24hrs?
    → YES: "Send screenshot." → Save → ban_pending_review → [ADMIN ALERT]
    → NO: "Replacement only within 24hrs."
  → [LOG: ban_reported]

intent == "refund":
  → Status == "awaiting_payment": Cancel, refund
  → Status == "fulfilled": "No refund after delivery."
  → [LOG: refund_request]

intent == "help":
  → Send help menu + RES vs MOB warning + RANDOM IP TIP
  → [LOG: help_sent]

intent == "renew":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Present all with status
  → Customer selects which to renew
  ↓
  [PRE-PAYMENT HEALTH CHECK]
    → Check provider availability
      → ❌ UNAVAILABLE: "Sorry, service is down."
      → ✅ AVAILABLE: Continue
  ↓
  [IF ISP/DC — IP active]: Extend same IP (+30 days)
  [IF ISP/DC — IP expired]: Generate NEW proxy
  [IF Residential]: Fresh GB, old data preserved
  [IF Mobile]: Fresh GB, old unused GB LOST
  → WhatsApp: Confirmation + type-specific warning + RANDOM IP TIP
  → [LOG: renewal_completed]

intent == "top up residential":
  → Google Sheets Read: Find residential proxy
  → Present top-up options (5GB / 10GB)
  → [PRE-PAYMENT HEALTH CHECK] → Check DataImpulse availability
  → Generate payment link
  → Payment confirmed → Add GB → Data Remaining updated
  → WhatsApp: "✅ Top up confirmed!" + RANDOM IP TIP
  → [LOG: topup_completed]

intent == "top up mobile":
  → Google Sheets Read: Find mobile proxy
  → Present top-up options (5GB / 10GB)
  → [PRE-PAYMENT HEALTH CHECK] → Check DataImpulse availability
  → Generate payment link
  → Payment confirmed → Add GB → Proxy reactivated
  → WhatsApp: "✅ Top up confirmed! ⚠️" + RANDOM IP TIP
  → [LOG: topup_completed]

intent == "free_trial" OR "trial" OR "free proxy" OR "free IP" OR "give me the free trial" OR "i want the free trial" OR "send me free trial":
  → Check daily limit
  → If eligible: Send disclaimer + survey link
  → If not eligible: "You've used all 3 free trials today."
  → [LOG: free_trial_requested]

intent == "how to use" OR "setup proxy" OR "configure":
  → Send proxy setup guide + RANDOM IP TIP
  → [LOG: how_to_use_sent]

Default:
  → LLM reply
  → [LOG: llm_response]
```

### Workflow 1b: New Customer

```
intent == "order":
  → Legal notice (already shown)
  → [PRE-PAYMENT HEALTH CHECK] → Check provider availability
    → ❌ UNAVAILABLE: "Sorry, [product] is temporarily unavailable."
    → ✅ AVAILABLE: Continue
  → Google Sheets Read: Lookup price
  → Flutterwave payment link → WhatsApp: "Payment link sent."
  → Log consent (first interaction)
  → [LOG: order_created — new_customer]

intent == "free_trial" OR "trial" OR "free proxy" OR "free IP" OR "give me the free trial" OR "i want the free trial" OR "send me free trial":
  → Check daily limit
  → If eligible: Send disclaimer + survey link
  → If not eligible: "You've used all 3 free trials today."
  → [LOG: free_trial_requested]

intent == "help":
  → Legal notice + RES vs MOB warning + RANDOM IP TIP + help menu
  → [LOG: help_sent]

intent == "lost proxy details":
  → WhatsApp: "Enter PIN or OTP"
    → PIN verify / OTP verify
      → Match: Send details + RANDOM IP TIP
      → Fail 3x: [ADMIN ALERT]
  → [LOG: recovery_attempt — method, success/fail]

Default:
  → LLM reply
  → [LOG: llm_response]
```

### Legal Notice (First Message Only — NO Free Trial Mention)

```
👋 Welcome to Bunche!

📄 By using Bunche, you agree to our
   Terms of Service, Privacy Policy,
   and Acceptable Use Policy.
   
   bunche.com/terms | bunche.com/privacy | bunche.com/aup

━━━━━━━━━━━━━━━━━━
PRICES:
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo
🌏 Premium ISP — ₦7,500/mo
💻 Datacenter — ₦3,000/mo
🌐 Residential 5GB — ₦9,500
📱 Mobile 4G 5GB — ₦20,000
━━━━━━━━━━━━━━━━━━

💡 IMPORTANT — RESIDENTIAL vs MOBILE:
→ Residential: Data NEVER expires!
→ Mobile: 30-day window, unused GB lost!

{RANDOM IP TIP}

TO ORDER: Reply with:
"Order ISP [country] [qty]"

TYPE "help" for support.
```

### When Customer Asks "Do you have free trial?"

```
Yes! We have a free trial 🎁

Here's how it works:
→ Complete ONE short survey
→ We send you 1 free proxy IP
→ Up to 3 trials per day

Free trial uses public proxies
(not as reliable as paid) — best
for testing our service quality.

To skip the trial and order now,
just say "Order ISP UK 1" or
similar.

Type "help" anytime.
```

### Help Menu

```
📋 Bunche Commands:

🛒 ORDER:
"Order ISP [country] [qty]"
"Order DC [country] [qty]"
"Order RES [qty]GB"
"Order MOB [qty]GB"

🔄 RENEW:
"Renew" — renew your proxies

📊 CHECK:
"My proxies" — all your proxies + data/status
"Check data" — data remaining (RES/Mobile)

📦 TOP UP:
"Top up residential" — add GB (data never expires)
"Top up mobile" — add GB (unused GB lost!)

💬 SUPPORT:
"Help" — show this menu
"Lost my details" — recover proxy info

━━━━━━━━━━━━━━━━━━
💡 RESIDENTIAL: Data never expires!
   MOBILE: 30-day window. Unused GB lost!
━━━━━━━━━━━━━━━━━━
```

### Proxy Setup Guide

```
🔧 How to use your ISP/Mobile Proxy:

📱 PHONE: Settings → Search "VPN" → Add VPN → Enter details
💻 DESKTOP: Browser network proxy settings or extension

━━━━━━━━━━━━━━━━━━
💡 IP TIPS:
━━━━━━━━━━━━━━━━━━
✅ One IP per device or per account.
✅ Use different IPs for different platforms.
🔄 ISP/DC: Renew BEFORE expiry to keep same IP.
🌐 Residential: Data never expires! Top up anytime.
📱 Mobile: Renew AFTER data runs out — unused GB lost!

{RANDOM IP TIP}
```

---

## Workflow 2: Payment Confirmation (Flutterwave Webhook)

```
Webhook Trigger (Flutterwave POST)
  ↓
Verify Flutterwave-Signature
[LOG: payment_webhook_received]
  ↓
IF event !== "charge.completed" OR status !== "successful":
  → Respond 200 "ignored"
  → [LOG: payment_ignored]
  ↓
Edit Fields: Extract tx_ref, amount, phone, meta
  ↓
Google Sheets: Find order by tx_ref
  ↓
IF Status !== "awaiting_payment":
  → Respond 200 "already processed"
  → [LOG: payment_duplicate]
  ↓
Google Sheets Update: Status = "paid_pending_fulfillment"
[LOG: payment_received]
  ↓
Google Sheets: Check if customer exists
  ↓
[IF NEW CUSTOMER — First purchase]
  → Recovery setup: PIN or OTP → Store name → Log consent
  → [LOG: customer_first_purchase]
  ↓
[IF NEW ORDER (not renewal)]
  → Provider API → Proxy credentials
  → IF fails → Try backup provider
    → All fail: Refund immediately → [ADMIN ALERT] → END
    → [LOG: provider_failure]
  ↓
  [IP TESTING]
    → Test IP with 5-second timeout
    → If IP responds: Continue ↓
    → If IP fails:
      → Request replacement from provider
      → Test replacement (5s timeout)
        → If replacement PASSES: Continue ↓
        → If replacement FAILS:
          → Refund immediately → [ADMIN ALERT]
          → WhatsApp: "We're so sorry! The proxy
             we generated had an issue. Your payment
             has been automatically refunded."
          → [LOG: ip_test_failed — refunded]
          → Respond HTTP 200 → END
  ↓
  [IF ISP or DC]:
    → [EXPIRY NORMALIZATION] — All → same Expires At
    → Google Sheets: Status = "fulfilled"
    → [PDF] → WhatsApp: Details + Receipt + RANDOM IP TIP
    → [LOG: proxy_delivered — ISP/DC]
  ↓
  [IF RESIDENTIAL]:
    → Google Sheets: Data Total = [X]GB, Data Remaining = [X]GB, Data Expires = "never"
    → Google Sheets: Status = "active"
    → [PDF] → WhatsApp: Details + Receipt + "data never expires" + RANDOM IP TIP
    → [LOG: proxy_delivered — Residential]
  ↓
  [IF MOBILE]:
    → Google Sheets: Data Total = [X]GB, Data Remaining = [X]GB, Data Expires = today + 30 days
    → Google Sheets: Status = "active"
    → [PDF] → WhatsApp: Details + Receipt + mobile warning + RANDOM IP TIP
    → [LOG: proxy_delivered — Mobile]
  ↓
[IF ISP/DC RENEWAL — IP active]:
  → [IP TESTING] → Test existing IP before extending
    → If IP still works: Extend +30 days → Send confirmation
    → If IP fails: Generate replacement → Test → Deliver
  → Google Sheets Update: Status = "fulfilled"
  → WhatsApp: "✅ Extended! Same IP." + RANDOM IP TIP
  → [LOG: renewal_delivered]

[IF ISP/DC RENEWAL — IP expired]:
  → Provider API: Generate NEW proxy
  → [IP TESTING] → Test new IP (5s)
    → If PASS: Deliver + RANDOM IP TIP
    → If FAIL: Refund immediately + [ADMIN ALERT]
  → WhatsApp: "✅ New proxy ready!" + RANDOM IP TIP
  → [LOG: renewal_new_ip]

[IF RESIDENTIAL RENEWAL]:
  → Fresh GB added to pool
  → Google Sheets Update: Data Remaining += [X]GB
  → WhatsApp: "✅ Residential renewed! +[X]GB. 📦 Total: [Y]GB. 💡" + RANDOM IP TIP
  → [LOG: renewal_residential]

[IF MOBILE RENEWAL]:
  → Fresh GB — old unused GB LOST
  → [PRE-PAYMENT HEALTH CHECK] → Check DataImpulse
    → If DOWN: Refund + notify customer
    → If UP: Continue
  → Google Sheets Update: Data Total = [X]GB, Data Remaining = [X]GB, Data Expires = today + 30 days
  → WhatsApp: "✅ Mobile renewed! ⚠️ Old unused GB lost." + RANDOM IP TIP
  → [LOG: renewal_mobile]

[IF RESIDENTIAL TOP-UP]:
  → [PRE-PAYMENT HEALTH CHECK] → DataImpulse
    → If DOWN: Refund + notify
    → If UP: Continue
  → Provider API: Add GB to order
  → Google Sheets Update: Data Remaining += [X]GB
  → WhatsApp: "✅ Top up confirmed! +[X]GB. Total: [Y]GB. 💡" + RANDOM IP TIP
  → [LOG: topup_residential]

[IF MOBILE TOP-UP]:
  → [PRE-PAYMENT HEALTH CHECK] → DataImpulse
    → If DOWN: Refund + notify
    → If UP: Continue
  → Provider API: Add GB to order
  → Google Sheets Update: Data Remaining = [X]GB, Data Expires = today + 30 days
  → WhatsApp: "✅ Top up confirmed! ⚠️" + RANDOM IP TIP
  → [LOG: topup_mobile]

Respond HTTP 200
```

### Delivery Messages

**ISP/DC:**
```
🎉 [Product] Proxy Ready! ✅

🔗 IP: [IP]
Port: [port]
Username: [user]
Password: [pass]

⏰ Expires: [DATE]

💡 Renew before expiry to keep the same IP!

{RANDOM IP TIP}

📄 Receipt: [PDF ATTACHED]
```

**Residential:**
```
🎉 Residential Proxy Ready! 🌐

🔗 IP: [IP]
Port: [port]
Username: [user]
Password: [pass]

📦 Data: [X]GB (data never expires!)
💡 Your data stays until you use it!

{RANDOM IP TIP}

📄 Receipt: [PDF ATTACHED]
```

**Mobile:**
```
🎉 Mobile Proxy Ready! 📱

🔗 IP: [IP]
Port: [port]
Username: [user]
Password: [pass]

📦 Data: [X]GB
⏰ Expires: [DATE] (30-day window)

⚠️ IMPORTANT:
→ Mobile data expires in 30 days
→ Unused GB is LOST on renewal!
→ Renew AFTER data runs out!

{RANDOM IP TIP}

📄 Receipt: [PDF ATTACHED]
```

---

## Workflow 3: Admin Command Handler

```
[CHECK: Is admin number?] → NO → Workflow 1
  ↓
Parse command:
[LOG: admin_command]
"Pending" → List all pending actions
"Approve ORD-XXXXX" → Route: ban → replace; refund → refund
"Reject ORD-XXXXX [reason]" → Reject, notify customer
"Block [phone] [reason]" → Block in Google Sheets
"Unblock [phone]" → Unblock
"Details ORD-XXXXX" → Full summary
"Refund ORD-XXXXX" → Check status → refund or warn
"Force-Refund ORD-XXXXX" → Admin override
"Provider Status" → Check all providers → Report
"Errors" → List open errors
"Errors critical" → List critical errors
"Resolve ERR-XXXXX" → Mark resolved
"Logs [phone]" → Show customer audit log (hashed)
"Provider log" → Show recent provider health
"Daily summary" → Today's metrics
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
[LOG: ban_claim]
```

---

## Workflow 5: Provider APIs + Health Endpoints

### Proxy-Seller API (ISP + DC)
**Order:** POST https://api.proxy-seller.com/v1/orders
**Health Check:** GET https://api.proxy-seller.com/v1/countries
**IP Replacement:** POST https://api.proxy-seller.com/v1/order/{order_id}/replace

### DataImpulse API (Residential + Mobile)
**Order:** POST https://api.dataimpulse.com/v1/order
**Health Check:** GET https://api.dataimpulse.com/v1/locations

### Geonode Free Proxy API (For Free Trial)
```
GET https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps
```

### Survey Postback URL
```
https://n8n.yourdomain.com/webhook/survey-postback?user_id={USER_ID}&reward={REWARD}
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
[LOG: refund_processed]
```

---

## Workflow 7: Expiry + Data Reminder Cron

**Trigger:** Daily 9:00 AM (Africa/Lagos)

```
For each customer with active proxies:
  ↓
  [FOR ISP/DC]: Expires At ≤ 7 days → Reminder
  [FOR Residential]: Data Remaining ≤ 1GB → Warning; 0GB → Exhausted
  [FOR Mobile]: Data ≤ 1GB → Warning; 0GB → Exhausted; Expires ≤ 3 days → Reminder
[LOG: reminder_sent]
```

---

## Workflow 8: Free Trial — Customer Opt-In

**Trigger:** Customer says "Free trial" / "Trial" / "Free proxy" / "YES" / "Give me the free trial" / "I want the free trial" / "Send me free trial"

### Step 1: Check Daily Limit
```
Google Sheets Read: Count trials for this phone today
[LOG: free_trial_check]
  ↓
  ❌ Count >= 3:
    → WhatsApp: "You've used all 3 free trials today."
    → [LOG: free_trial_limit_hit]
    → END
  ↓
  ✅ Count < 3:
    → Continue to Step 2
```

### Step 2: Send Disclaimer + Survey Link
```
WhatsApp: "🎁 FREE TRIAL — DISCLAIMER

Before we send your free IP, please read:

━━━━━━━━━━━━━━━━━━
⚠️ FREE TRIAL TERMS ⚠️
━━━━━━━━━━━━━━━━━━

This free trial uses PUBLIC PROXIES from
external sources. By accepting, you agree:

❌ NOT guaranteed to work
❌ NOT guaranteed stable
❌ May stop working at any moment
❌ Not for production/critical use
❌ No replacement if proxy dies
❌ Used entirely at YOUR OWN RISK

✅ Bunche is NOT responsible for proxy
   performance during free trial
✅ For testing our service only
✅ Upgrade to paid plan for reliability

━━━━━━━━━━━━━━━━━━

Complete ONE survey to unlock your IP:

[CPAGRIP SURVEY LINK]

After completing, reply DONE"
  ↓
Log: Disclaimer Accepted = true
[LOG: free_trial_disclaimer_sent]
```

### Step 3: Survey Completion

**Option A — Survey Postback Webhook:**
```
Webhook Trigger (POST)
  ↓
Verify HMAC signature
[LOG: survey_postback_received]
  ↓
Extract: user_id (phone), survey_id, reward, status
  ↓
IF status === "completed":
  → Continue to Step 4
IF status !== "completed":
  → Ignore
```

**Option B — Customer Says DONE:**
```
Customer: "DONE"
  ↓
Check Google Sheets for matching survey completion
  ↓
IF found: Continue to Step 4
IF not found: "Survey not detected yet. Try again in a few minutes."
```

### Step 4: Get + Test Proxy

```
GET https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps
  ↓
For each proxy:
  [TEST — 5 second timeout]
  ↓
  IF PASS: Continue to Step 5, BREAK
  IF FAIL: Try next
  ↓
IF all fail:
  → WhatsApp: "Sorry, no working proxies available right now. Please try again in a few minutes 🙏"
  → [LOG: free_trial_no_working_proxies]
  → END
```

### Step 5: Log + Send Proxy

```
Google Sheets Append: Free_Trials
  - Phone, Trial Date, Survey ID, Reward, Proxy IP, Status, Disclaimer Accepted
  ↓
WhatsApp:
"✅ SURVEY VERIFIED!

🔍 Verification:
→ Survey ID: [SRV-XXXXX]
→ Verified: [timestamp]

━━━━━━━━━━━━━━━━━━
🎁 FREE TRIAL PROXY — TEMPORARY
━━━━━━━━━━━━━━━━━━

🔗 Proxy: [IP]:[PORT]
📍 Location: [location]
🔓 Type: Open proxy (NO username/password)
⏰ TEMPORARY — lasts until it dies

━━━━━━━━━━━━━━━━━━
⚠️ REMINDER — FREE TRIAL TERMS
━━━━━━━━━━━━━━━━━━

This is a PUBLIC open proxy.

❌ NOT guaranteed to work
❌ May stop working anytime
❌ Open proxy = anyone can use it
❌ Not for sensitive/private activity
❌ Used at YOUR OWN RISK

🔧 How to use:
📱 Phone: Settings → Search VPN → Add VPN
   → Host: [IP] | Port: [PORT]
💻 Desktop: Browser proxy settings → HTTP
   → Host: [IP] | Port: [PORT]

📊 Today's trial usage: 1 of 3 used

🚀 Want RELIABLE proxies with username/password?
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo (with auth)
💻 Datacenter — ₦3,000/mo (with auth)
🌐 Residential 5GB — ₦9,500 (with auth)
📱 Mobile 4G 5GB — ₦20,000 (with auth)

{RANDOM IP TIP}
━━━━━━━━━━━━━━━━━━"
[LOG: free_trial_delivered]
```

---

## Workflow 9: Free Trial Follow-Up (15-Minute Idle Cron)

**Trigger:** Cron every 1 minute

### Flow

```
Cron Trigger (every 1 minute)
  ↓
Google Sheets Read: Find customers where:
  - Last Message At is between 15 and 16 minutes ago
  - No order placed after Last Message At
  - No active subscription
  - Free Trial Offer Sent Today = false
  - Free Trial Declined Today = false
  - Free Trials Used Today < 3
  - Blocked = false
[LOG: free_trial_offer_check]
  ↓
For each match:
  → WhatsApp: "👋 Hey! Still thinking about it?

    Not ready to commit? Try our FREE TRIAL!

    Complete a short survey, get 1 free proxy IP.
    3 free trials per day.

    ⚠️ Note: Free trial uses public proxies —
    not as reliable as our paid plans. Used at
    your own risk. For testing only.

    Want to try? Reply YES

    Type NO to skip."
  → Google Sheets Update: 
    - Free Trial Offer Sent Today = true
    - Free Trial Offer Sent At = now
  → [LOG: free_trial_offer_sent]
```

---

## Workflow 10: Trial Reset Cron

**Trigger:** Daily 00:00 (Africa/Lagos)

```
For each customer in Customers sheet:
  ↓
  Reset:
  - Free Trials Used Today = 0
  - Free Trial Offer Sent Today = false
  - Free Trial Declined Today = false
  ↓
Done — fresh day, fresh 3 trials per customer
[LOG: trial_reset]
```

---

## Workflow 11: Bunche Logger (Persistent Logging)

**Trigger:** Multiple — receives log events from all workflows

### Purpose
Persistent logging of all Bunche events to Google Sheets for tracking, debugging, and audit.

### Logging Schema (Standard — Applied From Scale Planning LOGS-3)

```json
{
  "timestamp": "2026-06-26T14:48:13Z",
  "level": "INFO",
  "request_id": "wa_msg_a1b2c3d4e5f6",
  "service": "bunche-n8n",
  "workflow": "workflow_1_order_handler",
  "customer_id_hash": "cust_8f3a2b",  // Hashed phone — never plain
  "action": "order_received",
  "resource": "ORD-12345",
  "ip_hash": "iph_xxxx",  // Hashed if used
  "duration_ms": 145,
  "msg": "Order ISP UK 1 received",
  "context": {
    "product": "ISP",
    "country": "GB",
    "quantity": 1
  },
  "error": null,
  "version": "1.0.0"
}
```

### PII Redaction (Applied From LOGS-12)

**NEVER log raw:**
- Phone numbers (hash with sha256, first 8 chars)
- Customer names (hash)
- IP addresses (hash)
- Order credentials
- PIN/OTP codes
- API keys/tokens
- Payment references (only last 4 chars)
- Survey reward amounts (only show ID)

### Correlation ID (Applied From LOGS-2)

- Use WhatsApp `msg_id` as correlation ID for incoming messages
- Generate `bunche_<12hex>` for outbound events
- Propagate through all related workflows
- Echo back in admin queries

### Retention Policy (Applied From LOGS-14)

| Tier | Storage | Retention |
|------|---------|-----------|
| Hot | n8n database | 7 days |
| Cold | Google Sheets (Customer_Audit_Log, Error_Log) | 90 days |
| Archive | Cloudflare R2 | 1 year (compliance) |

### Sheets Created

#### Sheet: Customer_Audit_Log

| Column | Header |
|--------|--------|
| Timestamp | datetime |
| Request ID | text |
| Customer Hash | text (hashed phone) |
| Event Type | text |
| Order ID | text |
| Workflow | text |
| Status | success / failure |
| Details (JSON) | text |

#### Sheet: Error_Log

| Column | Header |
|--------|--------|
| Timestamp | datetime |
| Workflow Name | text |
| Node Name | text |
| Error Type | text |
| Error Message | text |
| Error Stack | text |
| Execution ID | text |
| Customer Hash | text |
| Order ID | text |
| Severity | critical / high / medium / low |
| Status | open / investigating / resolved / ignored |
| Resolved By | text |
| Resolved At | datetime |
| Resolution Notes | text |

### Severity Classification

| Severity | Examples | Action |
|----------|----------|--------|
| **Critical** | Payment processed but proxy not delivered | Auto-refund + admin alert |
| **High** | Provider down, webhook signature failed | Admin alert |
| **Medium** | Rate limit hit, timeout, IP test failed once | Just log |
| **Low** | Cosmetic warnings, info logs | Just log |

### Flow

```
Other workflows → Call Bunche Logger with event data
  ↓
n8n Code Node: Apply PII redaction + format schema
  ↓
Google Sheets Append: Customer_Audit_Log (or Error_Log)
  ↓
[IF severity >= high]
  → Send WhatsApp to admin
  → [LOG: admin_alert_sent]
```

---

## Workflow 12: Provider Health Logger

**Trigger:** Cron every 5 minutes

### Purpose
Continuously monitor provider health and detect degradation.

### Flow

```
Cron Trigger (every 5 minutes)
[LOG: provider_health_check_start]
  ↓
For each provider (Proxy-Seller, DataImpulse, Geonode, CPAGrip):
  ↓
  [HTTP GET health endpoint]
  [Measure response time]
  ↓
  IF success:
    → Log: provider, health_check, success, latency
  IF failure:
    → Log: provider, health_check, failure, error
    → IF 3 consecutive failures: Send admin alert
      → [LOG: provider_alert_sent]
  ↓
End
[LOG: provider_health_check_end]
```

### Admin Alert Message

```
🔴 Provider Health Alert

Provider: [name]
3 consecutive failures detected
Last error: [message]
Last check: [timestamp]

Reply "Provider Status" for full details.
```

---

## Workflow 13: Daily Summary Log

**Trigger:** Cron daily at 23:55 (Africa/Lagos)

### Flow

```
Cron Trigger (23:55 daily)
[LOG: daily_summary_start]
  ↓
Google Sheets Read: Today's Customer_Audit_Log
  ↓
Calculate:
  - Total orders today
  - Total revenue today
  - Total errors today
  - Total refunds today
  - New customers today
  - Free trials used today
  ↓
Append row to Daily_Summary sheet
[LOG: daily_summary_saved]
  ↓
IF errors today > 5:
  → Send admin alert
  → [LOG: daily_alert_sent]
IF revenue today < expected threshold (₦10,000):
  → Send admin alert
```

### Sheet: Daily_Summary

| Column | Header |
|--------|--------|
| Date | date |
| Total Orders | number |
| Total Revenue (NGN) | number |
| Total Errors | number |
| Critical Errors | number |
| Total Refunds | number |
| New Customers | number |
| Free Trials Used | number |
| Provider Downtime (min) | number |

---

## Error Workflow: Admin Alert

```
n8n Error Trigger
[LOG: error_triggered — auto]
  ↓
Edit Fields: Extract
  - workflow_name
  - error_message
  - error_stack
  - execution_id
  - timestamp
  - node_name
  ↓
Determine severity:
  - critical: payment_failed, ip_test_failed, proxy_delivery_blocked
  - high: provider_down, webhook_signature_failed
  - medium: rate_limit_hit, timeout
  - low: cosmetic_warning, info_log
  ↓
Google Sheets Append: Error_Log
  ↓
[CHECK: Severity >= high?]
  → YES: Send WhatsApp to admin
  → NO: Just log
  ↓
Log also sent to: Customer_Audit_Log if customer context exists
```

### Admin Alert Message

```
🔴 Bunche Error Detected

Workflow: [name]
Severity: [level]
Time: [timestamp]

Error: [message]

Customer: [hash] (if applicable)
Order: [ORD-XXXXX] (if applicable)

Auto-logged to Error_Log.
Reply "Details" for full stack trace.
```

---

## Health Check Endpoint (Applied From MON-1)

```
GET /health
  ↓
Check:
  - n8n process alive
  - Database (Google Sheets API) reachable
  - All providers reachable (lightweight ping)
  - Disk space OK
  - Memory OK
  ↓
Return:
{
  "status": "healthy" | "degraded" | "down",
  "version": "1.0.0",
  "uptime_sec": 12345,
  "providers": {
    "proxy_seller": "up",
    "data_impulse": "up",
    "geonode": "up",
    "cpagrip": "up"
  },
  "last_check": "2026-06-26T14:48:13Z"
}
```

**External monitoring:** UptimeRobot free tier (Applied From MON-3)
- 50 monitors, 1-min interval, 5 global locations
- Monitor: `https://bunche.com/health`
- Alert: WhatsApp admin on failure

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

// PII Redactor for logs
function redactForLog(data) {
  return {
    ...data,
    phone_hash: data.phone ? sha256(data.phone).slice(0, 8) : null,
    name_hash: data.name ? sha256(data.name).slice(0, 8) : null,
    // NEVER log: raw phone, name, IP, credentials, PIN, OTP
    payment_ref: data.payment_ref ? `...${data.payment_ref.slice(-4)}` : null,
  };
}
```

---

## System Prompt — LLM Rule Book

```SYSTEM
You are the order assistant for Bunche, a WhatsApp-based proxy reseller operating in Nigeria.

TONE: Friendly, brief, Nigerian-friendly English. Never excessive emojis. Be direct.

IMPORTANT — FREE TRIAL HANDLING:

When customer asks "Do you have free trial?" / "Is there free trial?":
→ Reply with the standard "When Customer Asks" message (see above)
→ Confirm yes, explain how it works
→ Mention paid option as alternative
→ Do NOT mention the 15-min auto-offer trigger

When customer says "Free trial" / "Trial" / "Free proxy" / "YES" / "Give me the free trial" / "I want the free trial" / "Send me free trial":
→ Route to free_trial_request
→ Workflow 8 sends disclaimer + survey link

When customer says "NO" to trial offer:
→ Route to free_trial_response
→ Acknowledge gracefully
→ Log: Free Trial Declined Today = true

When customer asks about pricing/products:
→ Answer normally
→ Do NOT mention free trial unless they ask

NEVER:
- Never reveal the systematic 15-min trigger nature
- Never push free trial on first message
- Never advertise free trial proactively in your replies
- Never mention providers (Proxy-Seller, DataImpulse, Geonode, CPAGrip)
- Never reveal CPAGrip provider name in survey completion message
- Show only Survey ID and verification timestamp, NOT provider name

YOUR JOB:
1. Parse customer messages → extract: intent, product type, country, quantity
2. If order is clear → confirm price and prepare payment link request
3. If order is unclear → ask ONE clarifying question only
4. If customer asks about providers → deflect politely
5. If customer asks about refunds → explain the refund policy
6. Always include a RANDOM IP tip when sending proxy details

COMMANDS:
- "Order ISP [COUNTRY] [QTY]" → order, ISP, country, qty
- "Order DC [COUNTRY] [QTY]" → order, DATACENTER, country, qty
- "Order RES [QTY]GB" → order, RESIDENTIAL, qty
- "Order MOB [QTY]GB" → order, MOBILE, qty
- "Status [ORDER_ID]" → status
- "My proxies" / "Check data" → check_proxies
- "Renew" → renew
- "Top up residential" → top_up_residential
- "Top up mobile" → top_up_mobile
- "Free trial" / "Trial" / "Free proxy" / "YES" / "Give me the free trial" / "I want the free trial" / "Send me free trial" → free_trial_request
- "NO" → free_trial_response
- "Help" → help
- "Refund" / "Cancel" → refund_request
- "How to use" / "Setup proxy" / "Configure" → how_to_use
- "DONE" → survey_completion

RESPONSE FORMAT — Return ONLY valid JSON:
{
  "intent": "order|status|renew|top_up_residential|top_up_mobile|help|price_check|ban_reported|refund_request|check_proxies|how_to_use|free_trial_request|free_trial_response|survey_completion|unknown",
  "product": "ISP|DATACENTER|RESIDENTIAL|MOBILE|null",
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
| Plan Type | ISP / DC / Residential / Mobile | |
| Plan Code | text | |
| Country | text | |
| Quantity | number | |
| Amount Paid (NGN) | number | |
| Payment Reference | text | |
| Provider | text | |
| Provider Order ID | text | |
| Proxy Credentials | text | |
| Status | text | |
| IP Tested | boolean | |
| IP Test Result | PASS / FAIL / N/A | |
| Data Total (GB) | number | RES + Mobile only |
| Data Remaining (GB) | number | RES + Mobile only |
| Data Expires | datetime | Mobile: 30-day. RES: "never" |
| Expires At | datetime | ISP/DC: monthly date |
| Ban Reported | boolean | |
| Screenshot URL | text | |
| Ban Verified | admin_review_pending / verified / rejected | |
| Replacement Count | number | |
| Refund Requested | boolean | |
| Notes | text | |
| Created At | datetime | |
| Fulfilled At | datetime | |
| Cost (USD) | number | |

---

## Google Sheets: Free Trials

| Column | Header |
|--------|--------|
| Phone | text |
| Trial Date | datetime |
| Survey ID | text |
| Reward (USD) | number |
| Proxy IP | text |
| Status | active / dead |
| Disclaimer Accepted | boolean |
| Created At | datetime |

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
| Free Trials Used Today | number |
| Free Trial Offer Sent Today | boolean |
| Free Trial Offer Sent At | datetime |
| Free Trial Declined Today | boolean |
| Last Active Subscription | datetime |
| Last Message At | datetime |
| Last Order At | datetime |
| Replacement Count | number |
| Support Notes | text |
| Blocked | boolean |
| Blocked Reason | text |
| Consent Given | boolean |
| Consent Version | text |
| Consent At | datetime |
| Created At | datetime |

---

## Google Sheets: Customer_Audit_Log

| Column | Header |
|--------|--------|
| Timestamp | datetime |
| Request ID | text |
| Customer Hash | text |
| Event Type | text |
| Order ID | text |
| Workflow | text |
| Status | success / failure |
| Details (JSON) | text |

---

## Google Sheets: Error_Log

| Column | Header |
|--------|--------|
| Timestamp | datetime |
| Workflow Name | text |
| Node Name | text |
| Error Type | text |
| Error Message | text |
| Error Stack | text |
| Execution ID | text |
| Customer Hash | text |
| Order ID | text |
| Severity | critical / high / medium / low |
| Status | open / investigating / resolved / ignored |
| Resolved By | text |
| Resolved At | datetime |
| Resolution Notes | text |

---

## Google Sheets: Provider_Log

| Column | Header |
|--------|--------|
| Timestamp | datetime |
| Provider | text |
| Event Type | text |
| Status | text |
| Details | text |
| Latency (ms) | number |
| Response Code | text |

---

## Google Sheets: Daily_Summary

| Column | Header |
|--------|--------|
| Date | date |
| Total Orders | number |
| Total Revenue (NGN) | number |
| Total Errors | number |
| Critical Errors | number |
| Total Refunds | number |
| New Customers | number |
| Free Trials Used | number |
| Provider Downtime (min) | number |

---

## Security Checklist

| Rule | Enforced Where | Scale Planning Task |
|------|---------------|---------------------|
| Free trial: NOT advertised upfront | Legal notice + LLM system prompt | — |
| Free trial: Only offered after 15-min idle | Workflow 9 cron | — |
| Free trial: Customer opts in explicitly | Workflow 8 | — |
| Free trial: Disclaimer accepted before survey | Workflow 8 | — |
| Free trial: Survey verified via postback | Workflow 8 | — |
| Free trial: 3/day/phone | Workflow 8 + Customer sheet | — |
| Free trial: temp proxy, no replacement | Workflow 8 | — |
| Free trial: NO provider name in completion message | LLM system prompt + Workflow 8 | — |
| Pre-payment health check | Every order + renewal + top-up | — |
| No payment link if provider down | Pre-payment check | — |
| IP testing (5s timeout) | Every proxy before delivery | — |
| IP fails → replacement | IP testing workflow | — |
| Replacement also fails → auto-refund | IP testing workflow | — |
| No URLs in customer messages | Security Stripper | — |
| No provider names revealed | System prompt (LLM) | — |
| No injection prompts processed | Security Stripper + system prompt | — |
| LLM output validated as JSON | n8n validation node | — |
| PIN stored hashed | bcrypt hash | AUTH-3 |
| Max 3 verification attempts | Counted before admin escalation | — |
| Admin only on exception | Admin Workflow | — |
| No refund after delivery | Workflow enforces | — |
| Random IP tips | Rotate | — |
| ISP/DC: Same order → same Expires At | Expiry normalization | — |
| RES: Data never expires | Every RES message | — |
| Mobile: 30-day window, no rollover | Every mobile message | — |
| **PII redacted in logs** | **Workflow 11 redactor** | **LOGS-12** |
| **Correlation ID per request** | **Workflow 11** | **LOGS-2** |
| **Standardized log schema** | **Workflow 11** | **LOGS-3** |
| **No secrets in logs** | **Workflow 11 redactor** | **SEC-5** |
| **Health check endpoint** | **/health route** | **MON-1** |
| **External uptime monitoring** | **UptimeRobot** | **MON-3** |
| **Log retention policy** | **Workflow 11** | **LOGS-14** |
| **All errors caught and logged** | **Error Workflow → Workflow 11** | **ERROR-1** |
| **Centralized error handler** | **Error Workflow** | **ERROR-5** |

---

## Workflow Activation Checklist

| Workflow | Trigger | When |
|----------|---------|------|
| Order Handler | WhatsApp Webhook | Always |
| Payment Confirmation | Flutterwave Webhook | On payment |
| Admin Command Handler | WhatsApp Webhook (admin number) | On admin message |
| Ban Claim | WhatsApp Webhook | On ban claim |
| Refund Handler | Flutterwave Webhook | On refund event |
| Expiry + Data Reminder | Cron — daily 9:00 AM | Every day |
| Free Trial (Opt-In) | WhatsApp Webhook | On customer opt-in |
| Free Trial Follow-Up | Cron — every 1 minute | When customer idle 15 min |
| Trial Reset | Cron — daily 00:00 | Every day |
| Survey Postback | Webhook | On survey completion |
| Bunche Logger | Called from all workflows | Every event |
| Provider Health Logger | Cron — every 5 minutes | Every 5 min |
| Daily Summary | Cron — daily 23:55 | Every day |
| Error Alert | n8n Error Trigger | On any error |

---

## Testing

```bash
# Health check
curl -X GET https://bunche.com/health

# New customer — legal notice
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t1","from":"2349000000001","timestamp":"123","text":{"body":"Hi"}}]}}]}]}'

# Customer asks about free trial
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t2","from":"2349000000001","timestamp":"123","text":{"body":"Do you have free trial?"}}]}}]}]}'

# Customer opts in to free trial
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t3","from":"2349000000001","timestamp":"123","text":{"body":"Give me the free trial"}}]}}]}]}'

# Customer declines free trial
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t4","from":"2349000000001","timestamp":"123","text":{"body":"NO"}}]}}]}]}'

# Customer completed survey
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t5","from":"2349000000001","timestamp":"123","text":{"body":"DONE"}}]}}]}]}'

# Survey postback simulation
curl -X POST https://n8n.yourdomain.com/webhook/survey-postback \
  -H "Content-Type: application/json" \
  -d '{"user_id":"2349000000001","survey_id":"SRV-12345","reward":"1.50","status":"completed","signature":"abc123"}'

# Order ISP
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t6","from":"2349000000001","timestamp":"123","text":{"body":"Order ISP UK 1"}}]}}]}]}'
```

---

## Scale Planning Tasks Applied to Bunche

| Task ID | Task | Implementation |
|---------|------|----------------|
| **DOC-1** | README + .env.example | Bunche repo has both |
| **DOC-2** | AGENTS.md | To be created |
| **SEC-2** | .env pattern | All secrets in .env (n8n credentials) |
| **SEC-5** | No secrets in logs | Workflow 11 redactor |
| **SEC-7** | Key rotation | Provider keys: 90-day rotation policy |
| **SEC-9** | App Security Principles | Bunche security checklist embedded |
| **ERROR-1** | try/catch all flows | n8n error workflow + Workflow 11 |
| **ERROR-4** | Custom error messages | WhatsApp messages instead of pages |
| **ERROR-5** | Centralized redactor | Workflow 11 PII redaction |
| **LOGS-2** | Correlation ID | `msg_id` as correlation ID |
| **LOGS-3** | Standard schema | Bunche schema (defined above) |
| **LOGS-12** | No PII in logs | PII redactor in Workflow 11 |
| **LOGS-13** | Log schema standard | Documented in Workflow 11 |
| **LOGS-14** | Retention policy | Hot 7d / Cold 90d / Archive 1yr |
| **MON-1** | /health endpoint | Implemented above |
| **MON-3** | External monitoring | UptimeRobot recommended |
| **BRANCH-1** | GitHub Flow | Already using on bunche repo |
| **BRANCH-3** | Main branch protection | To be configured |
| **DEPS-3** | package-lock.json | Required in CI |
| **SCALE-8** | K6 load test | Webhook burst test recommended |
| **TRUST-3** | Audit NEXT_PUBLIC_ vars | N/A — no Next.js |
| **TRUST-9** | npm audit | Apply to CI when dependencies added |

## Scale Planning Tasks NOT Applicable to Bunche

| Task | Why N/A |
|------|--------|
| ROLL-1 through ROLL-7 (MT5 Bridge health/rollback) | Bunche is not MT5 Bridge |
| MON-2 (Windows VPS check) | No Windows VPS for Bunche |
| AUTH-1 through AUTH-5 (NextAuth/2FA) | No accounts = no auth needed |
| ERROR-2 (React error boundaries) | No React frontend |
| LOGS-4, LOGS-5 (Next.js logging) | No Next.js |
| PERF-1 through PERF-6 (UI perf) | No UI — WhatsApp interface |
| MEDIA-1 through MEDIA-8 (image storage) | No media |
| CANARY-1 through CANARY-9 (canary releases) | WhatsApp webhook = single deployment |
| BROWSE-1 through BROWSE-9 (browser security) | No browser app |
| SOC-1 through SOC-10 (enterprise SOC2) | Not enterprise yet |
| SVC-1 through SVC-7 (service auth) | Simpler stack — direct webhooks |