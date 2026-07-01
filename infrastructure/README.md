# Bunche — Infrastructure

**Status:** Ready to deploy
**Stack:** Docker Compose · PostgreSQL 16 · Redis 7 · FastAPI · n8n · Nginx

---

## Quick Start (New VPS)

```bash
# 1. Clone the repo
git clone https://github.com/sonnyagent30-beep/bunche.git
cd bunche/infrastructure

# 2. Set up env
cp .env.production.example .env
nano .env   # fill in all CHANGE_ME values

# 3. Generate secrets (if not set)
openssl rand -base64 32   # copy to ADMIN_TOKEN, POSTGRES_PASSWORD, REDIS_PASSWORD

# 4. SSL certs (first time only)
docker compose up -d nginx
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot -d bunche.ng \
  -d api.bunche.ng -d n8n.bunche.ng

# 5. Start all services
docker compose up -d

# 6. Verify
docker compose ps
curl https://bunche.ng/health
```

---

## Services

| Service | URL | Notes |
|---------|-----|-------|
| Website | `https://bunche.ng` | Static — display only |
| API | `https://api.bunche.ng` | FastAPI backend |
| n8n | `https://n8n.bunche.ng` | Automation |
| Admin | `https://bunche.ng/powerhold?token=...` | Hardened admin |

---

## File Structure

```
infrastructure/
├── docker-compose.yml        # All services
├── nginx/
│   ├── nginx.conf            # Main config
│   ├── ssl-params.conf       # TLS hardening
│   └── conf.d/
│       └── bunche.conf       # Site routing
├── postgres/init/
│   ├── 01-schema.sql        # Tables, indexes, triggers
│   └── 02-seed.sql          # Products + seed data
├── scripts/
│   ├── backup.sh            # Daily encrypted backup
│   └── healthcheck.sh        # Service health check
├── .github/workflows/
│   └── deploy.yml           # CI/CD pipeline
├── Makefile                 # Shortcut commands
└── .env.production.example  # Env template
```

---

## Admin Access (Hardened)

```
URL:     https://bunche.ng/powerhold?token=<ADMIN_TOKEN>
Allowed: Team IPs only (firewall + auth_basic)
```

See `BUNCHE_OPERATIONAL_WORKFLOW.md` for full admin security details.

---

## Daily Operations

```bash
make up          # Start all services
make down        # Stop all services
make logs        # Tail all logs
make restart     # Restart all services
make ps          # Show status
make backup      # Run manual backup
make health      # Check service health
make cert-renew  # Renew SSL certificates
```

---

## Backup

Backups run daily at 02:00 Africa/Lagos via cron. Stored encrypted to R2.

Manual backup:
```bash
./scripts/backup.sh
```

---

## SSL Certificate Renewal

Let's Encrypt certs expire after 90 days. Renew manually:

```bash
docker compose run --rm certbot renew
docker compose exec nginx nginx -s reload
```

Or use the Makefile:
```bash
make cert-renew
```

---

## Adding New Team IPs

```bash
# Edit nginx/conf.d/bunche.conf
# Add to the allow list:
allow <NEW_IP>;
# Reload nginx:
docker compose exec nginx nginx -s reload
```

---

## Troubleshooting

```bash
# View logs for a specific service
docker compose logs -f api
docker compose logs -f n8n
docker compose logs -f postgres

# Check database connectivity
docker compose exec postgres psql -U bunche -d bunche

# Check Redis
docker compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Restart a specific service
docker compose restart api
docker compose restart n8n
# Full rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## CI/CD

Push to `main` branch triggers:
1. Lint Dockerfiles
2. Run backup pre-check
3. Deploy to target VPS via SSH

See `.github/workflows/deploy.yml` for configuration.
