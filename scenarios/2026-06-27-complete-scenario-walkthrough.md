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

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

---

#### STEP 1 — Customer sends `Hi`

```
Customer: Hi
```

**Bunche system:**
- Receive message via [channel] webhook
- [For WhatsApp: HMAC signature verify ✅] [For Telegram: message authenticity handled by Telegram API ✅]
- Idempotency check ✅ (new sender)
- Rate limit ✅
- Hash phone → check customers table → **NEW PHONE**
- LLM Intent Parser: { intent: greeting, confidence: 0.99 }
- 24h LLM cache miss → cache response

**Bunche reply:**

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

━━━━━━━━━━━━━━━━━━
🛒 To order, just type:
Order ISP UK 1 · Order RES 5GB · Order MOB 10GB
━━━━━━━━━━━━━━━━━━

💡 Tip: For social media & multi-account work → ISP. For scraping & bulk
data → Residential. For mobile-only platforms (TikTok, etc.) → Mobile 4G.

What do you need? 👇
```

**Admin side:**
- 🟢 No admin action required
- Bunche Logger: `customer_new_session`, phone_hash logged (name=NULL at this stage)

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

**Admin side:**
- 🟢 No action — pre-check passed silently
- Bunche Logger: `provider_precheck_pass`, product=ISP_UK, provider=Proxy-Seller

---

#### STEP 3 — (Off-screen) Customer pays via Flutterwave

```
Customer: [pays ₦6,500 via bank transfer / card / USSD]
```

**Bunche system (webhook):**
- Flutterwave POSTs to `/webhook/payment`
- HMAC verify (verif-hash) ✅
- Idempotency: Redis key `webhook:processed:flutterwave:ORD-20260627-0947` → miss
- PostgreSQL check: order exists, status=pending ✅
- Payment status: successful ✅
- **Workflow 2 triggered**

**Admin side:**
- No direct alert for successful payment (let admin check daily summary)
- Logged: `payment_received`, order_id, amount=₦6,500

---

#### STEP 4 — Customer sends `Paid`

```
Customer: Paid
```

**Bunche system:**
- LLM Intent Parser: { intent: payment_confirmation }
- Check order ORD-20260627-0947: status=paid ✅
- **Generate IP via Proxy-Seller API:**
  - POST /api/v1/order/create → ip=198.51.100.42, port=8000, user=bunche_uk_a3c8, pass=T7nQ9xM2pK, expires=2026-07-27
- **TEST IP (2 endpoints, 5s timeout):**
  - curl --proxy 198.51.100.42:8000 --user bunche_uk_a3c8:T7nQ9xM2pK https://api.ipify.org → ✅ PASS
- Update order: status=fulfilled, ip_recorded
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

**Admin side:**
- 🟢 No action — IP test passed silently
- Bunche Logger: `ip_tested_pass`, order_id, ip=198.51.100.42
- If IP had failed: would log `ip_test_fail` + trigger retry flow (Scenario 1b)

---

#### STEP 5 — Customer sends `Dan`

```
Customer: Dan
```

**Bunche system:**
- Name uniqueness check: `SELECT id FROM customers WHERE LOWER(name)='dan'` → NOT taken ✅
- Save: INSERT customers (phone_hash, name, created_at)
- Save: INSERT order_customer (link order → customer)
- Trigger **PIN offer sub-step**
- Referral check: no referral code entered (would have been captured at order time)

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

**Admin side:**
- 🟢 No action
- Bunche Logger: `customer_registered`, name=Dan, order_id=ORD-20260627-0947

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

**If customer sends `skip`:**
- pin_hash = NULL
- Same delivery message (PIN step is skipped)

**Admin side:**
- 🟢 No action
- Bunche Logger: `order_fulfilled`, `pin_set` (or `pin_skipped`), order_id
- Daily Summary (cron 23:55): will include this order in revenue count

---

## SCENARIO 1B: Dead IP After Payment (within retries)

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

*Triggered when IP test fails 1-3 times before success*

---

#### STEP 1-4 — Same as Scenario 1 Steps 1-4

Through payment received → name captured → PIN set

---

#### STEP 5 — IP test FAILS (retry 1 of 3)

**Bunche system:**
- Test 1: curl → ❌ TIMEOUT
- **Auto-retry: request new IP from Proxy-Seller** (decrement Proxy-Seller balance)
- Test 2: curl → ❌ TIMEOUT
- **Auto-retry #2: request yet another IP**
- Test 3: curl → ✅ PASS (198.51.100.99)
- Deliver 198.51.100.99 to customer
- Log: `ip_retries=2` (shows 2 dead IPs were replaced before success)

**Bunche reply:** Same delivery message as Scenario 1, Step 6 (with new IP)

**Admin side:**
- ⚠️ Logged: `ip_retry`, order_id, retry_count=2, ip_replaced=198.51.100.42→198.51.100.99
- If retries > 5% of daily orders → **ALERT to admin**: "IP retry rate elevated: X%"

---

## SCENARIO 1C: All 4 IP Attempts Fail (Auto-Refund)

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

*Triggered when all 4 IP tests (1 initial + 3 retries) return dead IPs*

---

#### STEP 1-4 — Same as Scenario 1

---

#### STEP 5 — ALL 4 IP TESTS FAIL

**Bunche system:**
- Test 1: ❌ → Test 2: ❌ → Test 3: ❌ → Test 4: ❌
- **Trigger auto-refund via Flutterwave API**
- Update order: status=refunded, refund_id=FLW-REF-XXX
- Do NOT deliver IP

**Bunche reply:**

```
⚠️ Sorry, Dan — we hit a technical issue and couldn't generate a working IP for your order.

