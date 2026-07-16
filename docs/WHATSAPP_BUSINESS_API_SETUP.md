# Bunche — WhatsApp Business API Setup & Bot Flow

**Document Type:** Technical Setup Guide
**Date:** July 1, 2026
**Status:** Planning Complete

---

## Overview

WhatsApp Business API is Bunche's primary customer-facing bot channel for Nigeria.

**Stack:** WhatsApp Business API → n8n → PostgreSQL + Redis

---

## Two Integration Options

| | WhatsApp Business API (Direct) | Twilio WhatsApp |
|--|--|--|
| **Setup time** | 1–4 weeks approval | 1–3 days |
| **Cost** | ~$0.05/message outbound | ~$0.05/message outbound |
| **Recommended for Bunche** | ✅ Yes (production) | Good for staging/testing |

**Recommendation:** Start with Twilio WhatsApp for testing. Migrate to direct WhatsApp Business API for production.

---

## Option A: Direct WhatsApp Business API

### Step 1: Meta Business Account Setup

1. Go to [business.facebook.com](https://business.facebook.com)
2. Create Business Account: **Bunche Digital**
3. Email: `hello@styxproxy.com`
4. Verify business domain ownership (styxproxy.com)

### Step 2: Create WhatsApp Business App

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create App → select **Business** type
3. Add **WhatsApp** product to the app
4. In WhatsApp settings:
   - **Phone Number**: +234 XXX XXXX (dedicated, not personal)
   - **Business Name**: Bunche Digital
   - **Timezone**: Africa/Lagos

### Step 3: Get API Credentials

| Credential | Use |
|--|--|
| **Phone Number ID** | Identify which phone number is sending |
| **WhatsApp Business Account ID** | API requests |
| **Access Token** | Authenticate API calls |

### Step 4: Business Verification (Meta Verified)

**Documents needed (Nigeria):**
- CAC Registration Certificate
- Proof of address
- Business website with matching domain
- Privacy Policy URL (styxproxy.com/privacy)

**Timeline:** 2–10 business days

---

## Option B: Twilio WhatsApp (Faster Setup)

### Step 1: Create Twilio Account

1. Go to [twilio.com/whatsapp](https://twilio.com/whatsapp)
2. Sign up for free trial
3. Request WhatsApp sandbox: send `join [sandbox-code]` to +1-415-523-8886

### Step 2: Configure Webhook in n8n

```
URL: https://n8n.styxproxy.com/webhook/whatsapp-incoming
Method: POST
Auth: Verify X-Twilio-Signature header
```

---

## Webhook Configuration

### Register webhook URL

In Meta Business Console → WhatsApp → Configuration:
```
Callback URL: https://n8n.styxproxy.com/webhook/whatsapp-incoming
Verify Token: [random string — must match what n8n expects]
```

### Subscribe to webhook fields

- ✅ `messages` → `messages` (inbound messages)
- ✅ `messages` → `message_deliveries` (delivery receipts)
- ✅ `messages` → `message_reads` (read receipts)

---

## Message Types

### Session Messages (24-hour window)

After a customer messages you first, you have a **24-hour session** to reply freely.

**Starting a session:** Customer sends any message to your WhatsApp Business number → Meta starts 24-hour conversation window → Bunche can send replies freely.

### Template Messages (outside 24-hour window)

When the 24-hour window is closed, you can only send **approved template messages**.

| Category | Use case | Approval needed |
|----------|----------|--|
| `UTILITY` | Order confirmations, receipts, updates | Yes — 1-2 days |
| `MARKETING` | Promotions, deals, product updates | Yes — stricter review |
| `AUTHENTICATION` | OTP, PIN verification | Yes — 1-2 days |

---

## Required Message Templates

### UTILITY Templates (needed for operations)

| Template Name | Language | Variables | Purpose |
|---|---|---|---|
| `order_confirmation` | English (en) | `{order_id}`, `{product}`, `{amount}` | Order placed successfully |
| `payment_received` | English (en) | `{order_id}`, `{amount}` | Payment confirmed |
| `credentials_delivered` | English (en) | `{username}`, `{protocol}`, `{expiry}` | Proxy credentials sent |
| `ip_replaced` | English (en) | `{order_id}`, `{old_ip}`, `{new_ip}` | Dead IP replaced |
| `refund_processed` | English (en) | `{order_id}`, `{amount}`, `{method}` | Refund completed |

### Template Submission Guide

1. Click **New Template** in Meta Business Console
2. Name: lowercase_with_underscores
3. Language: English (en-GB or en-US)
4. Category: UTILITY or MARKETING
5. Content: Write template body using `{{variable}}` for dynamic fields
6. Submit → Wait 1–2 business days for review

**Template example — `credentials_delivered`:**
```
🛡️ Your Bunche proxies are ready!

📋 Order ID: {{1}}
👤 Username: {{2}}
🔐 Password: {{3}}
🌐 Protocol: SOCKS5
📍 Proxy: Bunche.ng:1080

⚡ Setup guide: styxproxy.com/setup
📅 Expires: {{4}}

Need help? Just reply here!
```

---

## Customer Bot Flow (WhatsApp)

### Flow 1: New Customer Discovery

```
Customer finds Bunche on WhatsApp (number shared on website/social)
         ↓
Customer sends: "Hi" or "Hello"
         ↓
[24h session window OPEN]
         ↓
Bot: "👋 Welcome to Bunche Digital!
We're Nigeria's most trusted proxy provider.

🌍 ISP, Datacenter, Residential & Mobile 4G proxies
⚡ Instant delivery • 24/7 support

What would you like to do?
1. 📦 Browse Products
2. 🛒 Place Order
3. ❓ Help / FAQ
4. 💬 Talk to an Operator"
```

### Flow 2: Order → Payment → Delivery

```
Customer: "I want to buy ISP UK Clean"
         ↓
Bot: "🇬🇧 ISP UK Clean — Gecko (Scamalytics 0)
💰 ₦6,500 for 30 days
📦 1 IP minimum

How do you want to pay?
[List: Bank Transfer / Card/Flutterwave]"
         ↓
Customer selects
         ↓
[If Bank Transfer] → Bot sends account details
[If Card] → Bot sends Flutterwave payment link
         ↓
[Webhook: charge.completed]
         ↓
Bot sends (within 24h session):
✅ Payment Received!
🛡️ Your proxies:
👤 Username: bun_ayomide7
🔐 Password: [generated]
🌐 Proxy: Bunche.ng:1080
📅 Expires: July 31, 2026
```

---

## Session Management in n8n

```python
# n8n — Check if within 24h session window

1. When inbound WhatsApp message received:
   Extract: from (customer's wa_id), timestamp

2. Calculate window:
   session_end = message_timestamp + (24 * 60 * 60)
   now = current_timestamp

3. If now < session_end:
   → Within session. Use "WhatsApp Send Message" node (no template)

4. If now >= session_end:
   → Session closed. Use "WhatsApp Send Template Message" node
```

---

## Rate Limits (WhatsApp Business API)

| Limit Type | Value |
|--|--|
| **Outbound template messages** | 1,000 per hour per phone number |
| **Template message sends** | Must be approved first |
| **Phone number verification** | 10 attempts per hour |

---

## Phone Number Format

Nigerian numbers use E.164 format:
```
+234 703 298 1049  (with +)
wa_id: 2347032981049  (without +)
```

---

## Setup Checklist

- [ ] Create Meta Business Account (business.facebook.com)
- [ ] Verify business domain ownership (styxproxy.com)
- [ ] Create WhatsApp Business App (developers.facebook.com)
- [ ] Add dedicated phone number (+234...)
- [ ] Submit for Business Verification (2–10 days) or use Twilio sandbox
- [ ] Get Access Token and Phone Number ID
- [ ] Configure webhook URL in Meta Console
- [ ] Create required message templates and get approved
- [ ] Configure n8n WhatsApp trigger with Access Token
- [ ] Test inbound → outbound flow end-to-end
