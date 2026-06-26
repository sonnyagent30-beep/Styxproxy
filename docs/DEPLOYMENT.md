# Bunche — Deployment Guide

**Last Updated:** 2026-06-26
**Status:** Ready for Deployment

---

## Prerequisites

Before starting, you need:

| Item | Where | Cost |
|------|-------|------|
| VPS (Ubuntu 22.04) | Hetzner / DigitalOcean | ~$15–20/mo |
| Domain name | Namecheap / Cloudflare | ~$10–15/yr |
| Flutterwave merchant account | rave.flutterwave.com | 1.5% per tx |
| WhatsApp Business API | business.whatsapp.com | Free receive / ~$0.05/outbound |
| Proxy-Seller account + API key | proxy-seller.com | ~$20–30 credit |
| DataImpulse account + API key | dataimpulse.com | ~$15–20 credit |
| Cloudflare R2 account | dash.cloudflare.com | Free tier (10GB) |
| age (encryption tool) | `apt install age` or github.com/FiloSottile/age | Free |
| rclone (R2 upload) | rclone.org/install | Free |
| UptimeRobot account | uptimerobot.com | Free tier (50 monitors) |

**Total setup cost: ~$65 in provider credits + ~$15–20/mo VPS + free monitoring**

---

## Infrastructure Overview

```
Internet
    ↓
Cloudflare (free tier) — DDoS + HTTPS
    ↓
VPS (your server)
    ├── Nginx (port 443) — reverse proxy + SSL
    ├── n8n (Docker) — workflow engine
    ├── PostgreSQL — database
    ├── Redis — caching + sessions + rate limiting
    └── pgBouncer — connection pooling
```

---

## Step 1: VPS Setup

### 1.1 Spin Up VPS

```bash
# Hetzner (recommended)
# CX21: 2 vCPU, 4GB RAM, 80GB SSD — ~€6-10/mo
# Or DO: 2 vCPU, 4GB RAM — ~$15/mo

# SSH into your VPS
ssh root@YOUR_VPS_IP
```

### 1.2 Update System

```bash
apt update && apt upgrade -y
```

### 1.3 Install Docker

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
```

### 1.4 Install Docker Compose

```bash
apt install docker-compose -y
```

### 1.5 Install age (backup encryption)

```bash
apt install age -y
# OR build from source:
# git clone https://github.com/FiloSottile/age
# cd age && ./build.sh
```

### 1.6 Install rclone (R2 uploads)

```bash
curl https://rclone.org/install.sh | sudo bash
```

### 1.7 Generate Backup Keypair (ONE TIME)

```bash
# Generate keypair
age-keygen -o /root/bunche-backup-private.key

# This creates a file like:
#   # created: 2026-06-26T22:30:00Z
#   # public key: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#   AGE-SECRET-KEY-1xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# EXTRACT public key (copy this to backup.conf later):
grep "public key" /root/bunche-backup-private.key

# SAVE PRIVATE KEY to 1Password AND to a paper copy in a fireproof safe
# Then DELETE from VPS — it should never live here permanently
# (You re-upload to VPS only during a restore operation)
cat /root/bunche-backup-private.key  # Copy to 1Password NOW
shred -u /root/bunche-backup-private.key
```

### 1.8 Configure rclone for R2

```bash
rclone config
# Name: r2
# Type: s3
# Provider: Cloudflare
# Access key ID: (from R2 dashboard)
# Secret access key: (from R2 dashboard)
# Endpoint: https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com

# Test it:
rclone lsd r2:
```

---

## Step 2: Domain + DNS

### 2.1 Register Domain

Buy from Namecheap or Cloudflare.
Point A record to your VPS IP.

```bash
# In Cloudflare/Namecheap DNS:
# Type: A | Name: @ | Content: YOUR_VPS_IP | Proxy: DNS only
```

### 2.2 Install Certbot (Let's Encrypt)

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d yourdomain.com
```

---

## Step 3: Database Setup

### 3.1 Install PostgreSQL

```bash
apt install postgresql postgresql-contrib -y
systemctl enable postgresql
systemctl start postgresql
```

### 3.2 Create Database + User

```bash
sudo -u postgres psql

CREATE USER bunche WITH PASSWORD 'YOUR_STRONG_PASSWORD';
CREATE DATABASE bunche OWNER bunche;
GRANT ALL PRIVILEGES ON DATABASE bunche TO bunche;
\q
```

### 3.3 Run Schema

