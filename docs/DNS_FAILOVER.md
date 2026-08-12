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

**Cloudflare zone ID:** `15b6b0cedbfb4afd56bc034ac977bce2`
**API key scope:** DNS + Zone Settings (no Firewall access — needs Pro plan)

---

## Cloudflare Security Settings (configured 2026-08-09)

| Setting | Value | Purpose |
|---|---|---|
| HSTS `strict_transport_security` | ✅ enabled, max-age=1yr, includeSubDomains, preload | Force HTTPS for 1 year |
| `always_use_https` | ✅ on | Auto-upgrade HTTP → HTTPS |
| `automatic_https_rewrites` | ✅ on | Fix mixed content warnings |
| `min_tls_version` | ✅ 1.2 (was 1.0) | Block TLS 1.0/1.1 |
| `tls_1_3` | ✅ on | Modern TLS |
| `ssl` | ✅ full | Encrypts end-to-end |
| `browser_check` | ✅ on | Block malicious browsers |
| `security_level` | ✅ medium | Threat score-based blocking |
| WAF | ⚠️ off (needs Pro plan) | Cloudflare Firewall Rules unavailable on Free plan |

---

## How DNS Failover Works

1. **Health check:** Betterstack monitors `api.styxproxy.com:443` every 3 minutes.
2. **Failure detected:** If endpoint fails 3 consecutive checks (9 min), Betterstack triggers.
3. **Alert sent:** `POST /api/internal/incidents/webhook` → email to ops team.
4. **DNS failover:** Betterstack switches the A record to the standby IP (if configured).
5. **Recovery:** When primary recovers, Betterstack switches back.

---

## Configuring Failover in Betterstack

1. Log in to Betterstack → Uptime → Monitors.
2. Select `styxproxy-api` monitor (ID: `4785749`).
3. **On-failure actions:**
   - ✅ Email → `oyebiyiayomide30@gmail.com`
   - ✅ Webhook → `https://styxproxy.com/api/internal/incidents/webhook`
   - ✅ DNS Failover → standby IP `84.247.132.12` (Contabo)

4. **Recovery actions:**
   - ✅ Email on recovery
   - ✅ Webhook → same endpoint (status=up)

---

## Manual Failover (if Betterstack is unavailable)

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
CLOUDFLARE_API_KEY="your-key"
ZONE_ID="15b6b0cedbfb4afd56bc034ac977bce2"

# Get current API A record ID
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?type=A&name=api.styxproxy.com" \
  -H "Authorization: Bearer $CLOUDFLARE_API_KEY" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['result'][0]['id'], d['result'][0]['content'])"

# Update A record to Contabo
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/RECORD_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "84.247.132.12"}'
```

**⚠️ DNS propagation takes 2-5 minutes.** Customers may experience brief interruptions.

---

## Current Standby

- **Contabo VPS:** `84.247.132.12` — backup Dante SOCKS5, potential failover target
- **Not yet configured** as Betterstack DNS failover destination

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
| API down (> 10 min) | Manually failover DNS to Contabo. Page Interserver support. |
| VPS unreachable | Open Interserver ticket + initiate DNS failover. |
| Betterstack alert failed | Check Betterstack status page. Use manual failover above. |
| DNS propagation delayed | `dig +short api.styxproxy.com @1.1.1.1` to bypass local cache. |
