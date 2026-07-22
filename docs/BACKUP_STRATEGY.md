# Styxproxy — Database Backup Strategy (Free)

**Last Updated:** 2026-07-01
**Purpose:** Complete free backup strategy for Styxproxy PostgreSQL — what to back up, how often, where to, how to restore.

---

## Overview

Fully free. No Hetzner. No paid storage. Upgrade to paid services when Styxproxy starts earning.

```
Local disk (6 hours):
  /backup/bunche/dumps/bunche_20260701_1400.dump

Backblaze B2 (free tier — 5GB):
  r2:bunche-backups/ ← Restic deduplication (only changed blocks uploaded)
  Hourly snapshots: last 72 (3 days)
  Daily snapshots: last 30 (30 days)
```

**Restic deduplication is the key.** Restic doesn't upload the whole database every hour. It only uploads the blocks that changed. At 10k customers, each hourly backup might only upload 5-10MB of changed data — not 50MB.

**5GB B2 free tier ≈ 500+ hourly backups** even at full scale.

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

**NOT backed up (ephemeral):**
- Redis data (cache, queues — rebuilt from DB)
- n8n SQLite (has its own backup)
- 3proxy config (rebuilt from scripts)

---

## Backup Schedule

| Time | What | Script | Where it goes |
|---|---|---|---|
| Every hour (:00) | pg_dump → Restic backup | `backup-hourly.sh` | B2 (72 hourly snapshots) |
| 3am daily | pg_dump → Restic backup | `backup-daily.sh` | B2 (30 daily snapshots) |
| Every hour | Local pg_dump | `backup-hourly.sh` | `/backup/bunche/dumps/` (6 files max) |

**Local cleanup:** Every hour, local dumps older than 6 hours are deleted.
**B2 cleanup:** Restic automatically deletes snapshots older than retention policy.

---

## Cron Setup

```bash
# /etc/crontab

# Hourly backup — every hour at :00
0 * * * * root /usr/local/bin/backup-hourly.sh >> /var/log/bunche-backup.log 2>&1

# Daily backup — 3am every day
0 3 * * * root /usr/local/bin/backup-daily.sh >> /var/log/bunche-backup.log 2>&1
```

---

## What 5GB Actually Holds (Restic Deduplication)

| DB state | Dump size | Restic uploads per hour | Backups in B2 |
|---|---|---|---|
| Fresh DB | 50MB | 5MB | ~1,000 |
| 1,000 orders | 52MB | 5MB | ~1,000 |
| 5,000 orders | 70MB | 8MB | ~625 |
| 10,000 orders | 100MB | 10MB | ~500 |

Even at 10,000 customers, you get **~500 hourly backups** before hitting B2's free limit.

When B2 fills up (~3 weeks at 10k customers with full activity):
- Migrate to **Hetzner Storage Box** (100GB for €3.49/month) or **BunnyNet** (100GB for ~$3/month)
- Or delete old snapshots to free up space

---

## Data Loss (Honest Answer)

| What | Data loss |
|---|---|
| Crash between backups | Up to 1 hour of orders lost |
| Recoverable? | YES — Flutterwave transaction log |

**How to recover the lost hour:**
1. Restore from latest pg_dump
2. Go to Flutterwave Dashboard → Transactions
3. Find all payments with `tx_ref` in the last hour not in your DB
4. Manually re-insert into `instant_orders` table
5. Re-run IP generation for those orders

This is **not zero data loss**. But it's **recoverable data loss** — Flutterwave has every transaction record.

When you upgrade to paid (Hetzner Storage Box), you get Point-In-Time Recovery (PITR) — restore to any second, zero data loss.

---

## Restore Procedure

### Step 1: List available snapshots

```bash
sudo /usr/local/bin/restore.sh --list
```

Output:
```
Available snapshots in B2:
  abc12345 | 2026-07-01 14:00 | hourly | 1 files
  def67890 | 2026-07-01 13:00 | hourly | 1 files
  ghi11111 | 2026-07-01 12:00 | daily  | 1 files
```

### Step 2: Verify the backup first (always do this)

```bash
# Verify latest backup (no DB overwrite)
sudo /usr/local/bin/restore.sh --verify

# Verify a specific snapshot
sudo /usr/local/bin/restore.sh --verify abc12345
```