✅ Your full payment of ₦6,500 has been refunded automatically.
⏰ Refund will land in your account within 24 hours.

We won't try again on this order — please reorder later or try a different product.

Sorry for the inconvenience 🙏
```

**Admin side:**
- 🔴 **Admin alert (via configured channel — Telegram or WhatsApp):**
  ```
  🚨 AUTO-REFUND TRIGGERED

  Order: ORD-20260627-0947
  Customer: Dan (a3f2b9...)
  Product: ISP UK × 1
  Amount: ₦6,500

  All 4 IP attempts failed.
  Refund ID: FLW-REF-XXX

  Provider: Proxy-Seller
  Action: Auto-refunded. Investigate if recurring.
  ```
- Bunche Logger: `auto_refund`, order_id, ip_failures=4, refund_id

---

## SCENARIO 2: Provider Down (Pre-Payment)

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

*Triggered when Proxy-Seller or DataImpulse is down at pre-payment check*

---

#### STEP 1 — Customer sends `Hi` (same standard greeting)
**Bunche reply:** Standard greeting (same as Scenario 1, Step 1)

---

#### STEP 2 — Customer sends `I want US ISP`

```
Customer: I want US ISP
```

**Bunche system:**
- LLM Intent Parser: { intent: order, product: ISP, country: US, quantity: 1 }
- **PRE-PAYMENT CHECK (ALL PROVIDERS):**
  - POST Proxy-Seller /balance → **503 Service Unavailable** ❌
  - POST Proxy-Seller /balance (retry) → still 503 ❌
  - POST DataImpulse /balance → 200 OK ✅
  - GET DataImpulse /products → ISP US NOT available ❌ (DataImpulse has RES/MOB only)
- **Do NOT generate payment link**
- **Alert admin via WhatsApp**
- Log: provider_down, provider=Proxy-Seller, product=ISP_US

**Bunche reply:**

```
⚠️ ISP US is temporarily unavailable.

Our provider is currently down — we can't generate ISP proxies right now.

━━━━━━━━━━━━━━━━━━
✅ OTHER PRODUCTS AVAILABLE RIGHT NOW:
━━━━━━━━━━━━━━━━━━

🌐 Residential 5GB → ₦5,000  (data never expires)
🌐 Residential 10GB → ₦9,000
📱 Mobile 4G 5GB → ₦20,000
📱 Mobile 4G 10GB → ₦35,000

��� Both Residential and Mobile are working — same fast delivery.

