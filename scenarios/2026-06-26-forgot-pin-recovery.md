# Bunche — Scenario Replay: Forgot-PIN Recovery

**Date captured:** 2026-06-26
**Source:** Live roleplay session between Dannion (customer) and Sonny (as Bunche)
**Status:** Rules extracted + locked for v3

---

## The Scenario (Verbatim)

### Setup:
- Dan is an existing customer (name='Dan', has 1 active ISP US proxy)
- Dan had set a PIN originally
- Dan is on a NEW phone (theft or new SIM)
- Dan does NOT remember his PIN
- Dan wants his proxy details recovered

---

### Turn 1 — Customer: `Hi`

**System:** New phone, standard greeting.

**Customer-facing:**

```
👋 Welcome to Bunche — your plug for ISP, Datacenter, Residential & Mobile proxies.

[full services + prices menu]
```

---

### Turn 2 — Customer: `My phone got stolen, I don't know if I can get my last proxy`

**System:** Account recovery branch initiated.

**Customer-facing:**

```
🔐 Sorry to hear about the theft — let's see what we can do.

To find your account, I need to verify it's really you:

1️⃣ Your referral name (e.g. Dan, Chidi, Tunde22)
2️⃣ Your 4-digit PIN

⚠️ Wrong PIN 3 times = locked + admin alert.

Reply with both, like: Dan 1234

💡 If you forgot your PIN or never set one, reply forgot.
```

**Rules extracted:**
- Always ask for BOTH name AND PIN
- Mention `forgot` option for cases where customer doesn't have PIN
- 3-strike lockout applies

---

### Turn 3 — Customer: `Daniel, and I forgot my password`

