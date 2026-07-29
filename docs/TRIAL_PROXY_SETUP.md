# Trial Proxy Setup — Contabo + 3proxy + socks-auth-proxy

**Last Updated:** 2026-07-29
**Purpose:** Document the free-trial proxy pool that runs on Contabo.

## What this is

The free trial is the **gateway into the paid product.** Customers earn time by completing surveys on Theorem Reach (1 survey = 2 hours, max 12 surveys = 24 hours). When they claim the trial, they receive a credential that gives them a temporary IP for the trial duration.

This is a **datacenter IP** — cheap, fast, and good enough for a trial. Not residential. Customers see `trial.styxproxy.com:8001` (or any port 8001–8100). The IP they get is one of our pre-allocated datacenter IPs.

## Architecture (the actual flow)

```
Customer →  trial.styxproxy.com:8001-8100
              ↓
     socks-auth-proxy on Contabo (auth gate)
              ↓
            verifies user is in /etc/dante/users.json
              ↓
            maps to a specific upstream IP (datacenter static IP)
              ↓
     danted on Contabo (SOCKS5 no-auth, port 1080)
              ↓
         forwards to that static IP
              ↓
     Customer's traffic exits through the assigned datacenter IP
```

The customer never sees the upstream IP. They see `trial.styxproxy.com`. The auth table is in `/etc/dante/users.json` on Contabo and is managed by the `control-api` service (also on Contabo).

## What's NOT here

This document is **specifically for the free trial**. It does NOT cover:

- **Paid residential proxies** — those go through [PAID_PROXY_RELAY.md](./PAID_PROXY_RELAY.md) on Interserver, using a different relay (gost + Postgres auth)
- **Paid mobile proxies** — same path as paid residential
- **Paid ISP proxies** — same relay, different upstream provider
- **Paid datacenter proxies** — same relay, but bypasses upstream provider (Contabo IS the static IP pool)

The two systems share the customer-facing principle (Styxproxy-only branding) but are technically separate:
- **Trials:** Contabo fleet, one IP per customer, time-bound
- **Paid:** Interserver relay, multiple providers behind, bandwidth or fixed-IP bound

## Why two separate systems

| Aspect | Trial (Contabo) | Paid (Interserver) |
|---|---|---|
| **Backend** | 3proxy + socks-auth-proxy | gost relay |
| **Auth storage** | `/etc/dante/users.json` file | Postgres `styxproxy_relay_entries` |
| **Hot reload** | file watcher + daemon | 30s sync from Postgres |
| **IP type** | Static datacenter | Resi pool / mobile / ISP / DC |
| **Termination** | Time-bound (24h max) | Bandwidth-bound or month-bound |
| **Customer cost** | Free | Paid (Flutterwave) |
| **Isolation** | One IP per trial | Multiple providers per customer |

The separation is intentional:
- Trial system is **low-volume, high-turnover** — file-based auth is fine
- Paid system is **high-volume, diverse** — needs a queryable DB
- Cross-contamination would compromise the trial's simplicity

## Installation (Contabo fleet)

The fleet runs as Docker Compose on Contabo VPS:

```yaml
# /opt/styxproxy/repo/infrastructure/contabo-dante/docker-compose.yml
services:
  danted:
    image: ubuntu/dante  # or build from ./dante
    network_mode: host
    ports: ["1080:1080"]  # internal SOCKS5, no auth
    
  socks-auth-proxy:
    build: ./socks-auth-proxy
    network_mode: host
    ports: ["1081:1081"]  # public-facing, with auth
    volumes:
      - dante-users:/etc/dante:ro
    
  control-api:
    build: ./control-api
    ports: ["9000:9000"]  # admin API for adding/removing trial users
    volumes:
      - dante-users:/etc/dante:rw
```

Restart policy: `unless-stopped`. Network: host mode.

## How a customer gets a trial credential

1. Customer in Telegram/WhatsApp: `/trial`
2. Bot explains the survey → earn time model
3. Customer completes N surveys (max 12)
4. Bot says "type DONE when finished"
5. Bot → backend: `POST /api/trials/fulfill` with `{phone_hash, surveys_done: N}`
6. Backend: 
   - Allocates a port from 8001-8100 range
   - Pulls a free datacenter IP from the pool
   - Calls `control-api` on Contabo: `POST /api/trial-users` with `{username: trial_<id>, password: <random>, upstream_ip: <ip>, port: 1080}`
   - Returns to customer: `{host: "trial.styxproxy.com", port: 8001, username: "trial_abc123", password: "***", expires_at: "<now+24h>"}`
7. Customer connects to `trial.styxproxy.com:8001` with their creds
8. `socks-auth-proxy` verifies, maps to upstream IP, forwards through `danted`
9. Customer's traffic exits from the assigned datacenter IP

## Trial expiry

Cron job on Contabo at 03:00 UTC daily:
- Read all `users.json` entries
- For each `expires_at < now`:
  - Call `control-api` `DELETE /api/trial-users/{username}`
  - Remove the user from `users.json`
  - Free the IP back to the pool

## Why this is cheap

- Static datacenter IPs from a provider (Proxy-Seller, DataImpulse, or our own VPS) cost ~$1/IP/month
- We have ~50 IPs in rotation (ports 8001-8100 = 100 slots, allocated in pairs)
- Free trial users get 24h max — high churn, low cost
- Total cost: ~$50/month for a generous trial pool

## See Also

- [PAID_PROXY_RELAY.md](./PAID_PROXY_RELAY.md) — the paid relay architecture
- [PRD.md § Region Routing](./PRD.md) — where each relay type lives
- [api/services/trial.py](../../backend/app/services/trial.py) — backend trial logic
- [infrastructure/contabo-dante/](../../infrastructure/contabo-dante/) — actual deployment code
