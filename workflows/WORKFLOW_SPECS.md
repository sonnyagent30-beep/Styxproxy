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

```
Customer selects product → We check provider availability FIRST
→ If provider is UP + IPs available → Generate payment link
→ If provider is DOWN or no IPs → Tell customer, don't charge them
```

---

## IP Testing — Overview

**We test every IP before sending it to a customer.**

```
Provider returns IP → We test it (5 second timeout)
→ If IP responds → Send to customer ✅
→ If IP fails → Request replacement → Test replacement
→ If replacement fails → Refund customer automatically ✅
```

---

## Free Trial Workflow — Survey-Based

**Customers can earn FREE temporary proxy IPs by completing surveys.**

### Rules

| Rule | Detail |
|------|--------|
| **Trial duration** | TEMPORARY — until proxy dies |
| **Daily limit** | 3 IPs per phone number per DAY |
| **Task type** | ONE survey per IP (only survey, no other tasks) |
| **Verification** | CPAGrip postback webhook |
| **Free proxy source** | Geonode Free API |
| **No replacement** | Dead proxy = complete another survey |
| **Reset** | Daily midnight (Africa/Lagos) |

### Why Survey Only

| Reason | Benefit |
|--------|---------|
| Simple for customer | No confusion picking from wall |
| Fast verification | Survey completion = postback fires |
| Reasonable payout | $0.30-$3.00 per survey |
| Universal | Works on any device |
| Reliable verification | Survey networks track real completions |

### Flow

```
Customer: "Free trial"
  ↓
Bunche: Check Google Sheets → trials today for phone
  ↓
  ❌ Already 3 today:
    "You've used all 3 free trials today.
    Resets at midnight. Upgrade for unlimited! 🚀"
  ↓
  ✅ Available (less than 3):
    "🎁 FREE TRIAL — COMPLETE A SURVEY

    Complete ONE survey to unlock 1 free IP:

    [CPAGRIP SURVEY LINK]

    Pick a survey, complete it, then reply DONE.
    Average survey: 2-5 minutes."
  ↓
Customer completes survey
  ↓
CPAGrip postback → Bunche webhook (auto)
  ↓
Bunche: Verify postback signature + ID
  ↓
  ✅ Verified:
    → Geonode Free API → pull proxy
    → Test (3 attempts max, 5s each)
    → Log: Trials Today += 1, Survey ID, Reward
    → Send proxy + disclaimer
    → "Trial logged. 2 more available today."
  ↓
  ❌ Not verified:
    "Survey not detected as complete yet.
    Please try again in a few minutes."
```

### What Customer Receives

```
🎁 FREE TRIAL PROXY — TEMPORARY

🔗 IP: 1.2.3.4:8080
📍 Location: US (best effort)
⏰ TEMPORARY — lasts until it dies

━━━━━━━━━━━━━━━━━━
⚠️ READ BEFORE USING ⚠️
━━━━━━━━━━━━━━━━━━

This is a FREE trial proxy.

❌ NOT guaranteed to work
❌ NOT guaranteed stable
❌ May stop working anytime
❌ Use at YOUR OWN RISK

✅ For testing only
✅ Not for production/critical tasks
✅ No replacement if it dies

━━━━━━━━━━━━━━━━━━
📊 Today's trial usage:
   1 of 3 used

🚀 Want reliable proxies?
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo
💻 Datacenter — ₦3,000/mo
🌐 Residential 5GB — ₦9,500
📱 Mobile 4G 5GB — ₦20,000

{RANDOM IP TIP}
━━━━━━━━━━━━━━━━━━
```

### Geonode Free API Integration

```
GET https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps
```

Returns JSON list of public proxies. Bunche pulls 5-10, tests each (5s timeout), sends the working one.

### Revenue Model (Per Survey)

| Survey type | Avg payout | Net per trial |
|-------------|-----------|--------------|
| Quick survey (2 min) | $0.30-0.80 | ₦414-1,104 |
| Medium survey (5 min) | $0.80-2.00 | ₦1,104-2,760 |
| Long survey (10 min) | $2.00-3.00 | ₦2,760-4,140 |

**Average revenue per trial: ~$1.00 = ₦1,380**

### Reset Logic

