# Bunche — Database Backup Strategy

**Last Updated:** 2026-07-01
**Purpose:** Complete backup and restore strategy for PostgreSQL — what to back up, how often, where to, how to restore, and disaster recovery.

---

## Overview

```
PostgreSQL (bunche database)
        │
        │ pg_dump (daily, 2am)
        ▼
/backup/bunche/bunche_YYYY-MM-DD.dump.age
   (age-encrypted, 7-day local retention)
        │
        │ rclone copy → R2
        ▼
Cloudflare R2: r2:bunche-backups/daily/
   (90-day lifecycle rule)
        │
        │ (first of each month)
        ▼
Cloudflare R2: r2:bunche-backups/monthly/
   (365-day retention)
```

**Encryption:** All backups encrypted with `age` before upload. Private key stored OFF-SERVER (1Password + paper copy).

---

## What's Backed Up

### PostgreSQL Tables

| Table | Data | Why it matters |
|---|---|---|
| `instant_orders` | Anonymous orders, tx_ref, IP, status | Core business data |
| `platform_accounts` | Telegram/WhatsApp chat IDs, hashed phone | Customer records |
| `bunche_credentials` | Username → provider IP mapping | Access control |
| `orders` | Chat-based orders | Core business data |
| `free_trials` | Trial sessions | Customer acquisition |
| `pending_trial_surveys` | Theorem Reach postbacks | Revenue tracking |
| `admin_auth` | Admin credentials (hashed) | Security |
| `admin_commands_log` | Immutable audit trail | Compliance |
| `customer_audit_log` | All customer actions | Audit trail |
| `processed_webhooks` | Idempotency records | Prevents replay attacks |
| `rate_limit_log` | Rate limit tracking | Security |

**NOT backed up (ephemeral):**
- Redis data (cache, queues — rebuilt from DB)
- n8n SQLite (has its own backup)
- 3proxy config (rebuilt from scripts)

---

## Backup Schedule

| Time | What | Script | Where it goes |
|---|---|---|---|
| 2:00am daily | Full pg_dump + age encrypt + R2 upload | `backup-bunche.sh` | `r2:bunche-backups/daily/` |
| 2:05am 1st of month | Copy first-of-month to monthly | `backup-monthly-archive.sh` | `r2:bunche-backups/monthly/` |
| 1st of month | Restore test (verify mode) | `backup-bunche.sh --verify` | Docker temp container |
| Every 7 days | Delete local backups older than 7 days | `backup-bunche.sh` | Local `/backup/bunche/` |

**R2 Lifecycle Rules:**
- `daily/` prefix: objects expire after 90 days
- `monthly/` prefix: objects expire after 365 days

---

## Cron Setup

```bash
# /etc/crontab

# Daily backup — 2:00am every day
0 2 * * * root /usr/local/bin/backup-bunche.sh >> /var/log/bunche-backup.log 2>&1

# Monthly archive — 2:05am on the 1st of each month
5 2 1 * * root /usr/local/bin/backup-monthly-archive.sh >> /var/log/bunche-backup.log 2>&1
```

---

## Restore Procedure

### Step 1: Download from R2

```bash
# Install age and rclone if not present
sudo apt install age
sudo apt install rclone

# Configure rclone (if not already configured)
rclone config
# Choose: s3 provider, Cloudflare, enter R2 credentials

# Download the backup you need
# For a specific date:
rclone copy "r2:bunche-backups/daily/2026-07-01/" /tmp/restore/ --dry-run  # preview first

rclone copy "r2:bunche-backups/daily/2026-07-01/bunche_2026-07-01.dump.age" /tmp/restore/

# For monthly (longer retention):
rclone copy "r2:bunche-backups/monthly/2026-07/" /tmp/restore/
```

### Step 2: Decrypt

```bash
# Get the backup private key (from 1Password — NEVER from the server)
# On a secure offline machine, extract from 1Password, transfer via USB to server

# Decrypt
age --decrypt \
  --identity /path/to/bunche-backup-private.key \
  --output /tmp/restore/bunche_2026-07-01.dump \
  /tmp/restore/bunche_2026-07-01.dump.age
```

### Step 3: Restore to PostgreSQL

```bash
# Option A: Restore to existing database (DESTRUCTIVE — use only if current DB is corrupt)
sudo systemctl stop bunche-api  # Stop the API first
sudo -u postgres psql -c "DROP DATABASE bunche;"  # Must be superuser
sudo -u postgres psql -c "CREATE DATABASE bunche;"

pg_restore \
  --host=localhost \
  --username=bunche \
  --dbname=bunche \
  --no-owner \
  --no-privileges \
  --clean \
  /tmp/restore/bunche_2026-07-01.dump

sudo systemctl start bunche-api

# Option B: Restore to a new database (for verification, not production)
sudo -u postgres psql -c "CREATE DATABASE bunche_restore;"
pg_restore --dbname=bunche_restore /tmp/restore/bunche_2026-07-01.dump
```

### Step 4: Verify

```bash
# Check row counts match expectations
sudo -u postgres psql -d bunche -c "SELECT COUNT(*) FROM instant_orders;"
sudo -u postgres psql -d bunche -c "SELECT COUNT(*) FROM bunche_credentials;"
sudo -u postgres psql -d bunche -c "SELECT COUNT(*) FROM admin_auth;"

# Check recent orders exist
sudo -u postgres psql -d bunche -c "SELECT tx_ref, status, created_at FROM instant_orders ORDER BY created_at DESC LIMIT 5;"
```

---

## Disaster Recovery Plan

