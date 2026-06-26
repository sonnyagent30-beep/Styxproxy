# Proxy Platform — Build Package
*Model B: WhatsApp Reseller — Nigerian Market*
*Ready to deploy the moment n8n platform is available*

---

## What We Are Building

A fully automated WhatsApp-based proxy resale platform for the Nigerian market.
- **Core product:** ISP proxies (static, recurring monthly)
- **Other products:** Residential, Mobile, Datacenter proxies
- **Interface:** WhatsApp Business API (customers message to order)
- **Automation:** n8n workflow engine (VPS: self-hosted)
- **Payments:** Flutterwave (NGN, transfer, card, USSD, QR)
- **Database:** Google Sheets (Orders, Inventory, Customers, Providers)
- **Margin:** 150–300% on all products

---

## The Stack at a Glance

```
Customer WhatsApp
       ↓
WhatsApp Business Cloud API (Meta)
       ↓
n8n Workflow Engine (VPS: self-hosted)
       ↓
┌──────────────────┬──────────────────┬──────────────────┐
│  Google Sheets  │   Flutterwave    │  Provider APIs   │
│  Orders/Inventory│  Payment Webhook │  Bright Data    │
│  /Customers/Prov │  Confirm + Collect│  Oxylabs        │
└──────────────────┴──────────────────┴──────────────────┘
       ↓
WhatsApp delivery to customer (proxy credentials)
```

---

## Infrastructure Required

### VPS (Server to Run Everything)
| Item | Specification |
|------|-------------|
| Provider | Hetzner, DigitalOcean, or AWS Lightsail |
| OS | Ubuntu 22.04 LTS or 24.04 LTS |
| vCPU | 2 vCPU |
| RAM | 4 GB |
| Storage | 50 GB SSD |
| Bandwidth | Unmetered or ≥ 2 TB/month |
| Static IP | 1 IPv4 (required for WhatsApp webhook) |
| Cost | USD 10–20/month |
| Access | SSH (key-based auth, password disabled) |

**Firewall (UFW) — open ports:**
```
22/tcp   (SSH)
80/tcp   (HTTP — Let's Encrypt)
443/tcp  (HTTPS — n8n UI + webhooks)
5678/tcp (n8n web interface — restrict to your IP)
```

### Domain Name
| Item | Notes |
|------|-------|
| Registrar | Namecheap, Cloudflare, or any registrar |
| Domain | e.g., `bunche.ng` or `bunche.com` |
| Purpose | n8n UI, webhook URLs, landing page |
| Cost | USD 10–15/year |
| DNS | A record pointing to VPS static IP |

---

## Tools & Accounts Needed

See `TOOLS_CHECKLIST.md` for the full checklist with what to get, where, and approximate cost.

### Critical Accounts (must have before building)

| # | Tool/Account | Purpose | Get it at |
|---|-------------|---------|-----------|
| 1 | **VPS** | Host n8n | Hetzner Cloud / DigitalOcean |
| 2 | **Domain name** | n8n URL + webhooks | Namecheap / Cloudflare |
| 3 | **Flutterwave account** | Naira payments | flutterwave.com |
| 4 | **WhatsApp Business API** | Customer messaging | business.whatsapp.com |
| 5 | **Google account** | Sheets database | drive.google.com |
| 6 | **n8n** | Automation engine | n8n.io (self-hosted) |
| 7 | **Provider API accounts** | Proxy supply | See below |

### Provider API Accounts (Proxy Supply)

| Provider | Best For | Sign Up | Wholesale Cost |
|----------|---------|---------|---------------|
| **IPRoyal** | ISP + Residential | iproyal.com | ~$7-10/IP/month |
| **NodeMaven** | Residential + ISP | nodemaven.com | ~$8-12/IP/month |
| **Proxy-Seller** | ISP + DC + Mobile | proxy-seller.com | ~$5-8/IP/month |
| **Bright Data** (backup) | All types, premium | brightdata.com | ~$15-20/IP/month |
| **Oxylabs** (backup) | All types, enterprise | oxylabs.io | ~$15-20/IP/month |

