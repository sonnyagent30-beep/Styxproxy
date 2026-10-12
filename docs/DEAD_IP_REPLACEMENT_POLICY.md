# Styxproxy — Provider Dead-IP Replacement Policy

**Date captured:** 2026-06-26
**Source:** Provider public docs + Trustpilot/GitHub reviews + Dannion's customer-experience rule
**Status:** Active policy for Styxproxy fulfillment

---

## Why This Doc Exists

When Styxproxy generates a proxy via the provider API, the IP **might be dead on arrival** — already banned, region-wrong, or unreachable. This costs us:
- Customer trust (they paid, got junk)
- Refund fees (Flutterwave takes 1.5% even on refunds)
- Support time (customer complains, we troubleshoot)

**Dannion's rule (locked this session):** Every IP we deliver to a customer must be tested and confirmed working. We never deliver a dead IP. If we can't get a working one from the provider after 3 retries, we auto-refund.

---

## Styxproxy's Dead-IP Handling Flow (Locked)

```
[Payment confirmed]
   ↓
[Workflow 2 generates IP via provider API]
   ↓
[Test the IP: curl --proxy <ip>:<port> https://api.ipify.org]
[Timeout: 5 seconds]
   ↓
   ✅ Pass → Deliver to customer (normal flow)
   ↓
   ❌ Fail → Send back to provider, request replacement IP
   ↓
[Retry #1 — request new IP from provider]
   ↓
[Test again]
   ✅ Pass → Deliver
   ❌ Fail → Retry #2
   ↓
[Retry #2]
   ↓
[Test again]
   ✅ Pass → Deliver
   ❌ Fail → Retry #3
   ↓
[Retry #3 — LAST attempt]
   ↓
[Test again]
   ✅ Pass → Deliver
   ❌ Fail → ALL DEAD — auto-refund flow
```

**Max attempts: 4 total (initial + 3 retries)**

---

## Auto-Refund Flow (When All 3 Retries Fail)

```
[All 3 retries failed]
   ↓
[Log to error_log: order_id, provider, all_attempts_failed]
[Audit log: fulfillment_failed_dead_ips]
[Alert admin: "🚨 ORD-XXXXX: Provider returned 4 dead IPs in a row. Refund issued. Check provider health."]
   ↓
[Call Flutterwave Refund API: refund full amount]
   ↓
[UPDATE orders: status='refunded_dead_ip', refund_reason='all_attempts_dead']
   ↓
[Send WhatsApp to customer]:
"⚠️ Sorry, Dan — we hit a technical issue and couldn't generate a working IP for your order.

✅ Your full payment of ₦6,500 has been refunded automatically.
⏰ Refund will land in your account within 24 hours.

We won't try again on this order — please reorder later or try a different product.

Sorry for the inconvenience 🙏"
```

---

## Provider Replacement SLAs (Research Summary)

### Proxy-Seller

| Item | Policy |
|------|--------|
| **IP replacement** | Free if IP dead/region-wrong/banned within 72h of purchase |
| **Full refund window** | 72 hours — for inoperable proxies + inability to replace |
| **First-purchase bonus** | Free residential IP replacement (3GB) on first purchase |
| **How to claim** | Open support ticket → verification → replacement or refund |
| **Source** | proxy-seller.com/return/, Trustpilot reviews |

**Implication for Styxproxy:** If we get a dead IP, we can hit their support OR use their replacement API. Our 3-retry + auto-refund is well within their 72h window — we don't need to escalate unless the API fails to give us a working IP after 3 calls.

### DataImpulse

| Item | Policy |
|------|--------|
| **IP replacement** | Not explicitly documented publicly — assumed yes via reseller API |
| **Refund window** | Not publicly documented — need to confirm via support |
| **How to claim** | Contact support — no formal SLA found |
| **Source** | dataimpulse.com, no public refund page |

**⚠️ Action item:** Email DataImpulse support to confirm:
- Replacement policy for dead-on-arrival IPs
- Refund window
- SLA for replacement API

