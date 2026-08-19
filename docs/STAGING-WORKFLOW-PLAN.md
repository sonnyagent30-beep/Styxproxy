# Styxproxy Staging Workflow Plan

**Owner:** Dannion (manual approval on all prod merges)
**Author:** Sonny
**Date:** 2026-08-19
**Status:** PROPOSED — review before implementation

---

## TL;DR

We currently have a half-broken deploy pipeline that caused today's 90-min prod
outage. This plan splits the work into **three independent environments** with
proper gates, deprecates the over-aggressive auto-deploy, and gives you clear
sign-off points before anything touches production.

---

## 1. Three-Environment Model

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DEV (local)   │ ──▶│  STAGING (live) │ ──▶│   PROD (live)   │
│  repo: cpt-*    │    │   repo: main    │    │   repo: main    │
│  /api → :8000   │    │  https://api-   │    │  https://api.   │
│                 │    │  staging.*      │    │  styxproxy.com  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
   auto-deploy            manual sign-off          manual sign-off
   on push                required                 required
```

### Environment definitions

| Env | Backend URL | Frontend URL | DB | Branch | Deploy trigger |
|---|---|---|---|---|---|
| **Dev** (local) | `localhost:8000` | `localhost:3000` | docker | any | manual |
| **Staging** | `https://api.staging.styxproxy.com` | `https://styxproxy-cpt-staging.vercel.app` | `styxproxy_staging` | `cpt-admin-ui` | auto (after fix) |
| **Prod** | `https://api.styxproxy.com` | `https://styxproxy.com` | `styxproxy` | `main` | manual sign-off |

---

## 2. Current State — What We Have Today

### What works
- ✅ Frontend auto-deploy to Vercel (`styxproxy-cpt-staging.vercel.app`)
- ✅ Production backend serving healthy 200s on `/api/v1/health`, `/api/catalog`,
     `/api/countries`, `/health`
- ✅ Repo on `cpt-admin-ui` has all fixes needed for both backend + frontend

### What's broken (caused today's outage)
- ❌ `.github/workflows/deploy-backend-staging.yml` syncs `/opt/styxproxy/repo`
     to `/opt/styxproxy/backend` on every push, with **no verification step**
- ❌ No health check after restart — workflow exits green even when the app
     fails to boot (we hit this 3 separate times today)
- ❌ `rsync --delete` wipes server-side fixes (any hotfix gets clobbered on
     next push)
- ❌ Auto-deploys to production AND staging from the same workflow
- ❌ No DB migrations step — we run `create_all` which requires CREATE
     privileges we don't have on `styxproxy` DB
- ❌ Alembic has **3 heads** (referral_system_v1, rls_platform_account_v1,
     023_usage_alert_timestamps) — need a merge migration
- ❌ Production DB has only `countries=197` rows; `plan_settings=0` so
     `/api/countries` returns `{"countries":[]}`

---

## 3. The Staging Workflow (Proposed)

### 3.1 Branch & Merge Model

```
main (PRODUCTION)
  ↑
  │  PR merge after manual approval
  │
cpt-admin-ui (STAGING + dev)
  ↑
  │  direct push (anyone on team)
  │
feature/* branches → PR to cpt-admin-ui (optional for solo dev)
```

- **`cpt-admin-ui`** is the only branch with auto-deploy to staging
- **`main`** only moves via PR from `cpt-admin-ui` after you've signed off
- We **never** push directly to `main`
- We **never** auto-deploy to production

### 3.2 What triggers staging deploy

| Trigger | Action |
|---|---|
| Push to `cpt-admin-ui` | Auto-deploy to **staging** only |
| PR merge to `main` (after approval) | Manual run of prod deploy workflow |
| Hotfix needed urgently | Manual SSH + git pull on prod, post-commit |

### 3.3 Staging deploy pipeline (new)

