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
Flutterwave webhook → Bunche buys IP from provider → tests it
        ↓
Bunche issues Bunche-branded credentials (proxy1.bunche.ng:1080)
        ↓
Credentials delivered on WhatsApp (< 2 min)
```

**Key difference:** Customers receive Bunche-branded proxy credentials, not direct provider credentials. Bunche controls the auth layer — enabling instant revoke on refund and free trial recycling.

---

## Products

| Product | Price | Provider | Tracking |
|---------|-------|----------|----------|
| ISP (UK/US/DE/FR/CA) | ₦6,500/mo | Vetted partner | Expires on date |
| ISP (JP/AU/BR/SG/KR) | ₦7,500/mo | Vetted partner | Expires on date |
| Residential 5GB | ₦9,500 | Vetted partner | No time expiry — lasts until GB used |
| Residential 10GB | ₦18,000 | Vetted partner | No time expiry |
| Mobile 4G 5GB | ₦20,000 | Vetted partner | 30-day window to use GB |
| Mobile 4G 10GB | ₦38,000 | Vetted partner | 30-day window to use GB |
| Datacenter | ₦3,000/mo | Vetted partner | Expires on date |

*Infrastructure partners are not publicly named per our Privacy Policy.*

---

## Bunche Auth Layer

All customers receive Bunche-branded credentials. The actual proxy IPs are sourced from vetted infrastructure partners but customers interact only with Bunche.

```
Customer sees:   proxy1.bunche.ng:1080
                 username: bun_001
                 password: P@ssw0rd!
                        │
                        ▼
              Bunche Dante SOCKS5 Server (Hetzner)
                        │
              Maps Bunche username → Provider IP
                        │
                        ▼
            Vetted infrastructure partners
            (Proxy-Seller / DataImpulse)
```

**Benefits:**
- Instant credential revoke on refund
- Free trial IPs recycled after 2hr expiry
- Customers never see provider names
- Full control over access

---

## Architecture

```
WhatsApp → Cloudflare → Nginx → n8n (Docker on VPS)
                                      ↓
                               PostgreSQL + Redis
                                      ↓
                               Dante SOCKS5 (Port 1080)
                                      ↓
                          Vetted Infrastructure Partners
                          (Proxy-Seller / DataImpulse)
```

- **n8n**: Workflow engine (15 workflows documented)
- **PostgreSQL**: Customers, orders, audit logs, bunche_credentials
- **Redis**: Caching, sessions, rate limiting
- **Dante SOCKS5**: Proxy auth layer — maps Bunche credentials to provider IPs
- **MiniMax M2**: LLM for intent parsing and responses
- **Flutterwave**: Payment processing
- **Cloudflare R2**: File storage (screenshots, receipts, backups)
- **UptimeRobot**: Uptime monitoring (5-min checks)

---

## Docs

### Setup + Build

| File | What it covers |
|------|---------------|
| `docs/DEPLOYMENT.md` | Full VPS deployment guide (steps 1–12) |
| `docs/ARCHITECTURE_PLAN.md` | System architecture with Dante layer |
| `docs/DATABASE_SCHEMA.md` | PostgreSQL schema including bunche_credentials |
| `docs/DANTE_SETUP.md` | Dante SOCKS5 installation and configuration |
| `.env.example` | Every environment variable documented |

### Operational

| File | What it covers |
|------|---------------|
| `docs/MONITORING.md` | UptimeRobot setup, alert webhook |
| `docs/SECURITY_RUNBOOK.md` | Secrets rotation, API monitoring, NDPA, incident response |
| `docs/PERFORMANCE_SCALING.md` | pgBouncer, Redis caching, 4-phase cost trajectory |
| `docs/PRICING_INTELLIGENCE.md` | Buy price, sell price, margins, FX analysis |
| `docs/FLUTTERWAVE_WHATSAPP_SETUP.md` | Payment + messaging setup |

### Features

| File | What it covers |
|------|---------------|
| `docs/REFERRAL_SYSTEM.md` | Referral system spec (name = code, 5% credit) |
| `workflows/WORKFLOW_SPECS.md` | 15 workflows documented (orders, payments, alerts, referrals) |
| `scripts/manage-bunche-credentials.sh` | Dante credential management script |

### Architecture Decisions (ADRs)

| File | Decision |
|------|----------|
| `docs/adr/ADR-001-postgresql-primary-database.md` | PostgreSQL over Google Sheets |
| `docs/adr/ADR-002-minimax-m2-llm.md` | MiniMax M2 cloud over Ollama local |
| `docs/adr/ADR-003-name-as-referral-code.md` | Customer name = referral code |
| `docs/adr/ADR-004-secrets-management.md` | .env → Doppler → Vault phased approach |
| `docs/adr/ADR-005-backup-strategy.md` | Daily R2 backup + age encryption + 90-day retention |

### Legal

`legal/TERMS_OF_SERVICE.md` · `legal/PRIVACY_POLICY.md` · `legal/ACCEPTABLE_USE_POLICY.md`

---

## Workflow Templates

Actual n8n JSON workflows in `.n8n/workflows/`:

| Workflow | File |
|----------|------|
| Order Handler | `order-handler.json` |
| Payment Confirmation | `payment-confirmation.json` |
| Data Alert Escalation | `data-alert.json` |
| Referral Credit Processor | `referral-credit.json` |
| Daily Summary | `daily-summary.json` |
| Error Alert | `error-alert.json` |
| Theorem Reach Webhook | `theorem-reach-webhook.json` |

---

## Backup Scripts

Operational scripts in `scripts/`:

| Script | Purpose |
|--------|---------|
| `scripts/backup-bunche.sh` | Daily pg_dump → age encrypt → rclone to R2 |
| `scripts/backup-monthly-archive.sh` | First-of-month → 1-year retention |
| `scripts/manage-bunche-credentials.sh` | Add/revoke/rotate/list Bunche credentials in Dante |
| `scripts/backup.conf.example` | Config template |

---

## Total Cost of Operation (Phase 1)

| Component | Cost |
|-----------|------|
| Hetzner CX21 VPS | €6/mo (~$9) |
| Domain | ~$2/mo |
| Provider credits (Proxy-Seller + DataImpulse) | ~$50 one-time |
| Flutterwave fees | 1.5% of revenue (pass-through) |
| Cloudflare (free tier) | $0 |
| Cloudflare R2 (free tier + backups) | <$1/mo |
| UptimeRobot free | $0 |
| **Total fixed** | **~$12/mo** |
| **Cost per customer at 1,000 users** | **<$0.01** |

---

## Archive

Obsolete docs (Google Sheets era, old providers): `archive/`

---

## Status

- ✅ Research complete
- ✅ Strategy defined
- ✅ Architecture decided (PostgreSQL + MiniMax + Dante auth layer)
- ✅ Legal docs updated (provider-neutral branding)
- ✅ 15 workflows spec'd + 7 JSON templates ready
- ✅ ADRs for all major decisions (5 ADRs)
- ✅ Deployment guide + monitoring + backup scripts
- ✅ Pricing intelligence documented
- ✅ Dante SOCKS5 setup documented
- ✅ Credential management script created
- 🟡 VPS not yet provisioned
- 🟡 Flutterwave account setup
- 🟡 WhatsApp Business API setup
- 🟡 Provider accounts + API keys
- 🟡 Custom domain registered