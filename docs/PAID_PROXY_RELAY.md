# Paid Proxy Relay — Interserver (gost + Postgres)

**Last Updated:** 2026-07-29
**Purpose:** Document the paid proxy relay that runs on Interserver.

## What this is

This is the **branding + auth layer** for paid customers. Every paid proxy (residential, mobile, ISP, paid datacenter) flows through this relay. The customer connects to `proxy.styxproxy.com:1080` (or :8080 for HTTP), authenticates with their styxproxy-* credentials, and the relay routes their traffic to the appropriate upstream provider.

The customer **never sees** Rayobyte, Proxy-Seller, DataImpulse, or any other provider name. The exit IP is the provider's, but the entry hostname is always Styxproxy.

## Architecture

```
Customer →  proxy.styxproxy.com:1080 (SOCKS5)
              :8080 (HTTP CONNECT)
              ↓
       gost relay on Interserver
              ↓
         Looks up username in /etc/styxproxy/auth.json
              ↓
         Maps to: styx_t1:12345-country-NG @ la.residential.rayobyte.com:8000
              ↓
       Forwards to upstream provider
              ↓
       Upstream provider assigns exit IP
              ↓
       Customer traffic exits through the assigned IP
```

The auth table is regenerated from Postgres every 30 seconds by `relay_sync.py`. This means:
- New customers get credentials within 30s of order fulfillment
- Customer-initiated password rotation propagates within 30s
- Customer revocation is effective within 30s

## Region routing

Static datacenter and ISP proxies flow through their geographically closest relay:

| Customer connects via | Best for | Why |
|---|---|---|
| **Interserver relay** (162.35.184.69) | US datacenter, US ISP, ALL rotating (residential/mobile) | Backend is on Interserver, low latency for relay_sync; rotating pools are global anyway |
| **Contabo relay** (84.247.132.12) | UK datacenter, UK ISP | Contabo is in EU/UK region; lower latency for UK customers; can be added to the same gost config |

For v1, **only Interserver relay is deployed**. Contabo relay is the same gost config deployed as a separate Docker container — the auth table is fetched from the same Postgres. Both relays show the same `proxy.styxproxy.com` to customers (Cloudflare DNS handles region-based routing).

The relay config is identical; only the listen address differs.

## Installation

### 1. Install gost on Interserver

```bash
# Option A: Docker (recommended)
docker pull gogost/gost:latest

# Option B: Direct binary
wget https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-linux-amd64-2.11.5.gz
gunzip gost-linux-amd64-2.11.5.gz
chmod +x gost-linux-amd64-2.11.5
sudo mv gost-linux-amd64-2.11.5 /usr/local/bin/gost
gost --version  # verify
```

### 2. gost config

```yaml
# /etc/gost/config.yaml
api:
  addr: 127.0.0.1:18080

# Audit log: every connection logged with user, source IP, destination
log:
  output: /var/log/gost/audit.log

# Auto-reload auth file (sighup or hot-reload via API)
reload:
  interval: 30s

# SOCKS5 listener with auth
socks5:
  - name: styxproxy-socks5
    addr: 0.0.0.0:1080
    auth:
      file:
        filename: /etc/styxproxy/auth.json
        reload: true
    # Each user routes to their upstream, defined in auth.json
    forwarder:
      # Default chain — gost reads from auth.json to find per-user routing
      nodes:
        - name: default
          addr: <upstream-from-auth.json>

# HTTP CONNECT listener with auth
http:
  - name: styxproxy-http
    addr: 0.0.0.0:8080
    auth:
      file:
        filename: /etc/styxproxy/auth.json
        reload: true
```

### 3. auth.json format

This file is rendered by `relay_sync.py` from Postgres. Format:

```json
{
  "users": [
    {
      "username": "jibola_styxproxy",
      "password": "xK9p...",
      "upstream": {
        "type": "rayobyte_resi",
        "host": "la.residential.rayobyte.com",
        "port": 8000,
        "user": "styx_t1",
        "pass": "12345-country-NG",
        "protocol": "socks5"
      },
      "expires_at": "2026-08-30T00:00:00Z",
      "monthly_bandwidth_gb": 5,
      "monthly_bandwidth_used_bytes": 0
    },
    {
      "username": "ahmed_isp",
      "password": "abc123",
      "upstream": {
        "type": "rayobyte_isp",
        "host": "192.0.2.10",
        "port": 8080,
        "user": "ahmed_isp",
        "pass": "fixed_creds",
        "protocol": "http"
      },
      "expires_at": "2026-08-30T00:00:00Z"
    }
  ]
}
```

### 4. relay_sync.py

