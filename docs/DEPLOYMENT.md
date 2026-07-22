# Styxproxy — Deployment Guide

**Last Updated:** 2026-06-27
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
| **Theorem Reach account** | theoremreach.com | Free signup; **Styxproxy earns $1–4/trial** |
| **3proxy** (for free trial) | github.com/3proxy/3proxy | Free |

**Total setup cost: ~$65 in provider credits + ~$15–20/mo VPS + free monitoring**

---

## Infrastructure Overview

```
Internet
    ↓
Cloudflare (free tier) — DDoS + HTTPS + edge rate limiting
    ↓
Nginx (port 443) — reverse proxy + SSL + per-endpoint rate limiting
    ↓
VPS (your server)
    ├── n8n (Docker) — workflow engine
    ├── PostgreSQL — database
    ├── Redis — caching + sessions + rate limiting
    ├── pgBouncer — connection pooling
    └── 3proxy — self-hosted free trial proxy (Step 12)
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
#   # AGE-SECRET-KEY-1xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

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
      - N8N_BASIC_AUTH_ACTIVE=***      - N8N_BASIC_AUTH_USER=***      - N8N_BASIC_AUTH_PASSWORD=YOUR_N...RD
      - N8N_HOST=n8n.yourdomain.com
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.yourdomain.com/
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=localhost
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=bunche
      - DB_POSTGRESDB_USER=bunche
      - DB_POSTGRESDB_PASSWORD=YOUR_B...RD
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

## Step 5: Nginx + SSL + Rate Limiting

### 5.1 Create Nginx Config

```bash
nano /etc/nginx/sites-available/n8n
```

```nginx
# ============================================
# Styxproxy — Nginx Config
# ============================================
# Features:
# - SSL termination (Let's Encrypt)
# - Reverse proxy to n8n (port 5679)
# - Per-endpoint rate limiting (council recommendation)
# - Webhook protection against flooding
# ============================================

# RATE LIMIT ZONES (define before server block)
# Connection limit per IP
limit_conn_zone $binary_remote_addr zone=conn_per_ip:10m;

# Request rate zones (separate for different webhook types)
# whatsapp: 10 req/sec per IP (allows bursts of 20)
limit_req_zone $binary_remote_addr zone=whatsapp_limit:10m rate=10r/s;
# flutterwave: 5 req/sec per IP (Flutterwave rarely hits >1/sec)
limit_req_zone $binary_remote_addr zone=flutterwave_limit:10m rate=5r/s;
# theorem_reach: 5 req/sec per IP (webhook from one source)
limit_req_zone $binary_remote_addr zone=theorem_reach_limit:10m rate=5r/s;
# general: 20 req/sec per IP (admin + health checks)
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=20r/s;

