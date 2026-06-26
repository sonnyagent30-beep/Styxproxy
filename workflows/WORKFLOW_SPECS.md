# Bunche — n8n Workflow Specifications
*Zero-inventory, fully on-demand. Every proxy is bought via API after customer pays.*

---

## Credentials to Create in n8n

| Name | Type | Auth |
|------|------|------|
| `flutterwave-api` | HTTP Header Auth | `Authorization: Bearer FLUTTERWAVE_SECRET_KEY` |
| `whatsapp-api` | HTTP Header Auth | `Authorization: Bearer WHATSAPP_ACCESS_TOKEN` |
| `google-sheets-service` | Google Cloud Service Account | Service Account JSON |
| `proxyseller-api` | HTTP Header Auth | `Authorization: Bearer PROXYSELLER_API_KEY` |
| `okeyproxy-api` | HTTP Header Auth | `Authorization: Bearer OKEYPROXY_API_KEY` |
| `dataimpulse-api` | HTTP Header Auth | `Authorization: Bearer DATAIMPULSE_API_KEY` |

---

## Workflow 1: Order Handler (WhatsApp Incoming)

**Trigger:** `POST /webhook/whatsapp-incoming`

```
Webhook Trigger (WhatsApp POST)
  ↓
Edit Fields: Extract from, msg_body, msg_id, timestamp
  ↓
Switch: Route by command
  ├── "order" → Order flow
  ├── "status" → Status lookup
  ├── "renew" → Renewal flow
  ├── "help" → Help menu
  └── Default → Unknown command
  
(If order)
  ↓
Parse: Extract proxy_type, country, quantity from message
  ↓
Google Sheets Read Row: Check if customer is blocked (Customers sheet)
  ↓
If blocked → WhatsApp: "Your account is restricted"
  ↓
Google Sheets Read Row: Lookup price in Pricing sheet
  ↓
If not available → WhatsApp: "Sorry, [country] is currently unavailable"
  ↓
Edit Fields: Generate order_id, tx_ref
  ↓
HTTP Request → Flutterwave POST /payments
  ↓
Google Sheets Append Row: Pending_Orders (status: awaiting_payment)
  ↓
WhatsApp Send Message: Payment link to customer
  ↓
Webhook Response: HTTP 200
```

### Message Parsing

Customer sends: `Order ISP UK 1`

```
parts = msg_body.split(" ")  → ["Order", "ISP", "UK", "1"]
proxy_type = parts[1].toUpperCase()  → "ISP"
country = parts[2].toUpperCase()     → "UK"
quantity = parseInt(parts[3])         → 1
```

### Country Code Map

| Message | Plan Code | Country Code |
|---------|-----------|-------------|
| UK, GB | ISP-UK | gb |
| US | ISP-US | us |
| Germany, DE | ISP-DE | de |
| France, FR | ISP-FR | fr |
| Canada, CA | ISP-CA | ca |
| Netherlands, NL | ISP-NL | nl |
| Japan, JP | ISP-JP | jp |
| Australia, AU | ISP-AU | au |
| Brazil, BR | ISP-BR | br |
| India, IN | ISP-IN | in |
| Singapore, SG | ISP-SG | sg |
| South Africa, ZA | ISP-ZA | za |
| Mexico, MX | ISP-MX | mx |
| South Korea, KR | ISP-KR | kr |
| Italy, IT | ISP-IT | it |
| Spain, ES | ISP-ES | es |
| RES 5GB | RES-5GB | — |
| MOB 5GB | MOB-5GB | — |

---

## Workflow 2: Payment Confirmation (Flutterwave Webhook)

**Trigger:** `POST /webhook/flutterwave`

```
Webhook Trigger (Flutterwave POST)
  ↓
Code Node: Verify Flutterwave-Signature (HMAC SHA256)
  ↓
IF event !== "charge.completed" OR status !== "successful":
  → Respond 200 "ignored"
  ↓
Edit Fields: Extract tx_ref, amount, customer.phone, meta
  ↓
Google Sheets Read Row: Find order by Payment Reference (Pending_Orders)
  ↓
IF order not found → Log error, respond 200
  ↓
IF Status !== "awaiting_payment":
  → Respond 200 "already processed" (idempotency)
  ↓
Google Sheets Update Row: Status = "paid_pending_fulfillment"
  ↓
Switch: Route by Plan Code to provider
  ├── ISP-* → Proxy-Seller API
  ├── RES-* → OkeyProxy API
  ├── MOB-* → DataImpulse API
  └── DC-* → Proxy-Seller API
  ↓
HTTP Request → Provider API (POST /orders)
  ↓
IF Provider API fails → Try backup provider
  ├── Proxy-Seller fails → OkeyProxy
  ├── OkeyProxy fails → IPRoyal
  ↓
IF All fail:
  → Initiate Flutterwave refund
  → Alert admin via WhatsApp
  → Mark order "failed"
  ↓
Edit Fields: Parse credentials from provider response
  ↓
Google Sheets Update Row: Status = "fulfilled", Proxy Details = creds
  ↓
Google Sheets Append/Update: Add/update Customer
  ↓
WhatsApp Send Message: Credentials to customer
  ↓
Webhook Response: HTTP 200
```