Reply with the product you want (e.g. Order RES 5GB) or
reply wait and I'll ping you the moment ISP is back 🙏
```

**Admin side:**
- 🔴 **Admin alert (via configured channel — Telegram or WhatsApp):**
  ```
  🚨 PROVIDER DOWN: Proxy-Seller

  Product: ISP (all countries)
  Error: 503 Service Unavailable
  Time: 14:23 Lagos

  Checking backup provider... DataImpulse ✓

  Customer queue: 1 (waiting for ISP)
  Action needed: Monitor. Auto-notify on recovery.
  ```
- Bunche Logger: `provider_down`, provider=Proxy-Seller, error=503, customer_queue=1

---

#### STEP 3 — Customer sends `wait`

```
Customer: wait
```

**Bunche system:**
- Add phone_hash to `notify_on_recovery` queue (product=ISP)
- Save to waiting_customers table

**Bunche reply:**

```
✅ You're on the list, Dan.

I'll ping you the moment ISP is back 🙏

No action needed from your side — just wait.
```

**Admin side:**
- 🟢 Queue incremented: 2 (waiting for ISP recovery)

---

#### STEP 4 — (Background) Admin or cron detects provider restored

**Bunche system (cron: every 5 min or admin command):**
- **PRE-PAYMENT CHECK (ALL PROVIDERS):**
  - POST Proxy-Seller /balance → **200 OK, balance $45.20** ✅
  - GET Proxy-Seller /countries → US available ✅
  - POST DataImpulse /balance → 200 OK ✅
  - GET DataImpulse /products → US available ✅
- Provider RESTORED
- **Notify ALL customers in `notify_on_recovery` queue (ISP product):**
  - WhatsApp message to each waiting customer

**Bunche reply (to each waiting customer):**

```
✅ Good news — ISP is back!

You can now order:
🇺🇸 ISP US → ₦6,500/mo
🇬🇧 ISP UK → ₦6,500/mo

Reply with what you want (e.g. Order ISP US 1) or
reply menu to see all products 💪
```

**Admin side:**
- 🟢 Admin gets resolution note:
  ```
  ✅ PROVIDER RESTORED: Proxy-Seller

  ISP available again.
  Customers notified: 2
  Downtime: 47 minutes
  ```
- Bunche Logger: `provider_restored`, provider=Proxy-Seller, downtime_min=47, customers_notified=2

---

#### STEP 5 — Customer re-orders `ISP US`

Now proceeds through normal Scenario 1 Steps 2-6 (pre-check passes, payment link generated, etc.)

---

## SCENARIO 3: New Number / Account Recovery

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

*Triggered when existing customer messages from a new phone number*

---

#### STEP 1 — Customer sends `Hi`

```
Customer: Hi
```

**Bunche system:**
- NEW PHONE → standard greeting (don't leak account existence)
- LLM Intent Parser: { intent: greeting, confidence: 0.99 }

**Bunche reply:** Standard first-time greeting (same as Scenario 1, Step 1)

**Admin side:**
- 🟢 No action
- Bunche Logger: `customer_new_session`, phone_hash (no name yet)

---

#### STEP 2 — Customer reveals situation

```
Customer: Please I misplaced my phone and I'm messaging with a new number.
can I get my IP details?
```

**Bunche system:**
- LLM Intent Parser: { intent: recover_account, confidence: 0.95 }
- Current phone NOT in customers table → unknown person
- Need to authenticate via **BOTH name + PIN**
- 3-strike lockout rule applies

**Bunche reply:**

```
🔐 Sorry to hear that — let's get you back in.

To verify it's really you, I need TWO things:

1️⃣ Your referral name (e.g. Dan, Chidi, Tunde22)
2️⃣ Your 4-digit PIN

⚠️ Wrong PIN 3 times = locked + admin alert.

Reply with both, like: Dan 1234
```

**Admin side:**
- 🟢 No action yet
- Bunche Logger: `account_recovery_attempt`, phone_hash (not yet matched to customer)

---

#### STEP 3 — Customer sends name + PIN

```
Customer: Dan 1234
```

**Bunche system:**
- Name lookup: `SELECT id, phone, pin_hash FROM customers WHERE LOWER(name)='dan'` → **found ✅**
- PIN verify: bcrypt.compare("1234", stored_hash) → **MATCH ✅**
- Look up active proxies: `SELECT * FROM orders WHERE customer_id=? AND status='fulfilled'`
- Found: 1 active ISP US proxy
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
👤 User: bunche_us_a3c8
🔑 Pass: T7nQ9xM2pK

━━━━━━━━━━━━━━━━━━
⚠️ SECURITY: Should I link this new number to your account?
━━━━━━━━━━━━━━━━━━

Reply:
• link — this new number becomes your primary. Old number loses access.
• keep both — both numbers work, but only the new one for new orders.
```

