# Styxproxy — Performance & Scaling Guide

**Last Updated:** 2026-06-26
**Status:** Defer to Phase 2 (after 1,000 customers)

---

## When to Scale

Styxproxy is sized for **up to ~1,000 customers** on a single Hetzner CX21 VPS. Beyond that, observe and act on these signals:

| Signal | Trigger | Action |
|--------|---------|--------|
| n8n p95 response > 2s | Sustained for 1 hour | Add Redis caching layer for LLM responses (already in place) |
| PostgreSQL connections > 80 | Sustained | Install pgBouncer (SCALE-1) |
| Redis memory > 70% of `maxmemory` | Sustained | Increase `maxmemory` or evict older keys |
| Provider API latency > 5s | Sustained for 1 day | Add provider response cache in Redis |
| Daily orders > 500 | For 7 days straight | Move n8n to dedicated VPS, DB to separate machine |

---

## SCALE-1: pgBouncer Connection Pooling

### Problem

PostgreSQL opens a new process per connection. n8n workflows can spawn multiple parallel queries (especially webhook + cron overlap). At >100 concurrent connections, PostgreSQL slows down significantly.

### Solution

pgBouncer sits between n8n and PostgreSQL, multiplexing many client connections onto few server connections.

### Phase 1 Status: Installed but minimal config

pgBouncer is installed in DEPLOYMENT.md §3.6 but configured with default pool mode (session). This is enough until ~500 concurrent connections.

### Phase 2 Config (activate when needed)

```ini
# /etc/pgbouncer/pgbouncer.ini

[databases]
styxproxy = host=localhost port=5432 dbname=styxproxy

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Transaction pooling — best for n8n workflow pattern
pool_mode = transaction

# Default pool size — tune based on DB capacity
default_pool_size = 20
max_client_conn = 1000

# Idle timeout
server_idle_timeout = 600
```

```bash
# Update n8n to connect via pgbouncer
# .env change:
DB_POSTGRESDB_HOST=127.0.0.1
DB_POSTGRESDB_PORT=6432
```

### Cost

$0 — pgBouncer is a lightweight Go binary, ~5MB RAM, <1% CPU.

### Trade-off

Transaction pooling breaks session-level features (prepared statements, advisory locks). n8n uses pgBouncer-compatible drivers so this should be transparent. If we hit issues, switch to `pool_mode = session` (less efficient but feature-complete).

---

## SCALE-3: Redis Caching Layer (already partial)

### Current State

Redis IS installed and used for:
- Webhook idempotency keys (24h TTL)
- Admin sessions (30m TTL)
- Fresh PIN entries (2m TTL)
- Rate limit counters (sliding window)

### What's NOT Cached Yet (Phase 2)

| What | Why cache | When |
|------|----------|------|
| LLM intent parsing | Same query → same intent 80%+ of the time | When LLM cost > $50/month |
| Provider balance reads | Same balance for 5-15 min | When API rate limits hit |
| Customer record lookups | Phone → customer is hot path | When DB queries > 50ms p95 |
| Product catalog | Static, never changes | Anytime (it's free) |

### Recommended Redis Config (already in .env)

```
# Already set in .env.example:
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=***

# Recommended additions to /etc/redis/redis.conf:
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Phase 2 Enhancements

1. **LLM response cache** — 24h TTL, key = `llm:intent:{hash(message)}`
2. **Customer cache** — 5min TTL, key = `customer:{phone_hash}`
3. **Product catalog** — 1h TTL, loaded once at startup

### Cost

$0 — Redis is already running. Extra memory is cheap (Hetzner CX21 has 4GB RAM, Redis uses ~50MB at Phase 1).

---

## Phase 3 (10,000+ Customers): Vertical + Horizontal Scaling

When Styxproxy hits 10K customers, single-VPS becomes the bottleneck.

### Vertical (cheaper, do first)

Upgrade VPS: Hetzner CCX23 (4 vCPU, 16GB RAM) — ~€30/mo
- All services stay on one machine
- 4x headroom for growth

### Horizontal (when vertical isn't enough)

Split services:
- VPS 1: n8n + Redis + Nginx (CX21, ~€7/mo)
- VPS 2: PostgreSQL + pgBouncer (CX31, ~€15/mo, more RAM for DB)
- VPS 3: Read replica for analytics (CCX13, ~€10/mo)

Add:
- **Load balancer** — Hetzner LB ($5/mo) or HAProxy on VPS 1
- **CDN for R2** — Cloudflare (free) for screenshots/PDFs
- **Read replica** — for reporting queries without affecting prod

### Cost at Phase 3

~$37–50/mo vs $7/mo at Phase 1. Acceptable when revenue justifies.

---

## Database Optimization (Phase 2)

### Indexes to Add at 1,000+ customers

```sql
-- Order lookup (already partial)
CREATE INDEX CONCURRENTLY idx_orders_phone_created ON orders(customer_phone, created_at DESC);
CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status) WHERE status IN ('pending', 'fulfilled');

