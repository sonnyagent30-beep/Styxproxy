# Styxproxy — Operational Security Runbook

**Last Updated:** 2026-06-26
**Status:** Phase 1 (Launch) policies

---

## 1. Secrets Rotation Policy (SEC-7)

### Why Rotate

A leaked secret that you've rotated is **half a problem**. A leaked secret you didn't rotate is **a complete breach**.

### Rotation Schedule

| Secret | Frequency | Who | How |
|--------|-----------|-----|-----|
| PostgreSQL password | **90 days** | Dannion | See procedure below |
| Redis password | **90 days** | Dannion | See procedure below |
| n8n basic auth password | 180 days | Dannion | n8n UI → Settings → Users |
| Admin PIN (bcrypt hash) | 180 days | Dannion | Re-run hash + update DB |
| TOTP encryption key | **NEVER** | Locked | Rotating invalidates all stored TOTP secrets |
| Flutterwave secret key | On staff change OR incident | Dannion | Dashboard → API → Regenerate |
| Flutterwave webhook hash | **30 days** | Dannion | Dashboard → Webhooks → Regenerate + sync to `.env` |
| WhatsApp access token | **Meta-managed** (60-day TTL) | Meta | Auto-rotates |
| WhatsApp app secret | On staff change OR incident | Dannion | Dashboard → App Settings |
| Proxy-Seller API key | On staff change OR incident | Dannion | Dashboard → API → Regenerate |
| DataImpulse API key | On staff change OR incident | Dannion | Dashboard → API → Regenerate |
| R2 access keys | 90 days | Dannion | R2 → API Tokens → Rotate |
| MiniMax API key | 90 days | Dannion | Dashboard → API Keys → Regenerate |
| Bitlock.ai API key | On staff change OR incident | Dannion | Dashboard → API |
| SSH key (VPS access) | 180 days | Dannion | Generate new keypair + update authorized_keys |

### Rotation Procedure (PostgreSQL Password)

**Estimated downtime:** 2 minutes (n8n restart)

```bash
# 1. SSH to VPS
ssh root@vps

# 2. Generate new password
NEW_PASS=$(openssl rand -base64 32)
echo "New password: $NEW_PASS"

# 3. Update in PostgreSQL
sudo -u postgres psql -c "ALTER USER bunche WITH PASSWORD '$NEW_PASS';"

# 4. Update .env
nano /opt/bunche/.env
# Update POSTGRES_PASSWORD line

# 5. Restart n8n
cd /opt/bunche
docker-compose restart n8n

# 6. Verify health
curl https://n8n.yourdomain.com/healthz

# 7. Test one workflow manually (send a test WhatsApp message to yourself)

# 8. Update 1Password entry with new password
```

### Rotation Procedure (Webhook Hash)

**Zero-downtime rotation:**

```bash
# 1. Generate new hash in Flutterwave dashboard
# 2. Update in .env
nano /opt/bunche/.env
# Update FLUTTERWAVE_WEBHOOK_VERIF_HASH line

# 3. Restart n8n (reads new env)
cd /opt/bunche
docker-compose restart n8n

# 4. Trigger a test webhook from Flutterwave dashboard
#    → Verify it lands in n8n execution log
```

### Tracking Rotations

Use `docs/SECRET_ROTATION_LOG.md` (one-line entry per rotation):

```markdown
| Date | Secret | Reason | By |
|------|--------|--------|-----|
| 2026-07-15 | POSTGRES_PASSWORD | scheduled 90-day | Dannion |
| 2026-08-01 | FLUTTERWAVE_WEBHOOK_HASH | scheduled 30-day | Dannion |
```

### Emergency Rotation (Suspected Compromise)

**Do all of these within 1 hour:**

1. **Stop n8n** to prevent further damage: `cd /opt/bunche && docker-compose down`
2. **Rotate** every secret the compromised component had access to
3. **Audit logs** — `SELECT * FROM customer_audit_log WHERE created_at > [compromise time]`
4. **Check Flutterwave dashboard** for unauthorized transactions
5. **Check provider dashboards** for unauthorized orders
6. **Notify customers** if their data may have been accessed (NDPR Article 5)
7. **Document incident** in `docs/INCIDENTS/YYYY-MM-DD-description.md`

---

## 2. API Key Usage Monitoring (SEC-8)

### What to Watch