**Admin side:**
- 🟢 No action
- Bunche Logger: `account_recovery_success`, customer_id, old_phone_hash, new_phone_hash
- phone_change_count incremented

---

#### STEP 4 — Customer sends `link`

```
Customer: link
```

**Bunche system:**
- `UPDATE customers SET phone=+234...NEW, previous_phone=+234...OLD, phone_updated_at=NOW(), phone_change_count=phone_change_count+1`
- **Send security alert to OLD phone**
- Don't block old number — let legitimate owner respond

**Bunche reply (new phone):**

```
✅ Done — this number is now your primary.

📞 Old number: +234...OLD (no longer has access)
📞 New number: +234...NEW (this one, primary)

🔒 Security alert sent to your old number.

From now on, all orders, support, and recovery go through this number.

Anything else? Reply menu anytime 💪
```

**Bunche reply (simultaneously to OLD phone):**

```
📱 Your Bunche account is now linked to a new number.
If this wasn't you, reply STOP immediately.
```

**Admin side:**
- ⚠️ Logged: `phone_linked`, customer_id, old_phone, new_phone, phone_change_count=2
- If old phone replies `STOP` → reverse link + lock account → alert admin

---

#### STEP 4B — Customer sends `keep both`

```
Customer: keep both
```

**Bunche system:**
- `UPDATE customers SET additional_phone=+234...NEW`
- Both phones work for viewing status / support
- New orders only from primary phone

**Bunche reply:**

```
✅ Both numbers linked.

📞 Primary: +234...OLD
📞 Secondary: +234...NEW

Both can view your proxy details. New orders come from primary only.

Anything else? Reply menu anytime 💪
```

**Admin side:**
- ⚠️ Logged: `phone_linked_both`, customer_id, primary_phone, additional_phone

---

## SCENARIO 4: Forgot PIN

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

*Triggered when customer tries account recovery but has forgotten their PIN*

---

#### STEP 1-2 — Same as Scenario 3 Steps 1-2

Customer sends `Hi` → reveals lost phone → Bunche asks for name + PIN

---

#### STEP 3 — Customer sends `Dan` then `I forgot my PIN`

```
Customer: I forgot my PIN
```

**Bunche system:**
- Name found ✅, but customer doesn't know PIN
- Trigger **forgot-PIN flow: order-details verification**
- Ask customer to describe their last order

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

**Admin side:**
- 🟢 No action
- Bunche Logger: `forgot_pin_attempt`, name=Dan, method=order_verification

---

#### STEP 4 — Customer describes order correctly

```
Customer: I bought ISP UK, about 2 weeks ago, for the UK
```

**Bunche system:**
- Lookup orders by name=Dan, product~ISP_UK, date~14 days ago → **match found ✅**
- ✅ Allow account access
- PIN remains locked (customer must set new PIN after access)

**Bunche reply:**

```
✅ Identity confirmed — welcome back, Dan!

I found your account. Since you forgot your PIN, let's set a new one.

🔐 Reply with a new 4-digit number 👇

(Skip if you don't want a PIN.)
```

**Admin side:**
- 🟢 Logged: `forgot_pin_verified`, name=Dan, verification=order_details
- **CRITICAL ANTI-LEAK RULE:** Bunche NEVER revealed order details (IP, exact date, amount) in this step. Customer described it → system confirmed match silently.

---

#### STEP 5 — Customer sets new PIN

```
Customer: 5678
```

**Bunche system:**
- bcrypt hash new PIN → update customers.pin_hash
- Show proxies + offer phone link option (same as Scenario 3, Step 3-4)

**Bunche reply:** Same as Scenario 3, Step 3 (show proxies + link/keep both options)

**Admin side:**
- 🟢 Logged: `pin_reset_via_forgot_flow`, customer_id

---

#### STEP 4X — Customer describes order INCORRECTLY (×3)

```
Customer: [wrong details]
Customer: [wrong details again]
Customer: [wrong details a third time]
```

