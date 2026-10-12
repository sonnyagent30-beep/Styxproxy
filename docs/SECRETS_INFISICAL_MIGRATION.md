# Option B — Infisical Secrets Platform (Future Migration Path)

**Status:** Proposed, not built. Built 2026-08-25.
**Prerequisite read:** This documents the upgrade path from the in-dashboard
Secrets Vault (`/admin/secrets`, Option A) to a dedicated self-hosted secrets
manager.

---

## Why migrate (trigger conditions)

Migrate from the Secrets Vault to Infisical when **any** of these become true:

1. A second project needs the same secrets (shared Flutterwave/Paystack keys across Styxproxy + another product).
2. You need per-secret audit history / rollback ("what was the key value last Tuesday?").
3. Multiple people/services need different views of the same secret set.
4. Secret rotation needs to be automated (scheduled rotation, expiring keys).
5. The VPS `.env` file becomes a coordination bottleneck (multiple services restarting on change).

If none of these apply, **stay on Option A** — it's simpler and already works.

---

## What Infisical gives us

- Web UI for secrets with environments (dev / staging / prod) per project
- Secret **versioning + point-in-time rollback**
- Role-based access (who can read vs write vs admin each project)
- Full audit log of every read/write
- Machine identities — services authenticate and pull secrets at boot; no `.env` on disk
- Dynamic secrets (optional): generate short-lived DB credentials instead of static ones
- Free self-hosted tier covers everything we need

## Architecture after migration

```
┌──────────────────────────── Interserver VPS (162.35.184.69) ──────────────────────────┐
│                                                                                       │
│  Infisical stack (Docker Compose)          styxproxy-api                              │
│  ├─ infisical (web + API) :8080            boots → fetches secrets from Infisical     │
│  ├─ infisical-db (Postgres)                via Machine Identity (client ID/secret)    │
│  └─ infisical-redis                        caches at boot; no plaintext .env on disk  │
│                                                                                       │
│  Frontend (Vercel) unchanged. Admin "Secrets" tab becomes a thin link/embed or is      │
│  retired in favor of Infisical's own UI at secrets.styxproxy.com (or internal URL).    │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

## Resource cost (matters: 7.8GB Contabo VPS)

| Component | RAM |
|---|---|
| infisical (Node web/API) | ~300–500MB |
| infisical-db (Postgres) | ~150–250MB |
| infisical-redis | ~50MB |
| **Total** | **~0.5–0.8GB** |

⚠️ The main gateway + monitoring stack already run on this box. Before migrating,
check `free -h` headroom. If tight, options: move Infisical DB to the existing
prod Postgres as a separate database (saves ~200MB), or host Infisical on a
small second box ($5/mo).

## Build plan (~1 day)

### Phase 1 — Deploy Infisical
1. Create `/opt/infisical/docker-compose.yml` from the official self-host compose:
   ```bash
   # on VPS
   mkdir -p /opt/infisical && cd /opt/infisical
   curl -o docker-compose.yml https://raw.githubusercontent.com/Infisical/infisical/main/deploy/self-host/docker-compose.yml
   cp .env.example .env  # then edit: ENCRYPTION_KEY, JWT_SECRET, SITE_URL, SMTP creds
   ```
2. Generate required keys:
   ```bash
   openssl rand -base64 32   # ENCRYPTION_KEY
   openssl rand -base64 32   # JWT_SECRET
   ```
3. `docker compose up -d`, then create the superadmin via the first-run signup.
4. Put it behind Nginx at `secrets.internal.styxproxy.com` (LAN-only or Cloudflare Access — do NOT expose publicly without SSO in front).
5. Back up `/opt/infisical` volumes in the nightly backup script (`scripts/backup-styxproxy.sh`).

### Phase 2 — Create project + import secrets
1. In Infisical UI: create project **styxproxy**, environments `dev` / `staging` / `prod`.
2. Import all keys currently in `/opt/styxproxy/backend/.env` into `prod`
   (bulk import via the UI or `infisical CLI import`). Keep the same KEY names
   so zero backend code changes are needed.
3. Create a **Machine Identity** for `styxproxy-api`; grant it read-only on
   `prod`. Save its Client ID + Client Secret somewhere safe (these become the
   only two secrets that still live outside Infisical).
4. Repeat for n8n (it has its own credential store but can pull env vars too).

### Phase 3 — Switch backend boot
Two options:

**a) Wrapper script (simplest, no code change):**
```bash
# /opt/styxproxy/backend/run-with-infisical.sh
export INFISICAL_TOKEN="<machine-identity-token>"  # or UID/SECRET pair
exec infisical run --env=prod -- \
  /opt/styxproxy/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Point `ExecStart=` in `styxproxy-api.service` at the wrapper. Install the
Infisical CLI binary on the VPS first.

**b) Native fetch at startup (code change, more control):**
Add a small loader in `app/config.py` that pulls from Infisical's API using the
Machine Identity before pydantic Settings reads env vars. Only do this if the
wrapper approach causes problems.

### Phase 4 — Decommission Option A pieces
- Keep the `/admin/secrets` tab as **read-only status view** (shows whether the
  service's last secret-sync succeeded), or remove it entirely.
- Remove the sudoers restart helper once Infisical relays changes via webhook
  (Infisical can call a webhook on secret change → trigger restart).

## Rollback plan

The wrapper only *injects* env vars — the app code never changes. Rollback =
point `ExecStart` back at uvicorn directly with the old `.env` (kept at
`/opt/styxproxy/backend/.env.pre-infisical`, chmod 600). Five-minute rollback.

## Security notes

- Never expose Infisical publicly without SSO/Cloudflare Access in front.
- The Machine Identity token lives in the systemd unit environment (root-only readable) — acceptable single bootstrap secret.
- Infisical's own Postgres holds secrets encrypted at rest with ENCRYPTION_KEY — back up both together, keep the key offline (password manager).

## Cost summary

| Item | Cost |
|---|---|
| Software | $0 (self-hosted free tier) |
| Hosting | $0 if current VPS has headroom; else ~$5/mo second box |
| Effort | ~1 day (Phases 1–3), Phase 4 optional |

## Decision record

- **2026-08-25:** Option A (in-dashboard vault) built instead. Infisical deferred until a trigger condition above fires. Dannion approved this ordering.
