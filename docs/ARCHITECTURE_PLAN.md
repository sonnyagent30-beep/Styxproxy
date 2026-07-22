# Styxproxy — Architecture Plan

**Last Updated:** 2026-06-26  
**Status:** Planning Complete — Ready for Implementation

---

## Overview

Styxproxy is a WhatsApp-first proxy reseller for the Nigerian market. Zero-inventory, on-demand delivery. No account creation required.

---

## Current Architecture (Problem)

```
Customer WhatsApp → n8n (VPS) → Google Sheets → Ollama (local LLM)
```

**Problems:**
- Google Sheets bottleneck at ~50 simultaneous users
- Ollama uses 3-4GB RAM, limits concurrency
- No webhook security
- No rate limiting
- Admin access only needs phone number

---

## Planned Architecture (Solution)

```
Customer WhatsApp
        ↓
[Cloudflare — DDoS protection + rate limiting]
        ↓
[Nginx — HTTPS + per-endpoint rate limits]
        ↓
[n8n webhook — signature verification + idempotency]
        ↓
[Redis — rate limiting + caching + session management]
        ↓
[PostgreSQL — customers, orders, audit logs]
        ↓
[MiniMax M2 API — cloud LLM]
        ↓
[Provider APIs — Proxy-Seller, DataImpulse, Geonode, CPAGrip]
        ↓
[WhatsApp reply]
```

---

## Technology Stack

| Component | Technology | Cost |
|-----------|-------------|------|
| Database | PostgreSQL (self-hosted) | $0 |
| Caching | Redis | $0 |
| Connection Pooling | pgBouncer | $0 |
| LLM | MiniMax M2 Cloud | ~$0.001/msg |
| HTTPS | Let's Encrypt (Certbot) | $0 |
| CDN/DDoS | Cloudflare | $0 (free tier) |
| Reverse Proxy | Nginx | $0 |
| Workflow Engine | n8n | $0 |
| WhatsApp | Meta WhatsApp Cloud API | $0 |
| Payments | Flutterwave | Transaction fees |

---

## Performance Comparison

| Metric | Current (Sheets) | Planned |
|--------|------------------|---------|
| Response time | 6-8 seconds | 1-2 seconds |
| Concurrent users | 200-500 | 5,000-10,000 |
| Daily active users | ~50 before breaking | ~10,000 |
| LLM speed | 2 seconds | 500ms-1s |
| Database cost | $0 (breaks) | $0 (scales) |

---

## Database: PostgreSQL (Self-Hosted)

### Why Self-Hosted Over Cloud-Free Tiers?

| Provider | Problem |
|----------|---------|
| Supabase Free | **Pauses after 1 week of inactivity** — kills a 24/7 business |
| Neon Free | Cold starts, limited resources |
| **Self-hosted on VPS** | Never pauses, complete control, $0 |

### Schema Overview

Full schema in `docs/DATABASE_SCHEMA.md`

### Tables

- `customers` — phone, name, recovery, metrics
- `orders` — order_id, plan_type, payment, proxy, status
- `free_trials` — trial tracking
- `customer_audit_log` — PII-redacted event log
- `error_log` — system errors with severity
- `provider_log` — provider health
- `daily_summary` — aggregated metrics
- `processed_webhooks` — idempotency storage
- `admin_auth` — PIN hash, TOTP secret, lockout
- `admin_commands_log` — admin action audit trail
- `admin_sessions_log` — session history
- `rate_limit_log` — rate limit events
- `webhook_security_log` — verification attempts

---

## Caching: Redis

### What's Cached

| Cache Type | TTL | Purpose |
|-----------|-----|---------|
| LLM response cache | 24 hours | 80% reduction in LLM API calls |
| Webhook idempotency | 24 hours | Prevent duplicate processing |
| Admin sessions | 15 minutes | Session management |
| Fresh PIN verification | 2 minutes | Medium-risk command auth |
| Rate limit counters | Sliding window | Anti-abuse |

### Redis Key Patterns

```
webhook:processed:{provider}:{webhook_id}
admin:session:{phone}
admin:fresh_pin:{phone}
ratelimit:phone:{endpoint}:{phone_hash}
ratelimit:ip:{endpoint}:{ip}
llm:intent:{message_hash}
blocked:{ip}
```

### Redis Configuration

```bash
# /etc/redis/redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
requirepass YOUR_STRONG_REDIS_PASSWORD
```

---

## Connection Pooling: pgBouncer

Handles thousands of concurrent connections from n8n without overwhelming PostgreSQL.

