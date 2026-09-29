# Payment Flow Architecture — Current State

**Date:** 2026-09-29  
**Author:** @styxproxy-developer  
**Status:** Phase 1 Discovery Output

---

## 1. End-to-End Journey

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend  │────▶│   Backend    │────▶│  Gateway    │────▶│   Webhook    │
│  Checkout   │     │  /payments   │     │ Flutterwave │     │  /webhooks   │
│             │     │  /initiate   │     │  Paystack   │     │  /flutterwave│
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
       │                   │                                         │
       │                   │                                         ▼
       │                   │                              ┌──────────────┐
       │                   │                              │  RQ Worker   │
       │                   │                              │  Fulfillment │
       │                   │                              └──────────────┘
       │                   │                                         │
       │                   │                                         ▼
       │                   │                              ┌──────────────┐
       │                   │                              │  n8n Webhook │
       │                   │                              │  + Email     │
       │                   │                              └──────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌──────────────┐
│  Thank-You  │◀────│  Poll /api/ │
│  Page       │     │  orders/{id} │
│  (3.5s)     │     │  /status     │
└─────────────┘     └──────────────┘
```

---

## 2. API Endpoints

### 2.1 Backend — Payment Initiation

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/payments/initiate` | POST | None | Create order, return gateway checkout URL |
| `/api/payments/gateways` | GET | None | List available gateways from feature flags |
| `/api/orders/precheck` | POST | None | Check provider availability before payment |
| `/api/orders/create` | POST | JWT | Create order (logged-in users) |
| `/api/orders/by-payment-reference/{ref}` | GET | None | Resolve tx_ref → order_id (for thank-you) |
| `/api/orders/{order_id}/status` | GET | JWT | Poll order + payment status |
| `/api/orders/{order_id}` | GET | JWT | Get order details |
| `/api/orders/{order_id}/cancel` | POST | JWT | Cancel pending order |
| `/api/orders/{order_id}/rotate` | POST | JWT | Rotate credentials |
| `/api/orders/{order_id}/deliver` | POST | JWT | Manual credential delivery trigger |
| `/api/orders/{order_id}/receipt` | GET | None | Public receipt data |
| `/api/orders/{order_id}/pdf` | GET | None | PDF receipt download |

### 2.2 Backend — Webhooks

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/webhooks/flutterwave` | POST | HMAC | Flutterwave payment events |
| `/api/webhooks/paystack` | POST | HMAC | Paystack payment events |
| `/api/webhooks/nowpayments` | POST | HMAC | Crypto payment IPN |
| `/api/webhooks/theorem-reach` | POST | HMAC | Survey completion → trial delivery |

---

## 3. State Machine

```
                  ┌──────────┐
                  │  pending  │◀── Order created
                  └────┬─────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │   paid   │ │ cancelled│ │  failed  │
    └────┬─────┘ └──────────┘ └──────────┘
         │
         ▼
    ┌──────────┐     ┌──────────┐
    │fulfilled │     │  failed  │
    │/ active  │     │unfulfilled│
    └──────────┘     └────┬─────┘
                          │
                          ▼
                    ┌──────────┐
                    │ refunded │
                    └──────────┘