```yaml
# .github/workflows/deploy-backend-staging.yml (rewritten)

name: deploy-staging
on:
  push:
    branches: [cpt-admin-ui]
    paths:
      - 'backend/**'

jobs:
  test:
    steps:
      - ruff lint
      - ruff format check
      - pytest (skip if env not available)
      - bandit (warnings only)

  migrate:
    needs: test
    steps:
      - SSH to staging
      - alembic upgrade heads (after merging the 3 heads first)

  deploy:
    needs: migrate
    steps:
      - SSH to staging
      - rsync repo → /opt/styxproxy/staging-repo (NOT /opt/styxproxy/backend)
      - symlink or restart `styxproxy-staging-api` only
      - **wait for healthy** — curl /api/v1/health with 30s timeout
      - **verify routes** — curl /api/catalog, /api/countries
      - **smoke test** — POST to /api/v1/auth/test-login or similar
      - on failure: roll back to last known good tag

  notify:
    needs: deploy
    if: always()
    steps:
      - post to Telegram "Staging deploy ✅" or "❌ rolled back"
```

**Key changes from current workflow:**
- Deploys to **`/opt/styxproxy/staging-repo`** (separate from prod code)
- Runs **`styxproxy-staging-api`** on a different port (9000) with staging DB
- **Doesn't touch** `/opt/styxproxy/backend` or `styxproxy-api` (prod)
- Has actual health verification before declaring success
- Has rollback to a known-good tag if health check fails

### 3.4 Production deploy pipeline (new)

```yaml
# .github/workflows/deploy-backend-prod.yml (rewritten)

name: deploy-prod
on:
  workflow_dispatch:
    inputs:
      approved_by:
        description: 'Manual approval — your name'
        required: true
      rollback_tag:
        description: 'Tag to roll back to if this fails (default: previous prod tag)'

jobs:
  preflight:
    steps:
      - check: latest commit on main matches staging HEAD
      - check: all tests green on main
      - check: no `DROP TABLE` or `TRUNCATE` in migration files
      - check: secrets are real (not "test-*") in target env

  backup:
    needs: preflight
    steps:
      - pg_dump prod DB → /opt/styxproxy/backups/$(date).sql
      - tag current prod code as rollback point

  migrate:
    needs: backup
    steps:
      - alembic upgrade heads
      - verify schema diff is expected

  deploy:
    needs: migrate
    steps:
      - rsync repo → /opt/styxproxy/backend
      - restart styxproxy-api
      - health check (30s timeout, 5 retries)
      - **manual confirmation required** before marking success
        (Telegram ping with "Type YES to confirm deploy")

  notify:
    if: always()
    steps:
      - Telegram ping with deploy status + DB backup location
```

**Key change from current:** this is `workflow_dispatch` only — never runs
automatically. You trigger it manually from GitHub Actions UI after merging
to main.

---

## 4. Immediate Action Items (Before Any Merges)

### 4.1 Merge alembic heads

```bash
cd /opt/styxproxy/backend
alembic merge heads -m "merge 3 heads (referral, rls, alerts)"
alembic upgrade heads
```

This single migration file unblocks all future schema changes.

### 4.2 Audit & seed production DB

Production needs these tables/columns populated:

| Table | Current | Required |
|---|---|---|
| `countries` | 197 ✅ | seeded |
| `plans` | 28 ✅ | has data |
| `plan_settings` | **0 ❌** | needs seeding (admin dashboard) |
| `referral_credits` | exists but empty | seed via dashboard or migration |
| `trial_sessions` | exists but empty | seed via dashboard or migration |
| `country_plan_types.is_special` | missing column ❌ | needs migration |

**Per your rule:** pricing/plan settings go through admin dashboard, not SQL.
I'll prep the dashboard steps for you. Anything that's strictly schema (missing
columns) goes through Alembic.

### 4.3 Replace placeholder secrets

Current prod `.env` has:
- `FLUTTERWAVE_WEBHOOK_SECRET=test-flutterwave-webhook-secret-not-real-32chars`
- `THEOREM_REACH_WEBHOOK_SECRET=test-theorem-reach-webhook-secret-not-real-32chars`

