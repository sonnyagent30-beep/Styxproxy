# Bunche — Complete Scenario Walkthrough
## Customer → Bunche → Admin (All Scenarios)

**Date:** 2026-06-27
**Status:** COMPREHENSIVE — all 5 canonical scenarios + admin operations
**Source:** 5 scenario docs + 18 admin commands + WORKFLOW_SPECS

---

## How to Read This Document

Each scenario shows:
1. **Customer message** — what the person on WhatsApp types
2. **Bunche system** — what happens behind the scenes
3. **Bunche reply** — what the customer sees on WhatsApp
4. **Admin side** — what admin sees, gets notified about, or acts on

---

## SCENARIO 1: First-Time Paid Order (ISP UK)

### Flow: Customer → Bunche → Admin

---

#### STEP 1 — Customer sends `Hi`

```
Customer: Hi
```

**Bunche system:**
- Receive WhatsApp webhook
- Signature verify ✅
- Idempotency check ✅ (new sender)
- Rate limit ✅
- Hash phone → check customers table → **NEW PHONE**
- LLM Intent Parser: { intent: greeting, confidence: 0.99 }
- 24h LLM cache miss → cache response

**Bunche reply:** Standard first-time greeting (services + prices + legal notice + tip)

**Admin side:** None

---

#### STEP 2 — Customer sends `I want UK ISP`

```
Customer: I want UK ISP
```

**Bunche system:**
- LLM Intent Parser: { intent: order, product: ISP, country: UK, quantity: 1 }
- NEW CUSTOMER branch
- **PRE-PAYMENT CHECK (ALL PROVIDERS):**
  - POST Proxy-Seller /balance → 200 OK, balance $45.20 ✅
  - GET Proxy-Seller /countries → UK available ✅
  - POST DataImpulse /balance → 200 OK ✅
  - GET DataImpulse /products → UK available via ISP (Proxy-Seller) ✅
- All checks pass → generate order
- Generate order ID: ORD-20260627-0947
- Generate Flutterwave payment link (expires: NOW + 30 min)
- Log: order_pending, provider_check_pass

**Bunche reply:**

```
✅ Confirmed: 1 × ISP UK @ ₦6,500/mo

💳 Pay here:
👉 https://checkout.flutterwave.com/ORD-20260627-0947

Pay with:
• Bank transfer • Card • USSD • QR code

⏰ Link valid for 30 minutes.

💡 Tip: Bank transfer is fastest — most banks complete in under 30 seconds.

Once I see your payment, your IP arrives in under 2 minutes ⚡
```

**Admin side:** None (pre-check passed silently)

---

#### STEP 3 — (Off-screen) Customer pays via Flutterwave

**Bunche system (webhook):**
- Flutterwave POSTs to `/webhook/payment`
- HMAC verify (verif-hash) ✅
- Idempotency: Redis key → miss → PostgreSQL check ✅ → payment successful ✅
- **Workflow 2 triggered**

---

#### STEP 4 — Customer sends `Paid`

```
Customer: Paid
```

**Bunche system:**
- LLM Intent Parser: { intent: payment_confirmation }
- Check order ORD-20260627-0947: status=paid ✅
- **Generate IP via Proxy-Seller API:** ip=198.51.100.42, port=8000, user=bunche_uk_a3c8, pass=T7nQ9xM2pK, expires=2026-07-27
- **TEST IP (2 endpoints, 5s timeout):** curl → ✅ PASS
- Update order: status=fulfilled
- **Trigger name capture (Workflow 2 sub-step)**

**Bunche reply:**

```
✅ Payment received — ₦6,500

⚡ Generating your UK IP now...

🔐 Before I send your proxy — what should we call you?

This becomes your referral name — share it with friends and you earn
5% credit on their first order. Credit never expires.

Reply with a name (letters + numbers, 3–20 chars) 👇

Example: Chidi · Tunde22 · Maya_proxy
```

**Admin side:** None

---

#### STEP 5 — Customer sends `Dan`

```
Customer: Dan
```

**Bunche system:**
- Name uniqueness: `SELECT id FROM customers WHERE LOWER(name)='dan'` → NOT taken ✅
- Save: INSERT customers + link order → customer
- Trigger **PIN offer sub-step**

**Bunche reply:**

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

