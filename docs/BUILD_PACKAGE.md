# Bunche — Build Package
*Zero-inventory, fully on-demand WhatsApp proxy reseller for the Nigerian market.*

---

## The Model

No proxy stock. No upfront investment in IPs.
- Customer pays first → you buy proxy via API → deliver
- Only costs you money when a customer has already paid you
- 220+ countries available via Proxy-Seller API alone

---

## How It Works

```
Customer messages "Order ISP UK 1" on WhatsApp
        ↓
n8n generates Flutterwave payment link → sent to customer
        ↓
Customer pays ₦6,500 via transfer/card/USSD
        ↓
Flutterwave webhook fires → n8n detects payment
        ↓
n8n calls Proxy-Seller API → generates UK ISP proxy
        ↓
Proxy credentials sent to customer on WhatsApp
        ↓
Entire process: under 2 minutes. Fully automated.
```

---

## Infrastructure

### VPS
| Spec | Detail |
|------|--------|
| Provider | Hetzner, DigitalOcean |
| OS | Ubuntu 22.04 LTS |
| vCPU | 2 |
| RAM | 4 GB |
| Cost | ~$10–20/month |

### Domain
| | |
|--|--|
| Purpose | n8n webhooks + UI |
| Cost | ~$10–15/year |

---

## Tools & Accounts Needed

### Must Have Before Building
| | Where | Cost |
|--|-------|------|
| VPS | Hetzner / DigitalOcean | ~$10–20/mo |
| Domain | Namecheap / Cloudflare | ~$10–15/yr |
| Flutterwave | rave.flutterwave.com | Free (1.5% per tx) |
| WhatsApp Business API | business.whatsapp.com | Free receive / ~$0.05 outbound |
| Google account | drive.google.com | Free |
| Google Cloud project | console.cloud.google.com | Free |

### Provider Accounts (Open First)
| Provider | Purpose | Sign Up | Initial Credit |
|----------|---------|---------|---------------|
| **Proxy-Seller** | ISP + Datacenter | proxy-seller.com | $20–30 |
| **OkeyProxy** | Residential | okeyproxy.com | $10–15 |
| **DataImpulse** | Mobile 4G | dataimpulse.com | $15–20 |

**Total start-up cost: ~$65 in provider credits + ~$10–20/month VPS**

---

## Start-up Cost Summary

| Item | Cost |
|------|------|
| Proxy-Seller credit | $25 |
| OkeyProxy credit | $10 |
| DataImpulse credit | $15 |
| VPS (month 1) | $15 |
| Domain | $12 |
| **Total to launch** | **~$77** |

---

## Products & Pricing

| Product | Bunche Price | Cost to You | Profit/Sale |
|---------|-------------|------------|------------|
| ISP UK/US/DE/FR/CA | ₦6,500 | $2.50 | ~₦2,375 |
| ISP JP/AU/BR/SG | ₦7,500 | $3.00 | ~₦3,000 |
| Residential 5GB | ₦5,000 | $1.75 | ~₦2,125 |
| Mobile 4G 5GB | ₦20,000 | $10.00 | ~₦3,500 |
| Datacenter | ₦2,500 | $0.70 | ~₦1,350 |

*Exchange rate: ~₦1,650/USD*

---

## Countries Available (220+ via API)

| Region | Countries |
|--------|-----------|
| Europe | UK, Germany, France, Netherlands, Italy, Spain, Poland, Sweden |
| North America | US, Canada, Mexico |
| Asia | Japan, Singapore, India, Hong Kong, South Korea |
| South America | Brazil, Argentina |
| Oceania | Australia |
| Africa | South Africa |

---

## Google Sheets (4 Tabs)

See `docs/GOOGLE_SHEETS_SETUP.md` for exact columns.

| Sheet | Purpose |
|-------|---------|
| `Pending_Orders` | Tracks every order from payment to delivery |
| `Customers` | Phone, name, order history, blocked status |
| `Providers` | Provider name, API status, balance |
| `Pricing` | Master price list — all products, all countries |

---

## n8n Workflows

See `workflows/WORKFLOW_SPECS.md` for full step-by-step.

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| Order Handler | WhatsApp webhook | Parse message → generate payment link |
| Payment Confirmation | Flutterwave webhook | Payment verified → call provider API |
| Refund Handler | Flutterwave webhook | Refund → revoke proxy |
| Error Alert | n8n Error Trigger | Alert you if anything fails |

---

## Step-by-Step Build

### Week 1: Infrastructure
- [ ] Spin up VPS (Hetzner/DO)
- [ ] Point domain to VPS IP
- [ ] Install Docker
- [ ] Deploy n8n via Docker
- [ ] Configure Nginx + SSL
- [ ] Test n8n at `https://n8n.yourdomain.com`

### Week 2: Accounts
- [ ] Flutterwave merchant account
- [ ] WhatsApp Business API (or Twilio WhatsApp)
- [ ] Google Sheets (4 tabs)
- [ ] Google Cloud service account
- [ ] Open all 3 provider accounts + fund

### Week 3: n8n Workflows
- [ ] Workflow 1: Order Handler
- [ ] Workflow 2: Payment Confirmation
- [ ] Workflow 3: Refund Handler
- [ ] Workflow 4: Error Alert
- [ ] Test everything end-to-end

### Week 4: Launch
- [ ] Deploy legal pages
- [ ] CAC registration (optional)
- [ ] WhatsApp Business profile set up
- [ ] Test with real payment
- [ ] Go live

---

## Key Files

```
bunche/
├── docs/
│   ├── BUILD_PACKAGE.md
│   ├── TOOLS_CHECKLIST.md
│   ├── GOOGLE_SHEETS_SETUP.md
│   ├── FLUTTERWAVE_WHATSAPP_SETUP.md
│   ├── PROVIDER_SETUP_GUIDE.md
│   └── OPERATIONAL_RUNBOOK.md
├── workflows/
│   └── WORKFLOW_SPECS.md
├── legal/
│   ├── TERMS_OF_SERVICE.md
│   ├── PRIVACY_POLICY.md
│   └── ACCEPTABLE_USE_POLICY.md
└── README.md
```