### Signature Verification (Code Node)

```javascript
const crypto = require('crypto');
const body = $input.first();
const secretHash = 'YOUR_FLUTTERWAVE_ENCRYPTION_KEY';
const signature = $headers['flutterwave-signature'];

const hash = crypto
  .createHmac('sha256', secretHash)
  .update(JSON.stringify(body))
  .digest('hex');

if (signature !== hash) {
  throw new Error('Invalid webhook signature');
}

return body;
```

---

## Workflow 3: Proxy Fulfillment (Provider APIs)

### Proxy-Seller API (Primary for ISP + DC)

```
POST https://api.proxy-seller.com/v1/orders
Headers: Authorization: Bearer {{ $credentials.proxyseller-api }}
Content-Type: application/json

Body:
{
  "type": "isp",
  "country": "gb",
  "quantity": 1,
  "period": 30
}

Response:
{
  "order_id": "PS-12345",
  "status": "active",
  "proxies": [
    {
      "ip": "203.0.113.42",
      "port": 8080,
      "username": "cust12345",
      "password": "secretpass",
      "expires_at": "2026-07-26"
    }
  ]
}
```

### OkeyProxy API (Residential)

```
POST https://api.okeyproxy.com/v1/order
Headers: Authorization: Bearer {{ $credentials.okeyproxy-api }}
Content-Type: application/json

Body:
{
  "type": "residential",
  "country": "global",
  "traffic": "5GB"
}
```

### DataImpulse API (Mobile)

```
POST https://api.dataimpulse.com/v1/order
Headers: Authorization: Bearer {{ $credentials.dataimpulse-api }}
Content-Type: application/json

Body:
{
  "type": "mobile",
  "country": "us",
  "traffic": "5GB"
}
```

### Fallback Chain

```
Proxy-Seller
  → Fails
    → OkeyProxy (if ISP or DC)
    → DataImpulse (if Mobile)
      → Fails
        → Initiate refund
        → Alert admin
        → Mark order failed
```

---

## Workflow 4: Refund Handler

**Trigger:** Flutterwave webhook (refund events)

```
Webhook Trigger
  ↓
Code Node: Verify signature
  ↓
IF event !== "refund.initiated" AND event !== "refund.completed":
  → Respond 200 "ignored"
  ↓
Edit Fields: Extract tx_ref, amount
  ↓
Google Sheets Read Row: Find order (Pending_Orders)
  ↓
IF Status == "fulfilled":
  → HTTP Request → Provider API: revoke/cancel order
  ↓
Google Sheets Update Row: Status = "refunded"
  ↓
WhatsApp Send Message:
  "✅ Refund Processed
  Your refund of ₦{amount} for {order_id} will appear in 5–7 business days."
```

---

## Error Workflow: Admin Alert

**Trigger:** n8n Error Trigger

```
n8n Error Trigger
  ↓
WhatsApp Send to Admin:
  "🔴 Workflow Error
  
  Workflow: {workflow_name}
  Error: {error_message}
  Execution: {execution_id}
  
  Check: https://n8n.yourdomain.com/executions"
```

*Set in n8n → Settings → Error Workflow*

---

## Workflow Activation Checklist

| Workflow | Trigger | Status |
|----------|---------|--------|
| Order Handler | WhatsApp Webhook | ACTIVE |
| Payment Confirmation | Flutterwave Webhook | ACTIVE |
| Refund Handler | Flutterwave Webhook | ACTIVE |
| Error Alert | n8n Error Trigger | ACTIVE |

---

## Testing

```bash
# Test Order Handler
curl -X POST https://n8n.yourdomain.com/webhook/whatsapp-incoming \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "test123",
            "from": "2348012345678",
            "timestamp": "1234567890",
            "text": {"body": "Order ISP UK 1"}
          }]
        }
      }]
    }]
  }'
```

Flutterwave Dashboard → Settings → Webhooks → Send Test → `charge.completed`

---

## n8n Production Settings

| Setting | Value |
|---------|-------|
| `N8N_SECURE_COOKIE` | `true` |
| `WEBHOOK_URL` | `https://n8n.yourdomain.com` |
| `EXECUTIONS_DATA_SAVE_ON_ERROR` | `all` |
| `EXECUTIONS_DATA_SAVE_ON_SUCCESS` | `none` |
| `GENERIC_TIMEZONE` | `Africa/Lagos` |