**Bunche system:**
- Attempt 1: no match → "That doesn't match our records. Try again."
- Attempt 2: no match → "Still not matching. Last try."
- Attempt 3: no match → **LOCKOUT + admin alert**
- `UPDATE customers SET pin_failed_attempts=3, locked_until=NOW()+15min`

**Bunche reply (after 3rd failure):**

```
🔒 Your account is temporarily locked.

This happens after 3 failed identity checks — for your security.

Try again in 15 minutes, or contact admin@example.com for help.
```

**Admin side:**
- 🔴 **Admin alert (via configured channel — Telegram or WhatsApp):**
  ```
  🚨 FORGOT-PIN LOCKOUT

  Customer: Dan (a3f2b9...)
  Phone: +234...NEW
  Result: 3 failed verification attempts
  Lockout: 15 minutes

  Risk: Possible account takeover attempt.
  Evidence: [admin may request payment receipt verification]
  ```
- Bunche Logger: `forgot_pin_lockout`, customer_id, attempts=3, method=order_details

---

## SCENARIO 5: Free Trial

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

*Triggered when customer asks for free trial*

---

#### STEP 1 — Customer sends `Hi` (standard greeting)
**Bunche reply:** Standard greeting (services + prices + legal notice + tip)

---

#### STEP 2 — Customer asks for free trial

```
Customer: Do you have a free plan, your product seems expensive for me right now
```

**Bunche system:**
- LLM Intent Parser: { intent: free_trial }
- **Send full disclaimer FIRST** (before any access)
- Do NOT grant any proxy yet

**Bunche reply:**

```
🎁 FREE TRIAL — DISCLAIMER

Before we send your free IP, please read:

━━━━━━━━━━━━━━━━━━
⚠️ FREE TRIAL TERMS ⚠️
━━━━━━━━━━━━━━━━━━

This free trial uses a Bunche-hosted proxy
shared with other trial users. By accepting, you agree:

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

**Admin side:**
- 🟢 No action
- Bunche Logger: `free_trial_disclaimer_shown`, phone_hash

---

#### STEP 3 — Customer completes survey + replies `Done`

```
Customer: Done
```

**Bunche system (behind the scenes, invisible to customer):**

```
1. Check daily counter:
   SELECT COUNT(*) FROM free_trials
   WHERE phone_hash=? AND DATE(created_at)=CURRENT_DATE
   → if >= 3 → reject with daily limit message

2. If Theorem Reach postback received:
   - Verify HMAC signature ✅
   - Check status=completed ✅
   - Idempotency: survey_transaction_id not yet processed ✅
   → Grant trial

3. Generate trial credentials:
   - user_id: trial_a7b9c2 (16 chars)
   - password: 16 random chars
   - port: next available (8001-8100, max 100 concurrent)
   - expires_at: NOW() + 2 hours

4. Execute: manage-3proxy-trial.sh add trial_a7b9c2 PASSWORD PORT

5. INSERT free_trials: order_id=TRIAL-20260627-1042, phone_hash, user_id,
   password_hash, proxy_ip=VPS_IP, proxy_port, expires_at,
   survey_transaction_id, survey_payout_usd=1.50, status=active

6. Schedule cleanup at expires_at (cron every 5 min)
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

💡 Want reliable private proxies? Reply menu to see paid plans.
```

**Bunche reply (⚠️ ALL SLOTS BUSY — 100/100 in use):**

```
⚠️ All trial slots busy right now.

We'll ping you the moment one opens up (usually within 30 minutes).

🛡️ You've used [X/3] free trials today.

💡 Want reliable proxies now? Reply menu.
```

**Bunche reply (🛡️ DAILY LIMIT HIT — 3/3 used):**

```
🛡️ Daily limit reached — you've used 3/3 free trials today.

Come back tomorrow, or skip the wait with a paid plan:
• ISP UK/US: ₦6,500/mo (private, reliable)
• Residential 5GB: ₦5,000 (data never expires)
• Mobile 5GB: ₦20,000 (4G)

Reply menu to order, or wait until tomorrow for another free trial.
```

**Admin side:**
- 🟢 No action for success
- ⚠️ If Theorem Reach HMAC fails: **alert admin immediately** (possible attack):
  ```
  🚨 THEOREM REACH HMAC FAILURE

  transaction_id: TR-987654
  signature_received: abc123...
  signature_expected: [computed]
  Source IP: x.x.x.x
  → Possible fake postback. Investigating.
  ```
- 🔴 If daily limit abuse detected (same phone_hash on 3+ different phones): alert admin

---

#### STEP 4 — (Background) Cron every 5 min: credential cleanup

**Bunche system (cron, invisible to customer):**

```
SELECT user_id, expires_at FROM free_trials
WHERE status='active' AND expires_at < NOW();

