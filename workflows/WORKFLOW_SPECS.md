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
| **Task** | ONE survey per IP (CPAGrip) |
| **Verification** | CPAGrip postback webhook |
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
- If customer says "Free trial" / "Trial" / "Free proxy" / "YES" → Route to Workflow 8

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

**Step 4: Customer Says YES**
```
Customer: "YES"
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
CPAGrip postback → Bunche webhook (auto-verified)
  ↓
Bunche: Pull Geonode Free proxy → Test (5s) → Send
  ↓
WhatsApp:
"🎁 FREE TRIAL PROXY — TEMPORARY

🔗 IP: 1.2.3.4:8080
📍 Location: US (best effort)
⏰ TEMPORARY — lasts until it dies

━━━━━━━━━━━━━━━━━━
⚠️ REMINDER — FREE TRIAL TERMS
━━━━━━━━━━━━━━━━━━

This proxy is from a public source.

❌ NOT guaranteed to work
❌ May stop working anytime
❌ Used at YOUR OWN RISK

📊 Today's trial usage: 1 of 3 used

🚀 Want reliable proxies?
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo
💻 Datacenter — ₦3,000/mo
🌐 Residential 5GB — ₦9,500
📱 Mobile 4G 5GB — ₦20,000

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
| Free trial: survey completion verified | CPAGrip postback ✅ |
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
  → Google Sheets Read: Lookup price + country
  → [PRE-PAYMENT HEALTH CHECK]
    → Call Proxy-Seller / DataImpulse API
    → Check: Is country/provider available?
      → ❌ UNAVAILABLE or DOWN:
        → WhatsApp: "Sorry, [product] for [country] is
           temporarily unavailable right now."
        → END
      → ✅ AVAILABLE:
        → Continue ↓
  → HTTP Request → Flutterwave POST /payments
  → Google Sheets Append: Pending_Orders (awaiting_payment)
  → WhatsApp: "Payment link sent! ₦[price] 💳"

intent == "lost proxy details":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → WhatsApp: Send all proxy details + RANDOM IP TIP

intent == "my proxies" OR "check data":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → WhatsApp: All proxies + status + RANDOM IP TIP

intent == "check expiry" OR "days left":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Show all with days / data remaining

intent == "ban reported" OR "ip blocked":
  → Was order within 24hrs?
    → YES: "Send screenshot." → Save → ban_pending_review → [ADMIN ALERT]
    → NO: "Replacement only within 24hrs."

intent == "refund":
  → Status == "awaiting_payment": Cancel, refund
  → Status == "fulfilled": "No refund after delivery."

intent == "help":
  → Send help menu + RES vs MOB warning + RANDOM IP TIP

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

intent == "top up residential":
  → Google Sheets Read: Find residential proxy
  → Present top-up options (5GB / 10GB)
  → [PRE-PAYMENT HEALTH CHECK] → Check DataImpulse availability
  → Generate payment link
  → Payment confirmed → Add GB → Data Remaining updated
  → WhatsApp: "✅ Top up confirmed!" + RANDOM IP TIP

intent == "top up mobile":
  → Google Sheets Read: Find mobile proxy
  → Present top-up options (5GB / 10GB)
  → [PRE-PAYMENT HEALTH CHECK] → Check DataImpulse availability
  → Generate payment link
  → Payment confirmed → Add GB → Proxy reactivated
  → WhatsApp: "✅ Top up confirmed! ⚠️" + RANDOM IP TIP

intent == "free_trial" OR "trial" OR "free proxy" OR "free IP":
  → Check daily limit
  → If eligible: Send disclaimer + survey link
  → If not eligible: "You've used all 3 free trials today."

intent == "how to use" OR "setup proxy" OR "configure":
  → Send proxy setup guide + RANDOM IP TIP

Default:
  → LLM reply
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

intent == "free_trial" OR "trial" OR "free proxy" OR "free IP":
  → Check daily limit
  → If eligible: Send disclaimer + survey link
  → If not eligible: "You've used all 3 free trials today."

intent == "help":
  → Legal notice + RES vs MOB warning + RANDOM IP TIP + help menu

intent == "lost proxy details":
  → WhatsApp: "Enter PIN or OTP"
    → PIN verify / OTP verify
      → Match: Send details + RANDOM IP TIP
      → Fail 3x: [ADMIN ALERT]

Default:
  → LLM reply
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
  → IF fails → Try backup provider
    → All fail: Refund immediately → [ADMIN ALERT] → END
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
          → Respond HTTP 200 → END
  ↓
  [IF ISP or DC]:
    → [EXPIRY NORMALIZATION] — All → same Expires At
    → Google Sheets: Status = "fulfilled"
    → [PDF] → WhatsApp: Details + Receipt + RANDOM IP TIP
  ↓
  [IF RESIDENTIAL]:
    → Google Sheets: Data Total = [X]GB, Data Remaining = [X]GB, Data Expires = "never"
    → Google Sheets: Status = "active"
    → [PDF] → WhatsApp: Details + Receipt + "data never expires" + RANDOM IP TIP
  ↓
  [IF MOBILE]:
    → Google Sheets: Data Total = [X]GB, Data Remaining = [X]GB, Data Expires = today + 30 days
    → Google Sheets: Status = "active"
    → [PDF] → WhatsApp: Details + Receipt + mobile warning + RANDOM IP TIP
  ↓
[IF ISP/DC RENEWAL — IP active]:
  → [IP TESTING] → Test existing IP before extending
    → If IP still works: Extend +30 days → Send confirmation
    → If IP fails: Generate replacement → Test → Deliver
  → Google Sheets Update: Status = "fulfilled"
  → WhatsApp: "✅ Extended! Same IP." + RANDOM IP TIP
  ↓
[IF ISP/DC RENEWAL — IP expired]:
  → Provider API: Generate NEW proxy
  → [IP TESTING] → Test new IP (5s)
    → If PASS: Deliver + RANDOM IP TIP
    → If FAIL: Refund immediately + [ADMIN ALERT]
  → WhatsApp: "✅ New proxy ready!" + RANDOM IP TIP
  ↓
[IF RESIDENTIAL RENEWAL]:
  → Fresh GB added to pool
  → Google Sheets Update: Data Remaining += [X]GB
  → WhatsApp: "✅ Residential renewed! +[X]GB. 📦 Total: [Y]GB. 💡" + RANDOM IP TIP
  ↓
[IF MOBILE RENEWAL]:
  → Fresh GB — old unused GB LOST
  → [PRE-PAYMENT HEALTH CHECK] → Check DataImpulse
    → If DOWN: Refund + notify customer
    → If UP: Continue
  → Google Sheets Update: Data Total = [X]GB, Data Remaining = [X]GB, Data Expires = today + 30 days
  → WhatsApp: "✅ Mobile renewed! ⚠️ Old unused GB lost." + RANDOM IP TIP
  ↓
[IF RESIDENTIAL TOP-UP]:
  → [PRE-PAYMENT HEALTH CHECK] → DataImpulse
    → If DOWN: Refund + notify
    → If UP: Continue
  → Provider API: Add GB to order
  → Google Sheets Update: Data Remaining += [X]GB
  → WhatsApp: "✅ Top up confirmed! +[X]GB. Total: [Y]GB. 💡" + RANDOM IP TIP
  ↓
[IF MOBILE TOP-UP]:
  → [PRE-PAYMENT HEALTH CHECK] → DataImpulse
    → If DOWN: Refund + notify
    → If UP: Continue
  → Provider API: Add GB to order
  → Google Sheets Update: Data Remaining = [X]GB, Data Expires = today + 30 days
  → WhatsApp: "✅ Top up confirmed! ⚠️" + RANDOM IP TIP
  ↓
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
"Pending" → List all pending actions
"Approve ORD-XXXXX" → Route: ban → replace; refund → refund
"Reject ORD-XXXXX [reason]" → Reject, notify customer
"Block [phone] [reason]" → Block in Google Sheets
"Unblock [phone]" → Unblock
"Details ORD-XXXXX" → Full summary
"Refund ORD-XXXXX" → Check status → refund or warn
"Force-Refund ORD-XXXXX" → Admin override
"Provider Status" → Check all providers → Report
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

### CPAGrip API (For Free Trial Survey Verification)
**Postback URL:** https://n8n.yourdomain.com/webhook/cpagrip-postback?user_id={USER_ID}&reward={REWARD}

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
  [FOR ISP/DC]: Expires At ≤ 7 days → Reminder
  [FOR Residential]: Data Remaining ≤ 1GB → Warning; 0GB → Exhausted
  [FOR Mobile]: Data ≤ 1GB → Warning; 0GB → Exhausted; Expires ≤ 3 days → Reminder
```