```
Daily midnight (Africa/Lagos):
  → Clear trials count
  → Fresh 3 trials available
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

## Legal Notice

**New customers only.**

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
→ Residential: Data NEVER expires
→ Mobile: 30-day window, unused GB lost

{RANDOM IP TIP}

🎁 FREE TRIAL: Complete 1 survey, get 1 free IP!
3 trials per day. Type "Free trial".

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
[IF INTENT == "free_trial"] → Workflow 8: Free Trial (Survey)
[IF INTENT == "order"] → Continue ↓
        ↓
[PRE-PAYMENT HEALTH CHECK]
  → Call provider API → Check availability
  → If DOWN → Tell customer, NO payment link
  → If UP → Continue
        ↓
[IF ROUTINE ORDER] → Flutterwave payment link
  ↓
[POST-PAYMENT] → Provider generates proxy
        ↓
[IP TESTING] → Test IP with 5-second timeout
  → If PASS → Deliver to customer ✅
  → If FAIL → Request replacement → Test replacement
  → If replacement also FAIL → Refund automatically ✅
        ↓
[PDF receipt] → WhatsApp delivery
```

---

## The Core Principle

| What happens | Who does it |
|-------------|------------|
| Free trial (survey-based) | n8n ✅ |
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
           temporarily unavailable right now.
           Please try again in a few minutes 🙏"
        → Webhook Response: HTTP 200
        → END
      → ✅ AVAILABLE:
        → Continue ↓
  → HTTP Request → Flutterwave POST /payments
  → Google Sheets Append: Pending_Orders (awaiting_payment)
  → WhatsApp: "Payment link sent! ₦[price] 💳"

intent == "free_trial" OR "free proxy" OR "trial":
  → Route to Workflow 8 (Free Trial - Survey)

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
  → Send help menu + RES vs MOB warning + free trial info + RANDOM IP TIP

intent == "renew":
  → Google Sheets Read: Get ALL proxies — NO LIMIT
  → Present all with status
  → Customer selects which to renew
  ↓
  [PRE-PAYMENT HEALTH CHECK]
    → Check provider availability
      → ❌ UNAVAILABLE: "Sorry, service is down. Try again shortly."
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

intent == "how to use" OR "setup proxy" OR "configure":
  → Send proxy setup guide + RANDOM IP TIP

Default:
  → LLM reply
```

### Workflow 1b: New Customer

```
intent == "order":
  → Legal notice (already shown) — continue to order
  → [PRE-PAYMENT HEALTH CHECK] → Check provider availability
    → ❌ UNAVAILABLE: "Sorry, [product] is temporarily unavailable. Try again in a few minutes."
    → ✅ AVAILABLE: Continue
  → Google Sheets Read: Lookup price
  → Flutterwave payment link → WhatsApp: "Payment link sent."
  → Log consent (first interaction)

intent == "free_trial":
  → Route to Workflow 8 (Free Trial - Survey)

intent == "help":
  → Legal notice + RES vs MOB warning + free trial info + RANDOM IP TIP + help menu

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
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo
🌏 Premium ISP — ₦7,500/mo
💻 Datacenter — ₦3,000/mo
🌐 Residential 5GB — ₦9,500
📱 Mobile 4G 5GB — ₦20,000
━━━━━━━━━━━━━━━━━━

💡 IMPORTANT — RESIDENTIAL vs MOBILE:
→ Residential: Data NEVER expires!
→ Mobile: 30-day window, unused GB lost!

🎁 FREE TRIAL: Complete 1 survey, get 1 free IP!
3 trials per day. Type "Free trial".

{RANDOM IP TIP}

TO ORDER: Reply with:
"Order ISP [country] [qty]"

TYPE "help" for support.
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

🎁 FREE TRIAL:
"Free trial" — complete a survey, get 1 free IP

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
             has been automatically refunded.
             We'll notify you when service is restored. 🙏"
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

### IP Testing Code (n8n Code Node)