**Admin side:** None

---

#### STEP 6 — Customer sends `1234` (or `skip`)

```
Customer: 1234
```

**Bunche system:**
- bcrypt hash PIN → store in customers.pin_hash
- Deliver the proxy

**Bunche reply:**

```
No problem — your proxy is ready.

━━━━━━━━━━━━━━━━━━
🌍 YOUR ISP UK PROXY — LIVE
━━━━━━━━━━━━━━━━━━

🔗 IP: 198.51.100.42
🔌 Port: 8000
👤 User: bunche_uk_a3c8
🔑 Pass: T7nQ9xM2pK
📅 Expires: July 27, 2026

━━━━━━━━━━━━━━━━━━
📄 Receipt: https://files.bunche.ng/receipts/ORD-20260627-0947.pdf
━━━━━━━━━━━━━━━━━━

💡 Setup tip: Phone → Settings → VPN → Add → enter the details above.
One IP per device works best.

💡 Share your name Dan with friends → 5% credit when they buy!

Need help? Reply how to use.

⚠️ No refunds once delivered. If your IP gets banned within 24 hours,
send the screenshot and we'll replace it free.
```

**Admin side:** None. Logged: order_fulfilled, pin_set

---

## SCENARIO 1B: Dead IP After Payment (1-3 Retries Before Success)

### Same as Scenario 1 Steps 1-5, then:

**Bunche system:**
- Test 1: ❌ → auto-retry → Test 2: ❌ → auto-retry → Test 3: ✅
- Log: `ip_retries=2`
- Deliver working IP (third attempt)

**Bunche reply:** Same as Scenario 1, Step 6 (with working IP)

**Admin side:** ⚠️ Logged: `ip_retry`, retry_count=2. If >5% of daily orders: alert

---

## SCENARIO 1C: All 4 IP Attempts Fail (Auto-Refund)

**Bunche system:**
- Test 1: ❌ → Test 2: ❌ → Test 3: ❌ → Test 4: ❌
- **Trigger auto-refund via Flutterwave API**
- Update order: status=refunded

**Bunche reply:**

```
⚠️ Sorry, Dan — we hit a technical issue and couldn't generate a working IP for your order.

✅ Your full payment of ₦6,500 has been refunded automatically.
⏰ Refund will land in your account within 24 hours.

We won't try again on this order — please reorder later or try a different product.

Sorry for the inconvenience 🙏
```

**Admin side:** 🔴 WhatsApp alert:
```
🚨 AUTO-REFUND TRIGGERED

Order: ORD-20260627-0947
Customer: Dan (a3f2b9...)
All 4 IP attempts failed.
Refund ID: FLW-REF-XXX
```

---

## SCENARIO 2: Provider Down (Pre-Payment)

### Flow: Customer → Bunche → Admin

---

#### STEP 1 — `Hi` (standard greeting) → STEP 2 — `I want US ISP`

**Bunche system:**
- **PRE-PAYMENT CHECK (ALL PROVIDERS):**
  - POST Proxy-Seller /balance → **503 Service Unavailable** ❌
  - POST Proxy-Seller /balance (retry) → still 503 ❌
  - POST DataImpulse /balance → 200 OK ✅
  - GET DataImpulse /products → ISP US NOT available ❌ (DataImpulse has RES/MOB only)
- **Do NOT generate payment link**
- **Alert admin via WhatsApp**

**Bunche reply:**

```
⚠️ ISP US is temporarily unavailable.

Our provider is currently down — we can't generate ISP proxies right now.

━━━━━━━━━━━━━━━━━━
✅ OTHER PRODUCTS AVAILABLE RIGHT NOW:
━━━━━━━━━━━━━━━━━━

🌐 Residential 5GB → ₦5,000  (data never expires)
📱 Mobile 4G 5GB → ₦20,000

Reply with the product you want (e.g. Order RES 5GB) or
reply wait and I'll ping you the moment ISP is back 🙏
```

**Admin side:** 🔴 Alert:
```
🚨 PROVIDER DOWN: Proxy-Seller

Product: ISP (all countries)
Error: 503 Service Unavailable
Customer queue: 1 (waiting for ISP)
```

---

#### STEP 3 — Customer sends `wait`

**Bunche system:** Add phone_hash to `notify_on_recovery` queue

