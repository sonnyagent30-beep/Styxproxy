# Bunche — Flutterwave Payment Flow

**Document Type:** Technical Integration Guide
**Date:** July 1, 2026
**Status:** Planning Complete

---

## Overview

Flutterwave is Bunche's primary payment processor for Nigerian Naira (NGN). This document covers the complete payment lifecycle — from order initiation to proxy credential delivery — with emphasis on webhook idempotency, error handling, and the differences across the 3 channels.

**Currency:** NGN. All amounts in NGN (integers) for Flutterwave v3 API.

**API Version:** v3
**Base URL:** `https://api.flutterwave.com/v3`

---

## Flutterwave API Reference

### Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/payments` | Create a payment session |
| GET | `/payments/{id}` | Verify a payment |
| POST | `/refunds` | Initiate a refund |

### API Keys

| Key | Used For | Stored Where |
|-----|---------|-------------|
| `FLUTTERWAVE_PUBLIC_KEY` | Client-side (Flutterwave.js) | Frontend env |
| `FLUTTERWAVE_SECRET_KEY` | Server-side (FastAPI + n8n) | Backend env / n8n credentials |
| `FLUTTERWAVE_ENCRYPTION_KEY` | Payload encryption | Backend env |

---

## Step 1: Order Initiation

### 1A: Customer selects product (Telegram / WhatsApp)

```
Customer → /order → Selects product → Confirms quantity
                                    ↓
            FastAPI: POST /api/orders/create
                                    ↓
            Creates orders row: status = 'pending_payment'
                              payment_reference = Flutterwave tx_ref
                                    ↓
            Returns: { payment_url, tx_ref, order_id }
                                    ↓
            Bot sends payment_url to customer (inline button or link)
```

**Flutterwave payment creation (FastAPI):**

```python
POST https://api.flutterwave.com/v3/payments
Headers:
  Authorization: Bearer {FLUTTERWAVE_SECRET_KEY}
  Content-Type: application/json

{
  "tx_ref": "BUN-{order_id}-{timestamp}",
  "amount": 6500,
  "currency": "NGN",
  "redirect_url": "https://styxproxy.com/order/{order_id}/confirm",
  "customer": {
    "email": "customer@example.com",
    "phonenumber": "234703XXXXXXX",
    "name": "Customer Name"
  },
  "customizations": {
    "title": "Bunche Proxy Order",
    "description": "ISP UK Clean - 30 days"
  },
  "meta": {
    "order_id": "ord_abc123",
    "platform_account_id": "uuid",
    "channel": "telegram"
  }
}
```

### 1B: Payment Link Delivery by Channel

| Channel | Method | UX |
|---------|--------|-----|
| **Telegram** | Inline keyboard button (`url` type) | Customer taps → opens Flutterwave in Telegram webview or browser |
| **WhatsApp** | Hyperlink button or formatted message with link | Customer taps → opens browser → Flutterwave |
| **Instant** | Operator sends link manually via WhatsApp | Same as WhatsApp flow |

---

## Step 2: Flutterwave Checkout

### 2A: Customer completes payment

Customer sees Flutterwave hosted page with:
- Order summary
- Amount in NGN
- Payment methods: Card, Bank Transfer, USSD, Mobile Money

**Payment methods enabled in Flutterwave dashboard:**
- ✅ Card (Visa, Mastercard, Verve)
- ✅ Bank Transfer (Nigeria banks)
- ✅ USSD (GTBank, UBA, Sterling, etc.)
- ✅ Mobile Money (MTN, Airtel, 9mobile)

### 2B: Payment confirmation

Once customer completes payment, Flutterwave fires `charge.completed` webhook to the registered URL.

**Important:** Do NOT fulfill based on redirect URL. Webhook is the source of truth.

---

## Step 3: Webhook Processing

### 3A: Webhook URL registration

In Flutterwave dashboard → Settings → Webhooks:
```
URL: https://n8n.styxproxy.com/webhook/flutterwave
```

Select events:
- ✅ `charge.completed` — payment successful
- ✅ `charge.failed` — payment failed
- ✅ `refund.initiated` — refund started by admin
- ✅ `refund.completed` — refund processed

### 3B: Webhook payload (charge.completed)

