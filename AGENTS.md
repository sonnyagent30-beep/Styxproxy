# Bunche — Agents

**Last Updated:** 2026-06-26

This file documents the agent system for Bunche — what each agent touches, what it must not change, failure modes, and what needs human approval.

---

## System Overview

Bunche is an n8n-based WhatsApp proxy reseller. There are no separate deployed agents — n8n workflows handle all automation. This file exists for the case where sub-agents (via Hermes) are used to build or modify Bunche.

---

## Agents That Touch Bunche

### Sonny (this agent)
- **What it touches:** Everything — docs, workflows, GitHub, deploy scripts, configs
- **Constraints:**
  - Never commit secrets or real credentials
  - Never push to main without review (PR-based workflow)
  - DATAIMPULSE_API_KEY and PROXY_SELLER_API_KEY are sensitive — never log or include in docs
- **Failure modes:**
  - GitHub push auth fails if SSH key not set up → use MCP GitHub tools instead
  - Branch conflicts → always branch before editing

---

## Workflow Templates (`.n8n/workflows/`)

The actual n8n JSON workflow files live here. These are the build artifacts — not just docs.

| Workflow | File | Trigger | Status |
|----------|------|---------|--------|
| Order Handler | `order-handler.json` | WhatsApp webhook | TODO |
| Payment Confirmation | `payment-confirmation.json` | Flutterwave webhook | TODO |
| Refund Handler | `refund-handler.json` | Flutterwave webhook | TODO |
| Admin Command Handler | `admin-handler.json` | WhatsApp (admin only) | TODO |
| Ban Claim | `ban-claim.json` | WhatsApp (manual) | TODO |
| Free Trial | `free-trial.json` | WhatsApp | TODO |
| Daily Summary | `daily-summary.json` | Cron (23:55) | TODO |
| Data Alert Escalation | `data-alert.json` | Cron (15 min) | TODO |
| Referral Credit | `referral-credit.json` | Sub-workflow | TODO |

**These files do not exist yet.** They need to be built from `workflows/WORKFLOW_SPECS.md`.

---

## What Not To Change

| File | Why |
|------|-----|
| `legal/TERMS_OF_SERVICE.md` | Legal document — changes need legal review |
| `legal/PRIVACY_POLICY.md` | Legal document — changes need legal review |
| `legal/ACCEPTABLE_USE_POLICY.md` | Legal document — changes need legal review |
| `docs/DATABASE_SCHEMA.md` | Changing the schema mid-flight breaks existing orders |

---

## What Needs Human Approval

| Change | Why |
|--------|-----|
| Any change to `legal/` | Legal documents |
| Changing product prices | Business impact |
| Adding a new provider | Requires API integration + testing |
| Changing commission/referral percentages | Business impact |
| Modifying admin PIN or TOTP setup | Security-critical |
| Refund policy changes | Business impact |

---

## Failure Modes

| Scenario | Behavior |
|----------|----------|
| n8n workflow fails | n8n Error Trigger → WhatsApp alert to admin |
| Provider API down | Workflow logs error + retries. Auto-refund if 3 consecutive failures. |
| Flutterwave webhook fails | n8n idempotency key prevents duplicate processing |
| WhatsApp webhook fails | Signature verification rejects invalid payloads |
| PostgreSQL down | n8n workflow fails → error alert → admin notified |
| MiniMax API fails | n8n retries with exponential backoff. Fallback: structured error message to customer. |

---

## Build Order

When building Bunche from scratch:

1. Set up VPS + Docker + PostgreSQL + Redis
2. Set up domain + SSL + Nginx
3. Deploy n8n via Docker Compose
4. Import workflow JSONs from `.n8n/workflows/`
5. Configure webhooks (Flutterwave + WhatsApp)
6. Configure env vars (`.env.example` → `.env`)
7. Test with sandbox accounts first
8. Go live

See `docs/DEPLOYMENT.md` for the full step-by-step.

---

## Environment Variables Reference

All env vars documented in `.env.example`. Critical ones:

| Variable | Sensitivity | Notes |
|----------|------------|-------|
| `FLUTTERWAVE_SECRET_KEY` | 🔴 HIGH | Payment processing — never expose |
| `PROXY_SELLER_API_KEY` | 🔴 HIGH | Provider access — never expose |
| `DATAIMPULSE_API_KEY` | 🔴 HIGH | Provider access — never expose |
| `ADMIN_PIN_HASH` | 🔴 HIGH | bcrypt hash only — never store plain PIN |
| `TOTP_ENCRYPTION_KEY` | 🔴 HIGH | Encrypts 2FA secrets |
| `WHATSAPP_ACCESS_TOKEN` | 🟡 MEDIUM | WhatsApp API access |
| `MINIMAX_API_KEY` | 🟡 MEDIUM | LLM — cost implications |

---

## Current Architecture

```
WhatsApp → Cloudflare → Nginx → n8n (Docker)
                                      ↓
                               PostgreSQL + Redis
                                      ↓
                               MiniMax M2 API
                                      ↓
                        Proxy-Seller / DataImpulse APIs
```

See `docs/ARCHITECTURE_PLAN.md` for full details.
