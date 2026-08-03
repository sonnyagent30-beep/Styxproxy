# Data Retention Policy

**Owner:** Operations  
**Last updated:** 2026-08-03

---

## Overview

This document defines retention periods for all data stored in the Styxproxy system. Retention periods are driven by:
- **Business requirements** (accounting, legal)
- **Operational needs** (debugging, replay)
- **Compliance** (privacy, PCI-DSS for payments)
- **Cost** (storage optimization)

---

## Retention Schedule

| Data Type | Retention | Rationale | Cleanup Mechanism |
|-----------|-----------|-----------|------------------|
| **Orders** | Indefinite | Business records, tax/accounting | None (permanent) |
| **Customers** | Indefinite | Business records, support history | None (permanent) |
| **Credentials** | Indefinite | Active proxy access | Manual revocation only |
| **Payments (Flutterwave)** | 7 years | Nigerian tax law requirement | None (permanent) |
| **Processed Webhooks** | 90 days | Debug replay, duplicate prevention | `cleanup_webhooks.py` cron (03:30 UTC) |
| **Charon Context** | 24 hours | Cost control, privacy | `cleanup_charon_context` cron |
| **Health Snapshots** | 7 days | Monitoring dashboards | Cron prunes older rows |
| **Admin TOTP Sessions** | 5 minutes TTL | Security | Expiry check on read |
| **JSON Access Logs** | 30 days | Debugging, security audit | Log rotation (nginx/docker) |
| **Error Logs** | 30 days | Debugging | Log rotation |
| **Blog Posts** | Indefinite | Content library | None (permanent) |
| **Free Trials** | 90 days | Abuse prevention | Auto-expire via query filter |

---

## Details

### Processed Webhooks

**Retention:** 90 days  
**Location:** `processed_webhooks` table  
**Cleanup:** Daily cron at 03:30 UTC

```bash
# Manual trigger (if needed)
python3 /opt/styxproxy/backend/scripts/cleanup_webhooks.py
```

**Rationale:** Webhook payloads are needed only for debugging duplicate payments during the replay window (300 seconds). After 90 days, the probability of needing to replay a webhook is negligible, and storing them indefinitely creates unnecessary storage cost.

**Script:** `/opt/styxproxy/backend/scripts/cleanup_webhooks.py`

---

### Charon Context

**Retention:** 24 hours  
**Location:** `charon_context` table  
**Cleanup:** `cleanup_charon_context` cron job

**Rationale:** Charon conversation history is only useful for ongoing sessions. Retaining longer increases cost (MiniMax API calls) and creates privacy concerns. After 24 hours, the context is cleared and Charon starts fresh.

---

### Health Snapshots

**Retention:** 7 days  
**Location:** `health_snapshots` table  
**Cleanup:** Caller should implement cron to prune rows older than 7 days

**Rationale:** Health snapshots are used for monitoring dashboards and incident post-mortems. 7 days is sufficient to detect patterns and correlate with incidents.

---

### Admin TOTP Sessions

**Retention:** 5 minutes TTL  
**Location:** `admin_totp_sessions` table  
**Cleanup:** Automatic expiry check on read

**Rationale:** Short TTL limits the window of opportunity for session hijacking. Sessions are not stored long-term.

---

### JSON Access Logs

**Retention:** 30 days  
**Location:** `/var/log/styxproxy/access.json` (container logs)  
**Cleanup:** Docker log rotation (via `docker-compose.yml`)

**Rationale:** Access logs are needed for:
- Security incident investigation
- Debugging customer issues
- Usage analytics

After 30 days, logs are rotated and archived (if needed) or discarded.

---

## Compliance Notes

- **PCI-DSS:** Payment data (card numbers, CVV) is never stored — all payment processing is delegated to Flutterwave
- **GDPR:** Customers can request data deletion — contact Dannion (`oyebiyiayomide30@gmail.com`)
- **Nigerian Tax:** Payment records retained for 7 years per FIRS requirements

---

## Updating Retention Periods

To change a retention period:

1. Update the relevant constant in the cleanup script (e.g., `RETENTION_DAYS` in `cleanup_webhooks.py`)
2. Update this document
3. Deploy and verify the new cleanup runs correctly
4. Manually delete existing rows outside the new window (if reducing retention)

---

## Related Docs

- [BACKUP_STRATEGY.md](./BACKUP_STRATEGY.md) — Backup procedures
- [SECURITY_RUNBOOK.md](./SECURITY_RUNBOOK.md) — Incident response
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) — Customer communication during outages
