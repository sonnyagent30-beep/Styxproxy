# Styxproxy — Acceptance Checklist

**Generated:** 2026-07-23
**Source:** `scenarios/` (11 files, 8715 lines, 90 scenarios)
**Purpose:** Single source of truth for regression testing. Re-run after every major change.

> **Rule:** Every scenario must pass before a release. If a scenario fails, the change is blocked until the regression is fixed or the scenario is explicitly marked as "known issue" with a tracking issue.

---

## How To Run

```bash
# 1. Backend health
curl -fs https://api.styxproxy.com/health | jq .

# 2. Frontend health
curl -fs https://styxproxy.com | head -50

# 3. Full smoke (auth + checkout + IP gen)
bash scripts/smoke.sh production

# 4. Unit + integration tests
cd backend && pytest tests/ -v

# 5. Lint + type-check
cd backend && ruff check . && mypy .
cd frontend && npm run lint && npm run type-check
```

**Pass criteria:** 100% of `[OK]` items below. Any `[FAIL]` blocks release.

---

## Section 1 — Public Anonymous Checkout (Website)

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 1.1 | Anonymous order (no login) | Customer selects product → pays → receives IP within 2 min, no account required | scenarios/2026-06-26-first-time-order.md |
| 1.2 | Payment failure | Flutterwave `failed` webhook → customer sees "payment failed" → no IP issued | scenarios/2026-06-27-scenarios-42-to-90.md (S36) |
| 1.3 | Wrong amount paid | Manual admin review triggered, customer notified | scenarios/2026-06-27-scenarios-42-to-90.md (S35) |
| 1.4 | Payment link regeneration | Customer can request new link after expiration | scenarios/2026-06-27-scenarios-42-to-90.md (S34) |
| 1.5 | Multi-product cart | Order screen supports product + country + qty combos | scenarios/2026-06-27-scenarios-16-to-40.md (S22) |

---

## Section 2 — Channels (WhatsApp / Telegram)

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 2.1 | WhatsApp greeting | `Hi` → price list + ordering reply | scenarios/2026-06-27-complete-scenario-walkthrough.md (S1) |
| 2.2 | Telegram greeting | Identical reply to WhatsApp | scenarios/2026-06-27-complete-scenario-walkthrough.md (S1) |
| 2.3 | Rate limit | 6th message in 60s → rate-limit reply | scenarios/2026-06-27-scenarios-42-to-90.md |
| 2.4 | Idempotency | Duplicate webhook → single DB write | scenarios/2026-06-27-scenarios-42-to-90.md |
| 2.5 | Abusive message | Flagged + admin notified | scenarios/2026-06-27-scenarios-16-to-40.md (S28) |
| 2.6 | Customer query out of scope | Falls back to LLM answer or admin handoff | scenarios/2026-06-27-scenarios-16-to-40.md |

---

## Section 3 — Free Trial

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 3.1 | First-time trial | Phone not seen → 30-min trial credentials issued | scenarios/2026-06-26-free-trial.md |
| 3.2 | Repeat trial | Same phone → "trial already used" reply | scenarios/2026-06-26-free-trial.md |
| 3.3 | Trial IP dead | Manual re-gen possible | scenarios/2026-06-27-scenarios-16-to-40.md |

---

## Section 4 — Order Lifecycle

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 4.1 | Order status check | Paid → "issuing IP" → "delivered" via simple status command | scenarios/2026-06-27-scenarios-16-to-40.md (S17) |
| 4.2 | Renewal request | Customer requests renewal → new payment link | scenarios/2026-06-27-scenarios-16-to-40.md (S18) |
| 4.3 | Top-up GB (residential/mobile) | Customer adds GB → balance updated | scenarios/2026-06-27-scenarios-16-to-40.md (S19) |
| 4.4 | Dead IP after payment | System auto-retries up to 4 times | scenarios/2026-06-27-complete-scenario-walkthrough.md (S1B) |
| 4.5 | All 4 IP attempts fail | Auto-refund issued | scenarios/2026-06-27-complete-scenario-walkthrough.md (S1C) |

---

## Section 5 — Provider Failures

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 5.1 | Provider down pre-payment | Customer sees "temporarily unavailable" | scenarios/2026-06-26-provider-down-recovery.md |
| 5.2 | Provider down mid-fulfillment | Auto-retry + admin alert | scenarios/2026-06-26-provider-down-recovery.md |
| 5.3 | Provider returns dead IP | Auto-replace + customer notified | scenarios/2026-06-26-provider-down-recovery.md |

