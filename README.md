# Bunche 🤝

**WhatsApp proxy reseller for the Nigerian market. Fully automated.**

Zero inventory. Zero upfront cost. Customer pays first → you buy proxy → deliver.

---

## How It Works

```
Customer messages "Order ISP UK 1" on WhatsApp
        ↓
Bunche sends Flutterwave payment link
        ↓
Customer pays ₦6,500
        ↓
Flutterwave webhook → Bunche calls provider API
        ↓
Proxy credentials delivered on WhatsApp (< 2 min)
```

---

## Products

| Product | Price | Provider | Tracking |
|---------|-------|----------|----------|
| ISP (UK/US/DE/FR/CA) | ₦6,500/mo | Proxy-Seller | Expires on date |
| ISP (JP/AU/BR/SG) | ₦7,500/mo | Proxy-Seller | Expires on date |
| Residential 5GB | ₦5,000 | DataImpulse | No time expiry — lasts until GB used |
| Residential 10GB | ₦9,000 | DataImpulse | No time expiry |
| Mobile 4G 5GB | ₦20,000 | DataImpulse | 30-day window to use GB |
| Mobile 4G 10GB | ₦35,000 | DataImpulse | 30-day window to use GB |
| Datacenter | ₦2,500/mo | Proxy-Seller | Expires on date |

---

## Architecture

```
WhatsApp → Cloudflare → Nginx → n8n → PostgreSQL + Redis
                                      ↓
                               MiniMax M2 (LLM)
                                      ↓
                          Proxy-Seller / DataImpulse API
```

- **n8n**: Workflow engine (Docker on VPS)
- **PostgreSQL**: Customers, orders, audit logs
- **Redis**: Caching, sessions, rate limiting
- **MiniMax M2**: LLM for intent parsing and responses
- **Flutterwave**: Payment processing
- **Cloudflare R2**: File storage (screenshots, receipts)

---

## Quick Start

1. Clone repo
2. Copy `.env.example` → `.env` and fill in values
3. Follow `docs/DEPLOYMENT.md` for full setup

---

## Docs

| File | What it covers |
|------|---------------|
| `docs/DEPLOYMENT.md` | Full VPS deployment guide |
| `docs/ARCHITECTURE_PLAN.md` | System architecture |
| `docs/DATABASE_SCHEMA.md` | PostgreSQL schema |
| `docs/SECURITY_PLAN.md` | Security implementation |
| `docs/REFERRAL_SYSTEM.md` | Referral system spec |
| `workflows/WORKFLOW_SPECS.md` | 15 workflows documented |

---

## Legal

- `legal/TERMS_OF_SERVICE.md`
- `legal/PRIVACY_POLICY.md`
- `legal/ACCEPTABLE_USE_POLICY.md`
