# Styxproxy — Region Routing Reference

**Status:** Living document
**Last Updated:** 2026-07-29

## What this document is

The single source of truth for **where each proxy type lives geographically** and **which relay handles each**.

## The three-proxy-types model

Styxproxy sells proxies in three mechanical categories:

| Category | IP type | Pricing | Customer use |
|---|---|---|---|
| **Rotating pool** | Residential, Mobile | Per GB (bandwidth) | Scraping, social automation, ad verification |
| **Static dedicated** | ISP, Datacenter | Per IP per month | Account management, sneaker bots, geo-locked browsing |
| **Free trial** | Datacenter | Free (time-bound) | Onboarding, sampling the product |

## Region routing table

When a customer connects to Styxproxy, they hit one of two relays: Interserver or Contabo. The relay routes to the upstream provider based on the customer's `styxproxy_relay_entries` row.

| Customer's plan | Customer enters via | Routes to upstream | Notes |
|---|---|---|---|
| **Residential US 5GB** | proxy.styxproxy.com:1080 (Interserver) | la.residential.rayobyte.com:8000 (LA) | US exit IP randomly chosen from pool |
| **Residential GB 5GB** | proxy.styxproxy.com:1080 (Interserver) | la.residential.rayobyte.com:8000 (LA) | GB exit IP from pool, password suffix `-country-GB` |
| **Mobile UK 2GB** | proxy.styxproxy.com:1080 (Interserver) | la.mobile.rayobyte.com:8000 (LA) | UK mobile carrier IP |
| **ISP US 1 IP** | proxy.styxproxy.com:1080 (Interserver) | 192.0.2.10:8080 (provider IP) | Static IP, no rotation |
| **Datacenter US 1 IP** | proxy.styxproxy.com:1080 (Interserver) | Direct (Interserver is the static IP) | Interserver's own datacenter IP |
| **Datacenter UK 1 IP** | proxy.styxproxy.com:1080 (Contabo) | Direct (Contabo is the static IP) | Contabo's own datacenter IP |
| **Free trial** | trial.styxproxy.com:8001-8100 (Contabo) | Direct (Contabo's trial IP pool) | Time-bound, 24h max |

## Where each relay lives

| Relay | Server | IP | Purpose |
|---|---|---|---|
| **Interserver relay** | Interserver 162.35.184.69 | 162.35.184.69 | US datacenter, ALL rotating (resi/mobile), US ISP |
| **Contabo relay** | Contabo 84.247.132.12 | 84.247.132.12 | UK datacenter, UK ISP, free trial pool |

Both relays use the **same Postgres database** (hosted on Interserver). The auth table is the same. Customer credentials work on either relay.

## Why two relays

Two reasons:

1. **Latency optimization.** A UK customer pinging Contabo gets <50ms. Pinging Interserver gets ~150ms. For per-IP-per-second scraping, that matters.
2. **Geographical representation.** Having a relay endpoint in each major region means we can serve customers worldwide without a single point of bottleneck.

For v1, only Interserver relay is deployed. Contabo relay is built in Sprint 10 and turned on when UK proxy SKUs ship.

## What's not here

- **Single-relay failover.** If Interserver goes down, the relay is down. v1 doesn't have failover.
- **Multi-region active-active.** v1 has one relay per region. v2 will add auto-failover.
- **Auth source choice.** v1 uses Postgres → auth.json file → gost. v2 will use Redis for instant updates.

## How a customer connects

The customer always uses ONE host: `proxy.styxproxy.com`. The DNS resolves to either Interserver (US) or Contabo (UK) based on the customer's plan.

For v1, we manually pick:
- Customer buys US Datacenter → DNS ping gives Interserver IP
- Customer buys UK Datacenter → DNS ping gives Contabo IP

Customers can override by using the IP directly:
- `proxy.styxproxy.com:1080` (CNAME → Interserver)
- `84.247.132.12:1080` (Contabo direct, for UK customers)

## Subscription tiers and their routing

| Tier | Region | Storage | Customer sees |
|---|---|---|---|
| USA Datacenter | US | Interserver static IP | proxy.styxproxy.com |
| UK Datacenter | UK | Contabo static IP | proxy.styxproxy.com (CNAME → Contabo) |
| USA ISP | US | Provider IP | proxy.styxproxy.com |
| UK ISP | UK | Provider IP | proxy.styxproxy.com |
| USA Residential 5GB | US | Rayobyte pool | proxy.styxproxy.com |
| Any Mobile | Global | Rayobyte pool | proxy.styxproxy.com |
| Free Trial | Global | Contabo trial pool | trial.styxproxy.com:8001-8100 |

## Customer-facing UX

The customer doesn't see any of this. They:
1. Pick a product on styxproxy.com
2. Pay
3. Get credentials
4. Connect to `proxy.styxproxy.com:1080` with their creds
5. Traffic exits through the right provider for the right type

The relay + backend handle all the routing invisibly.

## See Also

- [PAID_PROXY_RELAY.md](./PAID_PROXY_RELAY.md) — relay implementation details
- [TRIAL_PROXY_SETUP.md](./TRIAL_PROXY_SETUP.md) — trial pool setup
- [SPEC.md § Technical Architecture](./SPEC.md) — full product spec
- [RELAY_OPERATIONS.md](./RELAY_OPERATIONS.md) — operational runbook