server {
    listen 80;
    server_name n8n.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name n8n.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    # Connection limit per IP (max 20 concurrent)
    limit_conn conn_per_ip 20;

    # ============================================
    # WEBHOOK ENDPOINTS — strict rate limits
    # ============================================

    # WhatsApp webhook — 10 req/sec, burst 20
    location /webhook/whatsapp-incoming {
        limit_req zone=whatsapp_limit burst=20 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:5679;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;

        # 5s timeout (webhooks should be fast)
        proxy_read_timeout 5s;
    }

    # Flutterwave webhook — 5 req/sec
    location /webhook/flutterwave {
        limit_req zone=flutterwave_limit burst=10 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:5679;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 10s;
    }

    # Theorem Reach webhook — 5 req/sec
    location /webhook/theorem-reach {
        limit_req zone=theorem_reach_limit burst=10 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:5679;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 10s;
    }

    # ============================================
    # GENERAL — admin + health
    # ============================================

    location /webhook/ {
        # Catches any other webhook endpoints (catch-all)
        limit_req zone=general_limit burst=30 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:5679;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin UI + health
    location / {
        limit_req zone=general_limit burst=30 nodelay;
        limit_req_status 429;

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

    # Health check endpoint (no rate limit — UptimeRobot needs this)
    location = /healthz {
        access_log off;
        proxy_pass http://127.0.0.1:5679/healthz;
    }
}
```

### 5.2 Enable + Reload

```bash
ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Test rate limiting:
# Run this in a loop — should hit 429 after burst:
for i in {1..50}; do curl -s -o /dev/null -w "%{http_code}\n" https://n8n.yourdomain.com/webhook/whatsapp-incoming; done
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

### 6.3 Theorem Reach Postback (Free Trial)

1. Go to: theoremreach.com → Dashboard → Settings → Postbacks
2. Set Postback URL: `https://n8n.yourdomain.com/webhook/theorem-reach`
3. Enable HMAC signature verification
4. Copy the **HMAC secret** → paste into `.env` as `THEOREM_REACH_SECRET`
5. Copy the **API key** → paste into `.env` as `THEOREM_REACH_API_KEY`
6. Copy the **survey wall URL** → paste into `.env` as `THEOREM_REACH_SURVEY_URL`

### 6.4 Test Webhooks

```bash
# Test Flutterwave webhook manually
curl -X POST https://n8n.yourdomain.com/webhook/flutterwave \
  -H "Content-Type: application/json" \
  -d '{"tx_ref": "test", "event": "charge.completed"}'

# Test Theorem Reach postback (with valid HMAC)
# See scenarios/2026-06-26-free-trial.md for sample payload

# Test rate limiting (should hit 429 after 30+ req)
for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\n" https://n8n.yourdomain.com/webhook/whatsapp-incoming; done
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
- **Free Trial (Theorem Reach postback → 3proxy credential generation)**

---

## Step 8: Set Up Environment Variables

```bash
# On VPS — create .env for n8n
nano /opt/bunche/.env

# Copy all values from .env.example
# See: .env.example for full list

# Make sure these new vars are filled in:
#   THEOREM_REACH_API_KEY=***   THEOREM_REACH_SECRET=***   THEOREM_REACH_SURVEY_URL=***
#   THEOREM_REACH_POSTBACK_URL=https://n8n.yourdomain.com/webhook/theorem-reach
#   THREEPROXY_BIND_IP=YOUR_VPS_PUBLIC_IP
#   THREEPROXY_PORT_RANGE_START=8001
#   THREEPROXY_PORT_RANGE_END=8100
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
ufw allow 8001:8100/tcp   # 3proxy free trial proxy range
ufw enable
```

---

## Step 12: Install 3proxy (Free Trial Self-Hosted Proxy)

3proxy serves free trial customers. Self-hosted on VPS, uses VPS bandwidth + auth, costs ~$0.001 per trial.

### 12.1 Install 3proxy

```bash
# Install dependencies
apt install build-essential -y

# Clone and build
cd /opt
git clone https://github.com/3proxy/3proxy.git
cd 3proxy
make -f Makefile.Linux
make -f Makefile.Linux install

# Verify
3proxy --version
```

### 12.2 Generate Styxproxy Trial Config

```bash
mkdir -p /etc/3proxy /var/log/3proxy
cat > /etc/3proxy/bunche-trial.cfg << 'EOF'
#!/usr/local/3proxy/bin/3proxy

# Styxproxy Free Trial Proxy Configuration
# Managed dynamically by n8n workflow — see scripts/manage-3proxy-trial.sh

daemon
pidfile /var/run/3proxy-bunche.pid
nscache 65536
nserver 8.8.8.8

# Authentication: strong (username + password)
auth strong

# Users added dynamically here by n8n workflow:
# users trial_xxxx:CL:password_hash
# (initially empty — populated as trials are granted)

# Allow only authenticated trial users
allow trial_*

# External IP (your VPS public IP)
external YOUR_VPS_PUBLIC_IP
internal 0.0.0.0

# HTTP CONNECT proxy on ports 8001-8100
# Each trial user gets a unique port
proxy -p8001-8100

# Logging (optional — for debugging)
log /var/log/3proxy/bunche-trial.log D
logformat "- +_L%t.%. %N.%p %E %U %C:%c %R:%r %O %I %h %T"
EOF

# Replace YOUR_VPS_PUBLIC_IP with actual value
sed -i "s/YOUR_VPS_PUBLIC_IP/$(curl -s ifconfig.me)/" /etc/3proxy/bunche-trial.cfg
```

### 12.3 Start 3proxy

```bash
3proxy /etc/3proxy/bunche-trial.cfg

# Verify running
cat /var/run/3proxy-bunche.pid
ps aux | grep 3proxy

# Test it works (will reject without auth)
curl -x http://trial_test:test@localhost:8001 https://api.ipify.org
# Should return: "407 Proxy Authentication Required"
```

### 12.4 Install Dynamic User Management Script

This script is called by n8n workflow to add/remove trial users:

```bash
# Download from Styxproxy repo (when script is added)
curl -o /usr/local/bin/manage-3proxy-trial.sh \
  https://raw.githubusercontent.com/sonnyagent30-beep/bunche/main/scripts/manage-3proxy-trial.sh
chmod +x /usr/local/bin/manage-3proxy-trial.sh
```

**Usage:**
```bash
# Add a trial user (called by n8n on Theorem Reach postback):
/usr/local/bin/manage-3proxy-trial.sh add trial_a7b9c2 'Kx9mNp2qR8sT4wY7' 8001

# Remove a trial user (called by cleanup cron):
/usr/local/bin/manage-3proxy-trial.sh remove trial_a7b9c2

# List active trials:
/usr/local/bin/manage-3proxy-trial.sh list
```

### 12.5 Schedule Cleanup Cron (Every 5 Min)

```bash
# Download from Styxproxy repo (when script is added)
curl -o /usr/local/bin/cleanup-3proxy-trials.sh \
  https://raw.githubusercontent.com/sonnyagent30-beep/bunche/main/scripts/cleanup-3proxy-trials.sh
chmod +x /usr/local/bin/cleanup-3proxy-trials.sh

# Add to crontab
crontab -e
# Add this line (runs every 5 min, removes expired trials):
*/5 * * * * /usr/local/bin/cleanup-3proxy-trials.sh >> /var/log/bunche-trial-cleanup.log 2>&1
```

### 12.6 Test 3proxy Trial Flow

```bash
# 1. Manually add a test user
/usr/local/bin/manage-3proxy-trial.sh add trial_testuser 'testpass123' 8001

# 2. Test it works
curl -x http://trial_testuser:testpass123@YOUR_VPS_IP:8001 https://api.ipify.org
# Should return your VPS IP

# 3. Clean up
/usr/local/bin/manage-3proxy-trial.sh remove trial_testuser
```

---

## Step 13: Set Up Theorem Reach Webhook Handler

Theorem Reach sends postbacks when customers complete surveys. n8n handles the postback, validates the survey, and grants the trial.

### 13.1 Configure Theorem Reach Account

1. Sign up at theoremreach.com
2. Apply for publisher account (free)
3. Get approved (usually 1-2 days)
4. Navigate to Dashboard → API Settings
5. Copy:
   - **API Key** → `THEOREM_REACH_API_KEY` in `.env`
   - **Survey Wall URL** → `THEOREM_REACH_SURVEY_URL` in `.env`
   - **HMAC Secret** → `THEOREM_REACH_SECRET` in `.env`

### 13.2 Set Postback URL in Theorem Reach

1. Dashboard → Settings → Postbacks
2. Set Postback URL: `https://n8n.yourdomain.com/webhook/theorem-reach`
3. Enable HMAC verification
4. Save

### 13.3 Import Theorem Reach Webhook Workflow

The webhook handler workflow is in `.n8n/workflows/theorem-reach-webhook.json`.

**Workflow logic:**
```
POST /webhook/theorem-reach
   ↓
1. Verify HMAC signature using THEOREM_REACH_SECRET
   ↓
2. Check idempotency (INSERT ON CONFLICT in theorem_reach_postbacks)
   ↓
3. Check status == "completed"
   ↓
4. Check daily trial limit (3/3 used?)
   ↓
5. If OK:
   - Generate unique user_id (trial_ + 8 hex chars)
   - Generate random password (16 chars)
   - Add to 3proxy config via shell script
   - INSERT into free_trials table
   - Send WhatsApp with credentials + 2hr expiry
   ↓
6. Return 200 OK to Theorem Reach
```

### 13.4 Test Theorem Reach Integration

```bash
# Test webhook manually with valid HMAC signature
# See scenarios/2026-06-26-free-trial.md for sample payload

# Or test via Theorem Reach dashboard:
# Dashboard → Testing Tools → Send Test Postback
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

# 3proxy running
ps aux | grep 3proxy | grep -v grep

# 3proxy responsive
curl -x http://trial_test:test@localhost:8001 https://api.ipify.org

# Active trials
/usr/local/bin/manage-3proxy-trial.sh list | wc -l
```

### Automated Health Monitoring

UptimeRobot alerts on n8n downtime.
Backup freshness cron alerts if no backup in 24h.
3proxy cleanup cron removes expired credentials every 5 min.
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

### 3proxy Rollback

```bash
# Stop 3proxy
kill $(cat /var/run/3proxy-bunche.pid)

# Restore config from backup
cp /etc/3proxy/bunche-trial.cfg.bak /etc/3proxy/bunche-trial.cfg

# Restart
3proxy /etc/3proxy/bunche-trial.cfg

# Verify
ps aux | grep 3proxy
```

### Emergency: Pause Everything

```bash
# Stop n8n
cd /opt/bunche
docker-compose down

# Stop 3proxy
kill $(cat /var/run/3proxy-bunche.pid)

# All webhooks + trial proxy will return 503
```

---

## Provider Balance Monitoring

Check these daily — always keep credit above $10:

| Provider | URL | Alert if below |
|----------|-----|----------------|
| Proxy-Seller | proxy-seller.com → Dashboard | $10 |
| DataImpulse | dataimpulse.com → Dashboard | $10 |

## Free Trial Revenue Tracking

Check weekly — Theorem Reach pays out:

| Source | URL | Track |
|--------|-----|-------|
| Theorem Reach | theoremreach.com → Earnings | Cumulative payout, payout per survey |

---

## Daily Operations Checklist

- [ ] Check n8n error alerts on WhatsApp
- [ ] Check provider credit balances
- [ ] Check any pending orders older than 5 minutes
- [ ] Confirm all workflows are ACTIVE in n8n
- [ ] Check UptimeRobot status page (no incidents)
- [ ] **Check 3proxy is running** (`ps aux | grep 3proxy`)
- [ ] **Check active trial count** (`manage-3proxy-trial.sh list | wc -l`)

See `docs/OPERATIONAL_RUNBOOK.md` for full operations guide.

---

## Weekly Operations Checklist

- [ ] Run audit queries from `docs/SECURITY_RUNBOOK.md` §2
- [ ] Check backup sizes are consistent (no anomalies)
- [ ] Review n8n execution logs for warnings
- [ ] Check Flutterwave dashboard for failed transactions
- [ ] **Check Theorem Reach earnings** (should be increasing daily)
- [ ] **Review 3proxy cleanup log** for any errors

---

## Monthly Operations Checklist

- [ ] Verify monthly backup ran successfully (auto-verified by --verify cron)
- [ ] Rotate scheduled secrets per `docs/SECURITY_RUNBOOK.md` §1
- [ ] Review `docs/SECRET_ROTATION_LOG.md` and log this month's rotations
- [ ] Update this checklist with new operational learnings
- [ ] **Reconcile Theorem Reach payouts** vs `free_trials.survey_payout_usd` in DB

---

## Quick Reference

| URL | Purpose |
|-----|---------|
| `https://n8n.yourdomain.com` | n8n workflow editor |
| `https://n8n.yourdomain.com/healthz` | n8n health check |
| `YOUR_VPS_IP:8001-8100` | Free trial proxy (after auth) |
| `rave.flutterwave.com` | Payments dashboard |
| `business.whatsapp.com` | WhatsApp Business console |
| `dash.cloudflare.com` | Cloudflare + R2 |
| `uptimerobot.com/dashboard` | Uptime monitoring |
| `theoremreach.com/dashboard` | Free trial survey earnings |

| Command | What it does |
|---------|---------------|
| `cd /opt/bunche && docker-compose restart` | Restart n8n |
| `cd /opt/bunche && docker-compose logs -f` | View n8n logs |
| `systemctl restart nginx` | Reload Nginx (rate limit config too) |
| `sudo -u postgres psql -U bunche -d bunche` | Open DB console |
| `/usr/local/bin/backup-bunche.sh` | Manual backup |
| `/usr/local/bin/backup-bunche.sh --verify` | Test restore |
| `/usr/local/bin/manage-3proxy-trial.sh list` | List active trial users |
| `/usr/local/bin/manage-3proxy-trial.sh add USER PASS PORT` | Manually add trial user |
| `/usr/local/bin/manage-3proxy-trial.sh remove USER` | Manually remove trial user |
| `tail -f /var/log/bunche-trial-cleanup.log` | View cleanup cron output |
| `nginx -t && systemctl reload nginx` | Test + reload nginx rate limit config |

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
4. **If 429:** rate limit triggered — wait or increase limit

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

### Rate limit 429 errors in n8n
```bash
# Check current rate limit zones
nginx -T 2>/dev/null | grep limit_req_zone

# If too strict, increase limits in /etc/nginx/sites-available/n8n
# Then test + reload:
nginx -t && systemctl reload nginx

# Per-endpoint tuning:
# - WhatsApp: 10r/s (allows bursts of 20)
# - Flutterwave: 5r/s
# - Theorem Reach: 5r/s
# - General: 20r/s
```

### 3proxy not working
```bash
# Is it running?
ps aux | grep 3proxy | grep -v grep

# Check config syntax
3proxy --help

# Check listening ports
ss -tlnp | grep -E '800[0-9]'

# Test directly from VPS
curl -x http://trial_test:test@localhost:8001 https://api.ipify.org

# Check firewall
ufw status | grep 8001
```

### Theorem Reach postback not arriving
1. Check Theorem Reach dashboard → Postback History
2. Check n8n execution log for `theorem-reach` webhook
3. Test manually with their Test Postback tool
4. Verify postback URL is correct (HTTPS, no trailing slash)

### Free trial customer can't authenticate
1. Check active trial list: `manage-3proxy-trial.sh list | grep USERNAME`
2. Verify expiry: `SELECT expires_at FROM free_trials WHERE user_id = 'USERNAME';`
3. Check 3proxy config has the user line: `grep USERNAME /etc/3proxy/bunche-trial.cfg`
4. Try from VPS directly: `curl -x http://USER:PASS@localhost:PORT https://api.ipify.org`

### 3proxy port exhausted (all 100 in use)
```bash
# Check current usage
/usr/local/bin/manage-3proxy-trial.sh list | wc -l

# If legitimately at 100, customers will see "all slots busy"
# Wait for cron to free expired credentials (every 5 min)
# OR manually remove old ones:
/usr/local/bin/manage-3proxy-trial.sh remove trial_OLD_USER
```