```python
# backend/app/services/relay_sync.py
import asyncio
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from app.database import async_session
from app.models import StyxproxyRelayEntries, StyxproxyCredentials

AUTH_FILE = Path('/etc/styxproxy/auth.json')

async def render_auth_file():
    async with async_session() as session:
        stmt = select(StyxproxyRelayEntries).where(
            StyxproxyRelayEntries.status == 'active'
        )
        result = await session.execute(stmt)
        entries = result.scalars().all()
        
        users = []
        for entry in entries:
            creds = await session.get(StyxproxyCredentials, entry.credential_id)
            users.append({
                "username": creds.styxproxy_username,
                "password": creds.styxproxy_password,
                "upstream": {
                    "type": entry.upstream_type,
                    "host": entry.upstream_host,
                    "port": entry.upstream_port,
                    "user": entry.upstream_user,
                    "pass": entry.upstream_pass,
                    "protocol": entry.upstream_protocol or "socks5"
                },
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                "monthly_bandwidth_gb": entry.monthly_bandwidth_gb,
                "monthly_bandwidth_used_bytes": entry.monthly_bandwidth_used_bytes
            })
        
        AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUTH_FILE.write_text(json.dumps({"users": users}, indent=2))
        
        # Hot-reload gost
        # gost -L reload or send SIGHUP

async def main():
    while True:
        await render_auth_file()
        await asyncio.sleep(30)

if __name__ == '__main__':
    asyncio.run(main())
```

### 5. Bandwidth tracking

gost can emit per-user byte counts via the audit log. `relay_sync.py` reads the audit log every 5 minutes and updates `monthly_bandwidth_used_bytes` per user.

Bandwidth policy:
- `monthly_bandwidth_used_bytes >= monthly_bandwidth_gb * 1024^3 * 1.0` → send WhatsApp+email "80% used"
- `>= 1.1` → set status='suspended', customer can't connect
- Cron at 02:00 UTC: reset bandwidth counters for new billing cycle

## How a customer gets a paid credential

1. Customer on styxproxy.com: picks "Residential US 5GB" → pays via Flutterwave
2. Webhook fires → backend `order_handlers/residential.py`
3. Backend calls Rayobyte: `PUT /users/create` with `email=*** , password=*** , trafficLimitGB=5`
4. Backend writes `styxproxy_relay_entries` row: `{user_id, upstream_type="rayobyte_resi", upstream_host="la.residential.rayobyte.com", upstream_port=8000, upstream_user="styx_t1", upstream_pass="12345", exit_ip="pool", country="US", monthly_bandwidth_gb=5}`
5. Backend writes `styxproxy_credentials` row: `{styxproxy_username="jibola_styxproxy", styxproxy_password=<random>}`
6. `relay_sync.py` picks up the new entry within 30s, renders auth.json, gost reloads
7. Customer sees: `{host: "proxy.styxproxy.com", port: 1080, username: "jibola_styxproxy", password: "xK9p...", type: "SOCKS5"}`
8. Customer connects, traffic flows through Rayobyte

## Password rotation

### Customer-initiated rotation

`POST /api/credentials/{id}/rotate-password` (customer auth required)

Backend:
1. Generates new `styxproxy_password`
2. Updates `styxproxy_credentials.styxproxy_password`
3. If `upstream_type == "rayobyte_*"`, calls Rayobyte `/users/edit` to rotate upstream password too
4. Audit log entry
5. `relay_sync.py` picks up within 30s, gost reloads
6. Customer gets the new password via email + Telegram/WhatsApp

Rate limit: 3 rotations per day per user.

### Admin-initiated rotation

`POST /api/admin/relay/{user_id}/rotate` (admin auth required)

Same flow but no rate limit. Used when:
- Customer lost their password
- Customer shared their password and got banned
- Customer's upstream credentials are compromised

### Provider key rotation

Rayobyte sub-user password changed in dashboard → backend detects via `GET /info` polling → updates `styxproxy_relay_entries.upstream_pass` → `relay_sync.py` picks it up.

This is admin-only concern, never customer-facing.

## Customer-facing relay entry point

The customer always uses `proxy.styxproxy.com:1080` (SOCKS5) or `proxy.styxproxy.com:8080` (HTTP). DNS for `proxy.styxproxy.com` is on Cloudflare, with one A record pointing to Interserver (162.35.184.69). For Contabo relay region, a second A record is added once deployed.

If both relays are deployed, customers can connect to either. The auth table is the same, so credentials work on both. The customer chooses based on their location (Cloudflare doesn't do geo-routing for free tier, but we can document the IPs).

## See Also

- [TRIAL_PROXY_SETUP.md](./TRIAL_PROXY_SETUP.md) — for free trials (different relay, different auth)
- [api/services/rayobyte.py](../../backend/app/services/rayobyte.py) — Rayobyte adapter
- [api/services/relay_sync.py](../../backend/app/services/relay_sync.py) — auth file renderer
- [RELAY_OPERATIONS.md](./RELAY_OPERATIONS.md) — operational runbook
- [Sprint 10 in Notion](https://www.notion.so/Sprint-Todo-Checklist-Per-Layer-Build-Sequence-3aab776613fa81bf91c2cba7641415f8) — full task list
