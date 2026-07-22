# Styxproxy 🤝

**Anonymous proxy purchasing for the Nigerian market. Fully automated.**

Three ways to buy: website (instant), Telegram, or WhatsApp. No account needed on the website.

---

## The Three Channels

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   ┌──────────────┐   ┌─────────────┐   ┌──────────────────┐   │
│   │  styxproxy.com   │   │  Telegram   │   │    WhatsApp      │   │
│   │  (Instant)   │   │    Bot      │   │       Bot        │   │
│   │              │   │             │   │                  │   │
│   │ Pay → IP     │   │  Full       │   │  Full            │   │
│   │ No account   │   │  lifecycle  │   │  lifecycle       │   │
│   │ 100% anon    │   │  + support  │   │  + support       │   │
│   └──────────────┘   └─────────────┘   └──────────────────┘   │
│                                                                  │
│   Management Portal: styxproxy.com/manage — check, renew, complain  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Instant (Website) — Primary Path
- Select product → pay via Flutterwave → IP displayed on screen
- **No registration. No email required. No data collected.**
- Order number (tx_ref) is the only identifier

### Telegram + WhatsApp — Full Ordering + Support
- Order via chat → payment link → IP delivered in chat
- Free trial (chat only — Theorem Reach requires a postback URL)
- Full support: check status, renew, ban claims, questions

### Management Portal
- `styxproxy.com/manage` → enter tx_ref (no login)
- Check status, renew, report ban → redirects to Telegram or WhatsApp

---

## Products & Prices

| Product | Price | Details |
|---------|-------|---------|
| ISP UK | ₦6,500/mo | Stable, dedicated |
| ISP US | ₦6,500/mo | Stable, dedicated |
| ISP DE | ₦7,500/mo | Stable, dedicated |
| ISP Japan | ₦7,500/mo | Stable, dedicated |
| Datacenter | ₦2,500/mo | Budget-friendly |
| Residential 5GB | ₦5,000 | Data never expires |
| Residential 10GB | ₦9,000 | Data never expires |
| Mobile 4G 5GB | ₦20,000 | 30-day window to use data |
| Mobile 4G 10GB | ₦35,000 | 30-day window to use data |

---

## How Instant Works

```
Customer → styxproxy.com → Select product → Pay via Flutterwave
                                        ↓
                    Flutterwave generates tx_ref (= order number)
                                        ↓
                    Customer completes payment
                                        ↓
                    Flutterwave webhook → backend generates IP
                                        ↓
                    IP displayed on thank-you page
                                        ↓
                    Email receipt sent (optional)
```

**No account created. No customer data stored. Only the order record.**

---

## How Chat Ordering Works

```
Customer → Telegram/WhatsApp → "I want ISP UK"
        ↓
Styxproxy sends Flutterwave payment link
        ↓
Customer pays
        ↓
Webhook fires → IP generated → credentials delivered in chat
```

---

## Free Trial (Telegram + WhatsApp only)

```
Customer → "free trial"
        ↓
Styxproxy explains: complete Theorem Reach surveys → earn time
        ↓
Customer does surveys → postbacks recorded
        ↓
Customer says "done" (max 12 surveys)
        ↓
Trial credentials delivered → auto-expires after earned time

1 survey = 2 hours of trial
Max 12 surveys = 24 hours
```

---

## Styxproxy Auth Layer

Customers receive Styxproxy-branded credentials. Actual proxy IPs are sourced from vetted infrastructure partners but customers interact only with Styxproxy.

```
Customer sees:   proxy1.styxproxy.com:1080
Behind the scenes: actual provider IP → routed through Styxproxy auth
```

This enables instant revoke on refund and free trial recycling.

---

## Repository Structure

```
bunche/
├── SPEC.md                    ← Source of truth (product decisions)
├── PRE-BUILD-CHECKLIST.md     ← What to set up before coding
├── docs/
│   ├── ARCHITECTURE.md         ← Technical architecture + diagrams
│   ├── DATABASE_SCHEMA.md      ← PostgreSQL schema
│   └── legal/                  ← Terms, Privacy, AUP, Refund policies
├── .n8n/
│   └── workflows/              ← All n8n workflows (JSON)
├── server/
│   └── telegram-webhook-bridge.js  ← Express webhook bridge
├── scripts/
│   ├── manage-3proxy-trial.sh      ← Add/remove trial users
│   └── cleanup-3proxy-trials.sh    ← Expire old trials
├── scenarios/                 ← 93 numbered customer scenarios
└── intelligence/
    └── reports/              ← LLM council analysis
```

---

## Quick Links

| Resource | URL |
|----------|-----|
| Product Spec | `SPEC.md` |
| Pre-Build Checklist | `PRE-BUILD-CHECKLIST.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Database Schema | `docs/DATABASE_SCHEMA.md` |
| n8n Workflows | `.n8n/workflows/` |
| Scenarios | `scenarios/` |

---

## Status

**Planning complete. Ready for build.**

Credentials and accounts needed before coding begins — see `PRE-BUILD-CHECKLIST.md`.