### Scenario 1: Database server crashes

**Recovery time objective (RTO):** 2 hours
**Recovery point objective (RPO):** 24 hours (last daily backup)

**Steps:**
1. Provision new PostgreSQL server
2. Install PostgreSQL 16
3. Configure `pg_hba.conf` and `postgresql.conf`
4. Restore latest daily backup (see restore procedure above)
5. Verify data integrity
6. Point backend API at new server (update `POSTGRES_HOST` in `.env`)
7. Restart backend API
8. Verify site works

### Scenario 2: R2 bucket corrupted (rare)

**Prevention:** R2 has version history — enable versioning on the bucket.
**Recovery:** Download from a previous version using `rclone ls --avici-join`.

### Scenario 3: Encryption key lost

**Prevention:** Private key in 3 places — 1Password vault, paper copy in fireproof safe, trusted offline USB drive.
**Recovery:** If key is lost and local unencrypted backups don't exist, data is unrecoverable. This is why key management is critical.

### Scenario 4: Accidental data deletion by admin

**Prevention:** No DELETE permission on `admin_commands_log` for any DB user.
**Recovery:** Identify the `tx_ref` or admin action. Restore from previous night's backup. Replay any orders that came in after the backup.

---

## Backup Verification

### Automated (Monthly)

The `backup-bunche.sh --verify` flag runs on the 1st of every month:

```bash
# What it does:
# 1. Decrypts the latest backup
# 2. Spins up a throwaway Docker PostgreSQL container
# 3. Restores the backup to that container
# 4. Runs sanity checks (customer count, order count)
# 5. Tears down the container
# 6. Reports result to n8n via webhook
```

If verification fails, n8n sends an alert to the admin team.

### Manual (Before Any Major Change)

Before any database migration, schema change, or major backend deployment:

```bash
# Take a manual backup
sudo systemctl stop bunche-api
pg_dump --host=localhost --username=bunche --dbname=bunche --format=custom --file=/backup/bunche/pre-migration.dump
sudo systemctl start bunche-api

# Verify you can restore it
pg_restore --dbname=bunche_precheck /backup/bunche/pre-migration.dump
```

---

## Encryption Key Management

**Critical rule:** The backup private key must NEVER be on the same server as the backups.

### Generate the Key

```bash
# On a secure, offline machine
age-keygen -o bunche-backup.key
# Output:
# age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  <— this goes in /etc/bunche/backup.conf as BACKUP_PUBLIC_KEY
# The private key (the large base64 string) goes in 1Password + paper + USB
```

### Store in 3 places minimum

| Location | Format | Who has access |
|---|---|---|
| 1Password (Bunche vault) | Private key text | CTO + 1 other trusted person |
| Paper copy | Printed private key | Fireproof safe, office |
| Encrypted USB | `.key` file | CTO only |

### Key Rotation

Rotate the backup encryption key every 12 months:
1. Generate new keypair
2. Update `BACKUP_PUBLIC_KEY` in `/etc/bunche/backup.conf`
3. Restart backup cron
4. Old backups remain encrypted with old key (keep old key accessible for restore)
5. Store new key in 1Password + paper + USB

---

## Storage Costs (R2)

| Backup type | Size (estimated) | Monthly cost |
|---|---|---|
| Daily (90-day retention) | ~50MB compressed × 90 | ~$0.01/month |
| Monthly (365-day retention) | ~50MB × 12 | ~$0.01/month |
| **Total** | | **~$0.02/month** |

R2 pricing: $0.015/GB/month storage. At 50MB/day × 90 days = 4.5GB = ~$0.07/month. Very cheap insurance.

---

## Pre-Launch Backup Checklist

- [ ] PostgreSQL installed and configured on VPS
- [ ] `pg_hba.conf` set to localhost-only (no external access)
- [ ] `/etc/bunche/backup.conf` created with correct credentials
- [ ] `chmod 600 /etc/bunche/backup.conf`
- [ ] age installed: `sudo apt install age`
- [ ] rclone installed and configured with R2 credentials
- [ ] Backup encryption key generated (on offline machine)
- [ ] Public key in `backup.conf`, private key in 3 safe places
- [ ] R2 bucket created: `bunche-backups` with `daily/` and `monthly/` prefixes
- [ ] R2 lifecycle rules set: daily → 90 days, monthly → 365 days
- [ ] R2 versioning enabled (for Scenario 2 protection)
- [ ] Cron jobs added to `/etc/crontab`
- [ ] `/var/log/bunche-backup.log` rotation configured (`logrotate`)
- [ ] Test backup run: `sudo /usr/local/bin/backup-bunche.sh`
- [ ] Verify backup file appears in R2
- [ ] Test restore to Docker container: `sudo /usr/local/bin/backup-bunche.sh --verify`
- [ ] Verify n8n webhook URL is live for backup alerts
- [ ] Alert tested: manually trigger size alert → does n8n webhook fire?
- [ ] Backup log rotation: `/var/log/bunche-backup.log` → weekly rotate, 4 weeks kept

---

## Monitoring Alerts

The backup system sends alerts via n8n webhook when:

| Alert | Trigger | Severity |
|---|---|---|
| Backup size anomaly | Backup is <50% or >200% of 7-day average | High |
| Backup failed | Script exits with non-zero | Critical |
| Restore verification failed | `--verify` mode reports empty tables | Critical |

SuperAdmin receives backup failure alerts. If SuperAdmin is unreachable, Admin gets the alert.

---

*This strategy is the source of truth for Bunche backup and restore. Update before launch.*
