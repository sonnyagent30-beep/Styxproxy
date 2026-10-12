# Bunche — Build Package (Archived)
*This file is obsolete. Architecture has moved to PostgreSQL + MiniMax M2 + Redis. Kept for historical reference.*

---

## The Model

No proxy stock. No upfront investment in IPs.
- Customer pays first → you buy proxy via API → deliver
- Only costs you money when a customer has already paid you
- 220+ countries available via Proxy-Seller API alone

---

## How It Works

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

### Provider Accounts (Open First)
| Provider | Purpose | Sign Up | Initial Credit |
|----------|---------|---------|---------------|
| **Proxy-Seller** | ISP + Datacenter | proxy-seller.com | $20–30 |
| **DataImpulse** | Mobile 4G + Residential | dataimpulse.com | $15–20 |

**Total start-up cost: ~$65 in provider credits + ~$10–20/month VPS**

---

## Start-up Cost Summary

| Item | Cost |
|------|------|
| Proxy-Seller credit | $25 |
| DataImpulse credit | $15 |
| VPS (month 1) | $15 |
| Domain | $12 |
| **Total to launch** | **~$67** |

---

## Products & Pricing

| Product | Bunche Price | Cost to You | Profit/Sale |
|---------|-------------|------------|------------|
| ISP UK/US/DE/FR/CA | ₦6,500 | $2.50 | ~₦2,375 |
| ISP JP/AU/BR/SG | ₦7,500 | $3.00 | ~₦3,000 |
| Residential 5GB | ₦5,000 | $1.75 | ~₦2,125 |
| Mobile 4G 5GB | ₦20,000 | $10.00 | ~₦3,500 |
| Datacenter | ₦2,500 | $0.70 | ~₦1,350 |

*Exchange rate: ~₦1,380/USD*

---

## Architecture (Old — See docs/ARCHITECTURE_PLAN.md for Current)

Previous architecture used Google Sheets as the database.
Current architecture uses PostgreSQL + MiniMax M2 + Redis.
See `docs/ARCHITECTURE_PLAN.md` for the current system design.

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

## Key Files (Current)

```
bunche/
├── .env.example
├── README.md
├── docs/
│   ├── ARCHITECTURE_PLAN.md      ← current architecture
│   ├── DATABASE_SCHEMA.md         ← PostgreSQL schema
│   ├── DEPLOYMENT.md              ← deployment guide
│   ├── FLUTTERWAVE_WHATSAPP_SETUP.md
│   ├── SECURITY_PLAN.md
│   ├── REFERRAL_SYSTEM.md
│   └── OPERATIONAL_RUNBOOK.md
├── workflows/
│   └── WORKFLOW_SPECS.md          ← 15 workflows documented
├── legal/
│   ├── TERMS_OF_SERVICE.md
│   ├── PRIVACY_POLICY.md
│   └── ACCEPTABLE_USE_POLICY.md
└── archive/                       ← obsolete docs (this folder)
```

**This file was moved from `docs/BUILD_PACKAGE.md` on 2026-06-26.**
The architecture it describes (Google Sheets + Ollama) has been replaced.