**Bunche reply:**
```
✅ You're on the list, Dan.
I'll ping you the moment ISP is back 🙏
```

---

#### STEP 4 — (Background) Provider restored → all waiting customers notified

**Bunche system:**
- **PRE-PAYMENT CHECK (ALL PROVIDERS):**
  - POST Proxy-Seller /balance → **200 OK, balance $45.20** ✅
  - GET Proxy-Seller /countries → US available ✅
  - POST DataImpulse /balance → 200 OK ✅
  - GET DataImpulse /products → US available ✅
- Provider RESTORED
- Notify ALL customers in ISP wait queue

**Bunche reply (to each):**
```
✅ Good news — ISP is back!

You can now order:
🇺🇸 ISP US → ₦6,500/mo
🇬🇧 ISP UK → ₦6,500/mo

Reply with what you want 💪
```

**Admin side:** 🟢 Provider RESTORED → customers notified

---

## SCENARIO 3: New Number / Account Recovery

### Flow: Customer → Bunche → Admin

---

#### STEP 1 — `Hi` → standard greeting (don't leak account)

---

#### STEP 2 — Customer reveals lost phone

```
Customer: Please I misplaced my phone and I'm messaging with a new number.
Can I get my IP details?
```

**Bunche system:** Need BOTH name + PIN to authenticate

**Bunche reply:**
```
🔐 Sorry to hear that — let's get you back in.

To verify it's really you, I need TWO things:

1️⃣ Your referral name (e.g. Dan, Chidi, Tunde22)
2️⃣ Your 4-digit PIN

⚠️ Wrong PIN 3 times = locked + admin alert.

Reply with both, like: Dan 1234
```

---

#### STEP 3 — Customer sends `Dan 1234`

**Bunche system:**
- Name lookup: `SELECT ... WHERE LOWER(name)='dan'` → found ✅
- bcrypt PIN verify: MATCH ✅
- Look up active proxies
- **Ask before changing primary phone**

**Bunche reply:**
```
✅ Verified — welcome back, Dan!

I found 1 active proxy on your account. Showing now ↓

━━━━━━━━━━━━━━━━━━
📋 YOUR ACTIVE PROXIES
━━━━━━━━━━━━━━━━━━

🇺🇸 ISP US (expires July 27, 2026)
🔗 IP: 198.51.100.42
🔌 Port: 8000

━━━━━━━━━━━━━━━━━━
⚠️ SECURITY: Should I link this new number to your account?
━━━━━━━━━━━━━━━━━━

Reply:
• link — this new number becomes your primary. Old number loses access.
• keep both — both numbers work, but only the new one for new orders.
```

---

#### STEP 4A — Customer sends `link`

**Bunche system:**
- Update primary phone to new number
- **Send security alert to OLD phone**

**Bunche reply (new phone):**
```
✅ Done — this number is now your primary.

📞 Old number: +234...OLD (no longer has access)
📞 New number: +234...NEW (this one, primary)

🔒 Security alert sent to your old number.
```

**Bunche reply (OLD phone simultaneously):**
```
📱 Your Bunche account is now linked to a new number.
If this wasn't you, reply STOP immediately.
```

**Admin side:** ⚠️ Logged: phone_linked, old_phone, new_phone

---

#### STEP 4B — Customer sends `STOP` from old phone

**Bunche system:**
- Reverse the link
- Lock account until PIN reset

**Admin side:** 🔴 Alert:
```
🚨 STOP RECEIVED FROM OLD PHONE

Customer: Dan
Action: Link reversed. Account locked.
Old phone +234...OLD: no longer linked.
New phone +234...NEW: pending verification.
```

---

## SCENARIO 4: Forgot PIN

### Flow: Customer → Bunche → Admin

---

#### STEP 1-2 — `Hi` → "lost phone" → Bunche asks for name + PIN

---

#### STEP 3 — Customer sends `I forgot my PIN`

**Bunche system:** Trigger order-details verification

**Bunche reply:**
```
No problem — let's verify your identity another way.

What was your last order? (You don't need the exact details,
just enough to confirm it's you.)

Tell me:
• What product did you buy? (e.g. ISP UK, Residential 5GB)
• Roughly when? (e.g. last week, this month)
• What country was it for? (if applicable)

I'll cross-check against your account.
```