| Pattern | Why |
|---------|-----|
| Sudden spike in API calls from one IP | Credential stuffing / stolen key |
| API calls from unusual geographies | Compromised key being resold |
| API calls outside business hours | Automated abuse |
| Failed auth attempts spike | Brute force |
| Provider balance drops faster than order volume | Reseller abuse / leak |

### How We Monitor

#### Layer 1 — Provider Dashboards

Check daily:

| Provider | URL | What to check |
|----------|-----|---------------|
| Proxy-Seller | proxy-seller.com → Dashboard | Balance, recent orders |
| DataImpulse | dataimpulse.com → Dashboard | Balance, recent orders |
| Flutterwave | rave.flutterwave.com → Transactions | Failed txns, refunds |
| MiniMax | console.minimax.chat → Usage | Token spend, anomaly alerts |
| Cloudflare R2 | dash.cloudflare.com → R2 | Storage usage |
| Bitlock.ai | dashboard.bitlock.ai → Conversions | Conversion rate |

#### Layer 2 — PostgreSQL Audit Queries

Run these weekly (or set up as n8n cron → admin WhatsApp report):

```sql
-- Order volume by day — spike detection
SELECT 
  DATE(created_at) AS day,
  COUNT(*) AS orders,
  SUM(amount_ngn) AS revenue_ngn
FROM orders
WHERE created_at > NOW() - INTERVAL '14 days'
  AND status = 'fulfilled'
GROUP BY DATE(created_at)
ORDER BY day DESC;

-- Customers with high refund rate (potential abuse)
SELECT 
  c.phone_hash,
  c.name,
  COUNT(*) FILTER (WHERE o.status = 'refunded') AS refunds,
  COUNT(*) AS total_orders
FROM customers c
JOIN orders o ON o.customer_phone = c.phone
WHERE o.created_at > NOW() - INTERVAL '30 days'
GROUP BY c.phone_hash, c.name
HAVING COUNT(*) FILTER (WHERE o.status = 'refunded') > 2
ORDER BY refunds DESC;

-- Provider API errors (network reachability check)
SELECT 
  provider,
  DATE(created_at) AS day,
  COUNT(*) FILTER (WHERE status = 'error') AS errors,
  COUNT(*) AS total
FROM provider_log
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY provider, DATE(created_at)
ORDER BY day DESC;

-- Referral credit payouts (revenue leak check)
SELECT 
  DATE(created_at) AS day,
  SUM(referral_credit_earned_ngn) AS credit_paid_ngn,
  COUNT(*) AS referral_count
FROM orders
WHERE referred_by_phone IS NOT NULL
  AND created_at > NOW() - INTERVAL '30 days'
  AND status = 'fulfilled'
GROUP BY DATE(created_at)
ORDER BY day DESC;
```

#### Layer 3 — Provider Webhooks (Reverse Check)

Every provider webhook hits our DB. Sudden drops = provider integration broken:

```sql
-- Webhook volume by provider, last 7 days
SELECT 
  provider,
  DATE(created_at) AS day,
  COUNT(*) AS events
FROM webhook_log
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY provider, DATE(created_at)
ORDER BY day DESC, provider;
```

#### Layer 4 — Alert Automation (Phase 2)

Add to n8n cron workflows:

| Trigger | Action |
|---------|--------|
| Daily summary orders < 50% of 7-day average | Alert admin — possible integration issue |
| Provider error rate > 20% over 1 hour | Alert admin — provider down |
| Same phone attempting >10 orders/hour | Rate-limit + alert (potential card fraud) |
| Failed Flutterwave txns > 30% of attempts | Alert — possible webhook signature mismatch |
| MiniMax daily spend > 2× 7-day average | Alert — runaway prompt or leak |

### Incident Response (Compromised Key Detected)

1. **Rotate immediately** (see SEC-7 procedures)
2. **Identify blast radius** — what could attacker do with this key?
3. **Block attacker** — change keys, block IPs in Cloudflare
4. **Document** in `docs/INCIDENTS/YYYY-MM-DD-{key-name}.md`
5. **Notify** affected parties (customers, providers) per NDPR timelines

---

## 3. Sentry Error Tracking (ERROR-3)

### Decision: Defer Until Phase 2

**Rationale:**
- n8n has built-in execution logs + workflow error workflows (already implemented)
- Error volume at Phase 1 launch is expected to be < 50 events/day
- Sentry adds operational overhead (another account, SDK config, source map upload)
- We're already alerting on critical errors via WhatsApp