---

## Workflow 8: Free Trial — Customer Opt-In

**Trigger:** Customer says "Free trial" / "Trial" / "Free proxy" / "YES" (after Workflow 9 offer)

### Step 1: Check Daily Limit
```
Google Sheets Read: Count trials for this phone today
  ↓
  ❌ Count >= 3:
    → WhatsApp: "You've used all 3 free trials today."
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
```

### Step 3: Survey Completion

**Option A — CPAGrip Postback Webhook:**
```
Webhook Trigger (CPAGrip POST)
  ↓
Verify CPAGrip HMAC signature
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
  → END
```

### Step 5: Log + Send Proxy

```
Google Sheets Append: Free_Trials
  - Phone, Trial Date, Provider, Survey ID, Reward, Proxy IP, Status, Disclaimer Accepted
  ↓
WhatsApp:
"🎁 FREE TRIAL PROXY — TEMPORARY

🔗 IP: [IP]:[PORT]
📍 Location: [location]
⏰ TEMPORARY — lasts until it dies

━━━━━━━━━━━━━━━━━━
⚠️ REMINDER — FREE TRIAL TERMS
━━━━━━━━━━━━━━━━━━

This proxy is from a public source.

❌ NOT guaranteed to work
❌ May stop working anytime
❌ Used at YOUR OWN RISK

📊 Today's trial usage: 1 of 3 used

🚀 Want reliable proxies?
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo
💻 Datacenter — ₦3,000/mo
🌐 Residential 5GB — ₦9,500
📱 Mobile 4G 5GB — ₦20,000

{RANDOM IP TIP}
━━━━━━━━━━━━━━━━━━"
```

