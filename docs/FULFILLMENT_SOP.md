# Fulfillment SOP — Payment Flow Rewrite

**Version:** 1.0
**Date:** 2026-09-29
**Owner:** @styxproxy-operations
**Status:** Active

---

## 1. Normal Fulfillment Flow

**Trigger:** Webhook received → signature verified → replay check passed → order marked paid → RQ job enqueued

### Chain

1. **Webhook handler** verifies HMAC signature (all providers)
2. **Replay check:** reject ALL duplicates regardless of age → `409 Conflict`
3. **Order expiry check:** if `expires_at < now()` → `400` "order expired"
4. Mark order `paid` → enqueue RQ job
5. **Fulfillment worker:**
   - Load order from DB
   - Resolve plan via `resolve_plan(db, order.plan_code, country=order.country)`
   - Read `proxy_type` from plan (residential | mobile | isp | datacenter)
   - Read `quantity` from order
   - Create N credentials (one per IP)
   - Send to n8n webhook for delivery
6. **n8n** → email/WhatsApp/Telegram delivery
7. Order status → `fulfilled`

**SLA:** <30 seconds from webhook to credential delivery

---

## 2. n8n Fallback Path

**Trigger:** n8n webhook fails (timeout or 5xx)

### Flow

1. Retry with exponential backoff: 1s, 2s, 4s
2. If all retries fail → send credentials via **direct email** (Resend) using `send_order_active_email()`
3. Log n8n failure with `order_id` + `tx_ref`
4. Credential still created in DB (payment was received — customer gets proxy)
5. Support ticket created with order ID + error details

**Email template:** Must match design tokens, include credential block (username, password, upstream IP, port), same structure as n8n-delivered email.

---

## 3. Auto-Refund Flow

**Trigger:** Fulfillment worker catches `RuntimeError` (provider exhausted, credential creation failed)

### Flow

1. Log audit event: `fulfillment_failed` with full context
2. Call Flutterwave refund API
3. Create support ticket: order ID, customer email, error details, tx_ref
4. Mark order `refunded` + `refund_requested = True`
5. If refund API itself fails → order stays `failed_unfulfilled`, retry cron picks up every 15 min

---

## 4. Order Expiry

**Trigger:** systemd timer every 5 min

### Flow

```sql
UPDATE orders SET status='expired'
WHERE status IN ('pending', 'paid')
  AND created_at < now() - interval '30 minutes'
```

- Webhook for expired order → `400` "order expired"
- Thank-you page shows "Order expired" state + "Place New Order" CTA

---

## 5. Support Ticket Integration

### Auto-created tickets

| Trigger | Destination | Content |
|---------|-------------|---------|
| Fulfillment failure | `support_threads` DB table | Order ID, customer email, error details, tx_ref |
| n8n fallback | `support_threads` DB table | Order ID, error details, fallback path used |
| Refund API failure | `support_threads` DB table | Order ID, customer email, refund retry needed |

**Access:** Admin inbox at `/admin/support` or `GET /api/v1/admin/support/threads?status=open`

---

## 6. Monitoring & Alerting

### Logs

All payment/fulfillment steps log with `order_id` + `tx_ref` context → shipped to Loki

### Alerts

| Condition | Alert |
|-----------|-------|
| Fulfillment time >30s | ⚠️ SLA breach |
| n8n fallback triggered | ⚠️ Provider issue |
| Auto-refund triggered | ⚠️ Fulfillment failure |
| Order expiry cron failure | 🔴 Cron down |
| Webhook signature verification failure | 🔴 Security |

### Dashboards

- **Grafana:** fulfillment time, success rate, refund rate
- **Loki:** structured logs filtered by order_id or tx_ref

---

## 7. Escalation Procedures

| Issue | Owner | Action |
|-------|-------|--------|
| Fulfillment failure | @styxproxy-operations | Check logs, verify refund, manual fulfill if needed |
| n8n down | @styxproxy-devops | Verify container, restart if needed |
| Webhook failures | @styxproxy-devops | Check endpoint, verify secrets |
| Customer complaint | @styxproxy-support | Look up order, escalate to ops if needed |
| Refund API failure | @styxproxy-operations | Retry cron, manual refund if needed |

---

## 8. Key Metrics

| Metric | Target |
|--------|--------|
| Fulfillment time | <30s |
| Fulfillment success rate | >99% |
| Refund rate | <1% |
| n8n fallback rate | <5% |
| Order expiry rate | <2% |

---

## 9. Deployment Checklist

- [x] `styxproxy-order-expiry.timer` — every 5 min, covers `pending` + `paid` orders
- [x] `styxproxy-refund-retry.timer` — every 15 min, picks up `failed_unfulfilled` orders
- [x] n8n fallback email via `send_order_active_email()`
- [x] Support ticket auto-creation in `support_threads` table
- [x] Structured logging with `order_id` + `tx_ref` context
- [x] Rate limiting on `/api/orders/lookup` (10/minute)
