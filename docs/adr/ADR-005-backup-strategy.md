# ADR-005: Backup Strategy for Styxproxy

**Status:** Accepted
**Date:** 2026-06-26
**Decision Driver:** Customer money + audit trail. Loss of DB = loss of business + compliance failure.

---

## Context

Styxproxy's database holds:
- Customer records (phone, name, referral credits)
- Order records (₦ paid, proxy delivered, fulfillment status)
- Free trial records (anti-abuse tracking)
- Audit logs (PII-hashed, but records exist)
- Referral history
- Daily summary metrics

**Loss scenarios:**
- VPS disk failure (Hetzner hardware failure ~1%/year)
- Accidental `DROP TABLE` or `DELETE` in admin ops
- Bad migration that corrupts data
- Security breach with destructive intent
- Cloudflare R2 region outage (low probability but non-zero)

**Recovery time objective (RTO):** 4 hours — we can lose a day's worth of orders if needed, but not a week.

**Recovery point objective (RPO):** 24 hours — daily backup is acceptable for Phase 1.

---

## Decision

### Backup Layers

| Layer | What | When | Where | Retention |
|-------|------|------|-------|-----------|
| 1 — Daily PostgreSQL dump | Full DB | 02:00 Lagos daily | VPS local + R2 | Local: 7 days, R2: 90 days |
| 2 — Continuous WAL archiving | Transaction logs | Continuous (pg_basebackup + WAL streaming) | R2 | 7 days |
| 3 — Pre-migration snapshot | DB state before any schema change | Before each `psql -f migration.sql` | VPS local only | 30 days |
| 4 — Configuration snapshot | `.env` (sanitized), workflow JSON, nginx config | On deploy | Git (canonical), R2 (encrypted) | Forever |

### Backup Pipeline

```
[Cron: 02:00 daily]
        ↓
[pg_dump --format=custom --compress=9]
        ↓
[Save to /backup/bunche/bunche_${DATE}.dump]
        ↓
[Encrypt with age + Styxproxy backup public key]
        ↓
[rclone copy → r2:bunche-backups/daily/${DATE}/]
        ↓
[Delete local backups >7 days old]
        ↓
[Alert admin if backup size changed >50% from 7-day average]
```

### Why `pg_dump --format=custom` (not plain SQL)

- Compresses better (~3x smaller)
- Supports parallel restore with `pg_restore -j`
- Restore is reliable — no quoting issues with weird data
- Standard PostgreSQL tooling — no Styxproxy-specific format

### Why encryption (age, not gpg)

- Simpler key management (one keypair, public-key encrypts, private-key decrypts)
- Smaller surface area than gpg
- Forward secrecy by default
- Easy to add additional recipients when team grows

**Backup public key** is committed to repo. **Private key** lives ONLY on:
- Dannion's local machine (1Password)
- A printed paper copy in a safe (catastrophic recovery)

---

## Restore Procedure

### Scenario 1: Single table corruption (admin error)

```bash
# 1. SSH to VPS
ssh root@vps

# 2. Stop n8n (don't accept new orders during restore)
cd /opt/bunche
docker-compose down

# 3. List available backups
ls -la /backup/bunche/

# 4. Restore just the affected table
pg_restore --table=customers --dbname=bunche /backup/bunche/bunche_20260626.dump

# 5. Verify
sudo -u postgres psql -U bunche -d bunche -c "SELECT COUNT(*) FROM customers;"

# 6. Restart n8n
cd /opt/bunche
docker-compose up -d
```

### Scenario 2: Full DB loss (VPS disk failure)

```bash
# 1. Spin up new Hetzner VPS
# 2. Install PostgreSQL (see DEPLOYMENT.md §3)
# 3. Pull latest backup from R2
rclone copy r2:bunche-backups/daily/2026-06-26/ /tmp/restore/
age --decrypt /tmp/restore/bunche_20260626.dump.age > /tmp/restore/bunche_20260626.dump

# 4. Restore
pg_restore --dbname=bunche --create /tmp/restore/bunche_20260626.dump

# 5. Re-run schema migrations since backup date
# 6. Verify orders table against Flutterwave transaction log
# 7. Restore .env from secure storage (NOT from R2)
# 8. Restart n8n
```

### Scenario 3: Disaster recovery (everything gone)

Worst case = VPS + R2 + Dannion's laptop all compromised simultaneously. Probability: astronomically low.

Mitigation: print a paper copy of:
- Styxproxy backup public key
- Recovery runbook (this doc, abbreviated)
- Last known good backup date + R2 path

Stored in a fireproof safe. Updated quarterly.

---

## R2 Bucket Configuration

**Bucket name:** `bunche-backups`

**Lifecycle rules:**

