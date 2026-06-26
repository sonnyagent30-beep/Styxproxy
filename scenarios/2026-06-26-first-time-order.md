# Bunche — Scenario Replay: First-Time Customer Orders ISP UK

**Date captured:** 2026-06-26
**Source:** Live roleplay session between Dannion (customer) and Sonny (as Bunche)
**Status:** Rules extracted + locked into WORKFLOW_SPECS for v3

---

## Purpose

This document captures the **exact turn-by-turn UX we agreed on** for a brand-new customer ordering their first proxy. It serves as the canonical reference for:
- Building the n8n workflow
- QA testing the customer experience
- Training future agents or operators

---

## The Scenario (Verbatim)

### Customer persona: Dan, first-time user, no name saved, no referral

---

### Turn 1 — Customer: `Hi`

**Bunche (Workflow 1 → Greeting branch):**

```
👋 Welcome to Bunche — your plug for ISP, Datacenter, Residential & Mobile proxies.
Pay in Naira, get your proxy in under 2 minutes.

━━━━━━━━━━━━━━━━━━
💰 OUR SERVICES & PRICES
━━━━━━━━━━━━━━━━━━

🌍 ISP Proxies — stable, dedicated, fast
   🇬🇧🇺🇸🇩🇪🇫🇷🇨🇦 → ₦6,500/mo
   🇯🇵🇦🇺🇧🇷🇸🇬 → ₦7,500/mo

🏢 Datacenter — budget-friendly
   → ₦2,500/mo

🌐 Residential 5GB / 10GB
   → ₦5,000 / ₦9,000
   💡 Data never expires — use it whenever

📱 Mobile 4G 5GB / 10GB
   → ₦20,000 / ₦35,000
   💡 30-day window to use data — unused GB is lost on renewal

━━━━━━━━━━━━━━━━━━
🛒 To order, just type:
Order ISP UK 1 · Order RES 5GB · Order MOB 10GB
━━━━━━━━━━━━━━━━━━

💡 Tip: For social media & multi-account work → ISP. For scraping & bulk
data → Residential. For mobile-only platforms (TikTok, etc.) → Mobile 4G.

What do you need? 👇
```

**Rules extracted:**
- ✅ First message = greeting + full services + prices + tip
- ✅ No `free trial` mention at this stage (added later when customer asks or admin nudges)
- ✅ Tips are embedded inline with each product line where useful
- ✅ No name ask here

---

### Turn 2 — Customer: `I want uk ISP`

**Bunche (Workflow 1 → Order confirmation):**

```
Got it 🇬🇧 — ISP UK Proxy

💰 Price: ₦6,500 / month

Just to confirm before I send your payment link:

✅ 1 × ISP UK @ ₦6,500/mo

Reply Yes to proceed, or change the order:
• Order ISP UK 2 → 2 proxies (₦13,000)
• Order ISP US 1 → US instead
• Order RES 5GB → Residential data
• Order MOB 5GB → Mobile data

💡 Tip: ISP proxies are best for social media accounts (IG, X, TikTok),
managing multiple logins, and accessing UK-only sites. One IP = one
device recommended.

Which way? 👇
```

**Rules extracted:**
- ✅ Free-form input ("I want uk ISP") gets normalized to confirmation
- ✅ Show price + product before any payment link
- ✅ Confirm order, give escape hatches (change product/qty/country)
- ✅ Add relevant tip

---

### Turn 3 — Customer: `Yes`

**Bunche (Workflow 1 → Pre-payment check → Payment link):**

```
✅ Confirmed: 1 × ISP UK @ ₦6,500/mo

💳 Pay here:
👉 https://checkout.flutterwave.com/ORD-20260627-0917

Pay with:
• Bank transfer • Card • USSD • QR code

⏰ Link valid for 30 minutes.

💡 Tip: Bank transfer is fastest — most banks complete in under 30 seconds.

Once I see your payment, your IP arrives in under 2 minutes ⚡
```

**Rules extracted:**
- ✅ **MANDATORY pre-payment check:** Proxy-Seller API live + balance sufficient + product available
- ✅ If pre-check FAILS:
  - Tell customer product is currently unavailable
  - Show alternative products they could buy
  - Alert admin to fund the provider wallet
  - If admin funds while customer still in chat → notify customer product is back
- ✅ Generate unique order_id, INSERT as `pending`, save tx_ref
- ✅ Flutterwave link valid 30 minutes
- ✅ Add tip about fastest payment method

---

### Turn 4 — (Off-screen) Customer pays via Flutterwave

**Behind the scenes:**
- Flutterwave webhook → n8n
- HMAC verify ✅
- Idempotency check ✅
- Workflow 2: Payment Confirmation fires
- POST Proxy-Seller `/api/v1/order/create` → returns IP + credentials
- Test proxy: curl with 5s timeout
- ✅ Pass → save to DB (proxy_pass_encrypted = AES-256-GCM)
- ❌ Fail → replacement API, max 2 retries, then auto-refund

---

### Turn 5 — Bunche (Workflow 2 → Name capture, BEFORE delivering IP)

```
✅ Payment received — ₦6,500

⚡ Generating your UK IP now...

🔐 Before I send your proxy — what should we call you?

This becomes your referral name — share it with friends and you earn
5% credit on their first order. Credit never expires.

Reply with a name (letters + numbers, 3–20 chars) 👇

Example: Chidi · Tunde22 · Maya_proxy
```

**Rules extracted:**
- ✅ Name captured AFTER payment, BEFORE IP delivery
- ✅ Name = referral code (per ADR-003)
- ✅ Format: letters + numbers, 3–20 chars
- ✅ Case-insensitive uniqueness check
- ✅ Show examples so customer knows format

---

### Turn 6 — Customer: `Dan`