**Start with:** IPRoyal (best price-to-quality for Nigerian market)

---

## Google Sheets Setup

Four sheets needed. See `GOOGLE_SHEETS_SETUP.md` for full column-by-column templates.

### Sheet 1: Orders
| Column | Type | Notes |
|--------|------|-------|
| Order ID | Text | Format: ORD-2026-XXXXX |
| Customer Phone | Text | Nigeria format: 234xxxxxxxxx |
| Plan | Text | ISP-NG, ISP-UK, ISP-US, RES-5GB, etc. |
| Quantity | Number | Number of proxies or GB |
| Amount (NGN) | Number | Total price in Naira |
| Payment Status | Text | pending / paid / failed / refunded |
| Payment Reference | Text | Flutterwave tx_ref |
| Proxy Details | Text | Delivered credentials (IP:Port:User:Pass) |
| Created At | DateTime | |
| Paid At | DateTime | |
| Fulfilled At | DateTime | |

### Sheet 2: Inventory
| Column | Type | Notes |
|--------|------|-------|
| Provider | Text | IPRoyal, NodeMaven, etc. |
| Proxy Type | Text | ISP, Residential, Mobile, DC |
| Country | Text | NG, US, UK, DE, etc. |
| Quantity Available | Number | In stock |
| Cost Price (USD) | Number | Wholesale cost |
| Retail Price (NGN) | Number | Selling price |
| Last Updated | DateTime | |

### Sheet 3: Customers
| Column | Type | Notes |
|--------|------|-------|
| Phone | Text | Primary key |
| Name | Text | If captured |
| Total Orders | Number | |
| Lifetime Value (NGN) | Number | |
| Support Notes | Text | |
| Blocked | Boolean | TRUE = blocked |
| Blocked Reason | Text | Why blocked |
| Created At | DateTime | |

### Sheet 4: Providers
| Column | Type | Notes |
|--------|------|-------|
| Provider Name | Text | Primary key |
| API Key | Text | Stored in n8n credentials, not here |
| Base URL | Text | API endpoint |
| Account Status | Text | active / suspended / depleted |
| Balance (USD) | Number | Credit remaining |
| Account Manager | Text | Contact if issues |
| Notes | Text | |

---

## n8n Workflows to Build

Four workflows cover the entire order-to-delivery cycle.

See `workflows/WORKFLOW_SPECS.md` for full step-by-step specifications.

### Workflow 1: Order Handler (Incoming WhatsApp)
```
Trigger: WhatsApp webhook (incoming message)
↓
Parse message (detect: proxy type, country, quantity)
↓
Validate command against inventory
↓
Look up customer in Google Sheets (check if blocked)
↓
Calculate price
↓
Generate Flutterwave payment link
↓
Send payment link via WhatsApp
↓
Create order row in Google Sheets (status: pending)
```

### Workflow 2: Payment Confirmation (Flutterwave Webhook)
```
Trigger: Flutterwave webhook (payment.completed)
↓
Verify Flutterwave-Signature header
↓
Look up tx_ref in Google Sheets Orders
↓
If successful:
  → Update order status = "paid"
  → Call Provider API to generate proxies
  → Receive proxy credentials
  → Send credentials via WhatsApp
  → Update order status = "fulfilled"
  → Deduct from Inventory
  → Add/update customer in Customers sheet
If failed:
  → Update order status = "failed"
  → Notify customer via WhatsApp
```

### Workflow 3: Proxy Fulfillment
```
Called by Workflow 2 after payment confirmed
↓
Select provider based on product type + country
↓
Call provider API:
  POST /proxies/buy
  { country, quantity, type }
↓
Parse response (IP:Port:Username:Password)
↓
Format delivery message
↓
Send via WhatsApp to customer
↓
Update Google Sheets
```

### Workflow 4: Refund Handler
```
Trigger: Flutterwave webhook (refund.initiated)
↓
Verify signature
↓
Look up order
↓
Call provider API to revoke proxy access
↓
Update order status = "refunded"
↓
Send WhatsApp confirmation to customer
```

---