---

## Workflow 9: Free Trial Follow-Up (15-Minute Idle Cron)

**Trigger:** Cron every 1 minute

### Purpose
Find customers who browsed but didn't buy, idle 15+ minutes, and offer them a free trial.

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
```

### Why This Works
- Only targets browsing-but-not-buying customers
- 15-min delay feels natural, not pushy
- Filters out customers with active subscriptions (focus on their current order)
- One offer per day (not spam)
- Easy opt-out (NO)

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

IMPORTANT — FREE TRIAL HANDLING:

When customer asks "Do you have free trial?" / "Is there free trial?":
→ Reply with the standard "When Customer Asks" message (see above)
→ Confirm yes, explain how it works
→ Mention paid option as alternative
→ Do NOT mention the 15-min auto-offer trigger

When customer says "Free trial" / "Trial" / "Free proxy" / "YES" (after offer):
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
- "Free trial" / "Trial" / "Free proxy" / "YES" → free_trial_request
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
| Provider | CPAGrip |
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

## Security Checklist

| Rule | Enforced Where |
|------|---------------|
| Free trial: NOT advertised upfront | Legal notice + LLM system prompt |
| Free trial: Only offered after 15-min idle | Workflow 9 cron |
| Free trial: Customer opts in explicitly | Workflow 8 (YES/NO) |
| Free trial: Disclaimer accepted before survey | Workflow 8 |
| Free trial: Survey verified via CPAGrip postback | Workflow 8 |
| Free trial: 3/day/phone | Workflow 8 + Customer sheet |
| Free trial: temp proxy, no replacement | Workflow 8 |
| Pre-payment health check | Every order + renewal + top-up |
| No payment link if provider down | Pre-payment check |
| IP testing (5s timeout) | Every proxy before delivery |
| IP fails → replacement | IP testing workflow |
| Replacement also fails → auto-refund | IP testing workflow |
| No URLs in customer messages | Security Stripper |
| No provider names revealed | System prompt (LLM) |
| No injection prompts processed | Security Stripper + system prompt |
| LLM output validated as JSON | n8n validation node |
| PIN stored hashed | bcrypt hash |
| Max 3 verification attempts | Counted before admin escalation |
| Admin only on exception | Admin Workflow |
| No refund after delivery | Workflow enforces |
| Random IP tips | Rotate |
| ISP/DC: Same order → same Expires At | Expiry normalization |
| RES: Data never expires | Every RES message |
| Mobile: 30-day window, no rollover | Every mobile message |

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
| CPAGrip Postback | Webhook | On survey completion |
| Error Alert | n8n Error Trigger | On any error |

---

## Testing

```bash
# New customer — legal notice (NO free trial mention)
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
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t3","from":"2349000000001","timestamp":"123","text":{"body":"Free trial"}}]}}]}]}'

# Customer declines free trial
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t4","from":"2349000000001","timestamp":"123","text":{"body":"NO"}}]}}]}]}'

# Customer completed survey
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t5","from":"2349000000001","timestamp":"123","text":{"body":"DONE"}}]}}]}]}'

# CPAGrip postback simulation
curl -X POST https://n8n.yourdomain.com/webhook/cpagrip-postback \
  -H "Content-Type: application/json" \
  -d '{"user_id":"2349000000001","survey_id":"SRV-12345","reward":"1.50","status":"completed","signature":"abc123"}'

# Order ISP
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t6","from":"2349000000001","timestamp":"123","text":{"body":"Order ISP UK 1"}}]}}]}]}'
```