```

---

## 4. Key Files

### Backend
| File | Lines | Purpose |
|------|-------|---------|
| `app/routers/payments.py` | 156 | `/api/payments/initiate` + `/gateways` |
| `app/routers/webhooks.py` | 488 | All webhook handlers (FW, Paystack, NOWPayments, TheoremReach) |
| `app/routers/orders.py` | 1441 | Order CRUD, precheck, receipt, PDF, rotate, deliver |
| `app/routers/payment_status.py` | 85 | Polling endpoint `/api/orders/{id}/status` |
| `app/routers/_webhook_queue.py` | 74 | RQ enqueue helper |
| `app/scripts/fulfillment_worker.py` | 210 | RQ worker — credential creation + n8n + email + refund |
| `app/services/flutterwave.py` | — | Flutterwave API client |
| `app/services/paystack.py` | — | Paystack API client |
| `app/services/n8n.py` | — | n8n webhook trigger |
| `app/services/credential.py` | — | Provider API → credential creation |
| `app/services/payment_status.py` | 192 | Status computation logic |

### Frontend
| File | Lines | Purpose |
|------|-------|---------|
| `src/app/(public)/order/checkout/page.tsx` | 533 | Cart, email, gateway selection, pay button |
| `src/app/(public)/thank-you/page.tsx` | 952 | Polling, success/error/timeout states, PDF |
| `src/components/PaymentStatusPoller.tsx` | 246 | Reusable poller (NOT used by thank-you currently) |
| `src/components/CheckoutDisabledBanner.tsx` | — | Kill-switch banner |

---

## 5. Pain Points (Priority Order)

### P0 — Critical (Fix in Rewrite)

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 1 | **No idempotency on `/api/payments/initiate`** | Double-clicking Pay creates duplicate orders; customer charged twice | `payments.py:20-115` |
| 2 | **Frontend generates `tx_ref`** | Security: client-controlled payment reference; backend should generate | `checkout/page.tsx:18-24` |
| 3 | **Fulfillment worker hardcodes `proxy_type="isp"`** | All orders fulfilled as ISP regardless of actual plan (residential/mobile/DC) | `fulfillment_worker.py:89` |
| 4 | **Fulfillment worker hardcodes `quantity=1`** | Multi-IP orders only get 1 credential | `fulfillment_worker.py:90` |
| 5 | **`/api/orders/{id}/status` requires JWT** | Anonymous web customers can't poll; thank-you falls back to unauthenticated `by-payment-reference` | `payment_status.py:32` |

### P1 — High

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 6 | **Silent `except: pass`** | Failures invisible — no logging, no alerting | `orders.py:439-441`, `checkout/page.tsx:75-76` |
| 7 | **No order expiry** | Pending orders stay forever; no cleanup job | — |
| 8 | **Webhook marks processed AFTER work** | If processing fails, webhook replays and may double-fulfill | `webhooks.py:176-182` |
| 9 | **Race condition: webhook → RQ → inline fallback** | If RQ enqueue fails mid-webhook, inline processing may conflict with retry | `webhooks.py:154-157` |
| 10 | **Thank-you page duplicates polling logic** | `PaymentStatusPoller.tsx` exists but isn't used; 952-line page with inline polling | `thank-you/page.tsx:427-536` |

### P2 — Medium

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 11 | **No `loading.tsx` for thank-you** | No Next.js loading boundary | — |
| 12 | **Cart in `sessionStorage`** | Lost on refresh; no recovery | `checkout/page.tsx:160` |
| 13 | **No structured logging** | Can't trace a payment through the system | All routers |
| 14 | **PDF generation in frontend** | jsPDF in browser; should be server-side | `thank-you/page.tsx:44-374` |
| 15 | **No payment timeout** | Customer can leave checkout open for hours and pay later | — |

---

## 6. Current Webhook Security

| Provider | Signature Header | Algorithm | Replay Window | Duplicate Check |
|----------|-----------------|-----------|---------------|-----------------|
| Flutterwave | `Verif-Hash` | HMAC-SHA256 | 300s | `webhook_id` |
| Paystack | `X-Paystack-Signature` | HMAC-SHA512 | None | `webhook_id` |
| NOWPayments | `x-nowpayments-sig` | HMAC-SHA512 | None | `payment_id` |
| TheoremReach | `X-Signature` | HMAC-SHA256 | 300s | `survey_id` |

**Note:** Paystack and NOWPayments lack replay-window checks — only Flutterwave and TheoremReach validate payload freshness.

---

## 7. Fulfillment Chain (Current)

```
Webhook received
    │
    ▼
Verify HMAC signature ──▶ 401 if invalid
    │
    ▼
Parse payload
    │
    ▼
Check replay window ──▶ 400 if stale (FW + TheoremReach only)
    │
    ▼
Duplicate check (webhook_id) ──▶ 200 "already_processed"
    │
    ▼
Lookup order by payment_reference (tx_ref)
    │
    ▼
Mark order "paid"
    │
    ▼
Enqueue RQ job ──▶ Fallback to inline if RQ fails
    │
    ▼
┌─────────────────────────────────────────┐
│  RQ Worker: fulfill_order_job           │
│                                         │
│  1. Load order from DB                  │
│  2. create_credential() — provider API  │
│  3. Mark order "fulfilled"              │
│  4. Trigger n8n webhook                 │
│  5. Send email (if customer email)      │
│  6. On failure → auto-refund            │
└─────────────────────────────────────────┘
    │
    ▼
Mark webhook processed
    │
    ▼
Return 200 to gateway
```

---

## 8. Rewrite Recommendations

### Phase 2 — Backend
1. Add idempotency key to `/api/payments/initiate` (client-generated, stored on order)
2. Move `tx_ref` generation to backend
3. Fix fulfillment worker to use `order.plan_type` and `order.quantity`
4. Make `/api/orders/{id}/status` work for anonymous users (by payment_reference)
5. Add structured logging (structlog or JSON format)
6. Move `mark_webhook_processed` BEFORE processing (with status tracking)
7. Add order expiry cron (pending orders > 30min → expired)

### Phase 3 — Frontend
1. Use `PaymentStatusPoller` component in thank-you page
2. Add `loading.tsx` for thank-you route
3. Move PDF generation to server-side endpoint
4. Add payment timeout UI (15 min countdown)
5. Persist cart to localStorage with recovery

### Phase 4 — Testing
1. E2E: Flutterwave test mode → webhook → fulfillment → thank-you
2. Webhook signature verification (tampered payloads)
3. Replay attack simulation
4. Double-click Pay button (idempotency)
5. Adversarial UX test with non-technical user

---

## 9. Dependencies

- **Flutterwave:** `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_WEBHOOK_SECRET`
- **Paystack:** `PAYSTACK_SECRET_KEY`
- **n8n:** `N8N_API_KEY`, `N8N_BASE_URL`
- **Provider:** `PROXY_SELLER_API_KEY`, `DATAIMPULSE_API_KEY`
- **Redis:** `REDIS_URL` (for RQ)
- **Email:** `RESEND_API_KEY`

---

*End of Phase 1 discovery document.*