For each expired:
1. manage-3proxy-trial.sh remove trial_a7b9c2
2. UPDATE free_trials SET status='expired'
3. Audit log: free_trial_expired
```

**Customer side:**
- Trial stops working after 2 hours
- If customer messages "trial died":
  ```
  ⏰ Your trial expired after 2 hours (or stopped working).

  That's expected for free trials. Want to:

  • Try another free trial (you've used [X/3] today)
  • Upgrade to a paid plan (private proxies, longer-lasting)

  Reply menu or trial.
  ```

**Admin side (daily summary includes):**
```
🎁 Free trials today: 47 delivered, 31 expired
💰 Theorem Reach revenue: $70.50
🛡️ Port utilization: 12/100 currently active
⚠️ HMAC failures: 2 (potential attacks)
```

---

## SCENARIO 6: Ban Claim (IP Banned After Delivery)

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer → Bunche → Admin

*Triggered when customer reports their delivered IP is banned*

---

#### STEP 1 — Customer reports ban

```
Customer: My IP got banned, here's the screenshot [image attached]
```

**Bunche system:**
- LLM Intent Parser: { intent: ban_claim }
- Check order: is IP banned? → order status=fulfilled, ban reported_at=NULL
- Create ban claim record: BAN-CLAIM-001
- Store screenshot to R2/Cloudflare: files.bunche.ng/bans/BAN-CLAIM-001.jpg
- Add to `pending` list for admin review

**Bunche reply:**

```
📸 Received — screenshot saved.

Your ban claim is now in review. We'll check it and get back to you.

Claim ID: BAN-CLAIM-001
Expected response: within 24 hours.

Anything else while you wait? Reply menu.
```

**Admin side:**
- 🟡 Added to `Pending` queue:
  ```
  ⏳ BAN-CLAIM-001: Order ORD-20260627-0917
  Customer: a3f2b9... (Dan hash)
  Screenshot: https://files.bunche.ng/bans/BAN-CLAIM-001.jpg
  Reported: 2 hours ago
  ```

---

#### STEP 2 — Admin reviews + approves (PIN + TOTP required)

**Admin:** `Approve BAN-CLAIM-001`

**Bunche system:**
- Verify PIN + TOTP ✅
- Get original order: ORD-20260627-0917
- Request replacement IP from Proxy-Seller (different IP from original)
- Test new IP ✅
- Update order: old ip marked=replaced_via_ban, new_ip recorded
- Deliver new credentials to customer
- Update BAN-CLAIM-001: status=approved

**Bunche reply (to customer):**

```
✅ Ban claim approved — replacement IP is ready!

━━━━━━━━━━━━━━━━━━
🌍 YOUR REPLACEMENT ISP UK PROXY — LIVE
━━━━━━━━━━━━━━━━━━

🔗 IP: 185.123.45.99 (different from your previous IP)
🔌 Port: 8000
👤 User: bunche_uk_b8d3
🔑 Pass: Y2kL8mN4pR6tW9xZ1
📅 Expires: July 27, 2026 (original order date)

━━━━━━━━━━━━━━━━━━

Your old proxy has been replaced. Use the details above going forward.

💡 Tip: If this IP also gets banned, wait 24-48 hours before
requesting another replacement — some platforms ban temporarily.
```

**Admin side:**
- 🟢 Logged: `ban_claim_approved`, BAN-CLAIM-001, admin=phone_hash, new_ip=185.123.45.99

---

#### STEP 2B — Admin reviews + rejects (PIN + TOTP required)

**Admin:** `Reject BAN-CLAIM-001 not_actually_banned`

**Bunche reply (to customer):**

```
❌ Ban claim reviewed — replacement declined.

Reason: We couldn't confirm the ban from the screenshot provided.

Your proxy details:
🔗 IP: 198.51.100.42

If you believe this is an error, reply with more details or
a new screenshot showing the block message.

Claim ID: BAN-CLAIM-001
```

**Admin side:**
- ⚠️ Logged: `ban_claim_rejected`, BAN-CLAIM-001, reason, admin=phone_hash

---

## SCENARIO 7: Referral (Friend Uses Code)

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Customer (friend) → Bunche → Admin

*Triggered when a new customer places an order and enters a referral name*

---

#### STEP 1 — Friend sends `Hi`
**Bunche reply:** Standard greeting (same as Scenario 1, Step 1)

---

#### STEP 2 — Friend orders + uses referral name

```
Customer: I want UK ISP, a friend told me about this, her name is Ada
```

**Bunche system:**
- LLM Intent Parser: { intent: order, product: ISP, country: UK, referral_name: Ada }
- Pre-check ✅
- Generate payment link
- **Referral lookup: `SELECT id FROM customers WHERE LOWER(name)='ada'` → found ✅**
- Save referral_name to order record

**Bunche reply:** Standard payment link (same as Scenario 1, Step 2)

---

#### STEP 3 — Friend pays → name capture → PIN → delivery

Same flow as Scenario 1, Steps 3-6

**Bunche extra reply (at delivery):**

```
💡 Ada will earn ₦325 (5% of ₦6,500) credit when her referral
makes their first payment. She'll be notified separately!
```

---

#### STEP 4 — (Background) Ada notified

**Bunche system:**
- When referrer's referral friend **pays** → credit applied to Ada's account
- Ada gets WhatsApp:

```
🎉 Dan just ordered through your link!

You've earned ₦325 credit ��� added to your account.

Your total referral credit: ₦9,825
(Use it on your next order anytime.)

Keep sharing your name Ada 💪
```

**Admin side:**
- 🟢 Logged: `referral_credit_earned`, referrer_name=Ada, order_id, credit_amount=325
- Referral stats updated in daily summary

---

## SCENARIO 8: Data Alert Escalation

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Bunche (automated) → Admin

*Triggered by cron — when customer hits 80%/100% data cap*

---

#### (Background) Customer is using Residential 5GB

**Day 15 — cron runs:**
- `SELECT phone, used_gb, total_gb FROM data_impulse_orders WHERE used_gb >= total_gb * 0.8 AND alert_sent_at IS NULL`
- Customer Dan has used 4.0/5.0 GB

**Bunche reply (to Dan — automated):**

```
⚠️ Data Alert — Dan

You've used 4.0 GB of your 5 GB Residential proxy.

0.8 GB remaining. Once it's done, the proxy stops working.

To avoid interruption:
• Residential 5GB → ₦5,000 (adds 5 more GB)
• Residential 10GB → ₦9,000 (adds 10 GB)

Reply Order RES 5GB to top up.
```

---

#### Day 20 — cron runs: 100% exhausted

**Bunche reply (to Dan):**

```
🔴 Data Exhausted — Dan

Your 5 GB Residential proxy has run out.

The proxy has stopped working.

To restore access:
• Residential 5GB → ₦5,000 (adds 5 more GB)
• Residential 10GB → ₦9,000

Reply Order RES 5GB to continue.
```

---

## SCENARIO 9: Daily Summary (Admin Automated Report)

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Bunche (cron 23:55) → Admin

---

#### (Automated) 23:55 Lagos — cron triggers Workflow 13

**Admin receives WhatsApp:**

```
📊 Daily Summary — June 27

💰 Revenue: ₦312,500 (47 orders)
👥 New customers: 8
⚠️ Errors: 2 (1 critical)
💸 Refunds: 1
🎁 Free trials: 47 (₦70.50 from Theorem Reach)
🔗 Referral purchases: 2 (₦650 credit paid out)
📱 Data alerts sent: 12 (4 at 80%, 8 at 100%)

Top products:
1. ISP UK — 23 orders
2. Residential 5GB — 14 orders
3. ISP US — 7 orders

Top referrers:
1. Chidi — 12 referrals — ₦15,000 credit
2. Ada — 8 referrals — ₦9,500 credit

⚠️ Provider downtime: Proxy-Seller 47 min (14:23-15:10)
⚠️ IP retry rate: 2.1% (within acceptable range)

Full details: https://n8n.yunche.ng/executions/...
```

---

## SCENARIO 10: Error Alert (Critical)

**Channels:** WhatsApp & Telegram (identical experience)


### Flow: Bunche (error trigger) → Admin

*Triggered when a workflow fails with CRITICAL severity*

---

#### (Automated) Workflow fails — Proxy-Seller API down mid-order

**Bunche system:**
- Workflow 2 (payment confirmation) → Proxy-Seller API returns 503 × 4 retries
- **Auto-refund triggered**
- Workflow status = error, severity = CRITICAL
- Error Alert webhook fires

**Admin receives WhatsApp:**

```
🚨 CRITICAL ERROR — Order ORD-20260627-1423-001

Workflow: Payment Confirmation
Error: "Provider API returned 503 after 4 attempts"
Action: Auto-refunded customer

Time: 14:23 Lagos
Execution log: https://n8n.yunche.ng/executions/ERR-20260627-1423-001

Reply 'Resolve ERR-20260627-1423-001' when investigated.
```

**Admin side:**
- Admin reviews execution log
- Admin sends: `Resolve ERR-20260627-1423-001` + PIN
- System marks error resolved

---

## ADMIN COMMAND REFERENCE

### How admin authentication works:

| Risk Level | Auth Required | Session validity |
|-----------|-------------|----------------|
| Low | Session only | 30 min |
| Medium | Fresh PIN | 2 min |
| High | PIN + TOTP | Immediate |
| Critical | PIN + TOTP + confirm | Immediate |

---

### Low-Risk Commands (Session auth — just send the command)

| Command | What it does | Bunche reply |
|---------|-------------|--------------|
| `Daily Summary` | Shows today's stats | Full report |
| `Errors` | Shows last 24h errors | Error list |
| `Provider Status` | Shows Proxy-Seller + DataImpulse health | Provider health |
| `Trial Stats` | Shows free trial metrics | Trial stats |
| `Referral Stats` | Shows referral performance | Referral stats |
| `Pending` | Shows pending admin actions | Pending list |
| `Admin Status` | Shows current session info | Session status |
| `Admin Logout` | Ends admin session | Logout confirmed |

---

### Medium-Risk Commands (Fresh PIN — PIN prompted before execution)

| Command | What it does | Bunche reply |
|---------|-------------|--------------|
| `Block <phone_hash> <reason>` | Blocks phone hash for 30 days | Confirms block |
| `Unblock <phone_hash>` | Removes phone from blocklist | Confirms unblock |
| `Resolve ERR-XXXXX` | Marks error as resolved | Confirms resolution |
| `Details ORD-XXXXX` | Shows full order details | Full order info |

---

### High-Risk Commands (PIN + TOTP — both prompted)

| Command | What it does | Bunche reply |
|---------|-------------|--------------|
| `Refund ORD-XXXXX` | Standard Flutterwave refund | Confirms refund |
| `Force-Refund ORD-XXXXX <reason>` | Admin override refund | Confirms force-refund |
| `Approve BAN-CLAIM-XXX` | Approves ban replacement | Delivers new IP |
| `Reject BAN-CLAIM-XXX <reason>` | Rejects ban replacement | Notifies customer |
| `Revoke Trial <user_id>` | Force-removes trial user | Confirms revoke |

---

### Critical Commands (PIN + TOTP + explicit yes/no confirm)

| Command | What it does | Bunche reply |
|---------|-------------|--------------|
| `Pause Everything` | Stops n8n + 3proxy | Confirms pause |
| `Resume Everything` | Restarts n8n + 3proxy | Confirms resume |

---

## COMPLETE EVENT → ACTION → ADMIN FLOW TABLE

| # | Customer Action / System Event | Bunche Response | Admin Notification |
|---|-------------------------------|----------------|-------------------|
| 1 | New customer `Hi` | Standard greeting + menu | None |
| 2 | Order request | Pre-check provider → payment link | None |
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

---

## Related

- `scenarios/2026-06-26-first-time-order.md` — Scenario 1 (canonical)
- `scenarios/2026-06-26-provider-down-recovery.md` — Scenario 2 + 3
- `scenarios/2026-06-26-new-number-recovery.md` — Scenario 3
- `scenarios/2026-06-26-forgot-pin-recovery.md` — Scenario 4
- `scenarios/2026-06-26-free-trial.md` — Scenario 5