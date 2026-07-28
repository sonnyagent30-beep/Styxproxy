# Styxproxy — Threat Model

**Last Updated:** 2026-07-28
**Owner:** Dannion (operator) + Sonny (analyst)
**Review Cadence:** Quarterly, or after any incident / major architectural change

---

## Why This Document Exists

`SECURITY_PLAN.md` defines **defense layers** (Cloudflare, Nginx, webhooks, etc.). `SECURITY_HARDENING.md` defines **code-level controls** to implement. This document answers a different question: **what are we actually protecting, from whom, at what cost?**

Without a threat model, security work is cargo-cult. We add rate limits because the checklist said so. We add 2FA because the checklist said so. We don't know if we're defending against the right adversary or solving the right problem.

This document is intentionally **short**. Long threat models become unreadable. The point is to enumerate the threats that matter for **Styxproxy at its current stage** — pre-launch, Nigerian market, three channels (web / Telegram / WhatsApp), Stripe/Flutterwave integration, anonymous checkout.

---

## What We're Protecting (Assets)

| # | Asset | Where it lives | Sensitivity |
|---|---|---|---|
| A1 | Customer PII (phone, email — only when given) | Postgres `customers` table, Interserver | Low (most orders are anonymous, only `customer_phone` for chat channels) |
| A2 | Order records (tx_ref, plan, amount, fulfillment status) | Postgres `orders` table | Low |
| A3 | Proxy credentials (SOCKS5 username/password) | Postgres `styxproxy_credentials.styxproxy_password` (Fernet ciphertext) | **HIGH** — leaked creds = free proxy, reputational + financial damage |
| A4 | Proxy provider API keys (Rayobyte, future providers) | `.env` files, VPS | **CRITICAL** — leaked = unlimited proxy theft from upstream, billing exposure |
| A5 | Flutterwave secret key (server-side) | `.env` files, VPS | **CRITICAL** — leaked = forged webhooks = free product |
| A6 | Flutterwave webhook HMAC secret | `.env` files, VPS | **CRITICAL** — leaked = forge "payment received" events |
| A7 | Admin TOTP secret | Postgres `admin_auth.totp_secret` | **CRITICAL** — leaked = MFA bypass for admin panel |
| A8 | Admin JWT secret (`JWT_SECRET`) | `.env` files, VPS | **CRITICAL** — leaked = forge admin tokens, take over admin panel |
| A9 | Admin invite codes | Postgres `admin_invites` | Medium — short-lived, but grants initial access to new admin |
| A10 | Customer chat history (Telegram/WhatsApp) | External (Telegram/WhatsApp servers) + log snippets in our DB | Low |
| A11 | LLM API keys (charon + provider-specific) | `.env` files, VPS | High — leaked = billable cost abuse, brand damage if abused |
| A12 | Database (Postgres) — full read access | Interserver host-native | **CRITICAL** — leaked creds = full data + customer list + ability to issue admin tokens |
| A13 | Source code | GitHub (public repo) | Low (intentionally public) but trade secrets in comments/code paths must be flagged |
| A14 | Backup archives | B2 (when configured) | **CRITICAL** — full DB dump + possibly plaintext credentials if not encrypted at rest |
| A15 | Infrastructure access (SSH keys) | `/root/.ssh/` on VPS | **CRITICAL** — leaked = full VPS takeover, ability to pivot to DB / all `.env` files |
| A16 | Cloudflare account + DNS | Cloudflare dashboard | High — taken over DNS = MITM all traffic, redirect to phishing |
| A17 | Domain registration (styxproxy.com) | Registrar | High — transferred = total ownership loss |

---

## Who We're Protecting Against (Threat Actors)

