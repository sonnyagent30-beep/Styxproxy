# Styxproxy: Rebuild Plan (Staging from Scratch)

**Owner:** Dannion (manual approval)
**Author:** Sonny
**Date:** 2026-08-19
**Goal:** Wipe all staging remnants. Build a clean standard staging system.

---

## TL;DR

You want a clean slate:
- ❌ No `cpt-admin-ui` branch (delete it)
- ❌ No `styxproxy-cpt-staging` Vercel project (disconnect + archive)
- ❌ No `staging` / `styxproxy-staging-api` / `.staging.env` / `staging-repo` (delete)
- ❌ No `styxproxy-sprint-fixes-2026-08-19` branch (delete)
- ✅ **Rebuild staging properly** with its own GitHub repo + Vercel project + separate backend service + standard workflow

---

## Current State — Everything That Will Go

### GitHub (sonnyagent30-beep/Styxproxy)
| Resource | Action |
|---|---|
| `cpt-admin-ui` branch | 🗑️ Delete (work is already on main) |
| `styxproxy-sprint-fixes-2026-08-19` branch | 🗑️ Delete (work was merged) |
| `develop` branch | 🗑️ Delete (orphaned) |
| `feat/superadmin-dashboard` and other stale feature branches | 🗑️ Delete (6-7 stale branches) |
| `staging` environment (GitHub) | 🗑️ Delete |
| `Preview – styxproxy-cpt-staging` environment | 🗑️ Delete |
| `Production – styxproxy-cpt-staging` environment | 🗑️ Delete |
| `Preview – bunche-api-push` environment | 🗑️ Delete |
| `Production – bunche-api-push` environment | 🗑️ Delete |
| `cloudflare-pages` environment | 🗑️ Delete (was experimental) |
| `joyful-tenderness / production` environment | 🗑️ Delete (old test env) |
| `staging` workflow file | 🗑️ Delete `.github/workflows/deploy-backend-staging.yml` |
| `deploy-staging.yml` workflow file | 🗑️ Delete |

### Vercel
| Project | Action |
|---|---|
| `styxproxy-cpt-staging` (serves styxproxy-cpt-staging.vercel.app) | 🗑️ Disconnect from repo, archive in Vercel |
| `bunche-api-push` (serves styxproxy.com via NEXT_PUBLIC_API_URL) | ✅ KEEP — this is production frontend |

### Server (Interserver 162.35.184.69)
| Resource | Action |
|---|---|
| `styxproxy-staging-api` systemd service | 🗑️ `systemctl disable --now && rm service file` |
| `/opt/styxproxy/staging-repo/` | 🗑️ Archive to backups, then `rm -rf` |
| `/opt/styxproxy/.staging.env` | 🗑️ Archive then delete |
| `/opt/styxproxy/backend/` | ✅ KEEP — production backend |
| `/opt/styxproxy/repo/` | ✅ KEEP — git working copy on main |
| `/opt/styxproxy/.env` | ✅ KEEP — production env |
| `styxproxy-api`, `styxproxy-addkey`, `styxproxy-alloy`, `styxproxy-dante-*`, `styxproxy-fulfillment-worker`, `styxproxy-relay-paid` | ✅ KEEP — production services |

### Postgres
| Database | Action |
|---|---|
| `styxproxy` | ✅ KEEP — production DB |
| `styxproxy_staging` | 🗑️ Drop (only used by old staging backend) |

### Vercel URLs after cleanup
- `https://styxproxy.com` → production (via `bunche-api-push`) ✅
- `https://api.styxproxy.com` → production backend ✅
- `https://styxproxy-cpt-staging.vercel.app` → 🗑️ gone

---

## New State — What Gets Built

### New GitHub Repo: `sonnyagent30-beep/Styxproxy-staging`

A separate repo for staging. Mirrors the prod repo but stays on its own branch.

**Why a separate repo?**
- Clean separation: prod repo only has prod code, staging repo has staging code
- Vercel auto-deploys are scoped to one repo each
- Easy to delete staging entirely without touching prod
- Standard practice (most teams do this)

**Structure:**
```
sonnyagent30-beep/Styxproxy          (production repo)
├── main                — production code, protected branch
└── (no other branches)

sonnyagent30-beep/Styxproxy-staging  (new staging repo)
├── main                — staging code, auto-deploys to Vercel
└── (feature branches as needed)
```

**Workflow:**
- Push to staging repo `main` → auto-deploys to Vercel staging frontend
- Push to prod repo `main` → triggers prod backend deploy workflow
- To sync staging with prod: PR from prod `main` → staging `main` (or sync script)

### New Vercel Project: `styxproxy-staging`

- New Vercel project connected to `Styxproxy-staging` repo
- rootDirectory: `frontend`
- Auto-deploys on push to `main` in that repo
- URL: `https://styxproxy-staging.vercel.app` (or similar fresh URL)
- Environment variable: `NEXT_PUBLIC_API_URL=https://api-staging.styxproxy.com`

### New Backend URL: `api-staging.styxproxy.com`

- New DNS A record pointing to staging backend server (or new instance)
- New systemd service: `styxproxy-staging-api` on port 8001
- New env file: `/opt/styxproxy/staging/.env`
- New code dir: `/opt/styxproxy/staging/`
- New git working copy: `/opt/styxproxy/staging/repo`
- New DB: `styxproxy_staging` (already exists, will be reseeded)

