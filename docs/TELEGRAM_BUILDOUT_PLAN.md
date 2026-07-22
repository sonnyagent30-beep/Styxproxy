# Styxproxy — Telegram Customer Flow Buildout Plan

**Status: PLANNING — not yet built**
**Last updated: 2026-07-01**

---

## 1. What We're Building

A **dual-channel customer messaging system** so customers can message Styxproxy on WhatsApp OR Telegram and get the same experience — order, pay, receive credentials, track, get help.

**Why:** WhatsApp Business API is pending Meta approval. Telegram works today. We want to run the business on Telegram while WhatsApp is pending, and have a failover if either channel goes down.

**Key design principle:** Not every Nigerian number has WhatsApp. Phone number cannot be the common identifier. Each platform (Telegram, WhatsApp) has its own account record. Customers can optionally merge them when they choose via OTP verification.

---

## 2. Customer Channels

| Channel | Status | Receives orders | Sends messages | Failover |
|---|---|---|---|---|
| **WhatsApp** | Pending Meta approval | ✅ (once approved) | ✅ (pending) | ✅ Telegram |
| **Telegram** | Ready to build | ✅ (this build) | ✅ (this build) | ✅ WhatsApp |

**Strategy:** Telegram is the primary channel until WhatsApp Business API is approved. Once WhatsApp is live, both channels work. If one goes down, all traffic routes to the other automatically.

---

## 3. Customer Flows (Happy Path)

### 3.1 Order Flow
```
Customer → Messages "I want to order ISP UK"
    ↓
System identifies product from message (LLM intent)
    ↓
System asks for confirmation if needed (e.g. "5GB or 10GB?")
    ↓
System generates Flutterwave payment link
    ↓
Customer pays via Flutterwave (bank transfer, card, USSD, OPay, etc.)
    ↓
Flutterwave webhook fires → system confirms payment
    ↓
System creates proxy credentials (3proxy)
    ↓
System sends credentials to customer via same channel
    ↓
Customer gets order ID for tracking
```

### 3.2 Free Trial Flow
```
Customer → Messages "I want free trial"
    ↓
System sends disclaimer + terms + Theorem Reach survey link
    ↓
Customer completes survey 1 → Theorem Reach sends postback → system records survey_1 completed (2hr earned)
Customer completes survey 2 → Theorem Reach sends postback → system records survey_2 completed (4hr total)
Customer completes survey 3 → Theorem Reach sends postback → system records survey_3 completed (6hr total)
... customer continues at their own pace, up to 12 surveys max ...
Customer → Messages "I'm done" or "done"
    ↓
System checks: how many surveys did this customer complete this session?
    ↓
IF surveys_completed >= 1:
    → total_hours = surveys_completed × 2
    → Generate credentials with expiry = now + total_hours
    → Call 3proxy script to create user
    → Send credentials via same channel
IF surveys_completed = 0:
    → "You haven't completed any surveys yet. Complete at least one and try again."
IF surveys_completed >= 12:
    → Cap at 12 (24 hours). Generate 24hr credentials.
```

**Free trial rules:**
- Max 12 surveys per session (24 hours of proxy time)
- No daily limit (session cap replaces daily limit)
- Credentials sent ONCE after customer says "done" — not after each survey
- Theorem Reach postback is recorded but does NOT trigger credential delivery
- 3proxy ports: 8001-8100 (100 concurrent slots)

### 3.3 Status Check Flow
```
Customer → Messages "Check my order" or "Track order"
    ↓
System asks for order ID or phone number
    ↓
System looks up order in database
    ↓
System returns: status, expiry, proxy details (if active)
```

### 3.4 Renewal Flow
```
Customer → Messages "I want to renew" + proxy details
    ↓
System looks up current proxy
    ↓
System generates renewal payment link (Flutterwave)
    ↓
Payment confirmed → extends expiry
    ↓
System confirms renewal via same channel
```

### 3.5 Refund / Ban Claim Flow
```
Customer → Messages "My proxy no work" or "I want refund"
    ↓
System collects order ID / phone
    ↓
System routes to admin for review
    ↓
Admin reviews → approves or rejects
    ↓
System notifies customer of outcome
```

