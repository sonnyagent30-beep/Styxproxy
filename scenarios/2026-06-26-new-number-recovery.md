# Bunche — Scenario Replay: Customer Messaging from New Number

**Date captured:** 2026-06-26
**Source:** Live roleplay session between Dannion (customer) and Sonny (as Bunche)
**Status:** Rules extracted + locked for v3

---

## The Scenario (Verbatim)

### Setup:
- Dan is an existing customer (name='Dan', has 1 active ISP US proxy)
- Dan set a PIN: `1234` (from earlier first-time scenario)
- Dan lost his phone / got a new SIM
- Dan messages Bunche from a NEW phone number

---

### Turn 1 — Customer: `Hi`

**System:**
- New phone → phone NOT in customers table
- LLM Intent Parser: {intent: greeting, confidence: 0.99}
- Treat as fresh greeting (no assumption of account)

**Customer-facing:**

```
👋 Welcome to Bunche — your plug for ISP, Datacenter, Residential & Mobile proxies.
Pay in Naira, get your proxy in under 2 minutes.

[full services + prices menu shown]
```

**Rule extracted:** New phone = standard greeting, even if customer "looks" returning. Don't leak account existence to a stranger.

---

### Turn 2 — Customer: `Please I misplaced my phone and am messaging with a new number can I get my ip details`

**System:**
- LLM Intent Parser: {intent: recover_account, confidence: 0.95}
- Current phone NOT in customers → unknown person
- Need to authenticate via name + PIN
- 3-strike lockout rule applies

**Customer-facing:**

```
🔐 Sorry to hear that — let's get you back in.

To verify it's really you, I need TWO things:

1️⃣ Your referral name (e.g. Dan, Chidi, Tunde22)
2️⃣ Your 4-digit PIN

⚠️ Wrong PIN 3 times = locked + admin alert.

Reply with both, like: Dan 1234
```

**Rule extracted:** Account recovery ALWAYS requires BOTH name AND PIN. Never reveal account existence based on name alone.

---

### Turn 3 — Customer: `Dan` then `1234` (2 messages, same session)

