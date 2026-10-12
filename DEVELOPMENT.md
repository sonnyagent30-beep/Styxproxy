# Styxproxy — Local Development Setup

This guide gets the full backend stack running on your machine using Docker
Compose. It targets the **dev** compose file (`docker-compose.yml` in the repo
root), not the production deployment (`infrastructure/docker-compose.yml`).

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker Desktop (macOS/Windows) or Docker Engine + Compose plugin (Linux) | v24+ recommended |
| Git | To clone the repo |
| (Optional) Ollama | Only if you want local LLM inference via LiteLLM. Cloud-only mode works without it. |

> **Linux note:** If you are on Linux and prefer the performance of host
> networking (or you need the api to reach host-installed postgres/redis
> directly), see [Host-network opt-in (Linux only)](#host-network-opt-in-linux-only).

## Quick start

```bash
git clone <repo-url> Styxproxy
cd Styxproxy
cp .env.example .env   # if you have one; otherwise defaults below are safe
docker compose up -d
```

The compose file provides safe defaults for all dev secrets. You only need a
`.env` file if you want to override them (e.g. to add real payment provider
keys for end-to-end testing).

### Services started

| Service | URL | Notes |
|---------|-----|-------|
| api | http://localhost:8000 | FastAPI backend. Health: `/health` |
| litellm | http://localhost:4000 | LLM proxy sidecar. Health: `/health` |
| postgres | localhost:5432 | Default user/password/db: `styxproxy` / `styxproxy` / `styxproxy` |
| redis | localhost:6379 | No password in dev |

### Network model (default: bridge)

By default, all services join the `styxproxy_local_net` **bridge** network.
The api reaches postgres, redis, and litellm by **container hostname**:

- `DATABASE_URL` → `postgresql+asyncpg://styxproxy:styxproxy@postgres:5432/styxproxy`
- `REDIS_URL` → `redis://redis:6379/0`
- `LITELLM_BASE_URL` → `http://litellm:4000`

This works identically on Linux, macOS, and Windows Docker Desktop.

## Stopping / restarting

```bash
docker compose down          # stop and remove containers (keeps volumes)
docker compose down -v       # stop and remove containers + volumes (factory reset)
docker compose logs -f api   # tail api logs
docker compose restart api   # restart a single service
```

## Working with Ollama + LiteLLM (optional)

LiteLLM acts as the single LLM gateway for the api. It can route to a local
Ollama instance, cloud providers (Groq, MiniMax), or both.

### macOS / Windows (bridge mode — default)

1. Install and start Ollama natively (not in Docker):

   ```bash
   brew install ollama   # macOS
   ollama serve          # starts on http://127.0.0.1:11434
   ```

2. Edit `backend/litellm/config.yaml` to point at the host:

   ```yaml
   # In litellm_params for your local model, set:
   api_base: http://host.docker.internal:11434
   ```

3. Start the stack:

   ```bash
   docker compose up -d
   ```

### Linux (host-network opt-in)

If you run Ollama natively on Linux and want LiteLLM to reach it via
`127.0.0.1:11434`, you can use the host-network mode (see below). The bridge
mode above also works — just point `api_base` at
`http://172.17.0.1:11434` (your host's docker0 gateway IP).

## Host-network opt-in (Linux only)

Host networking (`network_mode: host`) is **Linux-only**. On macOS/Windows
Docker Desktop, containers do not share the host loopback — host mode will
silently break connectivity.

To use host networking on Linux (e.g. because you have postgres/redis
installed directly on the host, not in containers):

```bash
export CHARON_LLM_HOST_NETWORK=1
export DATABASE_URL=postgresql+asyncpg://styxproxy:styxproxy@127.0.0.1:5432/styxproxy
export REDIS_URL=redis://127.0.0.1:6379/0
export LITELLM_BASE_URL=http://127.0.0.1:4000
docker compose up -d
```

When `CHARON_LLM_HOST_NETWORK=1`:

- The api joins the host network directly (no bridge).
- The api reaches postgres/redis/litellm via `127.0.0.1` (override the env
  vars above if the compose file's bridge defaults don't apply).
- The `depends_on` blocks are still evaluated, but the api does not wait for
  the bridge network to be ready — you are responsible for ensuring host
  services are running.

## Production vs dev compose

| Aspect | Dev (`docker-compose.yml`) | Prod (`infrastructure/docker-compose.yml`) |
|--------|---------------------------|---------------------------------------------|
| Network | Bridge (default) or opt-in host | Bridge only (`styxproxy_net`) |
| DB pooling | Direct to postgres | Through PgBouncer |
| Sentry | Not included | Included |
| SSL/TLS | Not included | Nginx + Certbot |
| Restart policy | `unless-stopped` | `unless-stopped` |

The production compose file is unaffected by dev networking changes. Do not
use the dev compose file for production deployments.

## Troubleshooting

### `docker compose up` fails with "port is already allocated"

Another service (or a previous `docker compose up`) is using the port.
Either stop the conflicting service or override the port in `.env`:

```bash
# Example: remap api to port 8001
API_PORT=8001 docker compose up -d
```

### API can't connect to postgres or redis

Make sure you are running in **bridge mode** (the default) and that the
`DATABASE_URL` / `REDIS_URL` env vars point to `postgres` / `redis`
(hostnames), not `127.0.0.1`. In bridge mode, `127.0.0.1` inside the
container refers to the container itself, not the host.

### LiteLLM can't reach Ollama

- **macOS/Windows (bridge):** Ensure `api_base` in `config.yaml` uses
  `http://host.docker.internal:11434` (not `127.0.0.1`).
- **Linux (host mode):** Ensure Ollama is bound to `0.0.0.0` or `127.0.0.1`
  (check `ollama serve` output). The host network namespace is shared, so
  `127.0.0.1:11434` must be reachable from the host.

### Changes to backend code are not reflected

The dev compose file bind-mounts `./backend/app` into the container:

```yaml
volumes:
  - ./backend/app:/app/app:ro
```

After saving a file, restart the api service:

```bash
docker compose restart api
```

Uvicorn is configured with `--reload` in `Dockerfile.dev`, so most changes
should auto-reload without a manual restart. If that fails, restart anyway.

## `.env` variable reference

These variables can be set in `.env` (or exported in the shell) to override
the compose defaults. See `.env.example` if present.

| Variable | Default | Purpose |
|----------|---------|---------|
| `POSTGRES_DB` | `styxproxy` | Database name |
| `POSTGRES_USER` | `styxproxy` | Database user |
| `POSTGRES_PASSWORD` | `styxproxy` | Database password |
| `DATABASE_URL_BRIDGE` | `postgresql+asyncpg://…@postgres:5432/…` | Override DB URL (bridge mode) |
| `REDIS_URL_BRIDGE` | `redis://redis:6379/0` | Override Redis URL (bridge mode) |
| `DATABASE_URL_HOST` | (none) | DB URL when using host network |
| `REDIS_URL_HOST` | (none) | Redis URL when using host network |
| `LITELLM_BASE_URL` | `http://litellm:4000` | LiteLLM proxy URL |
| `LITELLM_API_KEY` | `sk-styxproxy-local-dev-only` | API key for the proxy |
| `LITELLM_CLOUD_API_KEY` | (none) | Cloud LLM fallback key |
| `LITELLM_DATABASE_URL` | (none) | LiteLLM's own database (for logging) |
| `CHARON_LLM_HOST_NETWORK` | `bridge` | Set to `1` for host network (Linux only) |
| `LITELLM_NETWORK_MODE` | `host` | Set to `bridge` to force LiteLLM onto bridge |
| `JWT_SECRET` | `dev-secret-change-in-production` | JWT signing key |
| `ADMIN_TOKEN` | `dev-admin-token` | Admin panel token |
| `LOG_LEVEL` | `DEBUG` | Logging verbosity |
| `FLUTTERWAVE_SECRET_KEY` | (none) | Payment provider (live mode) |
| `WHATSAPP_ACCESS_TOKEN` | (none) | WhatsApp Business API |
| `GROQ_API_KEY` | (none) | Groq cloud LLM |
| `MINIMAX_API_KEY` | (none) | MiniMax cloud LLM |
| `RESEND_API_KEY` | (none) | Email provider |

> **Never commit real secrets.** The `.env` file is gitignored. Use the
> defaults for local development only.

## FAQ

**Q: Does this work on Windows without WSL2?**
A: Yes. Docker Desktop on Windows (with WSL2 backend) works in bridge mode
(default). The host-network opt-in (`CHARON_LLM_HOST_NETWORK=1`) is Linux-only.

**Q: Can I run just the api without postgres/redis?**
A: Only if you have those services running elsewhere. Use
`docker compose up -d api` and set `DATABASE_URL` / `REDIS_URL` to point at
your external services.

**Q: How do I switch back to the old behavior (host network by default)?**
A: Set `CHARON_LLM_HOST_NETWORK=1` in your `.env` or shell environment. See
[Host-network opt-in](#host-network-opt-in-linux-only) above.

**Q: Where are the dev defaults for the production-like infra (Sentry, Nginx, PgBouncer)?**
A: Those live in `infrastructure/docker-compose.yml` and are intentionally not
part of the dev stack. Use the dev compose for backend development; use the
infrastructure compose for full-stack local testing or production deploys.
