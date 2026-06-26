# Bunche — Operational Runbook
*Zero-inventory, fully on-demand model*

---

## The Core Model

- No proxy inventory held
- Every proxy is bought from provider API only after customer pays
- Provider credit must always stay above $10
- Order flow: Customer pays → provider API called → proxy delivered

---

## Daily Operations (5–10 minutes)

### Every Morning: Check 3 Things

**1. n8n error alerts (WhatsApp)**
- Any failed executions overnight
- Open n8n → Workflows → failed → check error → fix

**2. Google Sheets Pending_Orders**
- Any `paid_pending_fulfillment` older than 5 mins? → Fulfill manually
- Any `awaiting_payment` older than 2 hours? → Follow up via WhatsApp

**3. Provider credit balances**
- Proxy-Seller: proxy-seller.com → Dashboard → Balance
- OkeyProxy: okeyproxy.com → Dashboard
- DataImpulse: dataimpulse.com → Dashboard
- **If any balance below $10 → top up immediately**

---

## Weekly Operations

### Every Monday: Financial Review
1. Flutterwave dashboard → Transactions
2. Note: revenue, refunds, net
3. Cross-check Pending_Orders sheet

### Every Week: Provider Credit Check
1. Check all 3 provider balances
2. Top up any below $15
3. Check for account issues

### Every Week: n8n Execution Review
1. n8n → Executions → Last 7 days
2. Same step failing repeatedly = bug to fix

---

## Incident Response

### Customer: "I paid but didn't get proxy"
1. Get payment reference (tx_ref)
2. Flutterwave dashboard → search tx_ref
3. If paid → manually call provider API → send credentials
4. If no payment → ask for screenshot

### Provider API is down
1. Test manually with curl
2. Switch to backup provider in n8n
3. Notify customer: "Proxy generation delayed — working on it"
4. Re-process once provider is back

### Flutterwave webhook not firing
1. Dashboard → Settings → Webhooks → confirm active
2. Test webhook manually
3. Confirm n8n workflow is active

### n8n is down
1. SSH to VPS → `docker ps | grep n8n`
2. If not running: `docker start n8n`
3. VPS unreachable: contact hosting provider

---

## Communication Templates

### Order Received — Awaiting Payment
```
Hi [Name] 👋

Order received!

Plan: [PLAN]
Country: [COUNTRY]
Amount: ₦[PRICE]

Pay here: [FLUTTERWAVE_LINK]

Payment confirms → proxy delivered instantly. Valid for 1 hour.
```

### Payment Confirmed — Proxy Delivered
```
✅ Payment Confirmed!

Your [PLAN] proxy is ready:

IP: [IP]
Port: [PORT]
Username: [USER]
Password: [PASS]
Country: [COUNTRY]
Expires: [DATE]

Need help? Reply to this message.
```

### Payment Failed
```
❌ Payment Unsuccessful

Order [ORDER_ID] was not completed.
No charges were made.

Please try again: [NEW PAYMENT LINK]
```

### Refund Processed
```
✅ Refund Initiated

Your refund of ₦[AMOUNT] for [ORDER_ID] is being processed.
It will appear in your account in 5–7 business days.
```

### Proxy Expiring (3 days before)
```
🔔 Renewal Reminder

Your [PLAN] proxy expires [DATE].

To renew: Reply "Renew [ORDER_ID]"
Price: ₦[PRICE]
```

### On-Demand Country Available on Request
```
We have [COUNTRY] available!

Order: "Order ISP [COUNTRY_CODE] 1"
Price: ₦[PRICE]
```

---

## Workflow Monitoring Checklist

Every day, confirm:
- [ ] Order Handler (WhatsApp trigger) — ACTIVE
- [ ] Payment Confirmation (Flutterwave webhook) — ACTIVE
- [ ] Refund Handler (Flutterwave webhook) — ACTIVE
- [ ] Error Alert (n8n Error Trigger) — ACTIVE
