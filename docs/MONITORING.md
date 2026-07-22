# Styxproxy — Monitoring Runbook

**Last Updated:** 2026-06-26
**Status:** Ready to configure

---

## Health Endpoints

Styxproxy has 3 health checks, all hit-able from public internet:

| Endpoint | URL | What it checks | Returns |
|----------|-----|----------------|---------|
| **n8n liveness** | `https://n8n.yourdomain.com/healthz` | n8n process is running | `{"status":"ok"}` 200 |
| **Webhook receiver** | `https://n8n.yourdomain.com/webhook/whatsapp-incoming` | n8n webhook routing works | 200 with empty body |
| **Postgres connectivity** | TBD via small Flask sidecar or pg_isready | DB accepts connections | OK / fail |

**For Phase 1**, we monitor the n8n `/healthz` endpoint. Postgres connectivity is implied (n8n won't respond healthy if DB is down because every workflow reads from it).

---

## UptimeRobot Setup (Free Tier)

**Cost:** $0 — supports 50 monitors, 5-minute checks
**Limit:** Monitor checks every 5 min (not 1 min) — fine for Phase 1

### Step 1: Create Account

1. Go to: https://uptimerobot.com/signUp
2. Free plan is sufficient — no card needed
3. Verify email

### Step 2: Add HTTP Monitor

1. Click **+ Add New Monitor**
2. Monitor Type: **HTTP(s)**
3. Friendly Name: `Styxproxy — n8n health`
4. URL: `https://n8n.yourdomain.com/healthz`
5. Monitoring Interval: **5 minutes** (free tier)
6. Monitor Timeout: **30 seconds**
7. Click **Create Monitor**

### Step 3: Add Webhook Alert Contact

1. Go to **My Settings** → **Alert Contacts**
2. Click **+ Add Alert Contact**
3. Type: **Webhook**
4. Friendly Name: `Styxproxy n8n Error Workflow`
5. URL to notify:

   Create a NEW n8n workflow:

   - Trigger: Webhook (POST)
   - Path: `uptimerobot-alert`
   - Action 1: Switch on `monitorFriendlyName`
     - If `Styxproxy — n8n health` → Send WhatsApp via WhatsApp Business API
   - Action 2: Log to `provider_log` table in PostgreSQL
   - Action 3: Return 200

   Then paste the n8n webhook URL (production URL, e.g. `https://n8n.yourdomain.com/webhook/uptimerobot-alert`) into UptimeRobot's webhook URL field.

### Step 4: Configure Alert Rules

For each monitor:
1. Click the monitor → **Alert Contacts** tab
2. Enable the webhook contact you just added
3. Set "When down" alert after **2 consecutive failures** (10 min grace — avoids false alarms)
4. Set "When up" alert: **enabled** (confirms recovery)

### Step 5: Test the Setup

1. Temporarily break n8n: `docker-compose stop n8n`
2. Wait 10 minutes (2 checks × 5 min)
3. Check WhatsApp — should receive "Styxproxy — n8n health is DOWN"
4. Restart n8n: `docker-compose start n8n`
5. Wait 5 minutes — should receive "Styxproxy — n8n health is UP"

---

## Backup Monitoring (Custom Cron)

UptimeRobot can't watch backup freshness directly. We use a custom cron check:

```bash
# /usr/local/bin/check-backup-freshness.sh
# Runs every day at 03:00 — runs 1 hour after backup script

LATEST=$(find /backup/bunche -name "bunche_*.dump.age" -mtime -1 | head -1)

if [ -z "$LATEST" ]; then
  # No backup in last 24h — alert admin
  curl -X POST https://n8n.yourdomain.com/webhook/backup-alert \
    -H "Content-Type: application/json" \
    -d '{"severity":"high","message":"No backup file found in last 24h"}'
fi

# Add to crontab:
# 0 3 * * * /usr/local/bin/check-backup-freshness.sh >> /var/log/backup-check.log 2>&1
```

The webhook `backup-alert` triggers a WhatsApp message to admin.

---

## Alert Severity Matrix

| Severity | When | Action |
|----------|------|--------|
| **Critical** | n8n down >10 min, DB down, payment webhook failing | WhatsApp + email + (Phase 2) SMS |
| **High** | Provider API down, backup missing, error rate spike | WhatsApp only |
| **Medium** | Slow response (>5s p95), single workflow failure | Log + daily summary |
| **Low** | Info, warnings, rate-limit hits | Log only |

---

## Phase 2 Monitoring Upgrades

When we hit 1,000+ customers:

| Upgrade | Tool | Cost |
|---------|------|------|
| 1-min checks | UptimeRobot Pro | $7/mo |
| Synthetic transactions | Checkly | $0–29/mo |
| APM (response time, DB queries) | n8n built-in exec stats | Free |
| Error tracking | Sentry (see ADR/ERROR-3) | $0–26/mo |
| Log aggregation | Loki + Grafana on VPS | Free (self-host) |

---

## What We Deliberately Don't Monitor in Phase 1

| What | Why not |
|------|---------|
| Each individual provider's IP quality | Slow + adds API calls. Provider's own dashboard covers this. |
| Customer LLM cost per message | Phase 2 — when cost becomes material |
| PostgreSQL query performance | Phase 2 — when DB load justifies |
| Network bandwidth | VPS providers cap this; not actionable |

---

## Health Check Auth

The `/healthz` endpoint is unauthenticated by design — UptimeRobot can't authenticate. To prevent abuse:

1. **Cloudflare in front** — DDoS protection + rate limit at edge
2. **Response is tiny** — `{"status":"ok"}` only, no info leak
3. **UptimeRobot IP allowlist** (Pro feature, Phase 2) — restrict to known monitor IPs

If abuse becomes an issue, add `BASIC_AUTH` to `/healthz` and configure UptimeRobot with Basic Auth (Pro feature).

---

## Related

- `docs/DEPLOYMENT.md` §4.1 — n8n Docker Compose (healthcheck config)
- `docs/SECURITY_PLAN.md` Layer 7 — Monitoring + Alerting
- ADR-005 — Backup Strategy (which feeds backup monitoring)