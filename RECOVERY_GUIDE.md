# Styxproxy Recovery Guide — "I paid but didn't see my credentials"

This guide covers the customer-facing recovery flow for Styxproxy when
a paid order doesn't surface credentials on the `/thank-you` page.

## TL;DR for customers

If you paid but the `/thank-you` page is stuck on **Loading...** or
shows **Still Processing** after 5 minutes:

1. **Don't pay again.** Your payment is already in the system.
2. Open **`/manage`** in your browser.
3. Type your **transaction reference** (format: `STX-XXXXXX`, shown
   in the original Flutterwave receipt) into the search box.
4. Hit Enter. Your order + credentials will appear if payment was
   confirmed.

If the search returns "Order not found":
- Wait 2 more minutes and retry (the webhook may be slow)
- Email support: oyebiyiayomide30@gmail.com
- WhatsApp: https://wa.me/2347032981049

## Why does the `/thank-you` page get stuck?

The `/thank-you` page polls `/api/orders/by-payment-reference/{tx_ref}`
every 5 seconds for up to 5 minutes (60 attempts). It stops polling
when the order reaches a terminal state:

| Status | Meaning |
|---|---|
| `active` | ✅ Credentials ready — shown on page |
| `fulfilled` | ✅ Credentials ready — shown on page |
| `expired` | ❌ Order expired (TTL passed) — contact support |
| `cancelled` | ❌ Order cancelled — contact support |
| `refunded` | 💸 Auto-refunded (provider could not deliver) |
| `pending` | ⏳ Still processing |
| `paid` | ⏳ Payment confirmed, credential creation in progress |

If the status stays at `pending` or `paid` for more than 5 minutes,
something is wrong. The recovery flow lets you check again without
starting over.

## Step-by-step recovery

### 1. Find your transaction reference

The transaction reference is the `tx_ref` field in:
- The Flutterwave payment receipt (email from Flutterwave)
- The browser's `sessionStorage` key `styxproxy_active_tx`
- Your order history at `/manage` (click any historical entry)

Format: `STX-XXXXXX` (e.g. `STX-A3K9L2`)

### 2. Open `/manage`

Navigate to **https://styxproxy.com/manage** in any browser. You do NOT
need to be logged in — `/manage` accepts any transaction reference.

### 3. Search by reference

Paste your `STX-XXXXXX` into the search box and hit Enter.

If you have multiple pending orders, the `/manage` page also lists your
local order history at the bottom (from `sessionStorage`).

### 4. View your credentials

Once the order appears, you'll see:
- Username (e.g. `styxproxy_xxxxx`)
- Password
- Proxy IP + port
- Expiration date

Click "Copy" to copy to clipboard. If credentials don't appear but
status is `paid`, the credential creation pipeline is still running —
wait 30 seconds and refresh.

### 5. Rotate credentials

If your proxy IP gets banned or stops working, click **Rotate Key** on
the `/manage` page. This:
- Generates a new upstream proxy from the provider pool
- Updates your Styxproxy credentials (same username/password prefix
  pattern)
- Resets the rotation counter

Each order can be rotated up to 3 times. After 3 rotations, contact
support for a manual swap.

### 6. Report a dead proxy

If your proxy is dead and rotation isn't enough, click **Report Dead**.
This triggers a refund request and assigns the order to the admin
queue for manual review.

## Common scenarios

### "I lost my transaction reference"

1. Check your email inbox for the Flutterwave receipt
2. Check your browser history — the `/thank-you?tx_ref=STX-XXXXXX` URL
   has your reference in the query string
3. Check `sessionStorage` in DevTools:
   - F12 → Application → Session Storage → styxproxy.com
   - Look for `styxproxy_active_tx`
4. If you provided an email at checkout, contact support and we can
   look up by email

### "I paid but `/thank-you` says 'Order Not Found'"

This means the transaction reference is malformed or doesn't match any
order. Causes:
- Customer opened an old `/thank-you` link from a previous order
- The browser cleared `sessionStorage` between payment and redirect

Fix: search `/manage` directly with a fresh reference from your email.

### "I paid but `/manage` says 'Order Not Found' too"

The payment webhook may not have fired yet, or the order was not
created. Contact support with:
- Your Flutterwave transaction reference (`TXF-XXXXXX`)
- The email you used at checkout
- The approximate time of payment

We'll manually verify the Flutterwave dashboard and either:
- Trigger a manual order creation, or
- Process a refund if the provider can't deliver

### "My credentials stopped working"

Click **Rotate Key** on `/manage`. If rotation fails (counter at max):
- The proxy IP may have been banned by the target site
- Some sites actively block known datacenter IPs (try residential plans)
- Contact support with the error you're seeing

### "I want a refund"

Click **Report Dead** on `/manage`. This queues a refund request that
the admin reviews within 24 hours. Refunds typically land in 5-10
minutes via Flutterwave once approved.

## Recovery endpoint summary

| Endpoint | Auth | Use |
|---|---|---|
| `GET /api/orders/by-payment-reference/{ref}` | None | Look up order by `STX-XXXXXX` (FE payment reference). No auth — ref itself is the token. |
| `GET /api/orders/{order_id}` | Required | Look up by `ORD-XXXXXX` (internal id). Auth required because order_id is not a secret. |
| `POST /api/orders/{order_id}/rotate` | Required | Rotate credentials. Max 3 rotations per order. |
| `POST /api/orders/{order_id}/report-dead` | Required | Mark proxy dead → triggers refund review. |
| `GET /api/admin/n8n/failures` | Admin | Admin dashboard shows recent webhook delivery failures. |

## Customer support contacts

- **Email:** oyebiyiayomide30@gmail.com
- **WhatsApp:** https://wa.me/2347032981049
- **Phone:** +234 703 298 1049

When contacting support, always include:
1. Transaction reference (`STX-XXXXXX` if you have it)
2. Order ID (`ORD-XXXXXX` if visible)
3. Email used at checkout
4. Approximate time of payment
5. Screenshot of the issue

## Why this matters

Before commit `4f9679b` (2026-07-28), every customer who paid was
stuck at the Loading spinner for 5 minutes because the FE polled the
wrong endpoint (`/api/orders/{tx_ref}` matched the BE handler for
`{order_id}` → 404). Customers who navigated away to look for support
contact info lost their sessionStorage `tx_ref` and had no way to
recover.

This guide + the `/by-payment-reference` endpoint + the `/manage` page
fix together close the entire recovery loop. Customers can always
find their credentials via `/manage` as long as they have either:
- A transaction reference from their payment receipt
- The original `/thank-you` URL (still works as long as sessionStorage
  isn't cleared)

## Implementation notes for engineers

- `/api/orders/by-payment-reference/{ref}` is the canonical recovery
  endpoint. It's auth-less by design — the reference is a 60-bit
  entropy token (32^6 = ~1B combos).
- `/manage` calls this same endpoint when the customer pastes a ref.
- For multi-item carts (commit `eaabc10`), each cart item gets its own
  STX-XXXXXX. Customers can search each separately in `/manage`.
- For order detail that's strictly the order owner (e.g. refund flow),
  use `/api/orders/{order_id}` (auth required).