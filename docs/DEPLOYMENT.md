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

**Total setup cost: ~$65 in provider credits + ~$15–20/mo VPS**

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

### 3.4 Install Redis

```bash
apt install redis-server -y
systemctl enable redis
systemctl start redis

# Set Redis password
redis-cli CONFIG SET requirepass "YOUR_REDIS_PASSWORD"
```

### 3.5 Install pgBouncer

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

### 6.3 Test Webhooks

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
- Refund Handler (Flutterwave webhook)
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

```bash
# Create backup directory
mkdir -p /backup/bunche

# Create backup script
nano /usr/local/bin/backup-bunche.sh
```

```bash
#!/bin/bash
# Daily PostgreSQL backup
DATE=$(date +%Y%m%d)
pg_dump -U bunche -h localhost bunche | gzip > /backup/bunche/bunche_${DATE}.sql.gz

# Upload to R2
rclone copy /backup/bunche/bunche_${DATE}.sql.gz r2:bunche-backups/

# Delete local backups older than 30 days
find /backup/bunche -name "bunche_*.sql.gz" -mtime +30 -delete
```

```bash
chmod +x /usr/local/bin/backup-bunche.sh

# Add to crontab — run at 2 AM daily
crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-bunche.sh >> /var/log/backup.log 2>&1
```

---

## Step 10: Firewall Setup

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
```

### Automated Health Monitoring

The n8n workflows include error alerting — you get a WhatsApp message when anything fails.

For additional monitoring, see `docs/SECURITY_PLAN.md` → Layer 7: Monitoring + Alerting.

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

See `docs/OPERATIONAL_RUNBOOK.md` for full operations guide.

---

## Quick Reference

| URL | Purpose |
|-----|---------|
| `https://n8n.yourdomain.com` | n8n workflow editor |
| `https://n8n.yourdomain.com/healthz` | Health check |
| `rave.flutterwave.com` | Payments dashboard |
| `business.whatsapp.com` | WhatsApp Business console |

| Command | What it does |
|---------|-------------|
| `cd /opt/bunche && docker-compose restart` | Restart n8n |
| `cd /opt/bunche && docker-compose logs -f` | View n8n logs |
| `systemctl restart nginx` | Reload Nginx |
| `sudo -u postgres psql -U bunche -d bunche` | Open DB console |

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