---

#### STEP 4 — Customer describes correctly

```
Customer: I bought ISP UK, about 2 weeks ago, for the UK
```

**Bunche system:** Order found → allow access

**Bunche reply:**
```
✅ Identity confirmed — welcome back, Dan!

Since you forgot your PIN, let's set a new one.

🔐 Reply with a new 4-digit number 👇
(Skip if you don't want a PIN.)
```

---

#### STEP 4X — Customer describes INCORRECTLY × 3

**Bunche system:** 3 failures → 15-min lockout

**Bunche reply:**
```
🔒 Your account is temporarily locked.

This happens after 3 failed identity checks — for your security.

Try again in 15 minutes, or contact admin for help.
```

**Admin side:** 🔴 Alert:
```
🚨 FORGOT-PIN LOCKOUT

Customer: Dan (a3f2b9...)
Result: 3 failed verification attempts
Lockout: 15 minutes

Risk: Possible account takeover attempt.
```

**CRITICAL ANTI-LEAK:** Bunche NEVER reveals actual order details (IP, exact date, amount) on failed verification — attacker learns nothing usable.

---

## SCENARIO 5: Free Trial

### Flow: Customer → Bunche → Admin

---

#### STEP 1 — `Hi` → standard greeting

---

#### STEP 2 — Customer asks for free trial

```
Customer: Do you have a free plan, your product seems expensive for me right now
```

**Bunche system:** Send disclaimer FIRST (before any access)

**Bunche reply:**

```
🎁 FREE TRIAL — DISCLAIMER

Before we send your free IP, please read:

━━━━━━━━━━━━━━━━━━
⚠️ FREE TRIAL TERMS ⚠️
━━━━━━━━━━━━━━━━━━

❌ NOT for production/critical use
❌ Not guaranteed private (shared with other trials)
❌ IP shared = if one user misbehaves, IP could get flagged
❌ No replacement if proxy dies or expires
❌ Used entirely at YOUR OWN RISK

✅ Bunche-hosted proxy — generally reliable
✅ Auto-expires after 2 hours
✅ For testing our service only
✅ Upgrade to paid plan for reliability + privacy

━━━━━━━━━━━━━━━━━━

Complete ONE survey to unlock your IP:

[SURVEY LINK — Theorem Reach]

After completing, reply DONE
```

**Admin side:** None

---

#### STEP 3 — Customer replies `Done` (survey completed)

**Bunche system (invisible to customer):**
```
1. Check daily counter: COUNT(*) FROM free_trials WHERE phone_hash=? AND DATE=NOW → if >= 3 → reject
2. Verify Theorem Reach HMAC signature ✅
3. Check status=completed ✅
4. Idempotency: transaction_id not yet processed ✅
5. Generate credentials: user_id=trial_a7b9c2, port=next available (8001-8100), expires=NOW+2hr
6. Execute: manage-3proxy-trial.sh add USER PASS PORT
7. INSERT free_trials: status=active
8. Schedule cleanup at expires_at
```

**Bunche reply (✅ SUCCESS):**
```
✅ Survey verified! Trial ready.

━━━━━━━━━━━━━━━━━━
🌐 BUNCHE TRIAL PROXY — 2 HOURS
━━━━━━━━━━━━━━━━━━

🔗 IP: bunche.ng
🔌 Port: 8001
👤 User: trial_a7b9c2
🔑 Pass: Kx9mNp2qR8sT4wY7

⏰ Expires: [current time + 2hrs]

⚠️ Shared proxy — other trial users share this IP.
For private/production use, upgrade to a paid plan.

🛡️ You've used [X/3] free trials today.

💡 Want reliable proxies? Reply menu to see paid plans.
```

**Bunche reply (🛡️ DAILY LIMIT HIT):**
```
🛡️ Daily limit reached — you've used 3/3 free trials today.

Come back tomorrow, or skip the wait with a paid plan:
• ISP UK/US: ₦6,500/mo
• Residential 5GB: ₦5,000

Reply menu to order.
```

**Bunche reply (⚠️ SLOTS BUSY):**
```
⚠️ All trial slots busy right now.

We'll ping you the moment one opens up (usually within 30 minutes).

🛡️ You've used [X/3] free trials today.
```