```bash
# Connect as bunche user
sudo -u postgres psql -U bunche -d bunche -h localhost

# Paste contents of docs/DATABASE_SCHEMA.md here
# (all CREATE TABLE statements)
```

### 3.4 Set Up pgpass (for backup script)

```bash
# /root/.pgpass — root can connect without password prompt
cat > /root/.pgpass << EOF
localhost:5432:bunche:bunche:YOUR_BUNCHE_DB_PASSWORD
EOF
chmod 600 /root/.pgpass
chown root:root /root/.pgpass
```

### 3.5 Install Redis

```bash
apt install redis-server -y
systemctl enable redis
systemctl start redis

# Set Redis password
redis-cli CONFIG SET requirepass "YOUR_REDIS_PASSWORD"
```

### 3.6 Install pgBouncer (SCALE-1)

```bash
apt install pgbouncer -y

# Configure /etc/pgbouncer/pgbouncer.ini
# See docs/ARCHITECTURE_PLAN.md → pgBouncer section

systemctl enable pgbouncer
systemctl start pgbouncer
```

---

## Step 4: n8n Setup

### 4.1 Create n8n Docker Compose File

```bash
mkdir -p /opt/bunche
cd /opt/bunche
nano docker-compose.yml
```

```yaml
version: '3'
services:
  n8n:
    image: n8nio/n8n:latest
    restart: unless-stopped
    ports:
      - "5679:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=YOUR_N8N_PASSWORD
      - N8N_HOST=n8n.yourdomain.com
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.yourdomain.com/
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=localhost
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=bunche
      - DB_POSTGRESDB_USER=bunche
      - DB_POSTGRESDB_PASSWORD=YOUR_BUNCHE_DB_PASSWORD
      - EXECUTIONS_DATA_PRUNE=true
      - EXECUTIONS_DATA_MAX_AGE=168
    volumes:
      - /opt/bunche/data:/home/node/.n8n
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5
```

### 4.2 Start n8n

```bash
cd /opt/bunche
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

### 4.3 Access n8n

Open: `https://n8n.yourdomain.com`

---

## Step 5: Nginx + SSL

### 5.1 Create Nginx Config

```bash
nano /etc/nginx/sites-available/n8n
```

```nginx
server {
    listen 80;
    server_name n8n.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name n8n.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5679;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
    }
}
```

### 5.2 Enable + Reload

```bash
ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

---

## Step 6: Configure Webhooks

### 6.1 Flutterwave Webhook

1. Go to: rave.flutterwave.com → Settings → Webhooks
2. Add URL: `https://n8n.yourdomain.com/webhook/flutterwave`
3. Select events:
   - ✅ `charge.completed`
   - ✅ `charge.failed`
   - ✅ `refund.initiated`
   - ✅ `refund.completed`
4. Save

### 6.2 WhatsApp Webhook

1. Go to: business.whatsapp.com → Meta Business Console
2. Set Webhook URL: `https://n8n.yourdomain.com/webhook/whatsapp-incoming`
3. Set Verify Token: (same as `WHATSAPP_VERIFY_TOKEN` in your .env)
4. Subscribe to: `messages` (message_received)

### 6.3 Bitlock.ai Webhook

1. Go to: dashboard.bitlock.ai → Postbacks
2. Set Webhook URL: `https://n8n.yourdomain.com/webhook/bitlock-postback`
3. Enable HMAC signature verification
4. Save the secret to `.env` as `BITLOCK_WEBHOOK_SECRET`

### 6.4 Test Webhooks

```bash
# Test Flutterwave webhook manually
curl -X POST https://n8n.yourdomain.com/webhook/flutterwave \
  -H "Content-Type: application/json" \
  -d '{"tx_ref": "test", "event": "charge.completed"}'
```

---

## Step 7: Import n8n Workflows

1. Open n8n at `https://n8n.yourdomain.com`
2. Go to **Workflows** → **Import** from JSON
3. Import each workflow from `.n8n/workflows/`
4. Activate each workflow (toggle ON)

**Workflows to import:**
- Order Handler (WhatsApp trigger)
- Payment Confirmation (Flutterwave webhook)
- Data Alert Escalation (cron every 15 min)
- Referral Credit Processor (sub-workflow)
- Daily Summary (cron at 23:55 Lagos)
- Error Alert (n8n Error Trigger)

---

## Step 8: Set Up Environment Variables

```bash
# On VPS — create .env for n8n
nano /opt/bunche/.env

# Copy all values from .env.example
# See: .env.example for full list
```