### New Deploy Workflows

**Staging backend deploy** (in `Styxproxy-staging` repo):
```yaml
name: deploy-staging-backend
on:
  push:
    branches: [main]
    paths: ['backend/**']
jobs:
  deploy:
    - SSH to staging server
    - git pull in /opt/styxproxy/staging/repo
    - rsync to /opt/styxproxy/staging/
    - systemctl restart styxproxy-staging-api
    - health check (curl /api/v1/health, /api/catalog, /api/countries)
    - fail-fast on any non-200
```

**Production backend deploy** (in `Styxproxy` repo, unchanged from today):
```yaml
name: deploy-prod-backend
on:
  workflow_dispatch:
    inputs:
      approved_by:
        required: true
```

### Standard Practice Improvements

| Item | Standard practice | Our plan |
|---|---|---|
| Branch model | `main` on each repo is the only long-lived branch | ✅ Yes |
| Staging URL | Separate domain/subdomain | `api-staging.styxproxy.com` |
| Frontend URL | Preview deployments per PR | Vercel auto (free) |
| Backend deploy | Auto on push for staging, manual for prod | ✅ Yes |
| Secrets | Per-environment, real values, rotated quarterly | ✅ Will set real Flutterwave + Theorem Reach secrets for staging only |
| DB | Separate DB per environment | ✅ `styxproxy` (prod) and `styxproxy_staging` (staging) |
| Health checks | Required before declaring deploy success | ✅ Yes |
| Rollback | Git tag per deploy, revert script | ✅ Yes |

---

## Execution Plan — Step by Step

### Phase A: Archive before delete (safe)

```bash
# On the server
mkdir -p /opt/styxproxy/backups/staging-wipe-2026-08-19
tar -czf /opt/styxproxy/backups/staging-wipe-2026-08-19/staging-repo.tar.gz /opt/styxproxy/staging-repo
cp /opt/styxproxy/.staging.env /opt/styxproxy/backups/staging-wipe-2026-08-19/.staging.env
cp /etc/systemd/system/styxproxy-staging-api.service /opt/styxproxy/backups/staging-wipe-2026-08-19/

# Backup the staging DB too
sudo -u postgres pg_dump -d styxproxy_staging -Fc -f /opt/styxproxy/backups/staging-wipe-2026-08-19/staging-db.dump
```

### Phase B: Delete on the server

```bash
systemctl disable --now styxproxy-staging-api
rm /etc/systemd/system/styxproxy-staging-api.service
systemctl daemon-reload
rm -rf /opt/styxproxy/staging-repo
rm -f /opt/styxproxy/.staging.env

# Drop the staging DB
sudo -u postgres dropdb styxproxy_staging
```

### Phase C: Delete GitHub stuff

```bash
# Delete branches
git push origin --delete cpt-admin-ui
git push origin --delete styxproxy-sprint-fixes-2026-08-19
git push origin --delete develop
git push origin --delete feat/superadmin-dashboard
# ... (other stale branches)

# Delete environments via gh API
gh api -X DELETE repos/sonnyagent30-beep/Styxproxy/environments/staging
gh api -X DELETE repos/sonnyagent30-beep/Styxproxy/environments/Preview%20%E2%80%93%20styxproxy-cpt-staging
# ... etc

# Delete workflow files
git rm .github/workflows/deploy-backend-staging.yml
git rm .github/workflows/deploy-staging.yml
git commit -m "chore: remove all staging workflows"
git push origin main
```

### Phase D: Disconnect Vercel project

In Vercel dashboard:
1. Go to `styxproxy-cpt-staging` project → Settings → Git → Disconnect
2. Archive the project (don't delete, just archive in case we need it)

### Phase E: Build new staging

1. Create new GitHub repo `sonnyagent30-beep/Styxproxy-staging`
2. Push main branch from prod repo (initial state)
3. In Vercel: create new project `styxproxy-staging` → link to new repo
4. Set `NEXT_PUBLIC_API_URL=https://api-staging.styxproxy.com` in Vercel env
5. On the server: create `/opt/styxproxy/staging/` with new systemd service on port 8001
6. Create DNS record: `api-staging.styxproxy.com` → server IP
7. Seed `styxproxy_staging` DB with same schema as prod (alembic upgrade heads)

---

## Risks & Open Questions

1. **DNS for api-staging.styxproxy.com** — do you own styxproxy.com DNS? Where? (Cloudflare? Namecheap?)
2. **Server for staging backend** — same VPS (162.35.184.69) or separate?
3. **Old `styxproxy-cpt-staging` URL** — anyone has it bookmarked? Customer-facing?
4. **bunche-api-push Vercel project** — leave alone or rename to `styxproxy-prod`?
5. **Plan to make staging DB live again** — fresh schema copy from prod, or start empty?
6. **Real webhook secrets for staging** — same Flutterwave test webhook, or new staging-only webhook URLs?

---

## What I'll Do Once You Say Go

1. Archive everything (Phase A) — 5 min
2. Delete on server (Phase B) — 5 min  
3. Delete GitHub branches + environments (Phase C) — 10 min
4. Walk you through Vercel disconnect (Phase D) — manual
5. Build new staging (Phase E) — depends on DNS/server questions

After Phase E, staging will be a clean separate system with its own repo, Vercel project, server dir, DB, and standard workflow.

**Total time:** ~30 min for cleanup, then your DNS answer needed for the rebuild.

---
