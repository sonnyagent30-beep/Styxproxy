# DNS Failover — Styxproxy Operator Guide

**Owner:** Operations / Sonny
**Last updated:** 2026-08-09

---

## Overview

DNS failover automatically routes traffic away from a failed VPS to a healthy standby VPS.
Styxproxy's critical DNS records:

| Record | Host | Value | Purpose |
|---|---|---|---|
| `styxproxy.com` A | @ | `162.35.184.69` | Primary API + website |
| `api.styxproxy.com` A | api | `162.35.184.69` | API gateway |
| `status.styxproxy.com` CNAME | status | `styxproxy-status.upstatus.io` | Betterstack status page |
| `mail.styxproxy.com` MX | mail | `162.35.184.69` | Mail relay |

---

## How It Works

1. **Health check:** Betterstack monitors `api.styxproxy.com:443` every 3 minutes.
2. **Failure detected:** If the endpoint fails 3 consecutive checks (9 minutes), Betterstack triggers.
3. **Alert sent:** `POST /api/internal/incidents/webhook` fires → email to ops team.
4. **DNS failover:** Betterstack automatically switches the A record to the standby IP (if configured).
5. **Recovery:** When the primary recovers, Betterstack switches back.

---

## Configuring Failover in Betterstack

1. Log in to Betterstack → Uptime → Monitors.
2. Select the `styxproxy-api` monitor (ID: `4785749`).
3. **On-failure actions:**
   - ✅ Alert: Email → `oyebiyiayomide30@gmail.com`
   - ✅ Webhook → `https://styxproxy.com/api/internal/incidents/webhook`
   - ✅ DNS Failover → Add standby IP (`84.247.132.12` — Contabo)

4. **Recovery actions:**
   - ✅ Email on recovery
   - ✅ Webhook → same endpoint (status=up)

---

## Manual Failover (if Betterstack is unavailable)

If the API goes down and Betterstack failover isn't working:

### Step 1 — Confirm primary is down

```bash
curl -sf https://styxproxy.com/api/v1/health || echo "PRIMARY DOWN"
```

### Step 2 — Check Contabo is healthy

```bash
curl -sf https://84.247.132.12:9000/health | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d.get('status'))"
```

### Step 3 — Switch DNS at Cloudflare

```bash
# Get current API IP
dig +short api.styxproxy.com

# Update Cloudflare API A record
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{RECORD_ID}" \
  -H "Authorization: Bearer $CLOUDFLARE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "84.247.132.12", "name": "api", "type": "A"}'
```

**⚠️ DNS propagation takes 2-5 minutes.** Customers may experience brief interruptions.

---

## Current Standby

- **Contabo VPS:** `84.247.132.12`
- **Purpose:** Backup Dante SOCKS5, LiteLLM fallback, potential failover target
- **Not yet configured** as Betterstack DNS failover destination (needs A record added in Cloudflare)

### To promote Contabo as full failover:

1. Add `162.35.184.69` as a standby in Betterstack DNS Failover
2. Or manually point `api.styxproxy.com` A record to `84.247.132.12`

---

## Critical Contacts

| Role | Contact |
|---|---|
| Interserver (primary VPS) | `support@interserver.net` |
| Contabo (standby VPS) | `support@contabo.com` |
| Cloudflare DNS | `dash.cloudflare.com` |
| Betterstack | `uptime.betterstack.com` |

---

## Response Runbook

| Scenario | Action |
|---|---|
| API down (< 10 min) | Wait for Betterstack auto-recovery. Monitor `/api/v1/health`. |
| API down (> 10 min) | Manually failover DNS to Contabo (see above). Page Interserver support. |
| VPS unreachable | Open Interserver ticket + initiate DNS failover. |
| Betterstack alert failed | Check Betterstack status page. Use manual failover above. |
| DNS propagation delayed | Use `dig +short api.styxproxy.com @1.1.1.1` to bypass local cache. |