```javascript
// IP Connectivity Test — 5 second timeout
const http = require('http');
const https = require('https');

function testIP(ip, port, protocol = 'http') {
  return new Promise((resolve) => {
    const client = protocol === 'https' ? https : http;
    const start = Date.now();
    
    const req = client.get({
      host: ip,
      port: port,
      timeout: 5000,
      rejectUnauthorized: false,
    }, (res) => {
      resolve({ ok: true, latency: Date.now() - start, status: res.statusCode });
    });
    
    req.on('timeout', () => {
      req.destroy();
      resolve({ ok: false, reason: 'timeout' });
    });
    
    req.on('error', (e) => {
      resolve({ ok: false, reason: e.message });
    });
  });
}

function testIPSocket(ip, port) {
  return new Promise((resolve) => {
    const net = require('net');
    const start = Date.now();
    
    const socket = new net.Socket();
    socket.setTimeout(5000);
    
    socket.connect(port, ip, () => {
      socket.destroy();
      resolve({ ok: true, latency: Date.now() - start });
    });
    
    socket.on('timeout', () => {
      socket.destroy();
      resolve({ ok: false, reason: 'timeout' });
    });
    
    socket.on('error', (e) => {
      socket.destroy();
      resolve({ ok: false, reason: e.message });
    });
  });
}

async function runTest(ip, port) {
  let result = await testIP(ip, port, 'http');
  if (result.ok) return result;
  result = await testIPSocket(ip, port);
  return result;
}

const proxy = $input.first().json;
const [ip, port] = proxy.ip_port.split(':').filter(Boolean);

const testResult = await runTest(ip, parseInt(port));

return {
  json: {
    order_id: proxy.order_id,
    ip: ip,
    port: parseInt(port),
    test_result: testResult.ok ? 'PASS' : 'FAIL',
    latency_ms: testResult.latency || null,
    fail_reason: testResult.reason || null,
    timestamp: new Date().toISOString()
  }
};
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

### Recovery Setup Messages (First Purchase Only)

```
✅ Payment confirmed!

Before your proxy is delivered,
set up quick security for your next visit:

1️⃣ PIN — Set a 4-digit PIN
2️⃣ OTP — Get code via WhatsApp

Reply "1" or "2" 👇
```

**If PIN:** "Reply with your 4-digit PIN 👇"
**If OTP:** "Got it! Code will be sent when needed. ✅"
**Name:** "What should we call you? 👇"

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
"Force-Refund ORD-XXXXX" → Admin override, log as exemption
"Provider Status" → Check all providers → Report to admin
Default → "Unknown command. Type 'Pending'."
```

### Provider Status Check (Admin Command)

```
"Provider Status":
  → HTTP GET → Proxy-Seller API: Check balance + countries
    → ✅ OK: "Proxy-Seller: ✅ Working"
    → ❌ DOWN: "Proxy-Seller: ❌ Down"
  → HTTP GET → DataImpulse API: Check balance
    → ✅ OK: "DataImpulse: ✅ Working"
    → ❌ DOWN: "DataImpulse: ❌ Down"
  → WhatsApp (admin): Full status report
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

**Order:**
```
POST https://api.proxy-seller.com/v1/orders
Body: {"type": "isp", "country": "gb", "quantity": 1, "period": 30}
Response: {"order_id": "PS-12345", "status": "active", "proxies": [...]}
```

**Health Check (Pre-Payment):**
```
GET https://api.proxy-seller.com/v1/countries
GET https://api.proxy-seller.com/v1/balance
Response: {"countries": [...], "balance": "100.00"}
→ If balance > 0 AND country in list → AVAILABLE
→ If balance == 0 OR country not in list → UNAVAILABLE
→ If API error → UNAVAILABLE
```

**IP Replacement:**
```
POST https://api.proxy-seller.com/v1/order/{order_id}/replace
Response: {"order_id": "PS-12345", "new_proxy": "5.6.7.8:8080"}
Limit: 1 replacement per day per proxy
```

### DataImpulse API (Residential + Mobile)

**Order:**
```
POST https://api.dataimpulse.com/v1/order
Body: {"type": "residential", "country": "global", "traffic": "5GB"}
Response: {"order_id": "DI-12345", "status": "active", "data_total": "5GB", ...}
```

**Health Check (Pre-Payment):**
```
GET https://api.dataimpulse.com/v1/locations
GET https://api.dataimpulse.com/v1/balance
Response: {"locations": [...], "balance": "50.00"}
→ If balance > cost of requested plan → AVAILABLE
→ If balance < cost → UNAVAILABLE
→ If API error → UNAVAILABLE
```

### Geonode Free Proxy API (For Free Trial)

```
GET https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps
```

Returns JSON list of public proxies. Bunche pulls 5-10, tests each (5s timeout), sends the working one.

### Fallback Chain

```
Proxy-Seller (ISP/DC) → Fails → [PRE-PAYMENT CHECK CATCHES → No payment link]
DataImpulse (RES/Mobile) → Fails → [PRE-PAYMENT CHECK CATCHES → No payment link]
Geonode Free (Trial) → Fails → Try next proxy from list
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
  [FOR ISP/DC]: Expires At ≤ 7 days → Reminder
  [FOR Residential]: Data Remaining ≤ 1GB → Warning; 0GB → Exhausted
  [FOR Mobile]: Data ≤ 1GB → Warning; 0GB → Exhausted; Expires ≤ 3 days → Reminder
  ↓
  [IF nothing to remind]: Do nothing