Document the response in this file once received.

---

## Why 3 Retries?

| Attempts | Math | Outcome |
|----------|------|---------|
| 1 (just deliver whatever provider gives) | 95% success rate per industry | ~5% dead-on-arrival = customer complaints + refunds |
| 1 + 3 retries | Each retry independent: 5% × 5% × 5% = 0.0125% | 99.99% chance of working IP delivered |
| Beyond 3 retries | Negligible improvement (~0.0006%) | Adds latency + provider rate-limit risk |

**3 retries gives us near-certain working delivery** without wasting time on bad providers.

---

## What Counts as "Dead"?

| Test | Fail criteria | Action |
|------|---------------|--------|
| `curl --proxy <ip>:<port> https://api.ipify.org` | No response in 5s, or returns wrong IP | Retry |
| `curl --proxy <ip>:<port> https://api.ipify.org` | Returns different IP than what provider gave | Retry (region-mismatch) |
| `curl --proxy <ip>:<port> https://ifconfig.me` | Timeout or 5xx | Retry |

**Two-test verification** (ipify + ifconfig.me) before declaring dead — eliminates false positives from a single test endpoint.

---

## Cost Impact

At 100 orders/month with ~5% initial dead rate:
- Without retry: ~5 dead IPs delivered → 5 customer complaints + 5 refunds = ₦32,500 lost revenue + reputation damage
- With 3 retries: ~0.006 dead IPs delivered (99.99% clean) → 0 complaints, 0.06 wasted retries ≈ ₦390 in provider costs

**ROI of retry loop:** ₦32,500 saved per 100 orders. Worth the 15s of latency.

---

## Logging Requirements

Every retry attempt logs:

```json
{
  "order_id": "ORD-20260627-0917",
  "attempt_number": 2,
  "provider": "Proxy-Seller",
  "provider_order_id": "PS-8393",
  "proxy_ip": "185.123.45.68",
  "test_endpoint": "https://api.ipify.org",
  "test_result": "fail",
  "failure_reason": "timeout_5s",
  "retry_at": "2026-06-27T14:23:18Z"
}
```

**Never logged:** Plain customer phone, plain customer name. Customer is hashed before any log line.

---

## Admin Visibility

Admin gets a daily summary addition:

```
⚠️ Dead-IP retries today: 3
   ORD-20260627-0917: 2 retries, delivered working IP
   ORD-20260627-0947: 1 retry, delivered working IP
   ORD-20260627-1012: 3 retries failed → auto-refunded
   
If retries > 5% of daily orders → alert: "Provider quality degrading, check status"
```

---

## Critical Rules Locked

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | Test EVERY IP before delivering to customer | This doc + WORKFLOW_SPECS §2 |
| 2 | Max 3 retries after initial attempt fails (4 total) | This doc + WORKFLOW_SPECS §2 |
| 3 | Two-test verification (ipify + ifconfig.me) before declaring dead | This doc |
| 4 | All 4 attempts fail → auto-refund + customer notification | This doc + WORKFLOW_SPECS §2 |
| 5 | Every retry attempt logged with structured data | WORKFLOW_SPECS §11 |
| 6 | Customer never sees a dead IP — fails silently to them | This doc |
| 7 | Admin alerted if retries > 5% of daily orders | This doc |

---

## TODO

- [ ] Email DataImpulse support to confirm their replacement + refund SLA
- [ ] Add `retry_count` column to `orders` table
- [ ] Add `failure_reason` column to `orders` table for analytics
- [ ] Update WORKFLOW_SPECS.md §2 with the retry flow
- [ ] Update PROVIDER_SETUP_GUIDE.md with replacement API details (when added back from archive)

---

## Related

- `workflows/WORKFLOW_SPECS.md` §2 — Payment Confirmation flow
- `workflows/WORKFLOW_SPECS.md` §11 — Styxproxy Logger
- `scenarios/2026-06-26-first-time-order.md` — happy path scenario
- `docs/SECURITY_RUNBOOK.md` §2 — API monitoring queries