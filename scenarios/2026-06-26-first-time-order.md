# Bunche — Scenario Replay: First-Time Customer Orders ISP UK

**Date captured:** 2026-06-26
**Status:** Rules extracted + locked into WORKFLOW_SPECS for v3
**Last update:** Added legal notice requirement to first message

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

**System (Bunche internal):**
- New phone → NEW CUSTOMER branch
- LLM Intent Parser: greeting
- 24h LLM cache miss → cache stored

**Customer-facing:**

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
⚖️ BY REPLYING YOU AGREE TO:
━━━━━━━━━━━━━━━━━━
• Terms of Service: bunche.ng/terms
• Privacy Policy: bunche.ng/privacy
• Acceptable Use Policy: bunche.ng/aup

We collect: phone number, order history, proxy usage data.
We DON'T collect: name (until you set one), address, ID.

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
- ✅ **Legal notice: Terms + Privacy + AUP with explicit "BY REPLYING YOU AGREE TO"** ← ADDED THIS SESSION
- ✅ What we collect / don't collect summary (NDPR transparency)
- ✅ Links use bunche.ng (or actual deployed domain) — not raw GitHub paths

---

### Turn 2 — Customer: `I want uk ISP`

(Same as before)

---

### Turn 3 — Customer: `Yes`

(Same as before)

---

### Turn 4 — (Off-screen) Customer pays via Flutterwave

(Same as before)

---

### Turn 5 — Bunche (Workflow 2 → Name capture, BEFORE delivering IP)

**Customer-facing:**

```
✅ Payment received — ₦6,500

⚡ Generating your UK IP now...

🔐 Before I send your proxy — what should we call you?

This becomes your referral name — share it with friends and you earn
5% credit on their first order. Credit never expires.

Reply with a name (letters + numbers, 3–20 chars) 👇

Example: Chidi · Tunde22 · Maya_proxy
```

---

### Turn 6 — Customer: `Dan`

**System:**
- Name uniqueness check: `dan` not taken ✅
- Save name = 'Dan'
- Trigger PIN offer (Workflow 2 sub-step)

**Customer-facing:**

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

---

### Turn 7 — Customer: `1234`

(Same as before — delivers IP)

---

## New Rule Locked This Session (Update #2)

### Legal Notice on First Message

| Item | Rule |
|------|------|
| **What** | Terms of Service, Privacy Policy, Acceptable Use Policy must appear in first message |
| **Format** | Section labeled "⚖️ BY REPLYING YOU AGREE TO:" with bullet list + URLs |
| **Consent mechanism** | Implicit — customer replies = agrees (NDPR-compliant for WhatsApp context) |
| **Data collection summary** | Required — state what we collect AND what we don't (NDPR Article 5: transparency) |
| **URLs** | Use deployed domain (bunche.ng) — short, clean, mobile-friendly |
| **Where stored** | `legal/` directory in repo, deployed to domain |

**Why critical:** NDPR requires explicit notice at point of data collection. WhatsApp message = our point of data collection. Without this notice, Bunche can't legally process the customer's phone number.

---

## Critical Rules Table (Updated)

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | First message = greeting + services + prices + tip (no free trial) | WORKFLOW_SPECS §1 |
| 1a | **First message MUST include legal notice (Terms, Privacy, AUP) with implicit consent** | WORKFLOW_SPECS §1, `legal/` |
| 1b | **First message MUST include data collection summary (NDPR transparency)** | WORKFLOW_SPECS §1 |
| 2 | No name ask at greeting — only after payment, before IP | WORKFLOW_SPECS §2 |
| 3 | Name = referral code (per ADR-003) | ADR-003 |
| 4 | Pre-payment provider check is MANDATORY | WORKFLOW_SPECS §2 |
| 5 | Provider down → alternatives + admin alert + offer `wait` | WORKFLOW_SPECS §2 |
| 6 | Admin funding → notify queued customers | WORKFLOW_SPECS §2 |
| 7 | PIN is OPT-IN, captured AFTER name, BEFORE IP delivery | WORKFLOW_SPECS §2 |
| 8 | PIN enables cross-device recovery, bcrypt hashed | SECURITY_PLAN |
| 9 | IP delivery includes: IP, port, user, pass, expiry, PDF receipt, setup tip, referral reminder, no-refund policy | WORKFLOW_SPECS §2 |

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
- `legal/TERMS_OF_SERVICE.md` — ToS document
- `legal/PRIVACY_POLICY.md` — Privacy Policy document
- `legal/ACCEPTABLE_USE_POLICY.md` — Acceptable Use Policy document