---

## Section 6 — Customer Account Recovery

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 6.1 | Forgot PIN (WhatsApp) | 6-digit reset link via WhatsApp | scenarios/2026-06-26-forgot-pin-recovery.md |
| 6.2 | New number recovery | Match by old phone hash → transfer PIN | scenarios/2026-06-26-new-number-recovery.md |
| 6.3 | Old customer returns (no PIN) | Onboarding flow to set PIN | scenarios/2026-06-27-scenarios-16-to-40.md (S33) |
| 6.4 | Old customer returns (with PIN) | PIN auth → resumes | scenarios/2026-06-27-scenarios-42-to-90.md (S41) |

---

## Section 7 — Admin Operations

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 7.1 | Admin login (email + TOTP) | Email + password + TOTP → admin dashboard | scenarios/2026-06-27-admin-operations.md |
| 7.2 | Refund approval | Admin approves → customer notified via email | scenarios/2026-06-27-admin-operations.md |
| 7.3 | Refund auto-issued | System auto-refunds on 4th IP failure | scenarios/2026-06-27-complete-scenario-walkthrough.md (S1C) |
| 7.4 | Manual IP reissue | Admin re-generates IP for customer | scenarios/2026-06-27-admin-operations.md |
| 7.5 | Ban claim | Customer reports banned IP → admin reviews → replaces | scenarios/2026-06-27-complete-scenario-walkthrough.md (S6) |
| 7.6 | Daily summary | 23:55 cron → admin gets totals | scenarios/2026-06-27-complete-scenario-walkthrough.md (S9) |
| 7.7 | Data alert escalation | Provider usage > 80% → admin alert | scenarios/2026-06-27-complete-scenario-walkthrough.md (S8) |
| 7.8 | Error alert | Workflow failure → admin notified within 5 min | scenarios/2026-06-27-complete-scenario-walkthrough.md (S10) |

---

## Section 8 — Pricing & Product

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 8.1 | Price list accuracy | All 4 product types (ISP/DC/RES/MOB) match current pricing | scenarios/2026-06-27-complete-scenario-walkthrough.md (S1) |
| 8.2 | ISP dual-tier pricing | Tier 1 countries (UK/US/DE/FR/CA) ≤ Tier 2 (JP/AU/BR/SG) | scenarios/2026-06-27-complete-scenario-walkthrough.md (S1) |
| 8.3 | Bulk pricing inquiry | Admin gets notified, standard response | scenarios/2026-06-27-scenarios-16-to-40.md (S24) |
| 8.4 | Business invoice request | Customer email → invoice generated + sent | scenarios/2026-06-27-scenarios-16-to-40.md (S25) |

---

## Section 9 — Referral

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 9.1 | Referral code applied | New customer uses code → referrer gets credit | scenarios/2026-06-27-complete-scenario-walkthrough.md (S7) |
| 9.2 | Self-referral blocked | Same phone hash → rejected | scenarios/2026-06-27-complete-scenario-walkthrough.md (S7) |

---

## Section 10 — Compliance & Edge

| # | Scenario | Pass Criteria | Source |
|---|---|---|---|
| 10.1 | NDPR data access request | Customer emails → admin pulls data | scenarios/2026-06-27-scenarios-16-to-40.md (S40) |
| 10.2 | Trial credentials shared publicly | Detected → admin alert | scenarios/2026-06-27-scenarios-16-to-40.md (S27) |
| 10.3 | Mobile 30-day window warning | Day 25 → customer pinged | scenarios/2026-06-27-scenarios-16-to-40.md (S37) |
| 10.4 | Late refund dispute (after 24h) | Admin review per policy | scenarios/2026-06-27-scenarios-16-to-40.md (S26) |
| 10.5 | Custom country request | Admin notified | scenarios/2026-06-27-scenarios-16-to-40.md (S23) |
| 10.6 | Dedicated/private proxy | Routed to admin | scenarios/2026-06-27-scenarios-16-to-40.md (S32) |
| 10.7 | SOCKS5 vs HTTP inquiry | Static reply with comparison | scenarios/2026-06-27-scenarios-16-to-40.md (S31) |
| 10.8 | API access inquiry | Routed to admin | scenarios/2026-06-27-scenarios-16-to-40.md (S30) |
| 10.9 | Price negotiation | Admin notified | scenarios/2026-06-27-scenarios-16-to-40.md (S29) |
| 10.10 | Admin pause during active order | Pause blocks new orders, in-flight continues | scenarios/2026-06-27-scenarios-16-to-40.md (S38) |
| 10.11 | How-to-use / setup guide | Static reply with link | scenarios/2026-06-27-scenarios-16-to-40.md (S20) |
| 10.12 | Slow proxy complaint | Customer gets diagnostic reply + admin alert | scenarios/2026-06-27-scenarios-16-to-40.md (S21) |