### 3.6 Account Merge Flow (Link Telegram ↔ WhatsApp)
```
Customer (on Telegram) → "Link my WhatsApp"
    ↓
Bot asks: "Enter your WhatsApp number (with country code)"
    ↓
Customer types phone number
    ↓
System looks up phone hash in platform_accounts (WhatsApp)
    ↓
IF found:
    → Generate 6-digit OTP
    → Send OTP to customer's WhatsApp
    → Ask Telegram customer to enter OTP
    → IF OTP correct + not expired:
        → Create customers record (if first time)
        → Link both platform_accounts to same customer_id
        → Tell customer: "✅ Accounts linked!"
    → IF OTP wrong (3 attempts):
        → Expire request, tell customer to try again
IF NOT found:
    → Tell customer: "No Styxproxy account on that WhatsApp. 
       Start an order on WhatsApp first, then come back to link."
```

**After merge:** Both platforms share the same order history, preferences, and customer profile. Customer can still message on either channel.

---

## 4. Failover Logic

**Rule: Always route to whichever channel is available.**

```
IF WhatsApp is down AND Telegram is up:
    → All new customer messages route to Telegram
    → Website WhatsApp CTA replaced with "Chat on Telegram" button

IF Telegram is down AND WhatsApp is up:
    → All new customer messages route to WhatsApp
    → Website Telegram CTA replaced with WhatsApp link

IF Both are down:
    → Website shows "We are temporarily unavailable" message
    → Admin gets alert
    → Customer can still visit website and initiate Flutterwave payment directly
```

**Health check:** System pings both channels every 5 minutes. If a channel fails 3 consecutive checks, trigger failover mode.

---

## 5. Admin Alerts

| Event | Channel | Who gets notified |
|---|---|---|
| New order placed | Telegram bot → admin chat | Dannion |
| Payment confirmed | Telegram bot → admin chat | Dannion |
| New free trial claimed | Telegram bot → admin chat | Dannion |
| Channel failover triggered | Telegram bot → admin chat | Dannion |
| Both channels down | Telegram bot → email | Dannion |
| Refund requested | Telegram bot → admin chat | Dannion |
| Ban claim submitted | Telegram bot → admin chat | Dannion |
| Suspicious activity | Telegram bot → admin chat | Dannion |

---

## 6. Tech Stack

| Component | Technology | Notes |
|---|---|---|
| Telegram bot | BotFather bot + Telegram Bot API | Available today |
| WhatsApp bot | WhatsApp Business Cloud API | Pending Meta approval |
| Message routing | telegram-webhook-bridge.js (Express) | Central hub |
| Workflow engine | n8n (self-hosted on VPS) | Handles all logic |
| Database | PostgreSQL (existing) | Customers, orders, credentials |
| Cache/sessions | Redis (existing) | Rate limiting, sessions |
| Payments | Flutterwave | Bank transfer, card, USSD, OPay |
| Proxy delivery | 3proxy (existing) | Creates/deletes proxy users |
| Monitoring | UptimeRobot (existing) | 5-min health checks |
| Channel failover | channel-failover.json n8n workflow | Monitors + routes |

---

## 7. Website CTAs (What customers see)

**Always show both buttons:**
- 🟢 WhatsApp button: `https://wa.me/2347032981049?text=Hi%20Bunche!%20I%27d%20like%20to%20order%20proxies.`
- 🔵 Telegram button: `https://t.me/buncheng?text=Hi%20Bunche!%20I%27d%20like%20to%20order%20proxies.`

**During failover:**
- If WhatsApp is down: WhatsApp button replaced with "WhatsApp temporarily unavailable" text + stronger Telegram button
- If Telegram is down: Telegram button replaced with "Telegram temporarily unavailable" text + stronger WhatsApp button
- If both are down: Both buttons replaced with "We are temporarily unavailable — you can still order below" + direct Flutterwave link

**CTA button style:**
- WhatsApp: Green `#25D366`
- Telegram: Blue `#229ED9`
- "Chat on WhatsApp" / "Chat on Telegram" text labels (not icons only)

---

## 8. n8n Workflows Needed

