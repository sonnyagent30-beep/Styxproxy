# Styxproxy Architecture

**Last updated:** 2026-08-20

## What this is

Styxproxy is a WhatsApp + Telegram proxy reseller. The product is a backend API plus
a web admin dashboard, with n8n workflows orchestrating customer chat on the
messaging channels. There is one Python/FastAPI backend. There is one PostgreSQL
database. There is one source of truth for everything business-critical
(prices, plans, customer state, orders, refunds, trials). The admin dashboard,
the n8n workflows, and the messaging channels all hit that one backend.

```
                                    ┌─────────────────────────┐
                                    │  Admin Dashboard (web)  │
                                    │  - sets prices          │
                                    │  - manages customers    │
                                    │  - handles refunds      │
                                    └────────────┬────────────┘
                                                 │
                                                 │ reads/writes
                                                 ▼
   ┌─────────────┐                  ┌─────────────────────────┐
   │  Customer   │── WhatsApp ───▶  │                         │
   │  phone      │                  │   FastAPI Backend       │
   │             │── Telegram ──▶   │   (single service)      │
   └─────────────┘                  │                         │
        ▲                           │  ┌─────────────────┐   │
        │                           │  │  PostgreSQL DB  │   │
        │                           │  │  - plans        │   │
        │ WhatsApp /                │  │  - prices       │   │
        │ Telegram reply            │  │  - customers    │   │
        │                           │  │  - orders       │   │
        │                           │  │  - refunds      │   │
        │                           │  │  - trials       │   │
        │                           │  └─────────────────┘   │
        │                           │                         │
        │                           │  ┌─────────────────┐   │
        │                           │  │  Charon LLM     │   │
        │                           │  │  module         │   │
        │                           │  │  (in-process)   │   │
        │                           │  └─────────────────┘   │
        │                           └────────────┬────────────┘
        │                                        │
        │                                        ▲
        │                                        │
   ┌────┴────────┐                               │
   │   n8n       │───────────────────────────────┘
   │  workflows  │   POST /api/orders, /api/refunds, etc.
   │             │   POST /api/charon/chat
   │ - WhatsApp  │
   │   flow      │
   │ - Telegram  │
   │   flow      │
   │ - admin     │
   │   commands  │
   │ - alerts    │
   └─────────────┘
       ▲
       │ webhook POST
       │
   ┌───┴────────────┐
   │  Flutterwave   │  payment webhooks
   │  WhatsApp BA   │  incoming messages
   │  Telegram Bot  │  incoming messages
   │  Theorem Reach │  affiliate postbacks
   └────────────────┘
```

## Single source of truth

**PostgreSQL is the only place prices and plan settings live.** There is no
separate pricing service, no charon-owned config, no n8n-owned config.

- The admin dashboard (web) reads/writes via `GET/PUT /api/admin/plans/...`
- The web catalog (`/api/catalog`) reads the same tables
- n8n workflows read prices via `GET /api/catalog` (same endpoint the web uses)
- n8n workflows never write prices directly

**Charon is an in-process LLM module inside the FastAPI backend.** It does not
run as a separate service. It does not own data. It is called via internal
Python functions from the backend, and via `POST /api/charon/chat` from n8n and
the web widget.

When n8n needs an LLM response for a customer message, it calls charon over
HTTP the same way the web chat widget does. Same endpoint, same context, same
behavior.

## Components

| Component | Where it runs | Responsibility |
|---|---|---|
| FastAPI backend | VPS (162.35.184.69), 4 uvicorn workers | All business logic + DB access + charon LLM |
| PostgreSQL 16 | VPS | All persistent state (plans, customers, orders, n8n tables) |
| Redis (prod) | VPS, port 6379 | Celery broker, app cache |
| Redis (n8n) | VPS, port 6380 | n8n queue + memory store |
| n8n 1.123.73 | Docker container `styxproxy-n8n` on VPS | Workflow orchestration for messaging channels |
| Admin dashboard | Vercel (`styxproxy.com` or staging variant) | React/Next.js UI for staff |
| Customer-facing site | Vercel | Marketing + checkout |

## Why n8n exists

n8n is the integration layer for things that already speak HTTP but don't fit
cleanly into the web backend:

- WhatsApp Business API incoming webhooks → workflow → reply
- Telegram bot incoming messages → workflow → reply
- Flutterwave payment confirmations → workflow → fulfill order
- Theorem Reach affiliate postbacks → workflow → record conversion
- Cron triggers (daily summary, data alerts, expiry reminders)

n8n **does not own business state.** Every action a workflow takes goes through
the FastAPI backend via authenticated HTTP calls. n8n's PostgreSQL tables store
workflow definitions and execution history only.

## n8n ↔ backend auth

n8n uses a service API key (`service_api_keys` table, hashed with bcrypt). The
backend's `verify_service_key` dependency accepts the key as `Authorization:
Bearer <key>`. The key has scoped permissions (e.g. `catalog:read orders:write
refunds:write trials:write`) — not superuser.

## Why this matters

The previous instinct (build a separate "charon API v1", build a separate admin
price editor in n8n, make charon its own service) would have introduced three
sources of truth for the same data. This document locks in the simpler model:
one backend, one DB, thin clients that read what they need and write what they're
allowed to.

## More detail

- Backend code: `/opt/styxproxy/backend/app/` (also at `/root/Styxproxy/backend/`)
- Database schema: `backend/alembic/versions/`
- API surface for n8n: `backend/app/api/charon_*.py`, `backend/app/api/customer_*.py`,
  `backend/app/api/admin_*.py`
- n8n workflows: `/.n8n/workflows/`
- Webhook routing: nginx port 5679 → n8n port 5678 (only loopback can reach 5678 directly)