**Admin side:** ⚠️ If HMAC fails: 🔴 Alert:
```
🚨 THEOREM REACH HMAC FAILURE

transaction_id: TR-987654
→ Possible fake postback. Investigating.
```

---

#### STEP 4 — (Background) Cron every 5 min: credential cleanup

**Bunche system:**
```
SELECT user_id FROM free_trials WHERE status='active' AND expires_at < NOW()
For each: manage-3proxy-trial.sh remove USER → UPDATE status='expired'
```

Customer messages "trial died" → Bunche:
```
⏰ Your trial expired after 2 hours.

That's expected for free trials. Want to:
• Try another free trial (you've used [X/3] today)
• Upgrade to a paid plan

Reply menu or trial.
```

---

## SCENARIO 6: Ban Claim

### Flow: Customer → Bunche → Admin

---

#### Customer sends `My IP got banned, here's the screenshot`

**Bunche system:**
- Create BAN-CLAIM-001, store screenshot
- Add to `pending` for admin

**Bunche reply:**
```
📸 Received — screenshot saved.

Your ban claim is now in review.

Claim ID: BAN-CLAIM-001
Expected response: within 24 hours.
```

**Admin side:** ⏳ Added to `Pending` queue

---

#### Admin approves: `Approve BAN-CLAIM-001` (PIN + TOTP)

**Bunche system:**
- Verify PIN + TOTP ✅
- Request replacement IP from Proxy-Seller (different from banned IP)
- Test new IP ✅ → deliver

**Bunche reply (to customer):**
```
✅ Ban claim approved — replacement IP is ready!

🔗 IP: 185.123.45.99 (different from previous)
🔌 Port: 8000
👤 User: bunche_uk_b8d3
🔑 Pass: Y2kL8mN4pR6tW9xZ1
📅 Expires: July 27, 2026
```

---

#### Admin rejects: `Reject BAN-CLAIM-001 reason` (PIN + TOTP)

**Bunche reply (to customer):**
```
❌ Ban claim reviewed — replacement declined.

Reason: [admin's reason]

Your proxy: 198.51.100.42

If you believe this is an error, reply with more details.
```

---

## SCENARIO 7: Referral

### Flow: Friend → Bunche → Admin

---

#### Friend orders and mentions referral name

```
Customer: I want UK ISP, my friend Ada told me about this
```

**Bunche system:**
- LLM: { intent: order, referral_name: Ada }
- Lookup: `SELECT id FROM customers WHERE LOWER(name)='ada'` → found ✅
- Save referral_name to order record

---

#### Friend pays

**Bunche system:**
- On payment: INSERT referral_credits (Ada gets 5% = ₦325)
- Ada receives WhatsApp:
```
🎉 Dan just ordered through your link!

You've earned ₦325 credit — added to your account.

Your total referral credit: ₦9,825

Keep sharing your name Ada 💪
```

---

## SCENARIO 8: Data Alert Escalation

### Flow: Bunche (cron) → Customer → Admin

---

#### Customer at 80% Residential data

**Bunche reply (automated):**
```
⚠️ Data Alert — Dan

You've used 4.0 GB of your 5 GB Residential proxy.
0.8 GB remaining. Once it's done, the proxy stops.

To avoid interruption:
• Residential 5GB → ₦5,000 (adds 5 more GB)

Reply Order RES 5GB to top up.
```

---

#### Customer at 100% data

**Bunche reply (automated):**
```
🔴 Data Exhausted — Dan

Your 5 GB Residential proxy has run out.
The proxy has stopped working.

To restore access:
• Residential 5GB → ₦5,000

Reply Order RES 5GB to continue.
```

**Admin side:** Informational (upsell opportunity)

---

## SCENARIO 9: Daily Summary

### Flow: Bunche (cron 23:55) → Admin

---

**Admin receives (automated):**
```
📊 Daily Summary — June 27

💰 Revenue: ₦312,500 (47 orders)
👥 New customers: 8
⚠️ Errors: 2 (1 critical)
💸 Refunds: 1
🎁 Free trials: 47 (₦70.50 from Theorem Reach)
🔗 Referral purchases: 2 (₦650 credit paid out)

⚠️ Provider downtime: Proxy-Seller 47 min
⚠️ IP retry rate: 2.1% (acceptable)

Full details: https://n8n.yunche.ng/executions/...
```

