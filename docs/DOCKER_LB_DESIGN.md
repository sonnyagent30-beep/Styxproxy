# Docker Load Balancing — Design Doc

**Status:** Design only — not scheduled for implementation

## Why This Exists

Single API container is the current bottleneck. If it crashes, all Styxproxy traffic stops. Load balancing with `docker compose --scale api=N` gives horizontal scaling + zero-downtime rolling deploys.

## Current Architecture

```
Internet → Nginx (Interserver:80/443) → styxproxy-api (Interserver, bare uvicorn)
                                          ↓
                                      Postgres (Interserver:5432)
```

All Styxproxy service runs on Interserver as bare processes or Docker containers on the same host.

## Proposed Architecture

```
Internet → Nginx (Contabo:80/443) → [api-1, api-2, api-3] (Contabo Docker)
                                       ↓
                                   Postgres (Interserver:5432) ← TLS tunnel
```

**Key changes:**
- Backend API moves to Contabo Docker containers
- Contabo nginx becomes the public-facing load balancer
- Interserver becomes DB-only + SOCKS5 (its current role for Dante)
- API containers connect to Interserver Postgres via TLS SSH tunnel

## Why Contabo, Not Interserver

| Constraint | Interserver | Contabo |
|---|---|---|
| Docker | ❌ Not available | ✅ Available |
| RAM | ~1.1GB free (tight) | ~7.8GB free |
| Disk | 38GB, /etc ephemeral | 145GB |
| CPU | Limited container | Full CPU |
| Static public IP | 162.35.184.69 | 84.247.132.12 |

Interserver is a containerized VPS with no Docker and limited RAM. Contabo is a full bare-metal VPS with Docker, ample RAM, and enough disk.

## Implementation Steps

### Phase 1 — Dockerize the API

```bash
# In /opt/styxproxy/repo/backend/
docker build -t styxproxy-api:latest .
docker run -d --name styxproxy-api-1 \
  -p 8001:8000 \
  -e DATABASE_URL=postgresql+asyncpg://styxproxy_app:...@162.35.184.69:5432/styxproxy \
  --restart unless-stopped \
  styxproxy-api:latest

# Scale to 3 replicas
docker compose up -d --scale api=3
```

### Phase 2 — Nginx Load Balancer

```nginx
# /etc/nginx/sites-available/styxproxy-lb
upstream styxproxy_backend {
    least_conn;  # or ip_hash for sticky sessions
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name styxproxy.com api.styxproxy.com;

    location / {
        proxy_pass http://styxproxy_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

### Phase 3 — Database Tunnel

API containers on Contabo need to reach Postgres on Interserver:

```bash
# On Contabo — SSH tunnel (keepalive, auto-restart)
ssh -N -L 5433:127.0.0.1:5432 root@162.35.184.69 \
  -o ServerAliveInterval=30 \
  -o StrictHostKeyChecking=no \
  -o PasswordAuthentication=no \
  -i /root/.ssh/styxproxy-interserver

# API containers connect to localhost:5433
```

Or use a proper VPN (WireGuard) between Interserver and Contabo.

### Phase 4 — Zero-Downtime Deploys

```bash
# Rolling update — no dropped connections
docker compose up -d --scale api=3 --no-deps
# Wait for health checks, then roll next
```

## docker-compose.yml Sketch

```yaml
version: '3.8'
services:
  api:
    build: ../backend
    ports:
      - "8001-8003:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://styxproxy_app:${DB_PASS}@host.docker.internal:5433/styxproxy
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Alpine nginx sidecar for health + metrics
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      api:
        condition: service_healthy

networks:
  default:
    name: styxproxy-net
```

## What's Hard About This

1. **DB connection from Contabo → Interserver** — needs SSH tunnel or VPN. Postgres isn't exposed publicly on Interserver.
2. **Sessions/Sticky sessions** — if JWT/session state is in-memory, `ip_hash` load balancing is needed. If Redis is used for sessions, any LB strategy works.
3. **Migration risk** — moving the API from Interserver bare uvicorn to Contabo Docker mid-flight requires a DNS cutover with short TTL.
4. **Interserver's ephemeral /etc** — Docker systemd units are already managed via git+symlink pattern. Extends to the load balancer setup.
5. **CI/CD update** — `deploy-backend.yml` workflow would need to push to Contabo Docker instead of/alongside Interserver bare uvicorn.

## Alternative: Keep Interserver, Scale Differently

If moving to Docker is too risky right now:

1. **Health check + auto-restart** (already exists via systemd)
2. **Read replicas** — Postgres streaming replication to Contabo
3. **Redis for session caching** — reduce DB load
4. **gunicorn workers** — multiple uvicorn workers on bare Interserver (no Docker needed)

```bash
# Run 4 uvicorn workers instead of 1
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

This gives ~4x throughput on a single host without Docker complexity.

## Recommendation

**Short-term:** Implement gunicorn workers on Interserver (Phase 4 alt above). Quick win, no infra change.

**Long-term:** Move to Contabo Docker + nginx LB when:
- Styxproxy has active traffic requiring horizontal scaling
- A VPN between Interserver and Contabo is set up
- DNS cutover plan is tested

## Files to Change

| File | Change |
|---|---|
| `backend/Dockerfile` | Create/verify Docker image build |
| `docker-compose.yml` | New file in `infrastructure/` |
| `infrastructure/nginx-lb/nginx.conf` | New load balancer config |
| `.github/workflows/deploy-backend.yml` | Add Contabo Docker push step |
| `docs/DOCKER_LB_DESIGN.md` | This file |