| Rule | Action |
|------|--------|
| Files older than 90 days in `daily/` | Auto-delete |
| Files older than 365 days in `monthly/` | Move to R2 Infrequent Access (cheaper) |
| All files | Server-side encryption (R2-managed keys) |

**Monthly archive** (first backup of each month) is kept for 1 year as a longer-term safety net.

**Access control:** R2 bucket is **private**. Only the VPS service account has read/write. Restoration requires Styxproxy backup private key (operator-held).

---

## Backup Verification

**Monthly restore test** (every 1st of the month, 02:30 — right after backup):

1. Spin up a temporary PostgreSQL container
2. Restore latest backup to it
3. Run sanity queries:
   - `SELECT COUNT(*) FROM customers;` — should match live count
   - `SELECT SUM(amount) FROM orders WHERE created_at > NOW() - INTERVAL '7 days';` — sanity-check revenue
   - `SELECT COUNT(*) FROM data_alert_history WHERE alert_sent_at > NOW() - INTERVAL '7 days';` — sanity-check cron ran
4. Compare to live DB
5. Alert admin if mismatch >5%

**This catches:**
- Silent backup corruption
- Schema changes that broke backup format
- Disk-full on backup destination
- Encryption key drift

---

## What Is NOT Backed Up

| Item | Why not | Recovery path |
|------|---------|---------------|
| `.env` | Backups should never contain live secrets | Re-enter from operator memory / 1Password |
| `n8n execution logs` | Stored in PostgreSQL already | DB restore covers it |
| Provider API responses (in-memory) | Ephemeral by design | Re-call API if needed |
| Cloudflare R2 user files | R2 has its own redundancy + lifecycle | Already durable |
| Customer WhatsApp messages (real-time) | Twilio/Meta owns these | Re-request from Meta if compliance audit |

---

## Cost Analysis

| Component | Cost |
|-----------|------|
| VPS local disk (50GB) | Included in Hetzner CX21 |
| R2 storage (90 days × 5GB compressed) | ~$0.04/month |
| R2 PUT requests (90/month) | Free tier |
| R2 GET requests (restores ~10/month) | Free tier |
| Age encryption overhead | Negligible |
| **Total backup cost** | **~$0.04/month** |

---

## Alternatives Considered

### Option A: Backup only to VPS local disk

**Rejected.** Single point of failure (VPS hardware loss = both prod and backup gone).

### Option B: AWS S3 Glacier for archival

**Rejected.** AWS bill + cross-region latency. R2 is cheaper and closer to our actual operational geography.

### Option C: Continuous logical replication to a second VPS

**Rejected for Phase 1.** Doubles VPS cost. Daily backup + monthly restore test gives us acceptable risk profile. Reconsider at 5,000+ customers.

### Option D: Managed PostgreSQL (Cloud SQL / Supabase / RDS)

**Rejected.** Cost ($25+/month minimum) + vendor lock-in + cross-region latency. We self-host in Phase 1 because Hetzner VPS already runs n8n. Same machine = same network = same ops story.

---

## Consequences

### Positive

- **$0.04/month cost** — essentially free
- **RPO = 24h** — acceptable for proxy resale (no life-safety implications)
- **RTO = 4h** — measurable, tested
- **Recovery is rehearsed** — monthly test catches drift
- **Encrypted at rest** — R2 bucket is encrypted, backups are encrypted separately

### Negative

- **24h data loss on full DB failure** — acceptable but not ideal
- **Manual restore requires operator** — no self-service for customers
- **One R2 region** — multi-region replication adds cost we don't need yet
- **Backup verification is monthly, not daily** — could miss recent corruption

### Mitigations

| Risk | Mitigation |
|------|------------|
| 24h data loss | Phase 2: WAL archiving (15-min RPO) once we're at 1,000+ customers |
| Operator unavailability | Runbook in 1Password + paper copy in safe |
| Single R2 region | Phase 3: replicate to second R2 region or Backblaze B2 when revenue justifies |
| Daily verification gap | Add daily `pg_dump | head -c 1` smoke test (alert if dump is empty) |

---

## Phase Plan

| Phase | When | What changes |
|-------|------|--------------|
| **1 — Launch** | Day 1 | Daily full dump + R2 upload + local 7-day retention |
| **2 — Scale** | 1,000 customers (~Month 3) | + WAL archiving (15-min RPO), + monthly verify |
| **3 — Mature** | 10,000 customers (~Year 1) | + Second region replication, + Point-in-Time Recovery test |

---

## Related

- `docs/DEPLOYMENT.md` §9 — Backup script installation
- `.env.example` — `BACKUP_RCLONE_PROFILE`, `BACKUP_DIR` variables
- `ADR-004` — Secrets Management (what gets excluded from backups)
- `docs/SECURITY_PLAN.md` — Layer 6 (Disaster Recovery)