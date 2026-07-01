# Bunche — Missing Scenarios A: Core Business + Off-Topic

**Date:** 2026-06-28
**Status:** New — Added to complete scenario coverage
**Priority:** 🔴 Critical

---

## SCENARIO 14: LLM Off-Topic Deflection

**Channels:** WhatsApp & Telegram

**Customer:** Any customer | **Status:** Sends a message completely outside IP/proxy scope

---

### Customer sends: `How are you?`

**Bunche system:**
- LLM Intent Parser: { intent: greeting, confidence: 0.3 }
- Confidence < 0.7 → not routed to any known intent
- Intent = `off_topic`
- **Do NOT call LLM again** — just deflect

**Bunche reply:**
```
I'm here to help with proxy and IP questions 😊

You can:
• Order a proxy — reply menu
• Check your existing proxy — reply status
• Renew or top up — reply renew
• Get help — reply help

What do you need? 👇
```

---

### Customer sends: `What's the capital of Nigeria?`

**Bunche system:**
- LLM Intent Parser: { intent: general_knowledge, confidence: 0.1 }
- < 0.7 → off_topic deflection
- **No second LLM call**
- Cost: zero additional tokens

**Bunche reply:**
```
That's outside what I handle 😅

I'm Bunche — I help with:
🌍 ISP, DC, Residential & Mobile proxies
📦 Ordering, renewing, troubleshooting
🔐 IP rotation, ban claims

What proxy question can I help with? 👇
```

---

### Customer sends: `Can you do my math homework?`

**Bunche reply:**
```
Please reach out to us on WhatsApp or Telegram for 
questions about proxies and IPs 😊

If you need help with your proxy, I'm here!
```

---

## Rules