-- Customer search
CREATE INDEX CONCURRENTLY idx_customers_name ON customers(LOWER(name));

-- Audit log retention
CREATE INDEX CONCURRENTLY idx_audit_log_created ON customer_audit_log(created_at);

-- Referral credit
CREATE INDEX CONCURRENTLY idx_orders_referral ON orders(referred_by_phone) WHERE referred_by_phone IS NOT NULL;
```

### Slow Query Monitoring

```sql
-- Enable pg_stat_statements
-- In postgresql.conf:
# shared_preload_libraries = 'pg_stat_statements'

-- Then:
CREATE EXTENSION pg_stat_statements;

-- Find slow queries:
SELECT 
  calls,
  round(mean_exec_time::numeric, 2) AS avg_ms,
  query
FROM pg_stat_statements
WHERE calls > 100
ORDER BY mean_exec_time DESC
LIMIT 20;
```

Add to n8n daily summary cron — alert if any query > 100ms average.

---

## n8n Performance Tuning

### Current Settings (already in docker-compose.yml)

```yaml
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168  # 7 days
```

### Phase 2 Additions

```yaml
# Use queue mode for parallel execution (requires Redis)
EXECUTIONS_MODE=queue
QUEUE_BULL_REDIS_HOST=localhost
QUEUE_BULL_REDIS_PORT=6379

# Multiple workers
EXECUTIONS_PROCESS=main
EXECUTIONS_PROCESS=worker  # Add second container for parallelism
```

### Cost

$0 — uses the same Redis already installed.

---

## Cost Trajectory Summary

| Phase | Customers | VPS | Add-ons | Total infra/mo |
|-------|-----------|-----|---------|---------------|
| **1 — Launch** | 0–1,000 | CX21 €7 | — | **€7/mo** |
| **2 — Scale** | 1,000–5,000 | CCX13 €15 | Doppler (free), Sentry (free) | **€15/mo** |
| **3 — Mature** | 5,000–10,000 | CCX23 €30 | WAL archiving, monitoring Pro | **€37/mo** |
| **4 — Big** | 10,000+ | Multi-VPS €37 | Load balancer, replica, Vault | **€60–100/mo** |

Compare to projected revenue at 10K customers × ₦6,500 avg × 0.5 orders/customer/year ≈ **₦32M/mo** (~$23K/mo at ₦1,380/$). Infra is <0.5% of revenue even at Phase 4.

---

## What We Deliberately DON'T Do

| Optimization | Why not now |
|--------------|-------------|
| Kubernetes | Operational nightmare for single operator. Docker Compose scales to ~50 services. |
| Microservices | n8n is the workflow engine — we don't split it. |
| GraphQL | WhatsApp is the API, not customer-facing. |
| Read replicas | Phase 3 only. PostgreSQL handles 10K customers easily on one machine. |
| CDN | R2 has built-in CDN via Cloudflare integration (free). |
| Multi-region | Nigeria is the market. Single region (EU Hetzner) is fast enough for NG. |

---

## Monitoring Checklist (Add at Phase 2)

- [ ] n8n execution p95 latency
- [ ] PostgreSQL slow query log (queries > 200ms)
- [ ] Redis memory usage
- [ ] PostgreSQL connections (count vs max)
- [ ] Provider API latency per request
- [ ] LLM token usage per day
- [ ] Daily summary orders count
- [ ] Error rate per workflow

---

## Related

- `docs/ARCHITECTURE_PLAN.md` — Current architecture
- `docs/MONITORING.md` — Phase 1 monitoring
- ADR-001 — PostgreSQL choice
- ADR-002 — MiniMax M2 choice
- ADR-005 — Backup strategy