Real secrets needed from:
- Flutterwave dashboard → Settings → Webhooks
- Theorem Reach dashboard → Integrations → Webhooks

Once provided, I'll add to `/opt/styxproxy/.env` via SSH.

### 4.4 Disable auto-deploy to prod

The current `deploy-backend.yml` triggers on push to `main`. Need to change
to `workflow_dispatch` only, so prod never moves unless you click the button.

### 4.5 Separate staging and prod code dirs

Today `/opt/styxproxy/backend` is prod and `/opt/styxproxy/staging-repo` is
staging (but staging uses the SAME systemd service on different port). Need
to make this cleaner:

```
/opt/styxproxy/
├── backend/              # PROD code (deployed from main)
├── staging-repo/         # STAGING code (deployed from cpt-admin-ui)
├── repo/                 # git working copy (prod branch main)
├── staging-repo-git/     # git working copy (staging branch cpt-admin-ui)
├── .env                  # prod env
├── .staging.env          # staging env
└── backups/              # pg_dump backups with timestamps
```

### 4.6 Add rollback tag pattern

Every successful prod deploy creates a tag `prod-YYYY-MM-DD-HHMM`. Rollback is
just `git checkout prod-YYYY-MM-DD-HHMM && ./restart.sh`.

---

## 5. Verification Checklist (Before You Sign Off on Prod Merge)

After staging is verified, before merging to main:

- [ ] All health endpoints return 200 on staging: `/api/v1/health`,
       `/api/catalog`, `/api/countries`, `/health`, `/api/maintenance`
- [ ] No new errors in `/var/log/styxproxy-api.err.log` after 24h on staging
- [ ] DB migrations ran cleanly on staging DB (no `alembic_version` drift)
- [ ] Plan prices visible in admin dashboard (confirms `plan_settings` seeded)
- [ ] Country filtering works on globe map (front-end test)
- [ ] Webhook endpoints accept test pings from Flutterwave + Theorem Reach
- [ ] Real (not test) secrets are set on staging env
- [ ] Load test: 100 RPS for 5 min on staging (smoke test for the workers fix)
- [ ] You've manually clicked through pricing → checkout → payment on staging

---

## 6. What I'll Build

### Phase 1 (this week)
1. **Merge alembic heads** — single migration file
2. **Add `is_special` column migration** — fix the column that's missing
3. **Rewrite `deploy-backend-staging.yml`** — separate staging dir, health checks
4. **Convert `deploy-backend.yml` to `workflow_dispatch`** — no more auto-prod
5. **Add rollback tag automation**
6. **Document the new env structure** — this file becomes the source of truth

### Phase 2 (after staging stabilized)
1. **Build `deploy-backend-prod.yml`** with preflight checks
2. **Add staging smoke tests** that run automatically after deploy
3. **Add Telegram notifications** for both staging and prod deploys
4. **Add the `admin-dashboard-steps` doc** so you have copy-paste instructions
   for pricing changes

### Phase 3 (production readiness)
1. **Secrets management** — replace `test-*` with real secrets, then rotate
   quarterly
2. **Backup automation** — daily pg_dump with 30-day retention
3. **Monitoring alerts** — Grafana alerts on boot failure, error rate spikes,
   DB connection pool exhaustion

---

## 7. What I Want From You

1. **Sign off on the 3-env model** — confirm you want staging on
   `api.staging.styxproxy.com` (or different URL)
2. **Confirm the branch model** — `cpt-admin-ui` → staging auto, `main` →
   prod only on your sign-off
