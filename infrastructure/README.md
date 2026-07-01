# Bunche — Infrastructure

**Status:** Ready to deploy
**Stack:** Docker Compose · PostgreSQL 16 · Redis 7 · FastAPI · n8n · PgBouncer · Sentry · Nginx

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
openssl rand -hex 64      # copy to SENTRY_SECRET_KEY

# 4. SSL certs (first time only)
docker compose up -d nginx
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot -d bunche.ng \
  -d api.bunche.ng -d n8n.bunche.ng -d sentry.bunche.ng

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
| Sentry | `https://sentry.bunche.ng` | Error tracking + APM |
| Admin | `https://bunche.ng/powerhold?token=...` | Hardened admin |

---

## File Structure

```
infrastructure/
├── docker-compose.yml        # All services (postgres, redis, pgbouncer, api, n8n, sentry, nginx)
├── nginx/
│   ├── nginx.conf            # Main config
│   ├── ssl-params.conf       # TLS hardening
│   └── conf.d/
│       └── bunche.conf       # Site routing (+ sentry.bunche.ng)
├── postgres/init/
│   ├── 01-schema.sql        # Tables, indexes, triggers
│   └── 02-seed.sql          # Products + seed data
├── pgbouncer/
│   ├── pgbouncer.ini        # Transaction pooling config
│   └── userlist.txt         # Auth mappings
├── scripts/
│   ├── backup.sh            # Daily encrypted backup
│   └── healthcheck.sh        # Service health check
├── .github/workflows/
│   └── deploy.yml           # CI/CD pipeline
├── Makefile                 # Shortcut commands
└── .env.production.example  # Env template
```

---

## PgBouncer — n8n Connection Pooling

n8n connects to PostgreSQL via PgBouncer (transaction pooling mode). FastAPI connects directly via `asyncpg` — no PgBouncer.

```
n8n → pgbouncer:5432 → postgres:5432
```

**PgBouncer settings:**
- `pool_mode = transaction` — connection returned to pool after each transaction
- `max_client_conn = 500` — max concurrent clients
- `default_pool_size = 20` — PostgreSQL connections per database
- `max_db_connections = 100` — max connections per database

**Why PgBouncer for n8n only?**
n8n holds persistent database connections for workflow state. With many concurrent workflows, this exhausts PostgreSQL's default 100 connections. PgBouncer sits in front so n8n borrows from the pool efficiently. FastAPI uses async I/O with asyncpg — each request holds a connection only during the actual query, returning it immediately, so PgBouncer adds no value there.

---

## Sentry — Error Tracking + APM

Self-hosted Sentry on-premise. Tracks errors and performance for both FastAPI and n8n.

### First-Time Sentry Setup

```bash
# 1. Start Sentry (it needs a migration run on first start)
docker compose up -d sentry

# 2. Run Sentry migrations (first time only)
docker compose run --rm sentry upgrade

# 3. Create your admin user
docker compose run --rm sentry createuser
# Follow prompts: email + password

# 4. Create projects in Sentry UI
# Visit https://sentry.bunche.ng
# Create two projects:
#   - bunche-api    (FastAPI)
#   - bunche-n8n   (n8n workflows)
# Copy the DSN for each project into your .env

# 5. Restart to pick up DSN
docker compose restart api n8n
```

### Sentry Environment Variables

```bash
SENTRY_SECRET_KEY=<openssl rand -hex 64>
SENTRY_DSN=https://<key>@o123456.ingest.sentry.io/<project_id>
SENTRY_ORG=Bunche
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1    # 10% of transactions traced
```

### What Sentry Captures

| | FastAPI | n8n |
|--|---------|-----|
| **Unhandled exceptions** | ✅ | ✅ |
| **Performance traces** | ✅ | Partial |
| **Slow DB queries** | ✅ (via SQLAlchemy) | — |
| **Workflow error logs** | — | ✅ |
| **Webhook failures** | ✅ | ✅ |

### Sentry Projects

- **`bunche-api`** — FastAPI backend: HTTP errors, unhandled exceptions, slow API calls
- **`bunche-n8n`** — n8n workflows: workflow execution errors, node failures

### Rate Limits

Sentry self-hosted uses your own storage. Monitor `sentry_data` volume size. Set `SENTRY_TRACES_SAMPLE_RATE=0.1` to limit performance data volume.

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
docker compose logs -f pgbouncer
docker compose logs -f sentry
docker compose logs -f postgres

# Check database connectivity
docker compose exec postgres psql -U bunche -d bunche

# Check Redis
docker compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Check PgBouncer
docker compose exec pgbouncer pgbouncer -V
echo "SELECT 1;" | docker compose exec -T pgbouncer psql -U bunche -d bunche

# Check Sentry
docker compose exec sentry sentry --version
curl http://localhost:9000/_health/

# Restart a specific service
docker compose restart api
docker compose restart n8n
docker compose restart pgbouncer

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