---

## SCENARIO 10: Error Alert (Critical)

### Flow: Bunche → Admin

---

**Admin receives:**
```
🚨 CRITICAL ERROR — Order ORD-20260627-1423-001

Workflow: Payment Confirmation
Error: "Provider API returned 503 after 4 attempts"
Action: Auto-refunded customer

Reply 'Resolve ERR-20260627-1423-001' when investigated.
```

Admin: `Resolve ERR-20260627-1423-001` + PIN → marks resolved

---

## COMPLETE EVENT → ACTION → ADMIN FLOW TABLE

| # | Event | Bunche Response | Admin Notification |
|---|-------|----------------|-------------------|
| 1 | New customer `Hi` | Standard greeting + menu | None |
| 2 | Order request | Pre-check all providers → payment link | None |
| 3 | Provider down at pre-check | Alternatives + wait offer | 🚨 Provider DOWN alert |
| 4 | Provider restored | Notify all waiting customers | ✅ Provider restored |
| 5 | Payment confirmed | Name capture | None |
| 6 | Name + PIN set | Deliver IP | None |
| 7 | IP dead (1-3 retries) | Retry silently → deliver if success | ⚠️ IP retry logged (>5% = alert) |
| 8 | All 4 IPs dead | Auto-refund message | 🚨 AUTO-REFUND alert |
| 9 | New phone + account recovery | Auth challenge (name + PIN) | None |
| 10 | Recovery success + `link` | Update primary phone | ⚠️ Phone linked logged |
| 11 | Recovery success + `STOP` from old phone | Reverse link + lock | 🚨 STOP received → reverse + lock |
| 12 | Forgot PIN + order verified | Reset PIN option | None |
| 13 | Forgot PIN + 3 wrong verifications | 15-min lockout | 🚨 FORGOT-PIN LOCKOUT alert |
| 14 | Free trial request | Disclaimer + survey link | None |
| 15 | Survey done + limit OK | Trial credentials (2hr) | None |
| 16 | Survey done + limit HIT | "3/3 used today" | None |
| 17 | Trial slots exhausted | "Try in 30 min" | None |
| 18 | Trial expires (2hr) | No auto-message (customer-initiated) | None |
| 19 | 3proxy HMAC fail | None (silent) | 🚨 HMAC FAILURE alert |
| 20 | Ban claim reported | "In review, 24h" | ⏳ Added to Pending |
| 21 | Ban claim approved | New IP delivered | 🟢 Logged |
| 22 | Ban claim rejected | "Declined + reason" | 🟢 Logged |
| 23 | Referral name entered | Saved with order | 🟢 Logged on payment |
| 24 | Referral order paid | Credit to referrer + notification | 🟢 Logged |
| 25 | Data 80% used | Warning message to customer | ⚠️ Data alert (escalation) |
| 26 | Data 100% used | Exhaustion message to customer | ⚠️ Data exhausted (upsell) |
| 27 | Daily cron 23:55 | None | 📊 Daily Summary report |
| 28 | Workflow CRITICAL error | Auto-refund if applicable | 🚨 CRITICAL ERROR alert |
| 29 | 3 consecutive failed PINs | Lockout message | 🚨 LOCKOUT alert |
| 30 | 5 failed PINs | 1-hour lockout | 🚨 PROLONGED LOCKOUT alert |

---

## CRITICAL SECURITY RULES (Summary)

| Rule | Description |
|------|-------------|
| Never reveal account existence from name alone | Must have PIN to confirm |
| Never show order details on failed verification | Anti-leak: attacker learns nothing |
| Wrong PIN × 3 = 15-min lockout + admin alert | Brute-force protection |
| All admin actions logged with phone_hash | Full audit trail |
| High-risk commands need PIN + TOTP | Two-factor for financial actions |
| Phone link sends alert to OLD number | Theft/fraud protection |
| Old phone STOP = reverse link + lock | Reversibility |
| Daily limit on free trials = 3 per phone | Anti-abuse |
| Theorem Reach HMAC verified before grant | Anti-fake-survey |
| All IP tested before delivery | Quality gate |
| Pre-payment check = ALL providers | Never generate link without confirming stock |