```json
{
  "event": "charge.completed",
  "data": {
    "id": 12345678,
    "tx_ref": "BUN-ord_abc123-1751438400",
    "flw_ref": "FLW/MCK/...",
    "amount": 6500,
    "currency": "NGN",
    "status": "successful",
    "customer": {
      "email": "customer@example.com",
      "phonenumber": "2347032981049",
      "name": "Customer Name"
    },
    "meta": {
      "order_id": "ord_abc123",
      "platform_account_id": "uuid",
      "channel": "telegram"
    }
  },
  "created_at": "2026-07-01T12:00:00Z"
}
```

### 3C: Idempotency — Preventing double fulfillment

**Critical:** Flutterwave retries webhooks for up to 7 days with exponential backoff.

```python
# n8n webhook handler — idempotency check
1. Extract: tx_ref from payload.data.tx_ref
2. Redis: SET flutterwave_idempotency:{tx_ref} EX 864000 NX
   # TTL = 10 days (864000 seconds = Flutterwave retry window)
   # NX = only set if not exists
3. If NX returned FALSE → webhook already processed
   → Return HTTP 200 immediately
4. If NX returned TRUE → new webhook
   → Process payment → fulfill order
5. DB: INSERT INTO processed_webhooks (webhook_id, provider, event_type, ...)
   ON CONFLICT (webhook_id) DO NOTHING
```

### 3D: Post-payment fulfillment (n8n workflow)

```
Flutterwave Webhook (charge.completed)
         ↓
    Idempotency Check (Redis SETNX)
         ↓
    Update orders table:
      status = 'paid'
      payment_reference = tx_ref
      paid_at = NOW()
         ↓
    Check stock (query provider API or inventory table)
         ↓
    [In stock?] → NO → Create pending fulfillment ticket
                  ↓ YES
    Generate Bunche credentials (Dante username + password)
         ↓
    INSERT bunche_credentials row
         ↓
    Update orders: status = 'fulfilled', fulfilled_at = NOW()
         ↓
    Send credentials to customer (Telegram/WhatsApp)
         ↓
    Referral credit (if applicable): Add 5% to referrer's account
```

---

## Step 4: Failed Payments

### charge.failed webhook

```json
{
  "event": "charge.failed",
  "data": {
    "tx_ref": "BUN-ord_abc123-1751438400",
    "status": "failed",
    "reason": "Insufficient funds"
  }
}
```

**n8n handling:**
```
charge.failed webhook
         ↓
    Lookup order by tx_ref
         ↓
    Update orders: status = 'payment_failed'
         ↓
    Notify customer: "Payment failed. Please try again."
```

### Expired payments (no webhook)

Flutterwave payments expire after **24 hours** if not completed.

**Cleanup cron job (n8n, daily):**
```
Daily scan: SELECT * FROM orders WHERE status = 'pending_payment' AND created_at < NOW() - INTERVAL '25 hours'
         ↓
    Update each: status = 'cancelled'
         ↓
    Notify customer: "Your order has expired. Place a new order."
```

---

## Step 5: Refund Flow

### 5A: Refund eligibility

| Condition | Eligible? |
|-----------|-----------|
| IP dead on delivery | ✅ Immediate refund |
| Doesn't work for use case | ⚠️ Case-by-case |
| Changed mind | ❌ 24-hour window only |
| Provider outage | ⚠️ Pro-rata credit |

### 5B: Admin initiates refund

**FastAPI: POST /api/payments/{order_id}/refund**

```python
# n8n handles refund:
POST https://api.flutterwave.com/v3/refunds
{
  "id": [flw_ref from original payment],
  "amount": [full or partial amount],
  "reason": "Customer request"
}
```

Flutterwave fires: `refund.initiated` → `refund.completed`

### 5C: Pro-rata calculation

```
days_used = (now - fulfilled_at).days
days_total = (expires_at - fulfilled_at).days
unused_ratio = max(0, 1 - days_used/days_total)
refund_amount = amount_paid_ngn * unused_ratio
```

---

## Step 6: Testing

### Flutterwave test mode

Use test API keys (prefix `FLWPUBK-TEST-` / `FLWSECK-TEST-`) in staging.

**Test card:**
- Card number: `5531888876544444`
- CVV: `123`
- Pin: `1234`
- OTP: `12345`
- Expiry: any future date

---

## Security Checklist

- [ ] Secret key stored in environment variable, never in code
- [ ] Webhook signature verification on every incoming webhook
- [ ] Idempotency check (Redis SETNX + DB unique constraint)
- [ ] Refund requires admin authentication
- [ ] All amounts validated server-side
- [ ] `tx_ref` is generated server-side, not from client input
- [ ] Webhook URL uses HTTPS
- [ ] Flutterwave API keys rotated every 90 days