| # | Actor | Motivation | Capability | Likelihood |
|---|---|---|---|---|
| T1 | Opportunistic scanners (mass `/wp-admin`, `/.git`, etc.) | Find exposed secrets / known CVEs | Automated, no targeting | **Daily** |
| T2 | Credential-stuffing attacker (against `/api/auth/login/email`) | Account takeover | Distributed botnets, leaked cred lists | **High** (we're online + accepting payments) |
| T3 | Payment-fraud attacker (forges Flutterwave webhook) | Free proxy / free product | Knows payment flow, can craft payloads | Medium (lowered if HMAC verified correctly) |
| T4 | Competitor / disgruntled ex-employee | Sabotage, data theft | Has inside knowledge of architecture | Low now, Medium if team grows |
| T5 | Customer trying to abuse free tier / trial | Get more than entitled | Phone numbers, basic scripting | Medium (Nigerian market is price-sensitive) |
| T6 | Customer trying to commit payment fraud (chargeback after delivery) | Get proxy for free | Legitimate customer, then disputes | Low now (no real customers), Medium post-launch |
| T7 | Supply-chain attack (compromised npm/PyPI package) | Backdoor deployed code | Sophisticated, infrequent | Low but high-impact |
| T8 | Nation-state / law enforcement with subpoena | Compelled disclosure | Legal process | **UNKNOWN — Nigerian context** |
| T9 | Random third party who finds an exposed secret | Varies (often curious, sometimes malicious) | Depends on how secret was leaked | Medium (humans are the weakest link) |
| T10 | Insider (Dannion or future team member) | Financial gain / convenience | Full system access | Very low now, scales with team size |

---

## Threat × Asset × Mitigation Matrix (the actual model)

Format: **T# × A#** = threat × asset = what could happen. Mitigation column references existing docs.

### T1 (Scanners) × Everything

- **What:** Mass scans look for `/.git/config`, `/wp-admin`, `/phpmyadmin`, etc. Probe for exposed dev ports (`.env` files served by misconfigured nginx, etc.)
- **Mitigation:** Cloudflare in front of all public endpoints (already done). Nginx `server_tokens off` (verify). No `.env` files in web root. CSP headers via `next.config.ts` (see SECURITY_HARDENING §3). Rotate any keys that have ever been pasted in chat / git history (see gitleaks scan task).

### T2 (Credential stuffing) × A12 (DB) + A8 (JWT_SECRET)

- **What:** Attacker brute-forces admin login → bypasses auth → full DB access.
- **Mitigation:**
  - BCrypt cost ≥ 12 for password hashes (verify in `app/auth.py`)
  - TOTP required for all admin logins (per SECURITY_HARDENING §6)
  - Rate limit `/api/auth/login/*` per IP + per email — **P0 (not yet implemented per Sprint 5)**
  - CAPTCHA after N failed attempts (future, P3)
  - Monitor failed login attempts → alert if spike (Sprint 7 telemetry)
- **Residual risk:** Zero-day in FastAPI auth path, or admin uses weak password

### T3 (Forged webhook) × A5, A6 (Flutterwave keys)

- **What:** Attacker posts to `/api/webhooks/flutterwave` with crafted `tx_ref` → backend thinks payment succeeded → generates free credential.
- **Mitigation:**
  - HMAC signature verification on every webhook (SECURITY_HARDENING §1.1)
  - **Replay window: reject webhooks >5min old via timestamp check** — added Jul 24 (97ed85e)
  - Idempotency table (`processed_webhooks`) — checked before fulfillment
  - **BUG IN PRODUCTION (Sprint 2): `mark_webhook_processed` runs BEFORE order lookup** — fix pending Flutterwave key from Dannion to test
- **Residual risk:** If `FLUTTERWARE_WEBHOOK_HASH` leaks, attacker can sign forged payloads. Mitigated by rotation policy (SECURITY_RUNBOOK §1, 30-day cadence).

### T5 (Trial / free tier abuse) × A1, A2 (customer data)

- **What:** Same person claims many free trials using different phone numbers.
- **Mitigation:**
  - Phone uniqueness on `free_trials` (Sprint 1 add-on, queued)
  - Per-IP rate limit 3/hour (Sprint 9)
  - Device fingerprinting (Sprint 9)
- **Residual risk:** Sophisticated attacker rotates phone + IP + device. Acceptable cost.

### T3 × A4 (Provider keys) — the new Rayobyte threat

- **What:** When Rayobyte integration lands, an attacker with the provider API key can issue proxy requests billed to us.
- **Mitigation:**
  - Provider keys live only in `.env` (not in code, not in DB)
  - Rotate on staff change (SECURITY_RUNBOOK §1)
  - **TODO (Sprint 5):** Add provider usage rate-limits + anomaly detection (if a single key suddenly issues 10x requests, alert)
- **Residual risk:** If `.env` file leaks, attacker has access until rotation. Mitigated by short rotation cycle + monitoring for unusual activity.

### T4 (Disgruntled insider) × A12, A8, A14

- **What:** Ex-employee uses retained SSH key or DB credentials to extract data.
- **Mitigation:**
  - **Disable SSH keys immediately on team changes** (audit `/root/.ssh/authorized_keys` on every personnel change)
  - **Rotate ALL `.env` secrets** on team changes (SECURITY_RUNBOOK §1)
  - Audit log for admin actions → detect unusual access patterns
  - Postgres role demotion (Sprint 8+): `styxproxy` app user should NOT be superuser — only `styxproxy_migrate` for Alembic
- **Residual risk:** If the insider had opportunity to clone the DB before leaving, rotation doesn't help. Mitigated by quarterly access reviews + alerting on first login from new IP.

### T6 (Chargeback fraud) × A2 (orders) + revenue

- **What:** Customer pays → gets proxy → disputes charge with bank → Flutterwave claws back the money → customer keeps proxy.
- **Mitigation:**
  - Flutterwave's own fraud detection catches most of this
  - Track chargeback rate per customer → flag + ban repeat offenders
  - Short-duration / data-capped plans limit exposure (can't dispute after 30 days of usage if the proxy already burned bandwidth)
  - Receipts + terms-of-service that explicitly forbid chargeback-after-usage
- **Residual risk:** Chargebacks before provider reports usage. Acceptable cost until volume justifies dedicated fraud team.

### T7 (Supply-chain) × A13 (source code)

- **What:** Malicious package update introduces backdoor in our deployed code.
- **Mitigation:**
  - **Pin every dep to exact version, no `^` or `~`** (Sprint 4 — partially done)
  - **Dependabot.yml for npm + pip** (Sprint 4, queued)
  - **gitleaks scan in CI** (Sprint 1.4, in progress)
  - **Snyk or similar vulnerability scanner** (Sprint 1 add-on, queued)
  - Manual review of major dep upgrades before merge
- **Residual risk:** Compromised maintainer account on a dep we use. Limited blast radius because we pin versions.

### T8 (Law enforcement / legal) × A1, A2, A10

- **What:** Nigerian or other jurisdiction serves legal process requesting customer data.
- **Mitigation:**
  - We collect minimal data by design (anonymous web orders = no PII to give up)
  - Phone numbers tied to chat channels — preserved for support continuity but documented as "we have this for chat support, not for sale"
  - Document retention policy (Sprint 7 add-on) — auto-archive or delete >1yr old data
  - Legal counsel identified in advance (not yet — Sprint 25 priority)
- **Residual risk:** Legal process for chat channels (we have phone + message content). Acceptable cost of doing chat business; documented in ToS.

### T9 (Random third party) × Everything via secret leak

- **What:** Someone finds a leaked secret (committed to git, pasted in Slack, left in backup) and uses/abuses it.
- **Mitigation:**
  - **gitleaks scan against git log -p** (Sprint 1.3, in progress) — find any existing leaks and rotate
  - **gitleaks in CI** (Sprint 1.4, in progress) — prevent future leaks
  - All secrets stored in `.env` perm 600 only, never in code or DB except where encrypted at rest
  - Backups encrypted before upload to B2 (Sprint 1.1, in progress)
- **Residual risk:** If a leak is found in chat history (Telegram, WhatsApp), we can't undo the leak — only mitigate downstream. Mitigated by assuming any chat-shared secret is compromised and rotating.

### T10 (Insider, future) × Everything

- **What:** Same as T4 but more likely with a larger team.
- **Mitigation:** Same as T4 + principle of least privilege (superadmin only for Dannion; admin role for support staff with audit logging).
- **Residual risk:** Single-person operation has implicit "trust one person" risk. Mitigated by audit logs + quarterly review.

---

## What We Are NOT Protecting Against (Out of Scope)

Calling these out so we don't accidentally claim coverage:

- **DDoS at the network level** — Cloudflare absorbs this up to plan limits. Beyond free plan = money cost.
- **Zero-day in FastAPI / SQLAlchemy / cryptography library** — patches applied promptly, but a 0-day always has a window.
- **Compromised Cloudflare account** — single point of failure for DNS. Mitigated by registrar-level domain lock + 2FA on CF.
- **Physical seizure of VPS hardware** — encrypted volumes? (No — TDE not configured.) Out of scope until we have physical-threat motivation.
- **Quantum computing breaking RSA/ECC** — all current crypto broken. Out of scope, irrelevant for our 30-day threat horizon.

---

## Prioritized Action List (Threat-Driven)

This is what the Sprint Backlog actually traces back to. Listed in order of risk reduction per hour of work:

| Priority | Action | Threat Mitigated | Sprint |
|---|---|---|---|
| 🔴 P0 | gitleaks scan against git history + rotate any leaked secrets | T9 | 1.3 |
| 🔴 P0 | gitleaks in CI for future commits | T9 | 1.4 |
| 🔴 P0 | Backups to B2 (encrypted at rest) | T9 (data loss + leak) | 1.1 |
| 🔴 P0 | Rate limit `/api/auth/login/*` + webhook idempotency reorder + auto-refund | T2, T3 | 2 (blocked on Flutterwave key) |
| 🟠 P1 | Dependabot + version-pinned deps | T7 | 4 |
| 🟠 P1 | HTTPS / HSTS / TLS hardening | T1, T9 | 5 |
| 🟠 P1 | Audit log for admin mutations + anomaly alerts | T4, T10 | 7 |
| 🟠 P1 | Demote `styxproxy` Postgres role from superuser | T4, T10 | 8+ |
| 🟢 P2 | Annual pen-test | T1-T9 all | future |
| 🟢 P3 | Bug bounty program | T1-T9 all | future |

---

## How To Use This Doc

1. **When proposing a new feature**, ask: does this introduce a new asset? A new threat actor? Update the matrices above.
2. **When a sprint item is "complete,"** check the relevant row above and confirm the mitigation actually holds (not just that the code compiles).
3. **Quarterly review:** re-read this doc. Have the threat actors changed? Have we added new assets? Are any mitigations now obsolete?
4. **After any incident:** add a row to "Incidents & Lessons" at the bottom of this doc.

---

## Incidents & Lessons

*(Empty — first run of this doc. Future incidents will be logged here with: date, threat realized, response time, mitigation added.)*

---

**See also:**
- [`SECURITY_PLAN.md`](SECURITY_PLAN.md) — the 7 defense layers
- [`SECURITY_HARDENING.md`](SECURITY_HARDENING.md) — code-level security checklist
- [`SECURITY_RUNBOOK.md`](SECURITY_RUNBOOK.md) — operational procedures + secret rotation
- [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md) — what to do when something breaks