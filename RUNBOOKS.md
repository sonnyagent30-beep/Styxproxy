# Styxproxy Operational Runbooks

**Last updated:** 2026-07-28
**Owner:** Sonny (Hermes orchestrator)
**Infra:** Interserver `162.35.184.69` is the SOLE production host. Contabo `84.247.132.12` is Dante-only.

---

## Table of Contents

1. [Service Status & Health Checks](#1-service-status--health-checks)
2. [API Restart](#2-api-restart)
3. [Database Restore from B2 Backup](#3-database-restore-from-b2-backup)
4. [Secret Rotation](#4-secret-rotation)
5. [SSL Certificate Renewal](#5-ssl-certificate-renewal)
6. [Dante Proxy Restart](#6-dante-proxy-restart)
7. [Monitoring Cron Health](#7-monitoring-cron-health)
8. [Incident Response](#8-incident-response)

---

## 1. Service Status & Health Checks

### Quick health (from anywhere)

```bash
# Public health endpoint (no auth required)
curl -s https://api.styxproxy.com/api/v1/health | python3 -m json.tool

# Expected:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "services": {
#     "database": "connected",
#     "redis": "connected",
#     "m2_cloud": "connected",
#     "litellm": "disconnected",   # OK — fallback
#     "ollama": "disconnected"     # OK — fallback
#   }
# }
```

### Service status on the host

```bash
ssh root@162.35.184.69

# All Styxproxy services
systemctl status styxproxy-api.service
systemctl status styxproxy-dante-auth.service
systemctl status styxproxy-dante-control.service

# Infrastructure
systemctl status postgresql@16-main
systemctl status redis-server
systemctl status nginx

# List everything Styxproxy-related
systemctl list-units | grep -E "styxproxy|postgres|redis|nginx"
```

### Port listeners

```bash
ss -tlnp | grep -E ':(80|443|5432|6379|8000|1080|1081|9000)'

# Expected:
# :80, :443        nginx (LE-terminated)
# :5432            postgres
# :6379            redis
# :8000            styxproxy-api (uvicorn)
# :1080            danted
# :1081            styxproxy-dante-auth
# :9000            styxproxy-dante-control
```

---

## 2. API Restart

The api is a `uvicorn` app served by `systemd`.

### Soft restart (no data loss)

```bash
ssh root@162.35.184.69
systemctl restart styxproxy-api.service
sleep 5
systemctl is-active styxproxy-api.service
curl -s http://127.0.0.1:8000/api/v1/health | head -1
```

### Hard restart (kill workers, reboot dependency order)

```bash
ssh root@162.35.184.69
systemctl stop styxproxy-api.service
sleep 2
# Kill any zombie workers
pkill -9 -f "uvicorn app.main" || true
sleep 1
systemctl start styxproxy-api.service
sleep 5
journalctl -u styxproxy-api.service -n 20 --no-pager
```

### After restart: verify

```bash
# Inside the host
curl -s http://127.0.0.1:8000/api/v1/health
# Then outside (proves nginx + LE are healthy)
curl -s https://api.styxproxy.com/api/v1/health
```

### Recent api logs

```bash
tail -50 /var/log/styxproxy-api.log
tail -20 /var/log/styxproxy-api.err.log
# Or
journalctl -u styxproxy-api.service -n 100 --no-pager
```

---

## 3. Database Restore from B2 Backup

### When to use

- DB is corrupted / dropped / out of sync
- Need to test migrations against real data
- Customer data disaster recovery

### Source of truth

- **Backups live in B2:** `b2-styxproxy:styxproxy-backups/pg_dump/`
- **Local backup (last 24h):** Contabo `/root/backups/styxproxy-pg/`
- **Encryption:** `age` X25519, recipient `age1qdr39xzhurz58eg79n3uyumyq7enzps2mcmd30pxyycpxjamfahqpu636d`
- **Decryption key (CRITICAL — back up off-VPS):** Contabo `/root/.hermes/keys/age-backup.key`
  - **MUST be in 1Password or printed paper backup.** If Contabo dies and you lose this key, all backups become unrecoverable.

### Restore drill (verified Jul 28 — works end-to-end)

```bash
# On Contabo (where age + rclone + private key live)
mkdir -p /tmp/restore-drill
cd /tmp/restore-drill

# 1. Download latest backup from B2
rclone copyto b2-styxproxy:styxproxy-backups/pg_dump/<FILENAME> ./backup.sql.gz.age

# 2. Decrypt
age -d -i /root/.hermes/keys/age-backup.key ./backup.sql.gz.age > ./backup.sql.gz

# 3. Decompress
gunzip ./backup.sql.gz

# 4. Push to Interserver
scp -i ~/.ssh/styxproxy-interserver ./backup.sql root@162.35.184.69:/tmp/restore.sql

# 5. On Interserver: restore to a NEW test DB (NEVER overwrite prod in a drill)
ssh root@162.35.184.69
sudo -u postgres psql -c "CREATE DATABASE styxproxy_restore_test OWNER styxproxy;"
sudo -u postgres psql -d styxproxy_restore_test -f /tmp/restore.sql
sudo -u postgres psql -d styxproxy_restore_test -c "\dt"
# Verify row counts match expected
sudo -u postgres psql -d styxproxy_restore_test -c "SELECT COUNT(*) FROM admin_auth;"

# 6. Drop test DB when done
sudo -u postgres psql -c "DROP DATABASE styxproxy_restore_test;"
rm -f /tmp/restore.sql
```

### RESTORE TO PROD (destructive — only when needed)

```bash
ssh root@162.35.184.69

# 1. Stop the api so it doesn't fight the restore
systemctl stop styxproxy-api.service

# 2. Drop and recreate the prod DB (this is irreversible without another backup)
sudo -u postgres psql -c "DROP DATABASE styxproxy;"
sudo -u postgres psql -c "CREATE DATABASE styxproxy OWNER styxproxy;"

# 3. Restore
sudo -u postgres psql -d styxproxy -f /tmp/restore.sql

# 4. Run any migrations that came after the backup timestamp
cd /opt/styxproxy/repo/backend
source /opt/styxproxy/backend/venv/bin/activate
alembic upgrade head

# 5. Restart api
systemctl start styxproxy-api.service

# 6. Smoke test
curl -s https://api.styxproxy.com/api/v1/health
```

---

## 4. Secret Rotation

Styxproxy prod secrets live in `/opt/styxproxy/.env` on Interserver.

### What's in there

- `TOTP_SECRET` — only used at admin setup time (per-admin DB TOTP secrets unaffected)
- `JWT_SECRET` — used to sign access tokens
- `ADMIN_TOKEN` — used by `/api/admin/auth/admin-token` route
- `SENTRY_DSN` — error monitoring
- Various B2, Telegram, WhatsApp keys

### Rotate TOTP_SECRET + JWT_SECRET + ADMIN_TOKEN

```bash
ssh root@162.35.184.69

# Backup current env
cp /opt/styxproxy/.env /opt/styxproxy/.env.backup-$(date +%Y%m%d-%H%M%S)

# Generate fresh values
NEW_TOTP=$(python3 -c 'import secrets,base64; print(base32 := base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("="))')
NEW_JWT=$(openssl rand -base64 48)
NEW_ADMIN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

# Patch .env (use sed or editor of choice)
sed -i "s|^TOTP_SECRET=.*|TOTP_SECRET=${NEW_TOTP}|" /opt/styxproxy/.env
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${NEW_JWT}|" /opt/styxproxy/.env
sed -i "s|^ADMIN_TOKEN=.*|ADMIN_TOKEN=${NEW_ADMIN}|" /opt/styxproxy/.env

# Restart api to pick up
systemctl restart styxproxy-api.service

# Verify
curl -s https://api.styxproxy.com/api/v1/health
```

### IMPORTANT: TOTP rotation does NOT invalidate admin DB TOTP secrets

Per `backend/app/routers/auth.py:530-538`, the per-admin `admin_auth.totp_secret` column is the source of truth for verifying admin TOTP codes. The env `TOTP_SECRET` is only used at admin setup time. Existing admins keep working after env rotation.

---

## 5. SSL Certificate Renewal

LE certs auto-renew via `certbot.timer`. Verify the timer:

```bash
ssh root@162.35.184.69
systemctl list-timers | grep certbot
certbot certificates
```

### Manual renewal (if timer fails)

```bash
ssh root@162.35.184.69
certbot renew --force-renewal
systemctl reload nginx
# Verify
echo | openssl s_client -connect api.styxproxy.com:443 -servername api.styxproxy.com 2>/dev/null | openssl x509 -noout -dates
```

### Cert files location

- Cert: `/etc/letsencrypt/live/api.styxproxy.com/fullchain.pem`
- Key: `/etc/letsencrypt/live/api.styxproxy.com/privkey.pem`
- nginx config: `/etc/nginx/sites-enabled/styxproxy.conf`

---

## 6. Dante Proxy Restart

Dante is split across 3 services on Contabo `84.247.132.12`:

- `danted.service` (port 1080) — main SOCKS proxy
- `styxproxy-dante-auth.service` (port 1081) — auth API
- `styxproxy-dante-control.service` (port 9000) — control API

### Restart all three

```bash
ssh root@84.247.132.12
systemctl restart danted.service
systemctl restart styxproxy-dante-auth.service
systemctl restart styxproxy-dante-control.service
sleep 3
systemctl status danted.service
systemctl status styxproxy-dante-auth.service
systemctl status styxproxy-dante-control.service
ss -tlnp | grep -E ':(1080|1081|9000)'
```

### Config locations

- `/etc/danted.conf` — main config
- `/opt/styxproxy-dante/auth/` — auth API
- `/opt/styxproxy-dante/control/` — control API
- `/var/log/danted.log` — main proxy log

---

## 7. Monitoring Cron Health

Two crons on Contabo:

- `*/5 * * * *` — `styxproxy_monitor.py` (every 5 min, health checks + alerts)
- `5 3 * * *` — `styxproxy_pg_dump_to_b2.sh` (3am UTC daily, pg_dump → encrypt → B2)

### Check cron is running

```bash
ssh root@84.247.132.12
crontab -l | grep -E "styxproxy|backup"
systemctl status cron
tail -10 /var/log/styxproxy-monitor.log
tail -10 /var/log/styxproxy-pgdump.log
```

### Manually trigger backup

```bash
ssh root@84.247.132.12
/root/.hermes/scripts/styxproxy_pg_dump_to_b2.sh
# Check log
tail -20 /var/log/styxproxy-pgdump.log
# Verify B2 has new file
rclone lsl b2-styxproxy:styxproxy-backups/pg_dump/ | tail -5
```

### Restore the age identity key (DR scenario)

If `/root/.hermes/keys/age-backup.key` is lost, all B2 backups are unreadable. This key MUST be backed up to:
- 1Password (or equivalent password manager)
- Printed paper in a safe
- Encrypted USB drive off-site

The recipient (public) half is in `/opt/styxproxy/.env` style: `age1qdr39xzhurz58eg79n3uyumyq7enzps2mcmd30pxyycpxjamfahqpu636d`

---

## 8. Incident Response

### Severity levels

| Level | Description | Response time | Notify |
|---|---|---|---|
| **P0** | Site down, payments broken, data loss | Immediate | Dannion via Telegram + email |
| **P1** | Major feature broken, no workaround | < 1 hour | Dannion via Telegram |
| **P2** | Minor bug, workaround exists | < 24 hours | Notion backlog |
| **P3** | Cosmetic, polish | Backlog | Notion backlog |

### P0 playbooks

**Site completely down:**
1. Check api: `curl -s https://api.styxproxy.com/api/v1/health`
2. If down → SSH to Interserver, `systemctl restart styxproxy-api.service`
3. Still down → check DB: `sudo -u postgres psql -d styxproxy -c "SELECT 1;"`
4. Still down → check nginx: `nginx -t && systemctl reload nginx`
5. Still down → check Cloudflare DNS for `api.styxproxy.com` (should A→162.35.184.69)

**Database corruption / data loss:**
1. Stop api: `systemctl stop styxproxy-api.service`
2. Run [Database Restore from B2 Backup](#3-database-restore-from-b2-backup) — RESTORE TO PROD
3. Run migrations: `cd /opt/styxproxy/repo/backend && source venv/bin/activate && alembic upgrade head`
4. Restart api: `systemctl start styxproxy-api.service`
5. Verify health

**Secrets leaked (git, Slack, etc.):**
1. Rotate immediately per [Secret Rotation](#4-secret-rotation)
2. Audit logs for misuse
3. Git history scrub via `git-filter-repo --blob-callback` (see Sprint 1.3 docs)
4. Force-push to GitHub via SSH

**Sentry alerts (post-Sprint 5.8):**
1. Check Sentry dashboard: https://dannion-creative-hub.sentry.io
2. Filter by project (frontend/backend) and environment (production)
3. For each new error: assess severity, decide if P0/P1/P2

### Notification channels

- **Dannion Telegram:** `+234 703 298 1049`
- **Dannion Email:** `oyebiyiayomide30@gmail.com`
- **Hermes monitor cron:** `/var/log/styxproxy-monitor.log` (auto-alerts via Telegram bot)

### Postmortem

After any P0:
1. Write postmortem in Notion (`Tech Upgrades Backlog`)
2. Identify root cause + contributing factors
3. List action items with owners + deadlines
4. Track until complete
---

## 9. Critical: Repo vs Live Backend

There are TWO copies of the backend:
- Repo (git): /opt/styxproxy/repo/backend/ - what GitHub sees, what CI tests
- Live (running): /opt/styxproxy/backend/ - what uvicorn app.main:app actually executes

The systemd unit styxproxy-api.service runs from /opt/styxproxy/backend/. All edits to /opt/styxproxy/repo/backend/ do NOT affect the live api until you sync them.

### Sync procedure after editing repo files
\\`\\`\\`bash
SYNC_FILES=( "backend/app/main.py" "backend/app/routers/auth.py" "backend/app/routers/orders.py" )
for f in "${SYNC_FILES[@]}"; do
  scp -i ~/.ssh/styxproxy-interserver "/opt/styxproxy/repo/$f" "root@162.35.184.69:/opt/styxproxy/$f"
done
ssh -i ~/.ssh/styxproxy-interserver root@162.35.184.69 "find /opt/styxproxy/backend -name __pycache__ -type d -exec rm -rf {} +; systemctl restart styxproxy-api.service"
\\`\\`\\`

---

## §10 DNS Cutover (Cloudflare)

**When**: Migrating domain between hosts, or pointing to a new VPS.

### Current DNS state
- `styxproxy.com` → Cloudflare-proxied (proxy enabled, real IP hidden)
- `api.styxproxy.com` → Cloudflare A record → `162.35.184.69` (Interserver)
- Admin pages same.

### Cutover procedure (5-step)

1. **Pre-cut**: Lower DNS TTL on the affected records to 60s at Cloudflare
   \\`\\`\\`bash
   CF_API="https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records/$CF_RECORD_ID"
   curl -s -X PATCH "$CF_API" -H "Authorization: Bearer $CF_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{"type":"A","name":"api","content":"162.35.184.69","ttl":60}'
   \\`\\`\\`

2. **Wait 24 hours** for old TTLs to expire across global resolvers.

3. **New server ready + nginx configured** with LE certs (try `certbot --nginx -d api.styxproxy.com`).

4. **Cutover** (atomic DNS swap, ~5 seconds of stale-cache probability):
   \\`\\`\\`bash
   curl -s -X PATCH "$CF_API" -H "Authorization: Bearer $CF_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{"type":"A","content":"$NEW_IP"}'
   \\`\\`\\`

5. **Verify**:  From a different network (`curl --resolve api.styxproxy.com:443:$NEW_IP https://api.styxproxy.com/api/v1/health`).
   After 24h, restore TTL to 3600.

### Rollback
- Re-point DNS to old IP (same patch, just flip content).
- DNS will revert in ≤TTL window (1-60s if TTL was lowered).

---

## §11 Monitoring (Prometheus node_exporter)

**Installed**: `2026-07-28 17:24 UTC` on Interserver via apt package `prometheus-node-exporter`.
**Bound to**: `:9100` on `127.0.0.1` (binds to all interfaces — secured by UFW).
**Unit**: `/lib/systemd/system/prometheus-node-exporter.service` (auto-start enabled).

### Network access control (UFW)

\\`\\`\\`bash
# External scrape blocked by default
# (UFW policy = DROP, only 22/80/443/1080/8000/5432/6379/9000/1081/9100 allowed)

# Contabo (Prometheus scraper) only:
ufw allow from 84.247.132.12 to any port 9100 proto tcp comment "prometheus scrape from Contabo"

# Verify
ufw status | grep 9100
# 9100/tcp   ALLOW   84.247.132.12   # prometheus scrape from Contabo
\\`\\`\\`

### Test scrape (from Contabo)

\\`\\`\\`bash
curl -s http://162.35.184.69:9100/metrics | grep '^node_' | head -5
# node_arp_entries{device="eth0"} 1
# node_boot_time_seconds 1.785...
# node_context_switches_total 1.04e+07
\\`\\`\\`

### What it exposes
- CPU seconds per mode (idle, system, user, iowait, etc.)
- Load average (1m/5m/15m)
- Memory (MemTotal, MemFree, Buffers, Cached, etc.)
- Disk I/O bytes and operations
- Network interfaces bytes and packets
- Filesystem usage per mount
- ARP entries, context switches, interrupts

### Future: connect to Grafana/Prometheus
- Set up Prometheus on Contabo: `apt install prometheus`
- Add scrape config to `/etc/prometheus/prometheus.yml`:
  \\`\\`\\`yaml
  scrape_configs:
    - job_name: 'styxproxy-interserver'
      static_configs:
        - targets: ['162.35.184.69:9100']
          labels: { hostname: 'interserver', env: 'production' }
  \\`\\`\\`
- Add Grafana: `apt install grafana`, configure Prometheus as data source.
- Dashboard: import community Node Exporter Full ID `1860`.

### Restart / reconfigure
\\`\\`\\`bash
systemctl restart prometheus-node-exporter
# Edit /etc/default/prometheus-node-exporter to change ARGS (e.g. --web.listen-address=':' to bind all)
systemctl edit prometheus-node-exporter  # for overriding unit
journalctl -u prometheus-node-exporter -n 50
\\`\\`\\`

---

## §12 Backup Pipeline (Cross-Reference)

### Overview
- **Daily 3:05 AM UTC**: `pg_dump` → gzip → age-encrypt → shred plaintext → rclone copy to B2
- **Weekly Sun 4 AM UTC**: DR drill (B2 → age decrypt → gunzip → restore to test DB → verify)
- **Both run from Contabo**, NOT Interserver (cron on Contabo orchestrates via SSH)

### Verified dates
- `2026-07-28 17:23 UTC` — DR drill PASSED (23 tables, 2 admin_auth rows)
- `2026-07-28 11:37 UTC` — daily backup PASSED (44K dump, encrypted to B2)

### Files
- Backup script: `/root/.hermes/scripts/styxproxy_pg_dump_to_b2.sh`
- DR drill script: `/root/.hermes/scripts/styxproxy_dr_drill.sh`
- Age key (X25519): `/root/.hermes/keys/age-backup.key` (chmod 600, **MUST be backed up off-VPS**)
- B2 config: `/root/.config/rclone/rclone.conf` (remote: `b2-styxproxy`)
- Logs: `/var/log/styxproxy-pgdump.log`, `/var/log/styxproxy-dr-drill.log`

### RTO / RPO
- **RPO**: ~24 hours (worst case: latest daily backup fails, fall back to previous day)
- **RTO**: ~30 minutes (manual restore: rclone copyto + age decrypt + gunzip + psql restore)

### Future hardening
- pg_basebackup weekly + WAL archiving for PITR (target RPO < 5min)
- Cross-region B2 bucket replication (US → EU)