---

## Section 11 — Cross-Cutting Non-Functional

| # | Check | Pass Criteria |
|---|---|---|
| 11.1 | Health endpoint | `GET /health` returns 200 with DB + Redis OK |
| 11.2 | Logs structured | All log lines JSON with `phone_hash`, `intent`, `action` |
| 11.3 | Secrets | No secret in logs / responses / frontend bundle |
| 11.4 | Rate limiting | 6 msgs/min per phone, 100 req/min per IP |
| 11.5 | Idempotency | All webhook handlers idempotent |
| 11.6 | PII safety | Phone stored as hash only; logs use hash |
| 11.7 | Audit trail | Admin actions logged with `who/when/what` |
| 11.8 | CORS | Only styxproxy.com + vercel preview domains |
| 11.9 | SSL | HTTPS enforced; HSTS header present |
| 11.10 | Migrations | All schema changes run via Alembic; no manual ALTER |

---

## Section 12 — Superadmin (P0-4)

| # | Scenario | Pass Criteria |
|---|---|---|
| 12.1 | Superadmin login | Email + TOTP → /superadmin dashboard |
| 12.2 | Manage blogs | CRUD posts, view engagement |
| 12.3 | Manage pricing | Edit prices, audit trail |
| 12.4 | Manage admins | Create/disable admin, assign permissions |
| 12.5 | Manage products | CRUD products, enable/disable |
| 12.6 | Global search | Find customer by phone hash, ticket ID, order ID |
| 12.7 | Refund queue | See pending refunds, approve/reject |
| 12.8 | Proxy rotation | Rotate credentials, rotate proxy IP |
| 12.9 | Maintenance toggle | One-click freeze public, page shown |
| 12.10 | Audit log | All superadmin actions logged + exportable |

---

## Section 13 — Charon (AI Assistant)

| # | Scenario | Pass Criteria |
|---|---|---|
| 13.1 | Public page loads Charon | Charon widget visible on styxproxy.com/blog/etc |
| 13.2 | Admin page hides Charon | No Charon on /admin or /superadmin |
| 13.3 | M2 primary | First response from M2 |
| 13.4 | MiniCPM5 fallback | When M2 fails → 1B model responds within 60s |
| 13.5 | RAG from Scenarios | Charon answer cites Scenarios doc |
| 13.6 | Admin knowledge | Admin can add Q/A pair, Charon uses it |
| 13.7 | Escalation | Low-confidence → escalated to admin dashboard |

---

## Coverage Map

```
Scenarios (90 total from 11 files) → Acceptance checklist sections:

Section 1 [5]   ← from first-time-order, multi-product
Section 2 [6]   ← from channel webhooks, abuse
Section 3 [3]   ← from free-trial
Section 4 [5]   ← from order-status, renewal, top-up, dead-IP
Section 5 [3]   ← from provider-down
Section 6 [4]   ← from forgot-pin, new-number, returns
Section 7 [8]   ← from admin-operations
Section 8 [4]   ← from pricing/invoice
Section 9 [2]   ← from referral
Section 10 [12] ← from scenarios-16-to-40, missing-scenarios-a
Section 11 [10] ← cross-cutting (non-functional)
Section 12 [10] ← superadmin (P0-4 features)
Section 13 [7]  ← Charon (P0-5 + P0-6)

Total: 79 acceptance items covering 90 scenarios + 17 cross-cutting/build targets.
```

---

## Maintenance

- **When a new scenario is added:** identify the section, add a row, link the source.
- **When a flow changes:** update the relevant row + run the affected test.
- **When a section hits 0 items:** collapse it.
- **After every release:** re-run the full checklist, attach output to release commit.

**Last regression run:** _never (initial creation)_
**Next scheduled run:** _after every P0 milestone_
