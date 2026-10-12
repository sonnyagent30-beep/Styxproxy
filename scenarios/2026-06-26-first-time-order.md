# Bunche — Scenario Replay: First-Time Customer Orders ISP UK

**Date captured:** 2026-06-26
**Status:** Rules extracted + locked into WORKFLOW_SPECS for v3
**Last update:** First-time greeting split into 3 messages (council batch-2 fix, all under 1024 chars)

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

**Customer-facing (greeting — short, <600 chars):**

```
👋 Welcome to Bunche — ISP, Residential & Mobile proxies!
Pay in Naira, get your proxy in under 2 minutes ⚡

To order: reply "order ISP UK" / "order RES 5GB" / "order mobile"
Or type "menu" to see everything 👇
```

---

**Customer-facing (services — auto-sent after 2s):**

```
━━━━━━━━━━━━━━━━━━
💰 OUR SERVICES & PRICES
━━━━━━━━━━━━━━━━━━

🌍 ISP UK/US — from ₦6,500/mo
🌐 Residential 5GB — ₦5,000 (data never expires!)
📱 Mobile 4G 5GB — ₦20,000/mo
🏢 Datacenter — from ₦2,500/mo

💡 ISP = social media. Residential = scraping & bulk.
Mobile = TikTok & similar platforms.

Reply "order" + product to get started 👇
```

---

**Customer-facing (AUP notice — auto-sent):**

```
⚖️ By ordering, you agree to our Acceptable Use Policy.
styxproxy.com/aup | Privacy: styxproxy.com/privacy
```

---

**Rules extracted:**
- ✅ First message = greeting + menu navigation (short, <600 chars)
- ✅ Services + prices sent as second message (auto)
- ✅ AUP notice sent as third message (auto)
- ✅ Each message under 1024 char WhatsApp limit
- ✅ No `free trial` mention at this stage (added later when customer asks or admin nudges)
- ✅ No name ask here
- ❌ ~~Full legal disclosure in first message~~ — REMOVED (split across messages 1-3)

### Turn 2 — Customer: `I want uk ISP`

(Same as before)

### Turn 3 — Customer: `Yes`

(Same as before)

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

## Critical Rules Table (Updated)

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | First message = greeting only (short) | WORKFLOW_SPECS §1 |
| 1a | Services + prices sent as 2nd message (auto) | WORKFLOW_SPECS §1 |
| 1b | AUP notice sent as 3rd message (auto) | WORKFLOW_SPECS §1 |
| 1c | All messages under 1024 char WhatsApp limit | WORKFLOW_SPECS §1 |
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