```bash
# Reload n8n after .env changes
cd /opt/bunche
docker-compose down
docker-compose up -d
```

---

## Step 9: Set Up Backups

### 9.1 Create Backup Config

```bash
mkdir -p /etc/bunche
cp scripts/backup.conf.example /etc/bunche/backup.conf
nano /etc/bunche/backup.conf
# Fill in:
#   BACKUP_PUBLIC_KEY (from Step 1.7)
#   POSTGRES_USER, POSTGRES_DB (usually 'bunche')
#   BACKUP_DIR (recommend /backup/bunche)
#   RCLONE_REMOTE (r2:bunche-backups/daily)
#   ALERT_WEBHOOK_URL (your backup-alert webhook)
#   RETENTION_DAYS_LOCAL (7)

chmod 600 /etc/bunche/backup.conf
```

### 9.2 Create Backup Directory + Scripts

```bash
mkdir -p /backup/bunche

# Copy scripts from repo
curl -o /usr/local/bin/backup-bunche.sh \
  https://raw.githubusercontent.com/sonnyagent30-beep/bunche/main/scripts/backup-bunche.sh
curl -o /usr/local/bin/backup-monthly-archive.sh \
  https://raw.githubusercontent.com/sonnyagent30-beep/bunche/main/scripts/backup-monthly-archive.sh

chmod +x /usr/local/bin/backup-bunche.sh
chmod +x /usr/local/bin/backup-monthly-archive.sh
```

### 9.3 Schedule Daily Backup (02:00)

```bash
crontab -e
# Add these lines:
0 2 * * * /usr/local/bin/backup-bunche.sh >> /var/log/bunche-backup.log 2>&1
5 2 1 * * /usr/local/bin/backup-monthly-archive.sh >> /var/log/bunche-backup.log 2>&1
```

### 9.4 Schedule Monthly Verification (1st of month, 02:30)

```bash
crontab -e
# Add this line:
30 2 1 * * /usr/local/bin/backup-bunche.sh --verify >> /var/log/bunche-backup.log 2>&1
```

### 9.5 Schedule Backup Freshness Check (03:00 daily)

```bash
cat > /usr/local/bin/check-backup-freshness.sh << 'EOF'
#!/bin/bash
LATEST=$(find /backup/bunche -name "bunche_*.dump.age" -mtime -1 | head -1)
if [ -z "$LATEST" ]; then
  curl -sS -X POST "https://n8n.yourdomain.com/webhook/backup-alert" \
    -H "Content-Type: application/json" \
    -d '{"severity":"high","message":"No backup file found in last 24h"}'
fi
EOF
chmod +x /usr/local/bin/check-backup-freshness.sh

crontab -e
# Add: 0 3 * * * /usr/local/bin/check-backup-freshness.sh >> /var/log/bunche-backup.log 2>&1
```

---

## Step 10: Set Up Monitoring (UptimeRobot)

See `docs/MONITORING.md` for full setup. Summary:

1. Create free account at uptimerobot.com
2. Add HTTP(s) monitor: `https://n8n.yourdomain.com/healthz`, 5-min interval
3. Create n8n webhook to receive UptimeRobot alerts
4. Configure webhook alert contact in UptimeRobot
5. Test by stopping n8n briefly

---

## Step 11: Firewall Setup

```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 443   # HTTPS
ufw allow 80    # HTTP (for certbot)
ufw enable
```

---

## Health Checks

### Manual Health Check

```bash
# n8n health
curl https://n8n.yourdomain.com/healthz

# PostgreSQL
sudo -u postgres psql -c "SELECT 1"

# Redis
redis-cli -a YOUR_REDIS_PASSWORD PING

# Backup freshness
ls -la /backup/bunche/ | tail -5

# R2 bucket
rclone ls r2:bunche-backups/daily/ | tail -5
```

### Automated Health Monitoring

UptimeRobot alerts on n8n downtime.
Backup freshness cron alerts if no backup in 24h.
Workflow errors alert via WhatsApp (Error Alert workflow).

---

## Rollback Procedure

If something breaks after a deploy:

### n8n Workflow Rollback

```bash
# Find the last working workflow version
# n8n stores previous versions — restore from the UI:
# Workflow → Version History → Restore

# Or re-import the JSON from git:
# .n8n/workflows/[workflow-name].json
```

### VPS Full Rollback

```bash
# SSH to VPS
cd /opt/bunche

# Check git log for last known good commit
git log --oneline

# Revert to previous commit
git revert HEAD

# Rebuild Docker
docker-compose down
docker-compose up -d
```

