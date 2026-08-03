# Incident Response — Customer-Facing

**Owner:** Sonny (automated) + Dannion (human sign-off)  
**Last updated:** 2026-08-03

---

## When Something Breaks

This doc tells you what to say to customers and when. It covers every major incident type.

---

## Severity Levels

| Severity | Impact | Response time | Example |
|---|---|---|---|
| 🔴 P0 | Full outage — checkout broken | Immediate | DB down, payment processor 500 |
| 🟠 P1 | Partial — some features down | Within 1 hour | Charon broken, blog down |
| 🟡 P2 | Degraded — slower than normal | Within 4 hours | Slow proxy rotation, high latency |
| 🟢 P3 | Minor — not customer-impacting | Next business day | Admin page slow, logs delayed |

---

## Incident Types & Response Scripts

### 🔴 P0 — Checkout / Payment Down

**What happened:** Customer can't complete payment.

**Customer message:**
> "We're experiencing a temporary payment issue. Your order and payment are safe — nothing has been charged. Please try again in the next 15-30 minutes. We'll have it resolved shortly. Sorry for the inconvenience."

**Internal actions:**
1. Check Flutterwave status → https://status.flutterwave.com
2. Check `systemctl status styxproxy-api`
3. Check DB connectivity: `sudo -u postgres psql -d styxproxy -c "SELECT 1"`
4. If BE issue → fix → restart → notify
5. If Flutterwave issue → wait + monitor

**Refund SLA:** If outage lasts >2 hours and customer requests refund → process within 24 hours. Contact: `oyebiyiayomide30@gmail.com`

---

### 🔴 P0 — Proxy Credentials Not Delivered

**What happened:** Customer paid but never received their proxy login.

**Customer message:**
> "We're sorry — there was a delay delivering your proxy credentials. Your order is confirmed and you're all set. Please allow up to 5 minutes. If you still haven't received them, reply here and we'll sort it out immediately."

**Internal actions:**
1. Find order: `sudo -u postgres psql -d styxproxy -c "SELECT * FROM orders WHERE tx_ref='TX_REF'"`
2. Check `styxproxy_credential_id` — if NULL, check credential creation error
3. Check `create_credential()` in flutterwave.py
4. Re-process if needed: `POST /ops/v1/orders/{id}/reprocess`
5. If upstream provider failed → swap provider IP → re-fulfill

**Refund SLA:** If credentials not delivered within 24 hours → full refund on request.

---

### 🟠 P1 — Charon (Support Bot) Not Responding

**What happened:** `/reply` returns 503 or no response.

**Customer message:**
> "Our support bot is temporarily unavailable. Your message has been logged and we'll respond manually within 2 hours. For urgent issues, email us at support@styxproxy.com."

**Internal actions:**
1. Check `systemctl status styxproxy-api`
2. Check Charon logs: `journalctl -u styxproxy-api --since "10 minutes ago" | grep charon`
3. Check `CHARON_DAILY_BUDGET_USD` — if exhausted, increase budget
4. Check MiniMax API key: `grep MINIMAX_API_KEY /opt/styxproxy/.env`
5. If BE issue → fix → restart

---

### 🟠 P1 — Webhook Not Processing (Order Stuck)

**What happened:** Order shows "pending" for >10 minutes after payment.

**Customer message:**
> "Your payment went through on Flutterwave's side — we're just verifying it on our end. This usually takes 1-2 minutes. If it doesn't update in 10 minutes, reply here."

**Internal actions:**
1. Check `processed_webhooks` table for duplicate webhook
2. Check Flutterwave dashboard for the transaction
3. Manually trigger fulfillment: `POST /ops/v1/orders/{id}/reprocess`
4. If Flutterwave shows paid but BE shows unpaid → manual adjustment

---

### 🟡 P2 — Slow Proxy Speeds

**What happened:** Customer reports proxy is slow or timing out.

**Customer message:**
> "Sorry for the slow proxy — we're looking into it. As a temporary fix, you can rotate your proxy credentials in your [Manage page](/manage). This gives you a fresh exit IP. We'll update you once resolved."

**Internal actions:**
1. Run provider test: `python3 /opt/styxproxy/backend/scripts/test_provider.py --ip X --port Y`
2. Check upstream provider (Rayobyte) status
3. If provider IP degraded → rotate to new IP → re-fulfill affected orders
4. Update customer credentials via `/manage`

---

### 🟡 P2 — Trial Not Working

**What happened:** Customer can't claim free trial.

**Customer message:**
> "Trials are limited to one per phone number per day. If you've already used your trial today, it will reset tomorrow. If you believe this is an error, reply with your phone number and we'll check."

**Internal actions:**
1. Check `free_trials` table: `sudo -u postgres psql -d styxproxy -c "SELECT * FROM free_trials WHERE phone='PHONE' ORDER BY created_at DESC LIMIT 5"`
2. Check trial uniqueness constraint: `uq_free_trials_phone_trial_date`
3. If customer already used trial → explain policy
4. If bug → fix → re-grant trial

---

### 🟢 P3 — Blog / Docs Down

**Customer message:**
> "Thanks for letting us know — we're fixing our blog now. All your active proxy orders and credentials are unaffected."

**Internal actions:**
1. Check Vercel deployment for blog
2. Check `/api/v1/blog/posts` endpoint
3. Not a customer-impacting product issue — fix within 24h

---

## Refund Policy

| Scenario | Policy | How to request |
|---|---|---|
| Payment made but order failed | Full refund | Email `support@styxproxy.com` with tx_ref |
| Proxy not delivered in 24h | Full refund | Reply in WhatsApp or email |
| Service down >2h during purchase | Full refund + apology | Auto-triggered or request |
| Customer changed mind | No refund | Proxy credentials already delivered |
| Partial month | Pro-rated refund | Case-by-case — email us |

Refund process: Admin processes via Flutterwave dashboard → funds return to customer within 5-7 business days.

---

## Maintenance Mode

When doing planned maintenance:

**Customer message:**
> "We're doing scheduled maintenance from [TIME] to [TIME] WAT. The site will be briefly unavailable. Sorry for the inconvenience — we'll be back up shortly."

Enable: `POST /api/v1/maintenance-mode` with `{ "mode": "soft-block" }`

---

## Status Page

Status page: `https://styxproxy.com/status` (TODO — implement)

When live, update it during every P0/P1 incident. Customers check it before emailing support.

---

## Contact

- **Dannion (human):** `oyebiyiayomide30@gmail.com`
- **Sonny (automated):** monitors 24/7 via Hermes cron