**Bunche (Workflow 2 → PIN setup, BEFORE delivering IP):**

```
Welcome Dan 🎉 — your referral name is now Dan.

🔐 One quick thing before I send your proxy:

Set a 4-digit PIN so you can access your IP details from any phone number.
(Skip if you don't want this.)

Reply with a 4-digit number 👇
Or reply skip to continue without a PIN.

💡 Why a PIN? If you lose your phone or buy a new SIM, the PIN lets
you prove it's you and recover your proxies from any number.
```

**Rules extracted:**
- ✅ PIN is OPT-IN (customer can skip)
- ✅ 4-digit numeric only
- ✅ PIN enables cross-device recovery
- ✅ Never log or store plain PIN — bcrypt hash only
- ✅ Customer can use this PIN later from any phone to authenticate

---

### Turn 7 — Customer: `1234`

**Bunche (Workflow 2 → Deliver IP):**

```
✅ PIN saved! You can now access your proxies from any phone using this PIN.

━━━━━━━━━━━━━━━━━━
🌍 YOUR ISP UK PROXY — LIVE
━━━━━━━━━━━━━━━━━━

🔗 IP: 185.123.45.67
🔌 Port: 8000
👤 User: chidi_uk_a7b9
🔑 Pass: xKp9mN2qR
📅 Expires: July 27, 2026

━━━━━━━━━━━━━━━━━━
📄 Receipt: https://files.bunche.ng/receipts/ORD-20260627-0917.pdf
━━━━━━━━━━━━━━━━━━

💡 Setup tip: Phone → Settings → VPN → Add → enter the details above.
One IP per device works best.

💡 Share your name Dan with friends → 5% credit when they buy!

Need help? Reply how to use.

⚠️ No refunds once delivered. If your IP gets banned within 24 hours,
send the screenshot and we'll replace it free.
```

**Rules extracted:**
- ✅ Acknowledge PIN saved (without showing it back)
- ✅ Clean formatted block with IP details (NOT in code block — for easy copy)
- ✅ PDF receipt link
- ✅ Setup tip
- ✅ Referral reminder
- ✅ Help command hint
- ✅ No-refund policy + 24hr replacement policy stated clearly

---

## The Decision Tree (Visual)

```
Customer message
    ↓
[LLM Intent Parser]
    ↓
┌─────────────────────────────────────────┐
│ Is this customer new (no name + no PIN)?│
├─────────────────────────────────────────┤
│ NEW:                                    │
│   greeting → show services + prices     │
│   order_intent → confirm + tip          │
│   confirm → pre-payment check           │
│      ✅ → payment link                  │
│      ❌ → alternatives + admin alert    │
│   payment_received → name ask           │
│   name_provided → PIN offer (optional)  │
│   pin_provided OR skip → DELIVER IP     │
│                                         │
│ EXISTING:                               │
│   order_intent → confirm (no name ask)  │
│   confirm → pre-payment check           │
│      ✅ → payment link                  │
│      ❌ → alternatives + admin alert    │
│   payment_received → DELIVER IP         │
│   (name already saved)                  │
│                                         │
│ RETURNING FROM NEW PHONE:               │
│   order_intent → "Enter your 4-digit PIN│
│   for security"                         │
│   pin_provided → verify → continue      │
│   ✅ match → DELIVER IP                 │
│   ❌ fail × 3 → admin alert + lockout   │
└─────────────────────────────────────────┘
```

---

## Critical Rules Locked In This Session

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | First message = greeting + services + prices + tip (no free trial mention) | WORKFLOW_SPECS §1 |
| 2 | No name ask at greeting — only after payment, before IP delivery | This doc + WORKFLOW_SPECS §2 |
| 3 | Name = referral code (per ADR-003) | ADR-003 |
| 4 | Pre-payment provider check is MANDATORY before sending payment link | WORKFLOW_SPECS §2 (new) |
| 5 | If provider check fails: alternatives + admin alert | WORKFLOW_SPECS §2 (new) |
| 6 | If admin funds while customer still in chat → notify customer | WORKFLOW_SPECS §2 (new) |
| 7 | PIN is OPTIONAL (customer can skip) | WORKFLOW_SPECS §2 (new) |
| 8 | PIN enables cross-device proxy recovery | This doc + SECURITY_PLAN |
| 9 | PIN is bcrypt-hashed, never plain in logs | ADR-004 |
| 10 | IP delivery includes: IP, port, user, pass, expiry, PDF receipt, setup tip, referral reminder, no-refund policy | WORKFLOW_SPECS §2 |

---

## What's NOT in This Scenario (Test Next)

| Scenario | What it tests |
|----------|---------------|
| Provider down at pre-check | Failure path + alternatives + admin alert |
| Admin funds while customer waits | Recovery notification |
| Returning customer with existing name + PIN | Skip name/PIN steps |
| Returning customer from new phone (PIN auth) | PIN recovery flow |
| Customer says "free trial" | Free trial path (Workflow 8) |
| Customer refers friend "Ada" | Referral capture (Workflow 2 sub-step) |
| Customer orders Mobile | Data-amount handling, expiry messaging |
| Customer orders Residential | No-expiry messaging, data tracking |
| Customer orders multiple products | Combined cart + single payment |
| Customer asks "how to use" | Setup guide (cached LLM response) |
| Customer reports IP banned | Ban claim flow (Workflow 4) |
| Customer wants refund after 24hrs | No-refund path |

---

## Related

- `workflows/WORKFLOW_SPECS.md` §1, §2 — full technical specs
- `docs/REFERRAL_SYSTEM.md` — referral mechanics
- `docs/adr/ADR-003-name-as-referral-code.md` — name = code decision
- `docs/adr/ADR-004-secrets-management.md` — bcrypt PIN storage