## Legal Documents

Three documents needed before launch. All drafted in `legal/` directory.

| Document | File | Purpose |
|----------|------|---------|
| Terms of Service | `TERMS_OF_SERVICE.md` | Governs use of the platform |
| Privacy Policy | `PRIVACY_POLICY.md` | GDPR/NDPR compliant data policy |
| Acceptable Use Policy | `ACCEPTABLE_USE_POLICY.md` | What customers cannot do with proxies |

---

## Pricing Reference

### Retail Prices

| Product | Retail (NGN) | Wholesale (USD) | Margin |
|---------|-------------|----------------|--------|
| ISP Proxy UK (1 IP, monthly) | ₦18,000–22,000 | $7 | 150–157% |
| ISP Proxy US (1 IP, monthly) | ₦20,000–28,000 | $8 | 133–200% |
| ISP Proxy NG (1 IP, monthly) | ₦8,000–12,000 | $5 | 100–150% |
| Residential 5GB | ₦8,000–12,000 | $30/5GB | — |
| Mobile 4G (monthly) | ₦15,000–30,000 | ~$10 | 100–200% |
| Datacenter (monthly) | ₦3,000–8,000 | ~$3 | 100–167% |

---

## Step-by-Step Build Sequence

### Week 1: Infrastructure Setup
- [ ] Spin up VPS on Hetzner/DigitalOcean
- [ ] Point domain to VPS
- [ ] Install Docker + Docker Compose
- [ ] Deploy n8n via Docker
- [ ] Configure Nginx reverse proxy
- [ ] Get SSL via Let's Encrypt
- [ ] Harden SSH (key-only, change port, Fail2Ban)
- [ ] Test n8n is accessible at `https://n8n.yourdomain.com`

### Week 2: Accounts & APIs
- [ ] Create Flutterwave merchant account
- [ ] Create WhatsApp Business API app
- [ ] Set up Google Sheets (4 sheets)
- [ ] Create Google Cloud service account for Sheets API
- [ ] Open IPRoyal / NodeMaven / Proxy-Seller accounts
- [ ] Fund provider accounts (~$50-100 starting credit)
- [ ] Test provider API → generate a test proxy manually

### Week 3: n8n Workflows
- [ ] Workflow 1: Order Handler (parse messages, generate payment link)
- [ ] Workflow 2: Payment Confirmation (webhook, verify, fulfill)
- [ ] Workflow 3: Proxy Fulfillment (call provider API, deliver)
- [ ] Workflow 4: Refund Handler
- [ ] Test all 4 workflows with test payments
- [ ] Set up n8n error workflow (alert you on failure)

### Week 4: Legal + Launch Prep
- [ ] Deploy Terms of Service (public URL)
- [ ] Deploy Privacy Policy
- [ ] Deploy Acceptable Use Policy
- [ ] CAC registration (Nigerian business name)
- [ ] Create WhatsApp Business profile
- [ ] Set up Telegram community (optional)
- [ ] Test full order-to-delivery with real test payment
- [ ] Soft launch: 5–10 trusted test customers

---

## Key Files in This Package

```
Bunche/
├── docs/
│   ├── BUILD_PACKAGE.md          ← This file — full build reference
│   ├── TOOLS_CHECKLIST.md        ← What to get, where, cost
│   ├── GOOGLE_SHEETS_SETUP.md   ← Full sheet templates
│   ├── FLUTTERWAVE_WHATSAPP_SETUP.md
│   ├── PROVIDER_SETUP_GUIDE.md
│   └── OPERATIONAL_RUNBOOK.md    ← Daily/weekly ops guide
├── workflows/
│   └── WORKFLOW_SPECS.md         ← Full n8n workflow step-by-step
├── legal/
│   ├── TERMS_OF_SERVICE.md       ← ToS draft
│   ├── PRIVACY_POLICY.md         ← Privacy policy draft
│   └── ACCEPTABLE_USE_POLICY.md  ← AUP draft
└── README.md
```

---

*Ready to build. Get the tools listed in TOOLS_CHECKLIST.md and we begin.*