**When to enable Sentry:**
- Error volume exceeds 100 events/day (hard to triage from logs)
- We add a frontend (currently WhatsApp-only)
- Multiple operators need to triage (currently just Dannion)

### If/When We Enable Sentry

**Plan for Phase 2:**

1. **Account:** sentry.io — free tier supports 5K events/month, 1 project
2. **Capture source:** n8n HTTP Request node → Sentry ingest API
3. **What to capture:**
   - Critical workflow errors
   - Provider API failures (after 3 retries)
   - Webhook signature mismatches (potential attack signal)
   - Database query failures
4. **What NOT to capture:**
   - Customer PII (phone, name, IP, email)
   - Proxy credentials
   - Payment data
5. **Integration:** Custom n8n node "Error to Sentry" that posts to Sentry's HTTP API

```javascript
// Pseudocode for Error to Sentry node
{
  "event_id": uuid(),
  "timestamp": new Date().toISOString(),
  "platform": "javascript",
  "level": "error",
  "logger": "bunche",
  "transaction": workflowName,
  "tags": {
    "customer_hash": sha256(phone).substring(0, 20),
    "order_id": orderId
  },
  "exception": {
    "values": [{
      "type": errorType,
      "value": errorMessage,
      "stacktrace": errorStack
    }]
  }
}
```

**Cost:** $0 in Phase 2 (free tier).

---

## 4. NDPR Compliance Checklist

Nigeria Data Protection Regulation — applies to Styxproxy because we process Nigerian customer data.

| Requirement | How we comply |
|-------------|---------------|
| Lawful basis for processing | Customer consent (implicit via WhatsApp message = opt-in) |
| Purpose limitation | We only use data for order fulfillment + customer support |
| Data minimization | We don't collect name until customer opts in to referral system |
| Accuracy | Customer can update name/address via WhatsApp admin command |
| Storage limitation | Logs auto-prune after 7 days (n8n), audit log retained 1 year |
| Integrity & confidentiality | Encrypted at rest (R2), TLS in transit, PII hashed in logs |
| Accountability | Audit log table records all data access |
| Breach notification | Within 72 hours to NITDA + affected customers |
| Cross-border transfer | All data stays on Hetzner EU (acceptable; R2 US is encrypted) |

### Customer Data Subject Rights (we must support)

| Right | How to fulfill |
|-------|----------------|
| Right to access | Admin: `Details <phone>` returns customer's record |
| Right to rectification | Admin: `Update <phone> name <new_name>` |
| Right to erasure | Admin: `Delete <phone>` — anonymizes PII, keeps orders as aggregate |
| Right to data portability | Export customer record as JSON via admin command |

**We will add these admin commands in Phase 2** (post-launch, pre-1000 customers).

---

## 5. Incident Response Playbook

### Severity 1: n8n Down

1. Check UptimeRobot alert
2. SSH to VPS, check `docker ps` — is n8n running?
3. If crashed: `docker logs n8n` — what's the error?
4. If hung: `docker restart n8n`
5. If still failing: `docker-compose down && docker-compose up -d`
6. Check health: `curl https://n8n.yourdomain.com/healthz`
7. If persistent: roll back to last known good image
8. Document incident

### Severity 1: Database Compromised

1. **Stop n8n immediately** to prevent exfiltration
2. Disconnect VPS from network (Cloudflare firewall rule)
3. **Do NOT power off** — forensic value
4. Restore from backup (see ADR-005 restore procedures)
5. Rotate ALL secrets
6. Notify NITDA + customers within 72 hours
7. Engage incident response specialist (Phase 2 — get a retainer)

### Severity 2: Provider API Key Leaked

1. Rotate immediately on provider dashboard
2. Check provider logs for unauthorized orders
3. Refund any fraudulent orders (admin command)
4. Update `.env` + restart n8n
5. Document incident

### Severity 3: Customer PII Exposed

1. Identify exposure scope (which customers, what data)
2. Notify affected customers within 72 hours
3. Log incident in `docs/INCIDENTS/`
4. Implement fix to prevent recurrence
5. If >500 customers affected, notify NITDA

---

## Related

- `ADR-004` — Secrets Management
- `ADR-005` — Backup Strategy
- `docs/SECURITY_PLAN.md` — Security layers
- `docs/MONITORING.md` — Uptime setup