```bash
# /etc/pgbouncer/pgbouncer.ini
[databases]
styxproxy = host=localhost port=5432 dbname=styxproxy

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 5
```

---

## LLM: MiniMax M2 Cloud

### Why MiniMax Over Ollama?

| Aspect | Ollama (Local) | MiniMax M2 Cloud |
|--------|-----------------|------------------|
| Speed | ~2 seconds | 500ms-1s |
| Concurrency | 3-5 simultaneous | Unlimited |
| VPS RAM usage | 3-4 GB | ~0 |
| Setup | Install + pull model | API key only |
| Cost | $0 (VPS) | ~$0.001/msg |

### n8n Configuration

```
Base URL: https://api.minimax.chat/v1
API Key: YOUR_MINIMAX_KEY
Model: MiniMax-M2
```

### Caching Strategy

```javascript
// Pseudocode for LLM caching
def get_llm_intent(message):
    hash = sha256(normalize(message))[:16]
    cached = redis.get(f"llm:intent:{hash}")
    if cached:
        return cached  # 0.001 seconds
    
    intent = minimax.generate(message)
    redis.setex(f"llm:intent:{hash}", 86400, intent)
    return intent  # 500ms-1s
```

---

## Webhook Flow (Complete)

```
[Cloudflare — DDoS + rate limit]
        ↓
[Nginx — HTTPS + endpoint limit]
        ↓
[n8n webhook trigger]
        ↓
[Signature verification — reject if invalid]
        ↓
[Idempotency check — reject if duplicate]
        ↓
[Rate limit check — block if exceeded]
        ↓
[Session/Auth check]
        ↓
[Main workflow logic]
        ↓
[WhatsApp reply]
```

---

## Backup Strategy

```bash
# Daily backup at 2 AM
pg_dump styxproxy | gzip > /backup/styxproxy_$(date +%Y%m%d).sql.gz

# Upload to R2 (Cloudflare R2 — $0/month for 10GB)
rclone copy /backup/styxproxy_*.gz r2:styxproxy-backups/

# Retention: 30 days locally, 90 days on R2
```

---

## Scalability Path

| Scale | What Breaks | Solution |
|-------|-------------|----------|
| 10K daily users | Single VPS CPU/memory | Add second VPS, load balancer |
| 50K daily users | PostgreSQL single instance | Read replicas |
| 100K+ daily users | Single region latency | Multi-region deployment |

**Current architecture handles 10,000+ daily users comfortably.**

---

## Environment Variables

```bash
# .env (never commit to git)

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=styxproxy
POSTGRES_USER=styxproxy
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=YOUR_STRONG_PASSWORD

# LLM
MINIMAX_API_KEY=YOUR_KEY

# Webhook Secrets
WHATSAPP_APP_SECRET=YOUR_SECRET
FLUTTERWAVE_SECRET_HASH=YOUR_HASH
CPAGRIP_SECRET=YOUR_SECRET

# TOTP Encryption
TOTP_ENCRYPTION_KEY=YOUR_64_CHAR_HEX_KEY
```

---

## Implementation Order

| Phase | Task | Time |
|-------|------|------|
| 1 | Install PostgreSQL + Redis + pgBouncer on VPS | 2 hours |
| 2 | Create database schema + indexes | 1 hour |
| 3 | Configure Nginx with HTTPS + rate limits | 2 hours |
| 4 | Setup n8n basic auth + HTTPS | 1 hour |
| 5 | Configure webhook signature verification | 4 hours |
| 6 | Implement payment idempotency | 4 hours |
| 7 | Setup rate limiting (3 layers) | 7 hours |
| 8 | Configure MiniMax M2 in n8n | 1 hour |
| 9 | Implement admin authentication (PIN/2FA) | 8 hours |
| 10 | Setup Redis caching + session management | 4 hours |
| 11 | Configure automated backups | 2 hours |
| 12 | Load testing (K6) | 4 hours |
| **Total** | | **~40 hours** |

---

## Cost Summary

| Component | Monthly Cost |
|-----------|-------------|
| VPS (8GB RAM) | ~$20-30/mo (already have) |
| Domain | ~$10-15/yr |
| Cloudflare | $0 (free tier) |
| Let's Encrypt | $0 |
| PostgreSQL + Redis + pgBouncer | $0 (self-hosted) |
| MiniMax M2 API | ~$10-50/mo (at scale) |
| R2 Backups | $0 (10GB free) |
| **Total** | **~$30-40/mo at scale** |