**System:**
- Name lookup: `SELECT id, phone, pin_hash FROM customers WHERE LOWER(name) = 'dan'` → found
- PIN verify: bcrypt.compare("1234", stored_hash) → MATCH ✅
- Look up active proxies: `SELECT * FROM orders WHERE customer_phone = +234...OLD AND status = 'fulfilled'`
- Found: 1 active ISP US proxy
- Ask before linking (don't assume)

**Customer-facing:**

```
✅ Verified — welcome back, Dan!

I found 1 active proxy on your account. Showing now ↓

━━━━━━━━━━━━━━━━━━
📋 YOUR ACTIVE PROXIES
━━━━━━━━━━━━━━━━━━

🇺🇸 ISP US (expires July 27, 2026)
🔗 IP: 198.51.100.42
🔌 Port: 8000
👤 User: bunche_us_a3c8
🔑 Pass: T7nQ9xM2pK

━━━━━━━━━━━━━━━━━━
⚠️ SECURITY: Should I link this new number to your account?
━━━━━━━━━━━━━━━━━━

Reply:
• link — this new number becomes your primary. Old number loses access.
• keep both — both numbers work, but only the new one for new orders.
```

**Rule extracted:** After successful auth, ALWAYS show proxies AND ask before changing account-critical state (like primary phone). Never assume.

---

### Turn 4 — Customer: `Link`

**System:**
- `UPDATE customers SET phone = +234...NEW, previous_phone = +234...OLD, phone_updated_at = NOW(), phone_change_count = phone_change_count + 1 WHERE id = ...`
- Audit log: phone_linked, old_phone_hash, new_phone_hash
- Send security alert to OLD phone number (in case thief is doing this)
- Don't block old number — let customer/legit owner respond to alert

**Customer-facing (new phone):**

```
✅ Done — this number is now your primary.

📞 Old number: +234...OLD (no longer has access)
📞 New number: +234...NEW (this one, primary)

🔒 Security alert sent to your old number.

From now on, all orders, support, and recovery go through this number.

Anything else? Reply menu anytime 💪
```

**Customer-facing (OLD phone, simultaneously):**

```
📱 Your Bunche account is now linked to a new number.
If this wasn't you, reply STOP immediately.
```

**Rule extracted:** When linking new phone, ALWAYS alert the old phone. If old phone replies STOP, reverse the link + lock account until PIN reset.

---

## Critical Rules Locked in This Scenario

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | New phone always gets standard greeting (don't leak account existence) | WORKFLOW_SPECS §1 |
| 2 | Account recovery requires BOTH name + PIN | WORKFLOW_SPECS §Account Recovery |
| 3 | Never reveal account based on name alone — PIN is required | WORKFLOW_SPECS §Account Recovery |
| 4 | Wrong PIN × 3 → lockout + admin alert | WORKFLOW_SPECS §Account Recovery + SECURITY_PLAN |
| 5 | After auth, show proxies AND ask before changing primary phone | WORKFLOW_SPECS §Account Recovery |
| 6 | Phone-link change sends security alert to OLD phone | WORKFLOW_SPECS §Account Recovery |
| 7 | Old phone can reply STOP to reverse the link | WORKFLOW_SPECS §Account Recovery |
| 8 | Track phone_change_count for fraud detection | DATABASE_SCHEMA |

---

## Database Schema Notes (New Requirements)

```sql
ALTER TABLE customers
ADD COLUMN previous_phone VARCHAR(20),            -- last phone before migration
ADD COLUMN phone_updated_at TIMESTAMPTZ,           -- when last phone change happened
ADD COLUMN phone_change_count INT DEFAULT 0,       -- how many times customer has changed phone
ADD COLUMN pin_hash VARCHAR(255),                  -- bcrypt hash (already exists if implemented)
ADD COLUMN pin_failed_attempts INT DEFAULT 0,      -- running counter, resets on success
ADD COLUMN pin_locked_until TIMESTAMPTZ;           -- NULL = unlocked, otherwise locked until this time
```

---

## Edge Cases NOT Covered in This Scenario

| Case | What should happen |
|------|-------------------|
| Customer gives wrong PIN 1st time | "Wrong PIN. 2 attempts left." |
| Customer gives wrong PIN 2nd time | "Wrong PIN. 1 attempt left. Admin will be alerted if you fail again." |
| Customer gives wrong PIN 3rd time | LOCKED for 15 min + admin alert: "Customer 'Dan' failed 3 PIN attempts from +234...NEW" |
| Customer says "keep both" | Old phone still has access, new phone also works for orders/recovery |
| Customer who never set a PIN originally | Special flow — see next scenario doc |
| Customer who forgot PIN | Special flow — see next scenario doc |
| Old phone replies STOP to security alert | Reverse link + lock account + admin alert: "Possible account takeover on Dan's account" |
| Thief who knows name + PIN (somehow) | Both phone-link security alert + admin manual review trigger |

---

## Admin Alert Templates (New)

**Wrong PIN attempt:**
```
⚠️ Failed PIN attempt 1/3
Customer: a3f2b9c1... (Dan hash)
Phone: 8d7e4f2c... (NEW phone hash)
Time: 2026-06-27 14:23 Lagos
No action needed unless 3 fails.
```

**3-strike lockout:**
```
🚨 ACCOUNT LOCKED
Customer: a3f2b9c1... (Dan hash)
Phone: 8d7e4f2c... (NEW phone hash)
Failed 3 PIN attempts. Account locked for 15 minutes.
Action: Monitor for repeated attempts. May indicate account takeover.
```

**Phone-link security alert triggered STOP:**
```
🚨 POSSIBLE ACCOUNT TAKEOVER
Customer: a3f2b9c1... (Dan hash)
Old phone (8d7e4f2c...): user replied STOP to security alert
New phone (2c9b1a3e...): user had valid name + PIN
Action: Account now LOCKED. Contact Dan via verified channel before unlocking.
```

---

## Related

- `workflows/WORKFLOW_SPECS.md` §1, §2, §Account Recovery (new section)
- `docs/REFERRAL_SYSTEM.md` — referral mechanics (name handling)
- `docs/adr/ADR-004-secrets-management.md` — bcrypt PIN storage
- `docs/SECURITY_RUNBOOK.md` §1, §4 — rotation + incident response
- `scenarios/2026-06-26-first-time-order.md` — original PIN setup
- `scenarios/2026-06-26-provider-down-recovery.md` — dead-IP + retry flow