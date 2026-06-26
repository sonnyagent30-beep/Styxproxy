# Bunche — Operational Runbook
*Day-to-day operations guide*

---

## Daily Operations (5–10 minutes)

### Every Morning: Check 3 Things

**1. Check n8n error workflow (Telegram/WhatsApp alert)**
- Look for any failed executions overnight
- If failures: open n8n → Workflows → find failed → check error → fix

**2. Check Google Sheets Orders tab**
- Any `pending` orders older than 2 hours? → Check Flutterwave
- Any `paid` but not `fulfilled`? → Manually fulfill
- Any `failed` or `refunded` → No action needed

**3. Check provider API credit balances**
- IPRoyal: iproyal.com → Dashboard → Balance
- If below $10 → top up

---

## Weekly Operations (30–60 minutes)

### Every Monday: Financial Review
1. Open Flutterwave dashboard → Transactions
2. Note: total revenue, total refunds, net revenue
3. Cross-check with Google Sheets Orders

### Every Week: Provider Credit Check
1. Check all provider accounts
2. Top up any below $20 balance
3. Check for any account suspension

### Every Week: n8n Workflow Review
1. n8n → Executions → Last 7 days
2. Look for any patterns: same step failing repeatedly = bug to fix

---

## Incident Response

### Customer says "I paid but didn't get proxy"
1. Ask for payment reference / tx_ref
2. Go to Flutterwave dashboard → search reference
3. If payment successful → manually fulfill via provider API
4. If no payment found → ask for screenshot

### Provider API is down
1. Test provider API manually
2. If provider is down: activate backup provider in n8n workflow
3. Notify affected customers: "Delay in proxy generation — working on it"
4. Once provider back: re-process failed orders

### Flutterwave webhook not firing
1. Dashboard → Settings → Webhooks → check if active
2. Test webhook manually
3. Check n8n workflow is active

### n8n is down
1. SSH to VPS → `docker ps | grep n8n`
2. If not running: `docker start n8n`
3. If VPS unreachable: contact hosting provider

---

## Customer Communication Templates

### Order Received — Awaiting Payment
```
Hi [Name] 👋

We've received your order.

Order ID: ORD-2026-XXXXX
Amount: ₦[PRICE]

To pay: [FLUTTERWAVE_LINK]

Payment is valid for 1 hour. Once confirmed, your proxy will be delivered instantly.
```

### Payment Confirmed — Proxy Delivered
```
✅ Payment Confirmed!

Your [PRODUCT] is ready:

[IP]:[PORT]
Username: [USER]
Password: [PASS]

Country: [COUNTRY]
Valid until: [DATE]

Need help? Reply to this message.
```

### Payment Failed
```
❌ Payment Unsuccessful

Your order ORD-2026-XXXXX was not completed.
No charges were made.

Please try again: [NEW PAYMENT LINK]
```

### Refund Processed
```
✅ Refund Processed

Your refund of ₦[AMOUNT] for ORD-2026-XXXXX has been initiated.
It will appear in your account within 5–7 business days.
```

### Proxy Expiring Soon (3 days before)
```
🔔 Renewal Reminder

Your [PRODUCT] proxy (ORD-2026-XXXXX) expires on [DATE].

To renew: Reply "Renew ORD-2026-XXXXX"
Price: ₦[PRICE]
```

---

## n8n Workflow Monitoring Checklist

Every day, confirm these workflows are active:

- [ ] Order Handler (WhatsApp trigger) — ACTIVE
- [ ] Payment Confirmation (Flutterwave webhook) — ACTIVE
- [ ] Refund Handler (Flutterwave webhook) — ACTIVE
- [ ] Error Alert Workflow (runs on any workflow error) — ACTIVE