**System:**
- LLM extracts name = "Daniel" → fuzzy match against "Dan" → found
- Customer states password forgotten → enter forgot-PIN flow
- Ask for confirmation before triggering recovery (security: don't auto-start sensitive flow)

**Customer-facing:**

```
Got it — name lookup found your account (Dan) ✓

Since you forgot your PIN, I need to verify it's really you another way.

⚠️ For security, forgot-PIN recovery takes a few steps. Are you ready?

Reply yes to continue.
```

---

### Turn 4 — Customer: `Yes`

**System:** Trigger recovery flow.

**Customer-facing:**

```
✅ Got it. Let's verify it's you.

Tell me about your last order:

1️⃣ What plan did you buy? (ISP, Datacenter, Residential, Mobile)
2️⃣ Which country/location?
3️⃣ Approximately when did you buy it?

Reply with all three, like:
"ISP US, USA, about 3 days ago"
```

---

### Turn 5 — Customer: `Mobile 5gb, USA about 2 weeks ago`

**System:**
- Cross-reference against DB
- Actual: ISP US, USA, 3 days ago
- Customer said: Mobile 5GB, USA, 2 weeks ago
- Match: 1 out of 3 (only country)
- Decision: NOT close enough → request receipt

**Customer-facing (FIRST ATTEMPT — WRONG — leaked order details):**

```
⚠️ Hmm, that doesn't match what's on your account.

Last order I see:
📦 ISP US · USA · about 3 days ago

You said: Mobile 5GB · USA · about 2 weeks ago

━━━━━━━━━━━━━━━━━━

📄 Send me your Flutterwave payment receipt:
• PDF receipt (download from the email Flutterwave sent)
• OR screenshot of the transaction from your bank app

I'll forward it to admin to verify. Takes up to 24 hours.
```

---

### Turn 6 — Dannion's correction: **NEVER reveal the last order details**

**Customer-facing (CORRECTED):**

```
⚠️ That doesn't match what I have on file.

Some details are right, others aren't.

━━━━━━━━━━━━━━━━━━

📄 To continue verification, send me your Flutterwave payment receipt:
• PDF receipt (download from the email Flutterwave sent)
• OR screenshot of the transaction from your bank app

I'll forward it to admin to verify against your account. Takes up to 24 hours.

⚠️ Don't share receipts from anyone else — only YOUR own.
```

**Rule extracted (CRITICAL):** Never leak specific order details to a customer who failed verification. They could use those details to:
- Forge a fake receipt
- Try forgot-PIN flow again from different number
- Social-engineer admin with "real" details

---

## Forgot-PIN Recovery Flow (Locked)

```
[Customer says forgot on PIN challenge]
   ↓
[Find account by name lookup]
   ↓
[Confirm customer ready for sensitive recovery flow]
   ↓
[Ask 3 order details: plan, country, approx time]
   ↓
[Cross-reference against DB]
   ↓
   ┌─────────────────────────────────────────┐
   │ Score the match                         │
   ├─────────────────────────────────────────┤
   │ 3/3 accurate       → Reset PIN directly │
   │ 2/3 accurate       → Reset PIN directly │
   │ 1/3 accurate       → Request receipt    │
   │ 0/3 accurate       → Request receipt    │
   └─────────────────────────────────────────┘
   ↓
[If receipt needed:]
   ↓
[Customer sends Flutterwave receipt (PDF or screenshot)]
   ↓
[Save receipt to R2: bunche-files/recovery-receipts/{customer_hash}/{timestamp}]
   ↓
[Forward to admin via WhatsApp with verification checklist]
   ↓
[Admin manually checks Flutterwave dashboard for matching tx_ref]
   ↓
[24-hour window for admin review]
   ↓
   ┌─────────────────────────────────────────┐
   │ Admin verdict                           │
   ├─────────────────────────────────────────┤
   │ ✅ Approved → Reset PIN + notify customer │
   │ ❌ Denied → Lock account + notify customer │
   └─────────────────────────────────────────┘
```

---

## Why Order Details + Receipt (Not Just One)

| Layer | What it stops |
|-------|---------------|
| **Order details check** | Random thief who doesn't know customer's order history |
| **Receipt verification** | Thief who guessed order details (or saw leaked info) — receipt must match tx_ref exactly |
| **Admin manual review** | Catches edge cases neither automation catches (e.g. genuine customer + receipt leak) |

**Three layers = very hard to bypass.**

---

## Bunche's Username Uniqueness = Built-in Verification

Dannion's insight (locked): Bunche names are **case-insensitive unique**. Combined with tx_ref lookup on Flutterwave receipts:

```
Customer says "my name is Dan"
   ↓
[Bunche confirms: yes, "Dan" exists in DB]
   ↓
[Customer sends receipt with tx_ref ORD-20260627-0917]
   ↓
[Admin: SELECT customer_name FROM orders WHERE tx_ref = 'ORD-20260627-0917']
   ↓
[Result: 'Dan' → MATCH ✅]
```

This is **strong proof** that the receipt belongs to the customer claiming it. No need for extra verification layers.

---

## Critical Rules Locked

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | Forgot-PIN triggers order-details verification, not auto-reset | WORKFLOW_SPECS §Account Recovery |
| 2 | Bunche asks 3 order questions: plan, country, approx time | WORKFLOW_SPECS §Account Recovery |
| 3 | 2-3 out of 3 correct → reset PIN directly | WORKFLOW_SPECS §Account Recovery |
| 4 | 0-1 out of 3 correct → request receipt | WORKFLOW_SPECS §Account Recovery |
| 5 | **CRITICAL: Never reveal actual order details on failed check** | This doc + WORKFLOW_SPECS §Account Recovery |
| 6 | Receipt request must include warning: "Don't share receipts from anyone else" | This doc |
| 7 | Receipts saved to R2 under customer_hash (not plain phone/name) | WORKFLOW_SPECS §Account Recovery |
| 8 | Admin reviews receipts in Flutterwave dashboard manually | WORKFLOW_SPECS §Account Recovery |
| 9 | 24-hour window for admin verdict | WORKFLOW_SPECS §Account Recovery |
| 10 | Admin verdict → reset PIN OR lock account | WORKFLOW_SPECS §Account Recovery |

---

## Open Question: Failed-Attempt Counter?

**Should forgot-PIN flow have its own lockout?**

| Pattern | Trade-off |
|---------|-----------|
| **3 fails in 24h → lock forgot-PIN for 24h** | Prevents brute-force probing of order details. Annoying for legit forgetful customers. |
| **No counter, just log attempts** | Customer-friendly. Risk: thief can keep trying different combos. |
| **3 fails → escalate to admin mandatory** | Balance. Customer can try a few times, then admin takes over. |

**Recommendation:** Add counter + admin escalation after 3 failed attempts within 24h.

**Status:** PENDING Dannion decision.

---

## Admin Alert Template (Receipt Forwarded)

```
🔐 FORGOT-PIN RECOVERY — Receipt Received

Customer hash: a3f2b9c1e8d4...
Claimed name: Dan
Receipt URL: https://files.styxproxy.com/recovery-receipts/a3f2b9c1e8d4/2026-07-11T1430.pdf

📋 Verification steps:
1. [ ] Confirm tx_ref in receipt matches an order for customer Dan
2. [ ] Confirm receipt amount matches order amount
3. [ ] Confirm receipt date is reasonable (within last 30 days)
4. [ ] Check Flutterwave dashboard for any fraud signals on this customer

Reply with verdict:
• reset Dan 1234 — to reset their PIN to 1234
• reset Dan [new_pin] — to set a different PIN
• deny — to deny the recovery and lock the account

Customer is waiting. 24-hour window.
```

---

## Database Schema Notes

```sql
ALTER TABLE customers
ADD COLUMN forgot_pin_attempts INT DEFAULT 0,
ADD COLUMN forgot_pin_last_attempt TIMESTAMPTZ,
ADD COLUMN forgot_pin_locked_until TIMESTAMPTZ;

CREATE TABLE pin_recovery_requests (
    id SERIAL PRIMARY KEY,
    customer_hash VARCHAR(20) NOT NULL,
    request_at TIMESTAMPTZ DEFAULT NOW(),
    customer_claimed_details JSONB,      -- {"plan": "Mobile", "country": "USA", "time": "2 weeks ago"}
    match_score INT,                      -- 0-3
    receipt_url TEXT,
    admin_verdict VARCHAR(20),            -- 'pending', 'approved', 'denied'
    admin_verdict_at TIMESTAMPTZ,
    admin_notes TEXT,
    new_pin_hash VARCHAR(255)             -- set on approval
);

CREATE INDEX idx_recovery_customer ON pin_recovery_requests(customer_hash);
CREATE INDEX idx_recovery_pending ON pin_recovery_requests(admin_verdict) WHERE admin_verdict = 'pending';
```

---

## Edge Cases NOT Covered in This Scenario

| Case | What should happen |
|------|-------------------|
| Customer gives correct 2-3 out of 3 | Reset PIN directly (no receipt needed) |
| Customer sends fake receipt | Admin catches it during verification → deny + lock |
| Customer who never had a PIN originally | Different branch — see separate scenario doc |
| Customer uses old phone + correct PIN | Normal recovery (covered in `new-number-recovery.md`) |
| Admin denies the recovery | Notify customer + lock account + suggest: contact admin directly via voice/video verification |
| Customer waits > 24h for verdict | Auto-deny with reason: "Recovery window expired" + suggest: contact support |
| Receipt from someone else's account | Admin must check tx_ref against claimed customer name — mismatch = deny |

---

## Related

- `workflows/WORKFLOW_SPECS.md` §Account Recovery (new section)
- `scenarios/2026-06-26-first-time-order.md` — original PIN setup
- `scenarios/2026-06-26-new-number-recovery.md` — normal recovery (had PIN)
- `docs/DEAD_IP_REPLACEMENT_POLICY.md` — dead-IP retry flow
- `docs/adr/ADR-004-secrets-management.md` — bcrypt PIN storage
- `docs/SECURITY_RUNBOOK.md` §4 — incident response for account takeover