### Database Rollback

```bash
# Restore from backup (see ADR-005 §"Restore Procedure")
# 1. Stop n8n
cd /opt/bunche && docker-compose down

# 2. Decrypt backup
age --decrypt /backup/bunche/bunche_2026-06-26.dump.age > /tmp/restore.dump

# 3. Drop + recreate DB
sudo -u postgres dropdb bunche
sudo -u postgres createdb bunche -O bunche

# 4. Restore
pg_restore --dbname=postgres --create /tmp/restore.dump

# 5. Restart n8n
cd /opt/bunche && docker-compose up -d
```

### Emergency: Pause Everything

```bash
# Stop n8n
cd /opt/bunche
docker-compose down

# All webhooks will return 503
```

---

## Provider Balance Monitoring

Check these daily — always keep credit above $10:

| Provider | URL | Alert if below |
|----------|-----|----------------|
| Proxy-Seller | proxy-seller.com → Dashboard | $10 |
| DataImpulse | dataimpulse.com → Dashboard | $10 |

---

## Daily Operations Checklist

- [ ] Check n8n error alerts on WhatsApp
- [ ] Check provider credit balances
- [ ] Check any pending orders older than 5 minutes
- [ ] Confirm all workflows are ACTIVE in n8n
- [ ] Check UptimeRobot status page (no incidents)

See `docs/OPERATIONAL_RUNBOOK.md` for full operations guide.

---

## Weekly Operations Checklist

- [ ] Run audit queries from `docs/SECURITY_RUNBOOK.md` §2
- [ ] Check backup sizes are consistent (no anomalies)
- [ ] Review n8n execution logs for warnings
- [ ] Check Flutterwave dashboard for failed transactions

---

## Monthly Operations Checklist

- [ ] Verify monthly backup ran successfully (auto-verified by --verify cron)
- [ ] Rotate scheduled secrets per `docs/SECURITY_RUNBOOK.md` §1
- [ ] Review `docs/SECRET_ROTATION_LOG.md` and log this month's rotations
- [ ] Update this checklist with new operational learnings

---

## Quick Reference

| URL | Purpose |
|-----|---------|
| `https://n8n.yourdomain.com` | n8n workflow editor |
| `https://n8n.yourdomain.com/healthz` | Health check |
| `rave.flutterwave.com` | Payments dashboard |
| `business.whatsapp.com` | WhatsApp Business console |
| `dash.cloudflare.com` | Cloudflare + R2 |
| `uptimerobot.com/dashboard` | Uptime monitoring |

| Command | What it does |
|---------|---------------|
| `cd /opt/bunche && docker-compose restart` | Restart n8n |
| `cd /opt/bunche && docker-compose logs -f` | View n8n logs |
| `systemctl restart nginx` | Reload Nginx |
| `sudo -u postgres psql -U bunche -d bunche` | Open DB console |
| `/usr/local/bin/backup-bunche.sh` | Manual backup |
| `/usr/local/bin/backup-bunche.sh --verify` | Test restore |

---

## Troubleshooting

### n8n won't start
```bash
docker-compose logs n8n
# Check for missing env vars or port conflicts
```

### WhatsApp webhooks not reaching n8n
1. Check Cloudflare → SSL mode is Full (not Flexible)
2. Check Nginx logs: `tail -f /var/log/nginx/error.log`
3. Test webhook URL directly: `curl -I https://n8n.yourdomain.com/webhook/whatsapp-incoming`

### Payment webhook not firing
1. Flutterwave dashboard → Settings → Webhooks → confirm URL is correct
2. Test webhook: Dashboard → Webhooks → Send Test
3. Check n8n execution log for the test

### Database connection errors
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Test connection
sudo -u postgres psql -U bunche -d bunche -h localhost -c "SELECT 1"
```

### Backup failures
```bash
# Check backup log
tail -50 /var/log/bunche-backup.log

# Test rclone
rclone lsd r2:

# Test age decryption (you need the private key uploaded temporarily)
age --decrypt /backup/bunche/bunche_2026-06-26.dump.age > /tmp/test.dump
pg_restore --list /tmp/test.dump | head -20
rm /tmp/test.dump
# IMPORTANT: re-shred the private key after test
```

### UptimeRobot showing false alerts
1. Check n8n logs for slow startup (first request after idle)
2. Increase UptimeRobot timeout to 30s (already configured)
3. Set "consecutive failures" to 2 (10-min grace)