```

---

## Workflow 8: Free Trial — Survey-Based

**Trigger:** Customer says "Free trial", "free proxy", "trial", or similar

### Step 1: Check Daily Limit

```
Google Sheets Read: Count trials for this phone today
  ↓
  ❌ Count >= 3:
    → WhatsApp: "You've used all 3 free trials today.
       Resets at midnight. Upgrade to a paid plan
       for unlimited proxies! 🚀"
    → END
  ↓
  ✅ Count < 3:
    → Continue to Step 2
```

### Step 2: Send Survey Link

```
WhatsApp: "🎁 FREE TRIAL — COMPLETE A SURVEY

Complete ONE survey to unlock 1 free IP:

[CPAGRIP SURVEY LINK]

Pick a survey, complete it, then reply DONE.
Average survey: 2-5 minutes.

📊 Today's trial usage: [X] of 3 used"
```

### Step 3: Wait for Survey Completion

```
Option A — CPAGrip Postback Webhook:
  Webhook Trigger (CPAGrip POST)
  ↓
  Verify CPAGrip signature
  ↓
  Extract: user_id, survey_id, reward, status
  ↓
  IF status === "completed":
    → Generate unique trial token
    → Store: phone, token, survey_id, reward, expires_at
    → Customer gets auto-message (or reply DONE)
  ↓
  IF status !== "completed":
    → Ignore (postback noise)

Option B — Customer Says DONE:
  Customer: "DONE"
  ↓
  Check Google Sheets for matching survey completion by phone
  ↓
  IF found: Continue to Step 4
  IF not found: "Survey not detected yet. Try in a few minutes."
```

### Step 4: Get Proxy from Geonode Free API

```
GET https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps
  ↓
Parse JSON → get list of proxies
  ↓
For each proxy in list:
  [TEST PROXY — 5 second timeout]
  ↓
  IF PASS:
    → Continue to Step 5
    → BREAK
  IF FAIL:
    → Try next proxy
  ↓
IF all 10 fail:
  → WhatsApp: "Sorry, no working proxies available right now.
     Please try again in a few minutes 🙏"
  → END
```

### Step 5: Log Trial + Send Proxy

```
Google Sheets Append: Free_Trials
  - Phone: [phone]
  - Trial Date: now()
  - Provider: CPAGrip
  - Survey ID: [survey_id]
  - Reward (USD): [amount]
  - Proxy IP: [ip]
  - Status: active
  - Created At: now()
  ↓
Google Sheets Update: Customers
  - Today's trial count += 1
  ↓
WhatsApp Customer:
"🎁 FREE TRIAL PROXY — TEMPORARY

🔗 IP: [IP]:[PORT]
📍 Location: [location] (best effort)
⏰ TEMPORARY — lasts until it dies

━━━━━━━━━━━━━━━━━━
⚠️ READ BEFORE USING ⚠️
━━━━━━━━━━━━━━━━━━

This is a FREE trial proxy.

❌ NOT guaranteed to work
❌ NOT guaranteed stable
❌ May stop working anytime
❌ Use at YOUR OWN RISK

✅ For testing only
✅ Not for production/critical tasks
✅ No replacement if it dies

━━━━━━━━━━━━━━━━━━
📊 Today's trial usage:
   [X] of 3 used

🚀 Want reliable proxies?
🇬🇧🇺🇸🇩🇪 ISP — ₦6,500/mo
💻 Datacenter — ₦3,000/mo
🌐 Residential 5GB — ₦9,500
📱 Mobile 4G 5GB — ₦20,000

