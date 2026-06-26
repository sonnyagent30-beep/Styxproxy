# ADR-004: Secrets Management for Bunche

**Status:** Accepted
**Date:** 2026-06-26
**Decision Driver:** Pay-money-on-the-line business, secrets are capabilities.

---

## Context

Bunche handles:
- Money (Flutterwave secret key, webhook verification hash)
- Customer PII (PostgreSQL credentials, Redis sessions)
- Provider APIs (Proxy-Seller, DataImpulse — proxy generation + balance reads)
- WhatsApp Business API (access token, app secret)
- Admin auth (TOTP encryption key, admin PIN bcrypt hash)
- Cloudflare R2 (file storage credentials)

A leaked key = loss of money, customer trust, or full account takeover.

**Constraint:** Bunche runs on a single Hetzner CX21 VPS (~$7/mo). Budget for infra tooling is minimal. We need a secrets strategy that:
1. Doesn't blow the budget
2. Doesn't leak via frontend code (N/A — Bunche is WhatsApp-only, no frontend)
3. Doesn't leak via logs or backups
4. Survives operator error (rotating a key doesn't break prod)
5. Scales gracefully when we add a secrets manager later

---

## Decision

### Phase 1 (Launch — Day 1)

Use `.env` file on VPS with strict operational discipline:

| Practice | Why |
|----------|-----|
| `.env` lives at `/opt/bunche/.env`, chmod 600, owned by `root` | Only root can read it |
| `.env.example` is in git, `.env` is in `.gitignore` | Operators copy example, fill in real values |
| Docker Compose reads env via `env_file:` directive | Never inline secrets in compose YAML |
| Never log env values (n8n expression: `JSON.stringify($env)` is forbidden) | Logs go to R2 / log aggregator — secrets must never reach them |
| Backup script strips env from any dumps (pg_dump doesn't include it — n8n config does; we exclude `/opt/bunche/.env` from backups) | Backups in R2 should never contain live secrets |
| All keys are scoped per provider (no global admin tokens) | Minimum blast radius per key |
| Webhook secrets (Flutterwave `verif-hash`, WhatsApp `app secret`) are HMAC-verify-only — no API capability | Compromise lets attacker forge webhooks, not steal funds |

### Phase 2 (After 1,000 customers — ~Month 3)

Move to **Doppler** (free tier supports 1 project, 3 users — fits Bunche):

| Benefit | Cost |
|---------|------|
| Centralized secret storage | Free |
| Audit log of secret access | Free |
| Per-environment secrets (dev/staging/prod) | Free |
| Auto-rotate webhook secrets with zero-downtime | Free |
| Inject via sidecar at n8n startup | Free |

**Migration trigger:** When we hit 3+ VPS instances OR when an operator changes roles (security incident response).

### Phase 3 (After 10,000 customers — ~Year 1)

Move to **HashiCorp Vault** or **AWS Secrets Manager** with workload identity:

| Benefit | Cost |
|---------|------|
| Short-lived credentials (15-min TTL) | $0–50/mo |
| Policy-as-code ACLs per workflow | — |
| Automated rotation (DB password every 90 days auto-triggered) | — |
| Full audit trail of every secret read | — |

---

## Alternatives Considered

### Option A: Hardcode secrets in n8n workflow JSON

**Rejected.** Workflows get exported to `.n8n/workflows/*.json` and committed to git. Anyone with repo read access sees the secrets. Disqualifying.

### Option B: HashiCorp Vault from Day 1

**Rejected for Phase 1.** Operational overhead (Vault server, unsealing, audit log shipping) is too much for a single-VPS deployment. Premature complexity. We'll reach for it when the deployment justifies the cost.

### Option C: AWS Secrets Manager / GCP Secret Manager

**Rejected.** Bunche runs on Hetzner, not AWS/GCP. Cross-cloud secret fetch adds latency + a permanent cloud bill. We don't need it yet.

### Option D: Doppler from Day 1

**Considered.** Doppler free tier is genuinely useful. Decided to defer because:
1. Bunche is single-VPS, single-operator (Dannion). Doppler shines for multi-env + multi-operator.
2. Adds one more account/credential to manage.
3. Phase 1 discipline + Phase 2 migration is a clean path.

---

## Consequences

### Positive

- **Zero cost** in Phase 1
- **Operator-friendly** — `.env` is industry standard, every dev knows it
- **Easy to migrate** — Doppler/Vault swap is a config change, not a rewrite
- **No frontend exposure** — Bunche has no frontend. There is no client-side key risk.

### Negative

- **Single point of failure** — VPS compromise = all secrets leaked
- **Manual rotation** — operator must SSH + edit + restart n8n for every rotation
- **No audit trail** — we can't tell when secrets were read or by whom
- **Backup hygiene required** — we MUST exclude `.env` from any backup that goes off-VPS

### Mitigations

| Risk | Mitigation |
|------|------------|
| VPS compromise | SSH key auth only (no password). Fail2ban on SSH. n8n runs as non-root user inside Docker. |
| Manual rotation pain | Phase 2 Doppler migration eliminates this |
| No audit trail | Application-level audit log (`customer_audit_log` table) records workflow executions; secret reads are NOT logged but secret USAGE is (via API call timestamps) |
| Backup leak | `rclone exclude` rule for `.env`. Backup script also explicitly `--exclude='.env'` |

---

## Rotation Policy

| Secret | Rotation Frequency | Owner |
|--------|--------------------|-------|
| PostgreSQL password | Every 90 days | Dannion |
| Redis password | Every 90 days | Dannion |
| n8n basic auth password | Every 180 days | Dannion |
| Admin PIN | Every 180 days (or on role change) | Dannion |
| TOTP encryption key | NEVER (data loss — would invalidate all TOTP secrets) | Locked |
| Flutterwave secret key | On staff change OR incident | Dannion |
| Flutterwave webhook hash | Every 30 days | Dannion |
| WhatsApp access token | Every 60 days (Meta rotates anyway) | Meta-managed |
| WhatsApp app secret | On staff change OR incident | Dannion |
| Proxy-Seller API key | On staff change OR incident | Dannion |
| DataImpulse API key | On staff change OR incident | Dannion |
| R2 access keys | Every 90 days | Dannion |
| MiniMax API key | Every 90 days | Dannion |
| Bitlock.ai API key | On staff change OR incident | Dannion |

**Emergency rotation** = immediately on any suspected compromise. Don't wait for the schedule.

---

## Compliance Notes

- NDPR (Nigeria Data Protection Regulation) applies — secrets handling contributes to Article 2.4 (security of processing)
- PCI-DSS doesn't directly apply (Flutterwave is the merchant of record — we don't touch raw card data)
- All keys are operator-only — no customer can ever see a key

---

## Related

- `.env.example` — full list of secrets with purpose comments
- `docs/SECURITY_PLAN.md` — Layer 1 (Webhook Signatures) and Layer 7 (Monitoring)
- `ADR-005` — Backup Strategy (which secrets get backed up vs excluded)
- ADR-001 (PostgreSQL choice)
- ADR-002 (MiniMax M2 API key handling)