| Rule | Description |
|------|-------------|
| R14-1 | LLM intent confidence < 0.7 = off_topic |
| R14-2 | Off-topic = deflection message only — NO second LLM call |
| R14-3 | Deflection message is short, helpful, on-brand |
| R14-4 | Never engage with off-topic conversation beyond 1 deflection |
| R14-5 | If customer continues off-topic → repeat same deflection (don't escalate) |

---

## SCENARIO 15: IP Rotation Request (Paid Customer)

**Channels:** WhatsApp & Telegram

**Customer:** Dan | **Status:** Active ISP UK subscriber, suspects IP is shared

---

### Customer sends: `I feel like someone else is using my IP`

**Bunche system:**
- LLM: { intent: rotation_request }
- Verify: same IP not issued to another active customer
- Check: order is active, not expired

**Bunche reply:**
```
I can rotate your credentials — you'll keep the same IP 
but get a fresh username and password.

This helps if the IP feels slow or shared.

Shall I go ahead? Reply yes or no.
```

---

### Customer sends: `Yes`

**Bunche system (atomic transaction):**
```
BEGIN TRANSACTION;
  Generate new bun_username: `bun_{customer_id}_v2`
  Generate new password: 16-char random
  Call `manage-bunche-credentials.sh revoke bun_dan_v1` → wait for ack ✅
  Call `manage-bunche-credentials.sh add bun_dan_v2 NEW_PASS` → wait for ack ✅
  IF add fails → ROLLBACK (re-add old credentials, restore state)
  IF both succeed → COMMIT
  Update `bunche_credentials` table: revoke old, create new (same upstream IP)
  Log: rotation_request, customer=dan, reason=suspected_shared_use
COMMIT;
```

**Error handling:**
- If `revoke` succeeds but `add` fails → automatic rollback, customer keeps old credentials
- If both fail → no change, alert admin, customer notified of delay
- If any step times out (30s) → retry once, then rollback + admin alert
- Customer reply only sent AFTER transaction COMMIT (so we don't lie about new creds that failed)
- Idempotency: if customer retries during rotation, second request returns "already in progress"

**Bunche reply:**
```
🔄 Credentials Rotated

Your IP stays the same (185.234.72.11)
but you've got fresh login details:

👤 New Username: bun_d4x9_v2
🔑 New Password: N3wP@ss2026!

Your old credentials have been revoked.
Use these from now on.

One rotation per month is free. 
Additional rotations need admin approval.

Need help? Reply how to use.
```

---

### If customer has exceeded rotation limit

**Bunche system:**
- Check: rotation_count this month ≥ 1

**Bunche reply:**
```
You've used your free rotation this month (1/1).

Additional rotations need admin review.
Reply rotate and I'll escalate to our team.
```

**Admin alert (Telegram + Email):**
```
🔄 ROTATION LIMIT EXCEEDED

Customer: Dan (a3f2b9...)
Order: ORD-20260627-0947
IP: 185.234.72.11

Reason: suspected shared use
Escalation: customer requests 2nd rotation this month
```

---

## Rules

| Rule | Description |
|------|-------------|
| R15-1 | Customer suspects shared use → rotate credentials, same IP |
| R15-2 | 1 free rotation per active subscription per month |
| R15-3 | Additional rotations → admin review |
| R15-4 | Same upstream IP, new Bunche username + password |
| R15-5 | Old credentials revoked immediately |
| R15-6 | Both channels notified if customer is linked |

---

## SCENARIO 43: Expired Payment Link + Claims Payment

**Channels:** WhatsApp & Telegram

**Customer:** Emeka | **Status:** Payment link expired, claims he paid

---

### Customer sends: `I paid but nothing happened, it's been 20 minutes`

**Bunche system (with retry + error handling):**
- Check order ORD-20260627-0947: status=pending, link_expired=true
- Check Flutterwave (with retry): no successful payment found for this tx_ref
  - Retry: 2 attempts with 3s delay
  - Timeout: 10s per attempt
  - If both fail → admin alert + customer told to contact support directly

**Bunche reply:**
```
Let me check your order...

I can see your payment link expired and we haven't 
received any payment from you yet.

If you paid to the old link:
• Bank transfers can take 5-15 minutes
• The link may have expired before it went through

Your order is still open. I can generate a new link.
Would you like me to send a fresh payment link?

Reply yes for a new link, or send me your payment proof.
```

---

### Customer sends proof of payment (screenshot)

**Bunche system:**
- Forward to admin queue
- Log: manual_payment_review, customer=Emeka

**Bunche reply:**
```
Thanks — I've forwarded your payment proof to our team.
We'll check with Flutterwave and get back to you within 1 hour.

Your order is on hold in the meantime.
```

**Admin alert (Telegram + Email):**
```
💰 MANUAL PAYMENT REVIEW

Customer: Emeka (b4d2e7...)
Order: ORD-20260627-0947
Amount: ₦6,500

Customer claims payment made but:
• Link expired
• No webhook received

Proof screenshot: [attached or forwarded]
Action: Check Flutterwave dashboard → confirm or deny
```

---

## Rules

| Rule | Description |
|------|-------------|
| R43-1 | Expired link + customer claims payment → check Flutterwave |
| R43-2 | If Flutterwave shows success → fulfill manually |
| R43-3 | If no record → new link or refund depending on evidence |
| R43-4 | Payment proof forwarded to admin for manual review |
| R43-5 | Admin resolves within 1 hour |

---

## SCENARIO 45: IP Authentication Failure

**Channels:** WhatsApp & Telegram

**Customer:** Ada | **Status:** ISP UK active, suddenly can't connect

---

### Customer sends: `My proxy suddenly stopped working, I didn't change anything`

**Bunche system:**
- LLM: { intent: technical_support }
- Check: order status=active, credential not revoked

**Bunche reply:**
```
Sorry to hear that. Let's troubleshoot.

Quick check first — have you tried:
1. Disconnecting and reconnecting?
2. Restarting your browser/app?

Try those and let me know if it works.
```

---

### Customer: `Still not working`

**Bunche system:**
- Test IP via Proxy-Seller API: IP responds ❌
- Check credential status in DB: active ✅
- Likely cause: upstream provider suspended or IP range blocked

**Bunche reply:**
```
I can see your IP isn't responding right now.

This usually means the provider is having a temporary issue
or your IP range was flagged.

Let me check with our provider...
```

**Bunche system (with retry + fallback):**
- Proxy-Seller API: IP is suspended ❌
  - Retry: 2 attempts with 5s delay
  - Timeout: 15s per attempt
  - If retries fail → escalate to admin + customer told "checking with provider, will update within 30 min"
- Provider status: account has balance, specific IPs flagged
- Option A: retry same IP → Option B: rotate to new IP

**If retries fail completely:**
- Customer reply: "I'm waiting on our provider to respond. I'll send new IP details within 30 minutes — hang tight 🙏"
- Admin alert: 🚨 IP ROTATION FAILED — manual rotation needed
- Cron job: every 5 min, retry provider check; auto-deliver IP if recovered
- Customer gets auto-reply when successful

**Bunche reply:**
```
Our provider confirmed the IP has an issue.
I'm rotating you to a fresh IP now.

🔄 New IP: 185.234.72.15
[Full new credentials...]

Your old IP has been revoked.
Use the new one — it should work now.

If this keeps happening, reply ban and we'll investigate further.
```

---

## Rules

| Rule | Description |
|------|-------------|
| R45-1 | Customer can't connect → troubleshoot first (reconnect, restart) |
| R45-2 | Still failing → check Proxy-Seller API status |
| R45-3 | Provider-side issue → rotate to new IP immediately |
| R45-4 | Same IP not responding = provider issue, not customer error |
| R45-5 | No ban claim counted if provider fault confirmed |

---

## SCENARIO 46: Multiple Customers Report Same /24 Range Banned

**Channels:** WhatsApp & Telegram

**Customer:** 8 customers report within same hour | **Status:** Mass ban event

---

### Bunche system (automated detection):

```
Monitor: ban_reports via support
Detected: 3+ ban reports within 1 hour for same /24 range

Trigger: mass_ban_alert
Alert admin: Telegram + Email immediately
```

**Admin alert (Telegram + Email):**
```
🚨 MASS BAN ALERT — /24 RANGE

IP Range: 185.234.72.0/24
Affected customers: 8 (and rising)

All 8 IPs from same provider block.
Pattern: platform-wide ban, not individual customer fault.

Actions needed:
1. Check if more customers affected
2. Contact Proxy-Seller for credit/replacement
3. Identify unaffected IPs in pool
4. Plan mass credential rotation for all affected
```

---

**Resolution: mass rotation (per-customer tracking)**

**Bunche system:**
- For each affected customer (tracked individually):
  - Generate new IP from different range
  - Rotate credentials (atomic transaction per customer)
  - Track per-customer rotation status: `rotation_status[customer_id] = success|fail|pending`
  - If any individual rotation fails:
    - Log failure with customer_id + reason
    - Continue with other customers (don't fail entire batch)
    - Send partial-failure admin alert at end with success/fail counts
  - Generate summary admin report: "Rotated 7/8 customers. 1 failed: <reason>. Manual intervention needed for: <customer_id>"

**Per-customer failure handling:**
- Failed rotation customer gets reply: "We're still working on getting you a fresh IP. Will update within 1 hour."
- Admin manually resolves failed customers
- Customer never gets partial/inconsistent state (no IP delivered unless rotation confirmed)

**Bunche reply (to each affected customer):**
```
⚠️ System Notice

We've detected an issue affecting your proxy IP.

We've automatically rotated you to a new IP.
Your proxy should work again — please reconnect.

New IP details:
[IP / Port / User / Pass]

Sorry for the inconvenience 🙏
If you still have issues, reply help.
```

---

## Rules

| Rule | Description |
|------|-------------|
| R46-1 | 3+ ban reports in 1 hour from same /24 = mass ban event |
| R46-2 | Admin alerted immediately via Telegram + Email |
| R46-3 | Auto-rotate all affected IPs to clean range |
| R46-4 | Affected customers notified automatically |
| R46-5 | Admin escalates to Proxy-Seller for credit on affected IPs |
| R46-6 | Document which platform triggered the mass ban |

---

## SCENARIO 58: Referral Abuse — Self-Referral

**Channels:** WhatsApp & Telegram

**Customer:** Dan | **Status:** Attempting to refer himself

---

### Customer sends: `My referral code is Dan`

**Bunche system:**
- LLM: { intent: order, referral_code: "dan" }
- Check: referral code = dan = SAME customer ❌

**Bunche reply:**
```
That's your own referral name — you can't refer yourself 😅

To earn referral credit, share your name with a friend.
When they order and complete payment, you get 5% credit
on your next renewal automatically.

Share your name: Dan
Your friend uses it at checkout.
Both of you benefit 💪
```

---

### Customer tries to create 2 accounts to self-refer

**Bunche system (verify before alert):**
- Detect: 2 accounts from same device fingerprint or similar behavior pattern
- Verify (atomic): Check DB for credit adjustment before alerting
  - BEGIN TRANSACTION
  - Update credits table (revoke self-referral credit, zero out balance if abuse)
  - COMMIT
  - Verify success (SELECT returned rows affected)
  - ONLY THEN send admin alert
- Referral credit only applied once per unique customer
- Same person = same referral = credit denied
- If DB update fails → retry once, then admin alert says "investigate manually" with reason

**Bunche reply:**
```
I can see both accounts are linked to the same person.
Referral credits are for genuine referrals only.

Your credits have been adjusted. 
If you have questions, reply help.
```

**Admin alert (Telegram + Email):**
```
⚠️ SUSPECTED SELF-REFERRAL

Accounts: Dan (a3f2b9...) + Dani (c5e1f3...)
Pattern: same device, similar ordering pattern
Referral credit: DENIED

Action: Review → confirm or reject fraud finding
```

---

## Rules

| Rule | Description |
|------|-------------|
| R58-1 | Cannot use own referral code |
| R58-2 | One referral credit per unique customer pair |
| R58-3 | Fraud pattern detection: same device/behavior = investigate |
| R58-4 | Self-referral credit = revoked + logged |
| R58-5 | Admin alerted for all suspected abuse cases |

---

## SCENARIO 60: Platform Feature Tour Tips

**Channels:** WhatsApp & Telegram

**Customer:** New customer | **Status:** Just received first proxy

---

### After IP delivery — Bunche sends feature tour

**Bunche reply (Message 1 — proxy details, <500 chars):**
```
✅ Payment confirmed — ₦6,500

Your ISP UK proxy is ready!

🌍 YOUR PROXY IS LIVE
🔗 IP: 198.51.100.42
🔌 Port: 8000
👤 User: bunche_uk_a3c8
🔑 Pass: T7nQ9xM2pK
📅 Expires: July 27, 2026

Setup help? Reply how to use.
```

**Bunche reply (Message 2 — top features, <500 chars):**
```
💡 You can do more with Bunche:

📦 Order — renew, top up, change country
🔄 Manage — reply rotate to change IP, ban if blocked
💰 Save — share your name: Dan → earn 5% credit
🎁 Trial — reply free trial to test before paying
📱 Link — reply link telegram to manage from Telegram too
🆘 Help — reply help anytime

Reply menu anytime to see all features.
```

**Bunche reply (Message 3 — AUP note, sent once after delivery):**
```
⚠️ Reminder: proxies are for personal use only.
No commercial resale, fraud, or platform abuse.
By ordering, you agreed to our AUP: bunche.ng/aup

Happy proxying! ⚡
```

**Delivery timing:**
- Message 1 (proxy details): immediately with credentials
- Message 2 (top features): 30 seconds after Message 1
- Message 3 (AUP note): 1 minute after Message 2

All three messages are well under 1024 chars each.

**Server-side tracking:**
- Log: feature_tour_sent (per customer)
- Only sent once (R60-2) — check before sending
- Verify WhatsApp/Telegram delivery succeeded before marking `tour_sent=true`
- If delivery fails → retry on next customer message
- Rotating tips appear after every delivery (one feature tip per non-order message, R60-5)

---

## Rules

| Rule | Description |
|------|-------------|
| R60-1 | Feature tour sent once — after first IP delivery |
| R60-2 | Not sent again on subsequent orders |
| R60-3 | Short tips appear after every delivery (rotating) |
| R60-4 | Customer can reply `menu` at any time to see all features |
| R60-5 | Tip rotation: 1 feature tip per non-order message |

---

## SCENARIO 61: Link WhatsApp + Telegram

**Channels:** WhatsApp & Telegram

**Customer:** Ngozi | **Status:** Existing WhatsApp customer, wants to add Telegram

---

### Customer (WhatsApp): `I want to link my Telegram`

**Bunche system:**
- LLM: { intent: link_channel }
- Current channel: WhatsApp
- Target: Telegram

**Bunche reply:**
```
Sure! To link Telegram to your Bunche account:

1️⃣ Go to Telegram → message @bunche_ng
2️⃣ Send: /link [your name]

Example: /link Ngozi

This verifies you own both accounts.
Reply here when you've done that. 👇
```

---

### Customer (Telegram): `/link Ngozi`

**Bunche system (via Telegram):**
- Name lookup: `ngozi` → found ✅
- Generate verification code: 6-character alphanumeric (e.g., `7X2K9M`)
  - 2.1B combinations → not brute-forceable
- Send code via WhatsApp to original customer (other channel)
- Telegram prompt: "Check your WhatsApp for the 6-character code, then send it here."
- Rate limit: 3 attempts per 10 minutes (atomic lock in Redis)
- Name lookup failure → graceful error "Name not found — please register first"
- Expire code after 10 minutes
- Log: channel_link_attempt, customer=Ngozi, code=7X2K9M (hashed)

**Bunche reply (WhatsApp):**
```
📱 We received a link request from Telegram.

Your verification code is: **7X2K9M**

Reply with this code to confirm.
⚠️ Code expires in 10 minutes.
```

---

### Customer (WhatsApp): `7X2K9M`

**Bunche system:**
- Verify code ✅ → link confirmed
- Update customers table: whatsapp_linked=true, telegram_username=@ngozi
- Log: channel_linked, channels=WhatsApp+Telegram

**Bunche reply (WhatsApp):**
```
✅ Telegram @ngozi linked to your account!

You can now manage your proxy from either app.

• Order, renew, check status on WhatsApp OR Telegram
• Replies come to whichever app you're using
• Your preferences and history stay the same

Enjoy the flexibility! 🎉
```

**Bunche reply (Telegram):**
```
✅ WhatsApp linked! Your Bunche account is now connected.

You can manage your proxy from both apps.
Welcome to dual-channel management 🎉
```

---

## SCENARIO 61B: Unlink Channels

**Channels:** WhatsApp & Telegram (identical experience)

**Customer:** Tunde | **Status:** Linked customer, wants to unlink secondary channel

---

### Customer ([channel]): `I want to unlink my Telegram`

**Bunche system:**
- Verify: Telegram @tunde_bunche is linked ✅

**Bunche reply:**
```
To unlink Telegram from your account:

Type exactly: UNLINK
⚠️ You'll only be able to manage from [primary channel] after this.

(Required to prevent accidental unlinks)
```

**Bunche system (rate limited + atomic):**
- Verify: Telegram @tunde_bunche is linked ✅
- Rate limit: 2 unlink attempts per hour (atomic lock)
- Log: unlink_attempted, channel=telegram
- Update: telegram_username=NULL
- Log: channel_unlinked

**Bunche reply:**
```
✅ Telegram unlinked.

Your Bunche account is now [primary channel]-only again.

If you want to relink anytime, just reply link telegram.
```

---

## Rules

| Rule | Description |
|------|-------------|
| R61-1 | Customer initiates link — Bunche never initiates |
| R61-2 | Name verification = code sent to other channel |
| R61-3 | Either channel can initiate link/unlink |
| R61-4 | Unlink requires explicit confirmation |
| R61-5 | Both channels receive confirmation of link/unlink |
| R61-6 | Linked customers: order confirmations go to BOTH channels |

---

## SCENARIO 62: Right to be Forgotten (NDPR Deletion)

**Channels:** WhatsApp & Telegram (identical experience)

**Customer:** Femi | **Status:** Wants all personal data deleted

---

### Customer sends: `I want to delete my account and all my data`

**Bunche system:**
- LLM: { intent: data_deletion_request }
- NDPR = customer has right to deletion, not just export

**Bunche reply:**
```
Under NDPR, you have the right to request deletion of your data.

Before I proceed — deletion is irreversible. Here's what happens:

📋 WHAT GETS DELETED:
• Your name and phone number
• Your order history
• Your proxy records
• Your chat logs (90-day logs also deleted immediately)
• Your referral credits (forfeited)

📋 WHAT WE MUST KEEP (by law):
• Financial records — 7 years (Nigerian tax law)
• Transaction data — 7 years

⚠️ After deletion:
• Your active proxy will be revoked immediately
• You cannot recover your account or data
• If you order again, you start fresh

Reply DELETE to confirm you want this.
Or reply cancel to keep your account.
```

---

### Customer: `DELETE`

**Bunche system (complete deletion scope):**
- Check: no active subscription with financial obligation
- ATOMIC deletion across all tables:
  - customers → DELETE (anonymize after 30 days grace)
  - chat_logs → DELETE (immediate purge)
  - referrals → DELETE (revoke credit + history)
  - bunche_credentials → DELETE (revoke all active proxies)
  - sessions → DELETE (clear login state)
  - notifications → DELETE
- orders → ANONYMIZE only (keep transaction records for 7-year tax compliance)
- Transaction records: kept anonymized (no PII) for 7 years
- Backups: cron job within 24 hours purges deleted customer from latest backup snapshot
- 90-day log retention: ALL chat logs including this conversation purged immediately
- After 30-day grace: full anonymization of any retained references
- All deletions in single PostgreSQL transaction with foreign-key cascades
- If any DELETE fails → ROLLBACK entire operation, customer notified, retry
- Log: data_deletion_request, customer_consent, NDPR_compliant, scope=full

**Bunche reply:**
```
✅ Your data has been deleted.

• Account: closed
• Personal data: removed
• Active proxy: revoked
• Chat logs: purged

📋 Retained for legal compliance:
• Transaction records (7 years)
• Order amounts (7 years)

If you return to Bunche in the future,
you'll start as a new customer.

Thank you for being a part of Bunche 🙏
```

**Admin alert (Telegram + Email):**
```
🗑️ DATA DELETION — NDPR

Customer: Femi (d6f3g8...)
Deleted at: 2026-06-28 10:32 UTC
Action: Full deletion, financial records retained
```

---

## Rules

| Rule | Description |
|------|-------------|
| R62-1 | Deletion request → explicit warning of consequences |
| R62-2 | Customer must type DELETE (not click a link) |
| R62-3 | Active proxy revoked immediately |
| R62-4 | Financial records retained 7 years (legal requirement) |
| R62-5 | Chat logs deleted immediately |
| R62-6 | Admin alerted of all deletion requests |
| R62-7 | Customer gets written confirmation |

---

### ADDENDUM — Scenario 15: Architecture Note (Jun 29 2026)

**CRITICAL CORRECTION to Scenario 15:**

Bunche uses Dante SOCKS5 as the auth layer between customers and upstream ISP providers.

```
Customer pays → Bunche issues Bunche-branded username/password
                → Dante authenticates with Bunche creds
                → Dante routes to upstream ISP IP

Rotate credentials → Dante stops accepting old Bunche username/password
                  → Upstream ISP IP stays the same
                  → BUT old creds are dead immediately
```

When Bunche says "IP stays the same" after rotation — this is **correct and secure**. The credential IS the access token, not the IP. Rotating credentials revokes access at the Dante auth layer, which locks out anyone with the old username/password, even if they somehow have the same upstream IP route.

The security value of rotation comes from **credential revocation**, not IP change.

What rotation CANNOT fix: If the upstream ISP's IP range is banned by a platform, rotating credentials won't help — a new IP from a different range is needed.

What rotation DOES fix: Unauthorized access by someone who has your old Bunche username/password.

---

### ADDENDUM — Scenario 16: Council Fixes Applied (Jun 29 2026)

**Changes required after council review:**

**1. Verification code — UPGRADE TO 6 CHARACTERS**
- Old: `7X2K` (4 chars = 1.6M combinations — TOO WEAK)
- New: `7X2K9M` (6 chars = 2.1 BILLION combinations)
- Stored as: `verification_codes(code, customer_id, expires_at, attempts)`
- Rate limit: max **3 attempts per 10 minutes**

**2. Unlink confirmation — CHANGE "confirm" to "UNLINK"**
- Old: reply `confirm` to unlink
- New: reply `UNLINK` to confirm (harder to accidentally type)
- Add rate limit on unlink attempts: max 2 per hour

**3. Audit log — ADD TO every link/unlink event**
```
link_events:
  - customer_id
  - action (link / unlink)
  - channels (e.g., WhatsApp + Telegram)
  - timestamp
  - IP address
  - verification_code_attempts
  - success / failure
```

**4. Atomic state lock — ADD**
```
BEGIN TRANSACTION;
  -- Check no pending link/unlink in progress
  -- Lock customer record
  -- Execute link/unlink
COMMIT;
```
Prevents race condition: link + unlink simultaneously from different channels.

**5. UX improvement — verification code message**
- Old: "Your verification code is: 7X2K9M. Reply with this code to confirm."
- New: "Your verification code is: **7X2K9M**. Reply with this exact code on WhatsApp to confirm linking. Code expires in 10 minutes."

---

**Council-corrected verdict:** PASS (Security: with fixes applied | UX: PASS | Operations: with fixes applied)

---

### ADDENDUM — Scenario 34: Payment Link Regeneration (Corrected Jun 29)

**Council verdict:** FLAGS (all 3 judges)
**Corrections applied:**

**1. Tell customer "1 of 2 available":**
```
✅ New payment link generated! (1 of 2)

Your order: ISP UK × 1 — ₦6,500

💳 Pay here:
👉 [Flutterwave link]

⏰ Valid for 30 minutes.
```

**2. Validate payment amount:**
When customer says "already paid old link":
→ Check: amount_paid >= order_total AND payment currency matches
→ Verify: Flutterwave TX ref tied to this specific order
→ NEVER deliver IP without validating amount

**3. Idempotency:**
→ Add idempotency key on webhook processing
→ If same payment TX triggers twice → only deliver once

**4. Persist regeneration_count:**
→ orders.regeneration_count INT DEFAULT 0
→ INCREMENT on each regeneration
→ BLOCK if count >= 2

**5. Post-limit escalation:**
If customer hits 2-regeneration limit:
```
You've used all 2 regenerations for this order.
I've flagged your order for manual review.
Our team will contact you within 1 hour.
For immediate help: admin@bunche.ng
```

**6. Verify IP before delivery:**
→ NEVER say "IP delivered" without checking Dante is routing
→ Ping IP in backend → confirm active → then confirm delivery

---

**Corrected flow:**
```
Customer: "Payment link expired"

Bunche checks: regeneration_count < 2?
  → NO: Apply post-limit escalation

Bunche generates new link, increments count, tells customer:
  "✅ New link generated (1 of 2) — valid 30 min"

Customer pays old link, says "I already paid":
  Bunche checks Flutterwave:
    amount >= order_total? YES → verify TX ref → verify Dante IP active → deliver
    amount < order_total? → ask for balance
    NO payment found → investigate

Bunche NEVER confirms delivery without IP health check.
```