This:
1. Downloads the snapshot from B2
2. Restores to a temporary database
3. Checks row counts in key tables
4. Reports if backup is valid
5. Cleans up temp DB

### Step 3: Full restore (overwrites DB)

```bash
# Restore latest backup
sudo /usr/local/bin/restore.sh --restore

# Restore specific snapshot
sudo /usr/local/bin/restore.sh --restore abc12345
```

**What happens:**
1. Styxproxy API is stopped
2. Current database is dropped
3. Backup is restored
4. API is restarted
5. Row counts are verified

---

## Disaster Recovery Plan

### Scenario 1: Database server crashes

**Recovery time:** 10-15 minutes
**Data loss:** Up to 1 hour

```bash
# 1. Fix/reprovision the server
# 2. Install PostgreSQL
# 3. Copy /etc/bunche/backup.conf
# 4. Install restic: sudo apt install restic
# 5. Configure rclone: rclone config (add B2 credentials)
# 6. Restore latest backup:
sudo /usr/local/bin/restore.sh --restore
# 7. Verify:
psql -U bunche -d bunche -c "SELECT COUNT(*) FROM instant_orders;"
# 8. Restart API
```

### Scenario 2: Accidentally deleted an order

**Recovery time:** 15 minutes
**Data loss:** 0

```bash
# 1. Find the tx_ref
# 2. Check which snapshot had the order:
#    - Go back through restic snapshots until you find one with the order
#    - restore.sh --verify on each snapshot
# 3. Restore to a temp DB to extract the row
# 4. Re-insert the row into current DB
```

### Scenario 3: B2 bucket full

**Detection:** `restic snapshots` shows no new snapshots for 2+ hours

**Fix:**
```bash
# Option A: Delete old snapshots to free space
restic -r b2:bunche-backups forget --keep-hourly 24 --prune

# Option B: Migrate to Hetzner Storage Box
#   1. Create Hetzner Storage Box account
#   2. rclone config → hetzner
#   3. Copy all snapshots: rclone copy b2:bunche-backups hetzner:bunche-backups
#   4. Update restore.sh to use hetzner remote
```

### Scenario 4: Encryption key lost

**Prevention:** Private key stored in 3 places (see below).

**If lost:** Backups cannot be decrypted. This is why key management is critical.

---

## Encryption Key Management

**Critical rule:** The Restic encryption password must NEVER be on the same server as the backups (or at least not in the same accessible place).

### Generate the Password

```bash
# On any machine
openssl rand -base64 32
# Example output: YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=
```

### Store in 3 places minimum

| Location | Format | Who has access |
|---|---|---|
| 1Password (Styxproxy vault) | Password entry | CTO + 1 trusted person |
| Paper copy | Printed or handwritten | Fireproof safe |
| Trusted person | Verbal/SMS | 1 other person |

### Key Rotation

Rotate every 12 months:
1. Generate new password
2. Update `RESTIC_PASSWORD` in `/etc/bunche/backup.conf`
3. Restart cron (the next backup will re-encrypt everything)
4. Old backups remain accessible with old key (keep both accessible for 30 days)
5. Update key in 1Password + paper copy

---

## Monitoring

### Backup Success Monitoring

The scripts log to `/var/log/bunche-backup.log`. Set up a simple check:

```bash
# Add to crontab (runs at 6am daily)
0 6 * * * grep -q "complete ✓" /var/log/bunche-backup.log || \
  curl -s -X POST https://api.pagerduty.com/v2/enqueue \
    -H "Content-Type: application/json" \
    -d '{"routing_key":"YOUR_KEY","event_action":"trigger","payload":{"summary":"Backup failed"}}'
```

Or use UptimeRobot's API to check the log file.

### UptimeRobot (Site Monitoring)

**Free tier:** 50 monitors, 5-minute check interval, email alerts.

```bash
# Set up at:uptimerobot.com
# Monitor: https://styxproxy.com (check HTTP 200)
# Monitor: https://api.styxproxy.com/health (check HTTP 200)
# Alert: email to admin@styxproxy.com
```

If the site goes down, UptimeRobot emails you immediately. You decide whether to restore.

**There is NO automatic rollback.** UptimeRobot tells you something is wrong → you assess → you decide if and what to restore.

---

## Pre-Launch Backup Setup (All Free)