3. **Provide real webhook secrets** when you're ready
4. **Approve Phase 1 work** before I start (or revise the plan first)

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Auto-deploy to staging still breaks prod | Separate `backend/` and `staging-repo/` dirs, separate systemd services |
| Merging 3 alembic heads fails | Test on staging DB first, keep rollback migration ready |
| Today's fixes (0897537, 50ed1d7) get overwritten again | Repo is now correct; server fixes are patches over fixed repo. Next deploy will work. |
| Missing columns cause app crash | Add migration BEFORE merging to main |
| No DB backup before prod migrate | Phase 1 #6 — daily pg_dump automation |
| Webhook secrets leak via `.env` in repo | Confirm `/opt/styxproxy/.env` is in `.gitignore` (it should be) and not committed |

---

## 9. Open Questions

1. **Staging URL:** `api.staging.styxproxy.com`? Or reuse the existing
   `styxproxy-cpt-staging.vercel.app` proxy? (current setup proxies through
   Vercel)
2. **Database:** new `styxproxy_staging` DB? Or shared DB with schema prefix?
3. **Rollback window:** how long do we keep `prod-*` tags? (suggest: 30 days)
4. **Who can approve prod merges?** Just you, or anyone with repo write access?
5. **What about data migrations?** Do we have any in-flight data fixes that
   need to run before schema changes?

---

*This is a living doc. I'll update it as we make decisions.*

---

## 10. Phase 1 Status (Aug 19 2026)

✅ **All Phase 1 prep work complete on `cpt-admin-ui` branch:**

| Item | Status | Commit |
|---|---|---|
| Merge 3 alembic heads into single migration | ✅ Done | `8247eb2` |
| Verify `is_special` column exists (it does) | ✅ Verified (no migration needed) | n/a |
| Rewrite `deploy-backend-staging.yml` — separate staging dir, health checks, rollback | ✅ Done | `e999ea9` |
| Convert `deploy-backend.yml` to `workflow_dispatch` only (no auto-prod) | ✅ Done | `e999ea9` |
| Add rollback tag automation to both workflows | ✅ Done | `e999ea9` |

### What still needs to happen BEFORE merging to main

1. **Provide real webhook secrets** (Flutterwave + Theorem Reach) so `.env` doesn't have `test-*` placeholders
2. **Seed `plan_settings` table** via admin dashboard (currently 0 rows → `/api/countries` returns empty)
3. **You manually test staging** by going through checkout flow on `https://styxproxy-cpt-staging.vercel.app`
4. **Merge staging plan into memory** — your explicit preferences for prod merge

### What the new prod deploy workflow looks like

Before:
```yaml
on:
  push:
    branches: [main]  # ← auto-deploys on every push to main
```

After:
```yaml
on:
  workflow_dispatch:   # ← ONLY manual button click
    inputs:
      approved_by:
        description: 'Your name (manual approval required)'
        required: true
```

Plus 3 new steps: DB backup, alembic upgrade, rsync to actual runtime dir.

### What the new staging deploy workflow looks like

Before:
- Triggered on push to cpt-admin-ui ✅ (kept)
- Synced /opt/styxproxy/repo → /opt/styxproxy/backend ❌ (this was the bug — it was deploying to prod!)
- No health check (exited green even when app crashed)
- No rollback

After:
- Triggers on push to cpt-admin-ui ✅
- Updates /opt/styxproxy/staging-repo (separate from prod) ✅
- Health check on port 8001 (not 8000 which is prod) ✅
- Verifies `/api/catalog`, `/api/countries`, `/health` all 200 ✅
- Auto-rollback using `staging-rollback-*` tag ✅

---

## 11. Open Questions — Still Waiting on Your Input

These are blocking the prod merge:

1. **Real webhook secrets** — when can you get them from Flutterwave + Theorem Reach dashboards?
2. **Plan settings seeding** — should I prep the admin dashboard steps doc, or do you want to seed them yourself?
3. **Staging URL** — `api.staging.styxproxy.com`? Or stay with Vercel proxy at `styxproxy-cpt-staging.vercel.app`?
4. **Branch model confirmation** — `cpt-admin-ui` → staging auto, `main` → prod only on your sign-off?
5. **Who can approve prod merges?** Just you?

---
