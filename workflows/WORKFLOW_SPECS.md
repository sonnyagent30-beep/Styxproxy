# Bunche — n8n Workflow Specifications
*Complete step-by-step specs for all 4 n8n workflows*

---

## Before You Start

### n8n Credentials to Create First

| Credential Name | Type | Fields |
|---------------|------|--------|
| `flutterwave-api` | HTTP Header Auth | `Authorization: Bearer FLUTTERWAVE_SECRET_KEY` |
| `whatsapp-api` | HTTP Header Auth | `Authorization: Bearer WHATSAPP_ACCESS_TOKEN` |
| `google-sheets-service` | Google Cloud Service Account | Service Account JSON |
| `iproyal-api` | HTTP Header Auth | `Authorization: Bearer IPROYAL_API_KEY` |
| `nodemaven-api` | HTTP Query Auth | `Authorization: Bearer NODEMAVEN_API_KEY` |
| `proxyseller-api` | HTTP Query Auth | `Authorization: Bearer PROXYSELLER_API_KEY` |

---

## Workflow 1: Order Handler (WhatsApp Incoming)

**Trigger:** WhatsApp Business API webhook (`POST /webhook/whatsapp-incoming`)
**Purpose:** Parse incoming message → validate → generate payment link → send to customer

### Flow

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
  ↓
(If order)
Parse: Extract proxy_type, country, quantity from message
  ↓
Google Sheets Read Row: Check if customer is blocked
  ↓
If blocked → WhatsApp: "Your account is restricted"
  ↓
Google Sheets Read Row: Lookup price in Inventory
  ↓
If not available → WhatsApp: "Product not available"
  ↓
Edit Fields: Generate order_id, tx_ref
  ↓
HTTP Request → Flutterwave POST /payments
  ↓
Google Sheets Append Row: Create order (status: pending)
  ↓
WhatsApp Send Message: Payment link to customer
  ↓
Webhook Response: HTTP 200 "ok"
```

### Message Parsing

Customer sends: `Order ISP UK 1`
```
parts = msg_body.split(" ")  → ["Order", "ISP", "UK", "1"]
proxy_type = parts[1].toUpperCase()  → "ISP"
country = parts[2].toUpperCase()     → "UK"
quantity = parseInt(parts[3])         → 1
```

### Plan Codes

| Message | Plan Code |
|---------|-----------|
| `Order ISP UK 1` | ISP-UK |
| `Order ISP US 1` | ISP-US |
| `Order ISP NG 1` | ISP-NG |
| `Order RES 5GB` | RES-5GB-NG |
| `Order MOB NG 1` | MOB-NG |
| `Order DC 1` | DC-US |

---

## Workflow 2: Payment Confirmation (Flutterwave Webhook)

**Trigger:** Flutterwave webhook (`POST /webhook/flutterwave`)
**Purpose:** Payment confirmed → verify → fulfill → deliver

### Flow

```
Webhook Trigger (Flutterwave POST)
  ↓
Code Node: Verify Flutterwave-Signature header (HMAC SHA256)
  ↓
IF event !== "charge.completed" OR status !== "successful":
  → Respond 200 "ignored"
  ↓
Edit Fields: Extract tx_ref, amount, customer_phone, meta
  ↓
Google Sheets Read Row: Find order by Payment Reference (tx_ref)
  ↓
IF order not found → Log error, respond 200
  ↓
IF Payment Status !== "pending":
  → Respond 200 "already processed" (idempotency)
  ↓
Google Sheets Update Row: Payment Status = "paid", Paid At = now
  ↓
Switch: Route by proxy type to appropriate provider
  ├── ISP → IPRoyal API
  ├── Residential → NodeMaven API
  ├── Mobile → Proxy-Seller API
  └── DC → IPRoyal API
  ↓
HTTP Request → Provider API (POST /orders)
  ↓
IF Provider API fails → Call backup provider
  ↓
IF All providers fail → Initiate refund, alert admin
  ↓
Edit Fields: Parse credentials from provider response
  ↓
