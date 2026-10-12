# DNS + Vercel Deployment Inventory

**Generated:** 2026-07-28 18:25 UTC
**Author:** Sonny's audit (commit fd3bd9e context)

This document captures the actual live state of DNS, Vercel projects, and
hosting for `styxproxy.com` and friends — replacing the vague
"Move api off bunche-api-push Vercel project" Notion ticket.

## The actual story (high-level)

| Layer           | Where it lives                  | Status |
|-----------------|---------------------------------|--------|
| DNS zone (NS)   | Cloudflare (Dannion manages)    | Healthy |
| Frontend (apex) | styxproxy.com -> Vercel project | Live |
| Frontend (www)  | CNAME -> bunche-api-push.vercel.app | Works (legacy alias) |
| API             | api.styxproxy.com -> 162.35.184.69 (Interserver) | Live, no Vercel involvement |

**The API never lived on Vercel.** The `bunche-api-push` Vercel project
hosts the **frontend** SPA — the name is a pre-rename artifact, not a
hosting concern.

## Vercel projects observed via HTTP probing

| Hostname                          | HTTP status | What it serves                                      |
|-----------------------------------|-------------|-----------------------------------------------------|
| `styxproxy.com` (apex)            | 200         | Live Next.js SPA (the Styxproxy homepage)           |
| `www.styxproxy.com`               | (via CNAME) | Same as apex                                        |
| `bunche-api-push.vercel.app`      | 200         | Vercel catch-all proxy for the SPA                  |
| `styxproxy-api-push.vercel.app`   | 404 DEPLOYMENT_NOT_FOUND | Dead; already removed from CORS_ORIGINS |
| `styxproxy-bunche.vercel.app`     | (no DNS)    | Never existed (placeholder guess)                   |

## Why the Notion ticket asked for "api off Vercel"

The original ticket framing assumed `bunche-api-push` was an API hosting
project. It was — until **the Interserver migration** (Sprint 24 in this
Notion queue). After that migration:

- `api.styxproxy.com` resolves to `162.35.184.69` (Interserver)
- The `bunche-api-push` Vercel project **only** hosts the Next.js SPA
- All API traffic goes nginx (Interserver :443) -> uvicorn :8000

The migration is complete. The ticket should close.

## What still needs a Vercel-side action (optional, cosmetic)

A cleaner deployment would rename `bunche-api-push` to `styxproxy-frontend`.
This involves:

1. Vercel CLI login (token in `~/.vercel/auth.json`, currently absent)
2. Create new project `styxproxy-frontend` with same git context
3. Add apex `styxproxy.com` and `www.styxproxy.com` domains to new project
4. Wait for DNS to switch over (Vercel auto-issues LE certs)
5. Decommission `bunche-api-push`

This is **irreversible** in the sense that:
- DNS cuts (even with low TTL) propagate globally in <60s
- LE certs only re-issue if the new project already has the domain

Recommend running it in a 30-minute window with low traffic, after Dannion
explicitly approves. Not blocking on this — the current name works.

## DNS records (Cloudflare dashboard)

We cannot pull the live zone file without API token. Approximate:

| Type  | Name | Value                                         |
|-------|------|-----------------------------------------------|
| A     | @    | 76.76.21.21 (Vercel anycast)                  |
| CNAME | www  | bunche-api-push.vercel.app.                   |
| A     | api  | 162.35.184.69 (Interserver)                   |

## Cross-reference

- RUNBOOKS.md §10: DNS cutover procedure for migrating in the future
- Apollo skill: `dns-cutover-checklist.md` if it exists
- Notion callout `3abb7766-13fa-81bc-9ccf-ce2bf0aece1e`: Sprint 11 closure