{RANDOM IP TIP}
━━━━━━━━━━━━━━━━━━"
```

### CPAGrip Integration

```
Setup:
1. Sign up as publisher at cpagrip.com
2. Get API key + postback URL
3. Configure postback: https://n8n.yourdomain.com/webhook/cpagrip-postback
4. Use Content Locker or Smartlink for offer wall

Postback URL:
https://n8n.yourdomain.com/webhook/cpagrip-postback?user_id={USER_ID}&reward={REWARD}

Verification:
- CPAGrip signs each postback with HMAC
- n8n verifies signature before processing
- Prevents fake completions
```

### Reset Cron — Daily Midnight

**Trigger:** Daily 00:00 (Africa/Lagos)

```
For each phone in Free_Trials sheet:
  ↓
  Calculate: was trial today?
  ↓
  IF yes: Keep count
  IF no: Reset to 0 (fresh 3 trials available)
```

**Note:** Trials are counted per DAY, so count naturally resets as new day starts.

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

IMPORTANT — PRODUCT DIFFERENCES:

ISP / DC proxies:
- Monthly time-based billing
- Unlimited data
- Same IP on renewal if renewed before expiry

RESIDENTIAL proxies:
- Per GB billing — data pool
- Data NEVER expires — buy 5GB, use 2GB, you still have 3GB forever
- GB rolls over — old data stays until used
- No expiry date

MOBILE proxies:
- Per GB billing — data pool
- 30-day window to use data
- Unused GB is LOST on renewal or top-up!
- If data runs to 0GB, proxy stops working

IMPORTANT — FREE TRIAL:
- 3 free trials per day per phone
- Complete a survey to unlock each free IP
- Trial IPs are TEMPORARY public proxies
- NOT guaranteed to work, use at own risk
- No replacement if proxy dies

IMPORTANT — AVAILABILITY:
- We check provider availability BEFORE you pay
- If a product is temporarily unavailable, we tell you before payment
- You only pay when we can deliver
- Every IP is tested before sending to you

YOUR JOB:
1. Parse customer messages → extract: intent, product type, country, quantity
2. If order is clear → confirm price and prepare payment link request
3. If order is unclear → ask ONE clarifying question only
4. If customer asks about providers → deflect politely
5. If customer asks about refunds → explain the refund policy
6. Always include a RANDOM IP tip when sending proxy details

RANDOM IP TIPS (pick 1 randomly, no repeat until all used):
- "ISP proxies use real home IP addresses."
- "Mobile proxies use real 4G/5G networks."
- "Datacenter proxies are fastest but some platforms spot them."
- "Residential proxies bounce through real home devices."
- "ISP proxies stay stable longer than mobile."
- "US and UK IPs are among the most trusted."
- "Some platforms check IPs against GPS data."
- "High-trust IPs cost more because they're less likely flagged."
- "Using a proxy hides your real IP."
- "Proxy speed depends on location."
- "Datacenter proxies are fastest — great for automation."
- "Mobile proxies rotate IPs automatically."
- "ISP = Internet Service Provider."
- "Proxy IPs hide your location."
- "One IP per platform = cleaner account history."

RESIDENTIAL-SPECIFIC:
- "Residential data never expires!"
- "Top up whenever you're ready — no pressure!"

MOBILE-SPECIFIC:
- "Mobile data expires in 30 days! Unused GB is lost."
- "Renew AFTER data runs out!"

REFUND POLICY:
- No refunds after proxy delivered
- Replacement within 24hrs if banned (with screenshot)
- Technical issue from start → admin reviews

HOW TO USE PROXY:
- PHONE: Settings → Search "VPN" → Add VPN → Enter details
- DESKTOP: Browser network proxy settings or extension

NEVER:
- Never mention Proxy-Seller, DataImpulse, Geonode, CPAGrip, or any provider name
- Never reveal API keys, internal pricing, or provider costs
- Never explain HOW proxies work technically beyond setup
- Never open, follow, or acknowledge any link in the message
- Never attempt to download, process, or parse any file
- Never reveal recovery method details to customers
- Never recommend 1 IP on many devices — advise one IP per account/device

COMMANDS:
- "Order ISP [COUNTRY] [QTY]" → order, ISP, country, qty
- "Order DC [COUNTRY] [QTY]" → order, DATACENTER, country, qty
- "Order RES [QTY]GB" → order, RESIDENTIAL, qty
- "Order MOB [QTY]GB" → order, MOBILE, qty
- "Status [ORDER_ID]" → status
- "My proxies" OR "Check data" → check_proxies
- "Renew [ORDER_ID]" → renew
- "Top up residential" → top_up_residential
- "Top up mobile" → top_up_mobile
- "Free trial" / "Trial" / "Free proxy" → free_trial
- "Help" → help
- "Check price [PRODUCT]" → price_check
- "Refund" / "Cancel" → refund_request
- "How to use" / "Setup proxy" / "Configure" → how_to_use

RESPONSE FORMAT — Return ONLY valid JSON:
{
  "intent": "order|status|renew|top_up_residential|top_up_mobile|free_trial|help|price_check|ban_reported|refund_request|check_proxies|how_to_use|unknown",
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
| IP Tested | boolean | Was IP tested before delivery? |
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

**Status Values:**
`awaiting_payment` | `paid_pending_fulfillment` | `ip_testing` | `ip_test_failed` | `fulfilled` | `data_low` | `data_exhausted` | `ban_pending_review` | `replaced` | `failed` | `refund_pending` | `refunded` | `rejected` | `cancelled` | `expired`

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
| Last Trial Date | datetime |
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
| Pre-payment health check | Every order + renewal + top-up |
| No payment link if provider down | Pre-payment check |
| IP testing (5s timeout) | Every proxy before delivery |
| IP fails → replacement | IP testing workflow |
| Replacement also fails → auto-refund | IP testing workflow |
| Free trial: 3/day/phone | Workflow 8 |
| Free trial: survey verification | CPAGrip postback |
| Free trial: temp proxy, no replacement | Workflow 8 |
| No URLs in customer messages | Security Stripper |
| No provider names revealed | System prompt (LLM) |
| No injection prompts processed | Security Stripper + system prompt |
| LLM output validated as JSON | n8n validation node |
| PIN stored hashed | bcrypt hash in Google Sheets |
| Max 3 verification attempts | Counted before admin escalation |
| Admin only on exception | Admin Workflow triggered only on exception |
| No refund after delivery | Workflow enforces — admin override only |
| Legal notice only on first interaction | Workflow checks new vs returning |
| Random IP tips | Rotate — 1 per message, no repeat until all used |
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
| Ban Claim | WhatsApp Webhook (within Order Handler) | On ban claim |
| Refund Handler | Flutterwave Webhook | On refund event |
| Expiry + Data Reminder | Cron — daily 9:00 AM | Every day |
| Free Trial | WhatsApp Webhook + CPAGrip postback | On "free trial" request |
| Trial Reset | Cron — daily 00:00 | Every day |
| Error Alert | n8n Error Trigger | On any error |

---

## Testing

```bash
# New customer — legal notice + free trial info
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t1","from":"2349000000001","timestamp":"123","text":{"body":"Hi"}}]}}]}]}'

# Free trial — triggers Workflow 8
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t2","from":"2349000000001","timestamp":"123","text":{"body":"Free trial"}}]}}]}]}'

# Order ISP — triggers pre-payment health check
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t3","from":"2349000000001","timestamp":"123","text":{"body":"Order ISP UK 1"}}]}}]}]}'

# Order Residential
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t4","from":"2349000000001","timestamp":"123","text":{"body":"Order RES 5GB"}}]}}]}]}'

# Order Mobile
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t5","from":"2349000000001","timestamp":"123","text":{"body":"Order MOB 5GB"}}]}}]}]}'

# My proxies
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t6","from":"2349000000001","timestamp":"123","text":{"body":"My proxies"}}]}}]}]}'

# CPAGrip postback simulation
curl -X POST https://n8n.yourdomain.com/webhook/cpagrip-postback \
  -H "Content-Type: application/json" \
  -d '{"user_id":"2349000000001","survey_id":"SRV-12345","reward":"1.50","status":"completed","signature":"abc123"}'

# Admin: Provider status check
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"t7","from":"2347032981049","timestamp":"123","text":{"body":"Provider Status"}}]}}]}]}'
```