Google Sheets Update Row: Payment Status = "fulfilled", Proxy Details = creds
  ↓
Google Sheets Update Row: Deduct from Inventory
  ↓
Google Sheets Append/Update: Add/update Customer
  ↓
WhatsApp Send Message: Credentials to customer
```

### Flutterwave Signature Verification (Node.js / Code Node)

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

## Workflow 3: Proxy Fulfillment (Provider API Calls)

### IPRoyal API Call

```
POST https://api.iproyal.com/v2/reseller/orders
Headers: Authorization: Bearer {{ $credentials.iproyal-api }}
Content-Type: application/json

Body:
{
  "product_id": "isp",
  "country": "gb",
  "quantity": 1,
  "months": 1
}

Response:
{
  "order_id": "ORD-12345",
  "status": "active",
  "credentials": [
    {
      "ip": "203.0.113.42",
      "port": 8080,
      "username": "cust12345",
      "password": "secretpass"
    }
  ]
}
```

### NodeMaven API Call

```
POST https://api.nodemaven.com/v1/orders
Headers: Authorization: Bearer {{ $credentials.nodemaven-api }}
Content-Type: application/json

Body:
{
  "product": "residential",
  "country": "ng",
  "quantity": 1,
  "session": true
}
```

### Provider Fallback Logic

```
Primary: IPRoyal
  → If fails or returns error:
    → Secondary: NodeMaven
      → If fails:
        → Tertiary: Proxy-Seller
          → If all fail:
            → Initiate Flutterwave refund
            → Alert admin via WhatsApp
            → Mark order as "refunded"
```

---

## Workflow 4: Refund Handler

**Trigger:** Flutterwave webhook (refund events)

### Flow

```
Webhook Trigger (Flutterwave POST)
  ↓
Code Node: Verify signature (same as Workflow 2)
  ↓
IF event !== "refund.initiated" AND event !== "refund.completed":
  → Respond 200 "ignored"
  ↓
Edit Fields: Extract tx_ref, amount, customer_phone
  ↓
Google Sheets Read Row: Find order
  ↓
IF order.Payment Status === "fulfilled":
  → HTTP Request → Provider API: DELETE /orders/{order_id}
  ↓
Google Sheets Update Row: Payment Status = "refunded"
  ↓
WhatsApp Send Message:
  "✅ Refund Processed
  
  Your refund of ₦{amount} for Order {order_id} has been initiated.
  It will appear in your account within 5–7 business days.
  
  Sorry for the inconvenience."
```

---

## Error Workflow: Admin Alert

**Trigger:** n8n Error Trigger (runs on any workflow error)

### Flow

```
n8n Error Trigger
  ↓
Edit Fields: Get workflow_name, error_message, execution_id
  ↓
WhatsApp Send Message to Admin:
  "🔴 Workflow Error
  
  Workflow: {workflow_name}
  Error: {error_message}
  Execution ID: {execution_id}
  
  Check n8n: https://n8n.yourdomain.com/executions"
```

**Setup:** n8n → Settings → Workflows → Error Workflow → select this workflow

---

## Workflow Activation Checklist

| Workflow | Trigger | Status |
|----------|---------|--------|
| Order Handler | WhatsApp Webhook | ACTIVE |
| Payment Confirmation | Flutterwave Webhook | ACTIVE |
| Refund Handler | Flutterwave Webhook | ACTIVE |
| Error Alert | n8n Error Trigger | ACTIVE |

---

## Testing the Workflows

### Test Order Handler (curl)

```bash
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

### Test Payment Webhook

Flutterwave Dashboard → Settings → Webhooks → Send Test → `charge.completed`

---

## n8n Settings for Production

| Setting | Value |
|---------|-------|
| `N8N_SECURE_COOKIE` | `true` |
| `WEBHOOK_URL` | `https://n8n.yourdomain.com` |
| `EXECUTIONS_DATA_SAVE_ON_ERROR` | `all` |
| `EXECUTIONS_DATA_SAVE_ON_SUCCESS` | `none` |
| `GENERIC_TIMEZONE` | `Africa/Lagos` |