| Workflow | Trigger | Purpose |
|---|---|---|
| `whatsapp-order.json` | WhatsApp Cloud API webhook | Order flow (WA channel) — existing, needs updating |
| `telegram-order.json` | Telegram webhook → bridge → n8n | Order flow (Telegram channel) — **TO BUILD** |
| `telegram-free-trial.json` | Telegram webhook | Free trial (Telegram) — **TO BUILD** |
| `whatsapp-free-trial.json` | WhatsApp webhook | Free trial (WA) — existing, needs updating |
| `payment-confirmation.json` | Flutterwave webhook | Confirms payment, triggers credential delivery |
| `channel-failover.json` | Schedule (every 5 min) | Health check both channels, update failover state |
| `admin-alerts.json` | Both channels via n8n sub-workflow | Routes admin notifications to Telegram |
| `ban-claim.json` | WhatsApp + Telegram | Ban claim handling |
| `refund-handler.json` | WhatsApp + Telegram | Refund processing |
| `account-link.json` | Telegram + WhatsApp | OTP flow for linking Telegram ↔ WhatsApp accounts |

**Workflows to BUILD:**
1. `telegram-order.json` ✅ BUILT (pending review)
2. `telegram-free-trial.json` ✅ BUILT (pending review)
3. `channel-failover.json` ✅ BUILT (pending review)

**Workflows to UPDATE from existing:**
4. `whatsapp-order.json` — Add Telegram fallback
5. `whatsapp-free-trial.json` — Add Telegram fallback
6. `admin-alerts.json` — Make it channel-agnostic

---

## 9. Buildout Sequence

### Phase 1: Telegram MVP (Build first)
1. Set up Telegram webhook bridge (telegram-webhook-bridge.js)
2. Import telegram-order.json into n8n, activate
3. Import telegram-free-trial.json into n8n, activate
4. Test: message @BuncheHQ → get order reply ✅
5. Test: free trial flow end-to-end ✅

### Phase 2: Failover
6. Import channel-failover.json into n8n
7. Configure health checks for WhatsApp + Telegram
8. Wire failover logic into website CTAs (update website CTA section dynamically)
9. Test failover: disable Telegram → WhatsApp CTA activates

### Phase 3: WhatsApp Integration
10. Once Meta approves WhatsApp Business API:
11. Update whatsapp-order.json with new API
12. Update whatsapp-free-trial.json with new API
13. Wire dual-channel routing
14. Both channels run simultaneously

### Phase 4: Polish
15. Admin alert unified routing
16. Refund/ban claim workflows for both channels
17. Payment confirmation with both channel sends

---

## 10. Current Gaps (Before Build)

| Gap | Status | Owner |
|---|---|---|
| Telegram webhook needs public HTTPS URL | ⚠️ BLOCKER | Needs decision |
| WhatsApp Business API not yet approved | ⏳ Pending | Meta |
| n8n not connected to Hermes MCP | ⚠️ Can write files but can't trigger/test | Setup |
| channel-failover.json needs WhatsApp token env var | Missing | WA approval |
| Website failover CTA logic (dynamic button swap) | Not built | Phase 2 |

---

## 11. Decisions Made

- [x] Telegram primary while WhatsApp pending
- [x] Both channels = independent until customer requests merge
- [x] Account linking via OTP (phone hash for WhatsApp, chat_id for Telegram)
- [x] Nigerian Pidgin English for Telegram responses
- [x] Flutterwave for all payments (not Paystack)
- [x] "Pay via Local Payment" label on website
- [x] Failover automatic, no manual switching
- [x] Admin alerts via Telegram (existing @BuncheHQ bot)
- [x] Platform accounts table as the identity layer (not phone-based)
- [x] customers table created at first merge, not at first message
- [x] Free trial: 1 survey = 2 hours, up to 12 surveys = 24 hours max
- [x] Free trial: credentials sent once after customer says "done" — not per survey
- [x] Free trial: no daily limit (session cap = 12 surveys)

---

## 12. Files In Repo (After This Build)

```
telegram-webhook-bridge.js     ← Webhook receiver (Express)
.n8n/workflows/
  telegram-order.json           ← Order handler (Telegram)
  telegram-free-trial.json      ← Free trial (Telegram)
  channel-failover.json        ← Health check + failover
  whatsapp-order.json          ← Order handler (WhatsApp) — existing, needs update
  whatsapp-free-trial.json     ← Free trial (WhatsApp) — existing, needs update
  payment-confirmation.json    ← Payment webhook → deliver credentials
  admin-alerts.json            ← Admin notifications
  ban-claim.json               ← Ban claim handler
  refund-handler.json          ← Refund handler
```

---

*This is a planning document. Build starts once this spec is approved.*