```bash
# 1. Create Backblaze B2 account
#    → backblaze.com/b2 → sign up (free, no credit card)
#    → Create bucket: "bunche-backups" (public: no)
#    → Create application key: note the keyID and applicationKey

# 2. Install restic
sudo apt install restic

# 3. Configure rclone for B2
sudo apt install rclone
rclone config
# Choose:
#   name: b2
#   type: b2
#   account: <keyID>
#   key: <applicationKey>

# 4. Generate Restic password
openssl rand -base64 32
# Store in 1Password + paper copy + give to trusted person

# 5. Initialize Restic repo
export RESTIC_PASSWORD="<your-password>"
restic -r b2:bunche-backups init

# 6. Create config
sudo cp /root/bunche/scripts/backup.conf.example /etc/bunche/backup.conf
sudo chmod 600 /etc/bunche/backup.conf
# Edit: set POSTGRES_USER, POSTGRES_DB, RESTIC_PASSWORD

# 7. Create directories
sudo mkdir -p /backup/bunche/dumps
sudo chown root:root /etc/bunche/backup.conf
sudo chmod 600 /etc/bunche/backup.conf

# 8. Copy scripts
sudo cp /root/bunche/scripts/backup-hourly.sh /usr/local/bin/
sudo cp /root/bunche/scripts/backup-daily.sh /usr/local/bin/
sudo cp /root/bunche/scripts/restore.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/backup-hourly.sh
sudo chmod +x /usr/local/bin/backup-daily.sh
sudo chmod +x /usr/local/bin/restore.sh

# 9. Add cron jobs
sudo crontab -e
# Add:
#   0 * * * * /usr/local/bin/backup-hourly.sh >> /var/log/bunche-backup.log 2>&1
#   0 3 * * * /usr/local/bin/backup-daily.sh >> /var/log/bunche-backup.log 2>&1

# 10. Test: run first backup
sudo /usr/local/bin/backup-hourly.sh

# 11. Verify backup is in B2
restic -r b2:bunche-backups snapshots

# 12. Test restore to temp DB
sudo /usr/local/bin/restore.sh --verify

# 13. Set up log rotation
sudo nano /etc/logrotate.d/bunche-backup
# Contents:
#   /var/log/bunche-backup.log {
#     weekly
#     rotate 4
#     compress
#     missingok
#     notifempty
#   }
```

---

## Upgrade Path (When Styxproxy Earns)

When Styxproxy starts generating revenue, upgrade from free tier to paid:

| Upgrade | Why | Cost |
|---|---|---|
| **Hetzner Storage Box** | 100GB, continuous WAL archiving, true PITR | €3.49/month |
| **Point-in-time recovery** | Restore to any second, zero data loss | Included with Storage Box |
| **Hetzner Snapshots** | Full VPS disk image, weekly | €1.00/month |

Total upgrade cost when ready: **~€4.50/month**

---

## Pre-Launch Checklist

- [ ] Backblaze B2 account created (free)
- [ ] B2 bucket created: `bunche-backups`
- [ ] B2 application key created (keyID + applicationKey noted)
- [ ] rclone configured with B2
- [ ] Restic repo initialized in B2
- [ ] Restic password generated and stored in 3 places
- [ ] `/etc/bunche/backup.conf` created with all credentials
- [ ] `chmod 600 /etc/bunche/backup.conf`
- [ ] Scripts installed to `/usr/local/bin/`
- [ ] Cron jobs added to `/etc/crontab`
- [ ] `/var/log/bunche-backup.log` rotation configured
- [ ] Test backup run: `sudo /usr/local/bin/backup-hourly.sh`
- [ ] Verify B2: `restic -r b2:bunche-backups snapshots`
- [ ] Test restore: `sudo /usr/local/bin/restore.sh --verify`
- [ ] UptimeRobot monitors set up (site + API health endpoint)
- [ ] First backup confirmed in B2 dashboard

---

## Scripts Reference

| Script | What it does |
|---|---|
| `backup-hourly.sh` | pg_dump → Restic → B2, keep last 72 hourly snapshots |
| `backup-daily.sh` | pg_dump → Restic → B2, keep last 30 daily snapshots |
| `restore.sh` | List/verify/restore from B2 snapshots |
| `backup.conf.example` | Template for `/etc/bunche/backup.conf` |

---

*This strategy is the source of truth. Update before launch.*
