# Styxproxy Platform — Full Platform Specification
**Version:** 1.2 | **Date:** 2026-07-22 | **Status:** Active Build · Honest Audit Pass

**Supersedes:** v1.0 (2026-06-26), v1.1 (2026-07-21)

**Change log:**
- v1.2 — Status flags corrected against actual codebase (Jul 22 audit). P0-1, P0-2, P0-3 confirmed DONE. P0-4 Superadmin backend DONE, frontend STUBBED. New "Recommendations Beyond Spec" section added. Goals 6–11 + A–D,G integrated.
- v1.1 — Resend email marked done, Phase 1 Blog marked done.
- v1.0 — Initial spec.

---

## Table of Contents
1. Prioritized Goals (P0 / P1 / P2)
2. Honest Audit — What's Actually Built (Jul 22 2026)
3. Scenarios → User Stories → Acceptance Criteria → Tests
4. Technical Architecture Notes
5. Test Plan
6. Rollout Plan
7. Risks + Mitigations
8. Additional Recommendations (A–G)
9. Recommendations Beyond Spec (Dannion's ask)
10. Superadmin Invite

---

## 1. PRIORITIZED GOALS

### P0 — Must Have (Live / Next Sprint)

| # | Workstream | Status (Jul 22 audit) | Notes |
|---|---|---|---|
| P0-1 | **Admin Auth Cleanup** | ✅ DONE | email + TOTP, no nav on setup/login, audit log writes |
| P0-2 | **Phase 1 Blog** | ✅ DONE (CMS + DB) · ⚠️ SEO GAPS | Missing og:image/Twitter card, masonry, Lighthouse baseline |
| P0-3 | **Resend Email Setup** | ✅ DONE | admin invites + customer order email verified |
| P0-4 | **Superadmin Dashboard** | 🟡 PARTIAL | Backend `/api/v1/superadmin/*` complete. Frontend pages are STUBS |
| P0-5 | **Charon Reliability** | 🔴 BROKEN | LiteLLM proxy down right now (`:4000` → 000). Spec says auto-restart + health |
| P0-6 | **Blog SEO Completion** | 🔴 NEW | Add og:image, Twitter cards, masonry, remove DEMO_POSTS fallback |

### P1 — Should Have (This Sprint + Next)

| # | Workstream | Status | Why |
|---|---|---|---|
| P1-1 | **Scenarios → RAG for Charon** | ⬜ TODO | Deterministic answers for canonical flows (order, recovery, outage) |
| P1-2 | **Charon Escalations Queue** | ⬜ TODO | Required to prevent user abandonment when LLM is down or low-confidence |
| P1-3 | **Maintenance Mode + Scheduling** | ⬜ TODO | Zero-downtime ops for backend deploys |
| P1-4 | **Frontend/Backend Alignment + OpenAPI** | 🟡 PARTIAL | Backend Pydantic schemas, but no generated Zod on frontend, no OpenAPI export |
| P1-5 | **Input Validation Hardening (client+server)** | 🟡 PARTIAL | Server ✅, client needs Zod mirror, file upload scan, CSRF on forms |
| P1-6 | **Cumulative Testing (Postman + CI)** | 🟡 PARTIAL | Backend pytest ✅, Postman collection TODO, Playwright TODO, load TODO |

### P2 — Post-Launch (After First Real Customers)

| # | Workstream | Why |
|---|---|---|
| P2-1 | **Security & Compliance (RBAC, alerts, session mgmt)** | Enterprise readiness, two-person approval for refunds |
| P2-2 | **Media Library + Alt-text + Review Workflow** | Content quality at scale |
| P2-3 | **Search (Public + Admin with export)** | UX improvement |
| P2-4 | **Observability (status panel, feature flags, alerting)** | Operational excellence |
| P2-5 | **Localization & Accessibility foundation** | Future-proofing |
| P2-6 | **Public Blog UX upgrade (masonry, featured, collections)** | Instagram-feel |

---

## 2. HONEST AUDIT — WHAT'S ACTUALLY BUILT (Jul 22 2026)

This is a snapshot against the actual filesystem. Every claim is verifiable.

### Goal 1 — Public Blog (Instagram-like + SEO)
**Verdict: PARTIAL**

**Built:**
- ✅ Routes: `/blog`, `/blog/[slug]`, `/blog/category/[slug]`, `/blog/tag/[tag]`, `/blog/author/[name]`
- ✅ `BlogFeed` component with infinite scroll + tag filter
- ✅ `schema.org` JSON-LD on post detail page (Article)
- ✅ `sitemap.ts` + `robots.ts` (root + admin-noindex)
- ✅ `next/image` with `sizes` for responsive images

**Wrong / Weak — must fix:**
1. Feed is a card grid, **not Instagram-style masonry** → add `column-count` masonry pattern
2. **No `og:image` meta** on blog post detail page → `generateMetadata` returns no images
3. **No Twitter card** meta
4. **`DEMO_POSTS` silent fallback** in `blog/page.tsx` → if API fails, you serve stale demo posts. Hides outages.
5. **No blur placeholders** → add `placeholder="blur"` + `blurDataURL`
6. **No Breadcrumb schema** → add `BreadcrumbList` JSON-LD
7. **No featured/pinned posts**
8. **No collections**
9. **No Lighthouse baseline stored** — acceptance criteria not actually measured

### Goal 2 — Charon on VPS + Backend Connectivity
**Verdict: BACKEND DONE, INFRA BROKEN**

**Built:**
- ✅ `app/routers/charon.py` (public + admin endpoints)
- ✅ `app/services/charon/` agent stack (knowledge, weights, stats, escalate)
- ✅ Ollama MiniCPM5 1B @ `localhost:11434` → status 200 ✅
- ✅ `ChatWidget` has `pathname.startsWith('/admin')` guard → confirmed in code
- ✅ Rate limiter (`app.limiter`) wired

**Wrong / Weak:**
1. **LiteLLM proxy is DOWN right now** (`curl :4000` → 000). Spec violated.
2. **No public `/api/v1/charon/health` that surfaces LiteLLM status** — `/health` exists but only self-checks
3. **No fallback UI** in ChatWidget when LLM is down → user sees broken spinner
4. **No Charon tests** in `backend/tests/` (13 test files, zero for Charon)
5. **`/api/v1/charon/_internal/stats` lives under public `/charon/` prefix** — firewall-bleed risk; move under `/admin/`

### Goal 3 — Admin Auth + UI Cleanup
**Verdict: DONE**

- ✅ Email login (no phone)
- ✅ TOTP enrollment + verification
- ✅ Auth layout (`(auth)/layout.tsx`) has NO sidebar / header
- ✅ Combined order + credentials email

**Minor improvements:**
1. **No TOTP recovery / backup codes** (spec said "recommended") → add
2. **No re-authentication for sensitive superadmin actions** → add `require_recent_auth(min_age_seconds=300)`
3. **No audit log on auth events** (login, failed login, TOTP setup) → already partially logged, verify coverage

### Goal 4 — Superadmin Dashboard
**Verdict: BACKEND DONE, FRONTEND STUBBED**

**Backend (`app/routers/superadmin.py`):**
- ✅ `/audit-log`, `/admins` (GET, POST, PATCH role, DELETE, lock/unlock)
- ✅ `/providers/costs`, `/settings` (GET, PATCH)
- ✅ `/search` (global search), `/metrics/overview`
- ✅ `/charon/stats`, `/charon/reset`

**Frontend (`frontend/src/app/admin/(dashboard)/*`):**
- 🟡 Pages exist (orders, customers, blog, charon, audit-log, admins, search, settings, escalations, credentials, providers, plans, features, contact-submissions, support, team)
- ❌ `grep "TODO|placeholder|stub"` returns hits in 11 pages → mostly empty
- ❌ No real data fetching, no media library UI, no global search UI, no metrics chart

### Goal 5 — Validation + Security
**Verdict: PARTIAL**

- ✅ Pydantic schemas on backend
- ✅ SQLAlchemy parameterized queries
- ✅ `SanitizedHtml` component for blog content (XSS prevent)

**Weak:**
1. No shared validation rules (Zod mirror on frontend)
2. No file upload type/size validation
3. No CSRF protection on admin form posts (Server Actions need it; standard POST forms rely on auth header)
4. No rate-limit on `/api/v1/admin/login`
5. No ZAP / OWASP scanner run

### Goal 6 — Scenarios as Spec + RAG for Charon
**Verdict: SCENARIOS EXIST, RAG NOT BUILT**

- ✅ 11 scenario files in `/scenarios/` (`2026-06-26-*` through `2026-06-28-missing-scenarios-a.md`)
- ❌ No scenario parser
- ❌ No `charon_knowledge_chunks` table populated
- ❌ No citation in Charon responses
- ❌ No admin knowledge tool UI

### Goal 7 — Charon Escalations in Dashboard
**Verdict: BACKEND TABLE EXISTS, UI STUB**

- ✅ `charon_escalations` table exists (empty)
- 🟡 `/admin/(dashboard)/escalations/page.tsx` exists, stub
- ❌ No SLA tracking
- ❌ No "convert escalation → ticket" flow

### Goal 8 — Maintenance Mode + Scheduling
**Verdict: NOT BUILT**

- ✅ `system_settings` table exists
- ❌ No `/admin/features` toggle wired to middleware
- ❌ No animated maintenance page
- ❌ No scheduling
- ❌ Maintenance mode bypass for `/admin/*` not implemented

### Goal 9 — Resend Email Setup
**Verdict: DONE** — admin invites + customer order email verified in prod.

### Goal 10 — Frontend/Backend Alignment + DB
**Verdict: PARTIAL**

- ✅ Pydantic + SQLAlchemy
- ✅ Alembic migrations
- ❌ No OpenAPI export artifact
- ❌ No Zod schemas generated from Pydantic
- ❌ No public-content caching (Redis exists but not used for blog)
- ❌ No load test run

### Goal 11 — Full Platform Testing
**Verdict: PARTIAL**

- ✅ 13 backend test files (auth, routers, schemas, services)
- ❌ 0 frontend tests
- ❌ No Postman/Newman collection
- ❌ No Playwright E2E
- ❌ No k6 load tests

---

## 3. SCENARIOS → USER STORIES → ACCEPTANCE CRITERIA → TESTS

The 11 scenario files in `/scenarios/` are the canonical behavior spec. They are converted into user stories, acceptance criteria, and test cases below.

### WORKSTREAM 6: Scenarios → RAG → Charon Knowledge Base

**Context:** 11 scenario files in `/root/styxproxy/scenarios/`. Each captures canonical customer/admin flows as turn-by-turn replays with system behavior + replies.

**Sample scenarios:**
- First-time order (greeting → menu → order → payment → delivery)
- Provider outage (offer alternatives, wait queue, notify on recovery)
- Forgot PIN / new phone recovery
- Free trial flow
- Admin operations (15+ commands, risk levels: low/medium/high/critical)
- Off-topic deflection
- Escalation and resolution

#### Epic: Charon Knowledge Management
```
EPIC: As Charon, I want accurate, source-cited answers so users trust me.
```

**Story 6.1: Scenario Ingestion**
```
As: System (automated)
I want: Scenario files parsed and chunked into retrievable knowledge units
So that: Charon can cite sources in answers
Acceptance Criteria:
- [ ] Each scenario file parsed (title, status, rules, replies, system behavior)
- [ ] Chunks tagged by scenario ID, category (order/recovery/admin/etc), channel
- [ ] Chunk stored with source URL/path metadata
- [ ] Admin can view all chunks in a knowledge base UI
- [ ] Re-running ingestion is idempotent (no dupes)
Tests: pytest unit on parser; integration on ingestion script
```

**Story 6.2: Knowledge Base Admin Tool**
```
As: Admin
I want: A UI to view, add, edit, and retire knowledge chunks
So that: I can keep Charon's knowledge current without engineering
Acceptance Criteria:
- [ ] /admin/charon/knowledge: list all chunks, filter by category/tag/scenario
- [ ] Create chunk: text content, category, tags, source reference
- [ ] Edit chunk: versioning preserved (old version archived)
- [ ] Retire chunk: soft-delete (mark inactive, keep history)
- [ ] 2-step approval: draft → pending_approval → live (or rejected)
- [ ] Version history visible: who changed what, when, why
Tests: API + UI E2E
```

**Story 6.3: Charon Answers Cite Sources**
```
As: User
I want: Every Charon answer to show where the information came from
So that: I can verify and trust the response
Acceptance Criteria:
- [ ] Charon response includes citation: "Source: Scenarios 2026-06-26, Scenario 3"
- [ ] Unanswerable queries return: "I don't have information on that. Contact support."
- [ ] No hallucinated facts — Charon never makes up proxy pricing, policies, or procedures
Tests: contract test comparing LLM output to expected citations
```

**Story 6.4: Learning Loop (Safe)**
```
As: System
I want: User feedback stored for review, not auto-applied
So that: Charon improves without receiving garbage or manipulated training data
Acceptance Criteria:
- [ ] Thumbs up/down on Charon replies logged to charon_feedback table
- [ ] Flagged responses (thumbs down) queued for admin review
- [ ] Admin can mark feedback as "helpful update" → creates a new knowledge chunk (draft, needs approval)
- [ ] No feedback auto-applies to knowledge base — explicit admin approval required
- [ ] Learning loop audit log: what was flagged, reviewed, accepted/rejected
Tests: contract tests + audit-log inspection
```

**Story 6.5: Scenario → Test Case Conversion**
```
As: QA / Developer
I want: Each scenario file automatically converted into testable specs
So that: I can verify the system behaves exactly as the scenario describes
Acceptance Criteria:
- [ ] Parser reads scenario markdown → extracts: trigger, system behavior, expected reply
- [ ] Output: JSON test spec { scenario_id, input, expected_output, assertions }
- [ ] Test specs run against actual system via Postman or Playwright
- [ ] Each scenario → at least 3 test cases (happy path, error path, edge case)
Tests: pytest on parser, generated specs land in /tests/scenarios/*.json
```

### WORKSTREAM 7: Charon Escalations in Dashboard

**Context:** When Charon's confidence < threshold, the user explicitly asks for a human, or feedback is negative, an escalation is created.

#### Epic: Escalation Workflow
```
EPIC: As support staff, I want to see and resolve escalations so customers never get stuck.
```

**Story 7.1: Auto-Escalation Triggers**
```
As: System
I want: Auto-create an escalation when Charon can't help
So that: Customers get human support without re-explaining themselves
Acceptance Criteria:
- [ ] Confidence < 0.5 → auto-escalate
- [ ] User types "human" / "agent" / "support" → auto-escalate
- [ ] User clicks thumbs-down on reply → flag for review
- [ ] User clicks "Talk to a person" button in widget → escalate
- [ ] Escalation record contains: conversation transcript, last charon reply, user context (page, device)
Tests: contract test feeding each trigger, asserting escalation created
```

**Story 7.2: Escalation Queue UI**
```
As: Support staff
I want: A queue at /admin/escalations showing all open escalations
So that: I can triage and resolve them
Acceptance Criteria:
- [ ] List shows: status (new/in_progress/resolved), customer, last message, age, confidence score
- [ ] Sort/filter: by status, age, confidence, channel
- [ ] Click row → opens conversation view with full transcript
- [ ] Mark as in_progress (assigned to me)
- [ ] Resolve: reply to customer + close escalation
- [ ] SLA timer: escalations > 30min age show "SLA risk" badge
Tests: Playwright E2E: trigger escalation → see in queue → resolve → customer receives reply
```

**Story 7.3: Escalation → Ticket Conversion**
```
As: Support staff
I want: Convert escalations into persistent tickets
So that: complex issues survive across sessions and have audit trail
Acceptance Criteria:
- [ ] "Convert to ticket" button on escalation
- [ ] Ticket has: customer, conversation context, assigned_to, status, priority
- [ ] Ticket replies via Resend email or WhatsApp (per customer channel)
- [ ] Ticket state syncs both ways (status changes reflected in escalation view)
Tests: contract test for ticket creation + email send
```

**Story 7.4: SLA Metrics**
```
As: Admin
I want: Dashboard widget showing escalation volume + resolution time
So that: I know if support is keeping up
Acceptance Criteria:
- [ ] Widget shows: open count, resolved today, avg time-to-first-response, avg time-to-resolution
- [ ] Date range filter (today, 7d, 30d)
- [ ] Break down by channel (chat/email/whatsapp)
Tests: integration test with seeded data
```

### WORKSTREAM 8: Maintenance Mode + Scheduling + Animated Page

#### Epic: Operator Control of Public Site Availability
```
EPIC: As operator, I want to take the public site offline cleanly with a planned ETA so I can deploy without breaking customer experience.
```

**Story 8.1: Maintenance Toggle**
```
As: Admin
I want: A toggle at /admin/features labeled "Maintenance Mode"
So that: I can flip the public site to a maintenance page instantly
Acceptance Criteria:
- [ ] Toggle writes to system_settings (key=maintenance_mode, value=on/off)
- [ ] Public pages check this setting on every request (cached 30s)
- [ ] When on, all public pages render /maintenance
- [ ] /admin/* is NEVER affected by maintenance mode
- [ ] /api/v1/platform/* (product list for order flow) is NEVER affected — order keeps working
- [ ] Toggle logs to audit_log with timestamp + admin email
Tests: integration: toggle on → curl / → maintenance HTML; curl /admin/dashboard → 200
```

**Story 8.2: Maintenance Scheduling**
```
As: Admin
I want: Schedule a maintenance window (start + end time)
So that: I don't have to be awake at the scheduled time
Acceptance Criteria:
- [ ] /admin/maintenance: form for start_at, end_at, message
- [ ] Cron job (every 60s) checks schedules → enables maintenance if start_at <= now < end_at
- [ ] Auto-disable when end_at <= now
- [ ] Schedule conflicts (overlapping windows) rejected
- [ ] All scheduled events logged
Tests: integration with mocked clock; cron integration test
```

**Story 8.3: Animated Maintenance Page**
```
As: Visitor
I want: A clean, branded maintenance page with countdown + clear messaging
So that: I know when to come back and trust that you care
Acceptance Criteria:
- [ ] Styxproxy brand colors + dark mode
- [ ] Animated SVG/illustration (subtle, no flashy autoplay video)
- [ ] Live countdown to end_at
- [ ] Message from admin (e.g. "Upgrading payment systems")
- [ ] Optional contact: Telegram handle, support email
- [ ] No "Leave a message" form (this isn't an escalation channel)
- [ ] WCAG AA contrast + keyboard navigable
Tests: Lighthouse a11y ≥ 90, Playwright snapshot of page when maintenance=on
```

### WORKSTREAM 9: Resend Email Setup ✅ DONE

**Built:**
- ✅ `noreply@styxproxy.com` sender verified (SPF/DKIM/DMARC)
- ✅ Admin invite email (TOTP setup link)
- ✅ Customer order email (combined: IP + credentials + receipt PDF + WhatsApp handoff)
- ✅ TOTP security alerts (new device, password change)
- ✅ Branded HTML templates with dark-mode support

**Verification:**
- Mailtrap test → delivered to inbox (not spam)
- Apple Mail, Gmail web, Outlook desktop renders consistent

### WORKSTREAM 10: Frontend/Backend Alignment + DB Design + Performance

#### Epic: Contract Discipline + Scale-Ready DB
```
EPIC: As developer, I want the frontend and backend to never disagree so I don't waste hours on a stale field.
```

**Story 10.1: OpenAPI as Source of Truth**
```
As: Developer
I want: Backend auto-exports OpenAPI spec on every build
So that: I can generate typed clients and verify alignment
Acceptance Criteria:
- [ ] /openapi.json served at root of API
- [ ] CI fails if /openapi.json changes without explicit approval (drift detector)
- [ ] Frontend types generated from OpenAPI (npm run gen:api-types)
- [ ] Generated types committed to repo (committed, not ignored)
- [ ] Contract test: every API endpoint called by frontend has matching response type
Tests: CI step that diffs OpenAPI against last commit
```

**Story 10.2: Pagination/Filter/Sort Standards**
```
As: Frontend
I want: Every list endpoint to follow the same shape: {items, pagination, total}
So that: I don't write a custom fetcher per endpoint
Acceptance Criteria:
- [ ] All list endpoints return: { items: T[], pagination: { page, limit, total_items, total_pages, has_next, has_prev } }
- [ ] Query params: ?page=1&limit=20&sort=-created_at&filter[status]=active
- [ ] Sort: prefix `-` for descending, comma-separated for multi-field
- [ ] Filter: bracket syntax `filter[field]=value`, repeatable
- [ ] Standard 400 errors: { error: { code, message, field } }
- [ ] Documented in OpenAPI
Tests: contract test on every list endpoint
```

**Story 10.3: DB Index Audit**
```
As: DBA / Backend dev
I want: All hot queries to have indexes verified by EXPLAIN
So that: p95 latency stays under 200ms at 10k rows
Acceptance Criteria:
- [ ] Audit doc: every endpoint with frequency > 100/min → EXPLAIN ANALYZE run
- [ ] Indexes added for: posts(slug), posts(status, published_at DESC), orders(tx_ref), orders(customer_phone_hash), charon_sessions(user_id, created_at DESC), charon_escalations(status, created_at DESC)
- [ ] Migration script applied
- [ ] Re-run EXPLAIN after → confirm index scan
Tests: pytest that asserts < 50ms p95 on seeded 10k-row dataset
```

**Story 10.4: Cache Strategy**
```
As: Backend dev
I want: Redis cache for public content (blog list, post detail, product list)
So that: DB load stays low under traffic spikes
Acceptance Criteria:
- [ ] Redis cache keys: blog:list:page=1, blog:post:{slug}, platform:products
- [ ] TTL: 5 minutes for lists, 10 minutes for detail
- [ ] Invalidation: on POST/PUT/DELETE to those resources
- [ ] Stale-while-revalidate: serve stale on Redis miss + async refresh
- [ ] Cache hit rate metric exposed at /admin/status
Tests: load test (k6) showing DB query reduction
```

**Story 10.5: Backup/Restore**
```
As: Operator
I want: Daily pg_dump + tested restore procedure
So that: I don't lose customer data on accident
Acceptance Criteria:
- [ ] Cron: daily 03:00 UTC pg_dump to /var/backups/styxproxy/
- [ ] Off-host copy: rsync to second VPS or S3
- [ ] 7-day retention for daily, 4-week retention for weekly
- [ ] Restore test: monthly cron restores to a throwaway DB, runs integrity check
- [ ] RPO: 24h, RTO: 1h documented in OPERATIONAL_RUNBOOK.md
Tests: smoke test of restore procedure
```

### WORKSTREAM 11: Full Platform Testing

#### Epic: Regressions Cannot Reach Production
```
EPIC: As platform team, I want every critical flow tested on every PR so regressions stop shipping.
```

**Story 11.1: Postman Collection**
```
As: QA / Developer
I want: A complete Postman collection covering every endpoint
So that: I can manually verify any API surface
Acceptance Criteria:
- [ ] /postman/styxproxy.postman_collection.json
- [ ] Every endpoint has: method, path, auth (admin/superadmin/none), sample body, expected response, tests tab
- [ ] Environment variables: base_url, admin_token, superadmin_token
- [ ] Newman run in CI: `newman run collection.json --environment ci.json`
Tests: collection runs green in CI on every PR
```

**Story 11.2: E2E Critical Journeys (Playwright)**
```
As: Platform team
I want: 7 critical journeys automated end-to-end
Acceptance Criteria:
- [ ] Admin email login + TOTP → dashboard
- [ ] Superadmin creates admin + viewer cannot access /admin/team
- [ ] Maintenance mode toggle → public page shows maintenance → disable → public back
- [ ] Publish blog post (draft → approved → published) → visible on /blog
- [ ] Customer refund flow (admin marks order → customer receives email)
- [ ] Charon chat → low-confidence reply → escalation → admin resolves
- [ ] OpenAPI contract: every endpoint called by frontend returns the documented shape
Tests: Playwright suite in /tests/e2e, runs in CI in < 5 min
```

**Story 11.3: Load Testing (k6)**
```
As: Platform team
I want: Load test on public + Charon endpoints before each release
Acceptance Criteria:
- [ ] k6 script: /tests/load/public.js, /tests/load/charon.js
- [ ] Public: 100 VUs, 5 min, / + /blog + /blog/{slug} + /pricing
- [ ] Charon: 50 VUs, 5 min, /api/v1/charon/reply
- [ ] Thresholds: p95 < 500ms public, p95 < 2000ms Charon, error rate < 1%
- [ ] Result HTML report committed under /tests/load/reports/
Tests: CI job runs k6 weekly + on release tag
```

**Story 11.4: Security Testing in CI**
```
As: Security-conscious dev
I want: Secrets, deps, and inputs scanned on every PR
Acceptance Criteria:
- [ ] TruffleHog: scan git history for committed secrets → fail on any
- [ ] npm audit + pip-audit: 0 high/critical vulnerabilities
- [ ] schemathesis: fuzz test Pydantic schemas with random inputs
- [ ] OWASP ZAP baseline: scan public site for XSS/SQLi/CSRF
Tests: CI runs all four on every PR
```

---

## 4. TECHNICAL ARCHITECTURE NOTES

### 4a. Architecture
```
Public:  styxproxy.com (Vercel/Next.js)
         ├── /blog/*         → DB-backed blog (Next.js + Redis cache)
         ├── /products        → pricing/products page
         ├── /maintenance     → animated maintenance (when toggle on)
         └── ChatWidget       → public-only, mounted in root layout w/ pathname guard

API:     api.styxproxy.com (FastAPI on VPS Docker)
         ├── /api/v1/blog/*     → blog CRUD + public list
         ├── /api/v1/charon/*   → Charon LLM endpoint (public) + /charon/_internal/* moved to /admin/charon/_internal/*
         ├── /api/v1/admin/*    → admin dashboard API
         ├── /api/v1/superadmin/* → superadmin operations
         ├── /api/v1/platform/* → public product/pricing API (NOT affected by maintenance)
         ├── /openapi.json      → OpenAPI spec source of truth
         └── /api/v1/health     → deep health (DB, Redis, LiteLLM, Ollama)

VPS:     84.247.132.12 (Docker stack)
         ├── styxproxy-local-api-1      (FastAPI, port 8000, network_mode=host)
         ├── styxproxy-local-postgres-1 (PostgreSQL, port 5432)
         ├── styxproxy-local-redis-1    (Redis, port 6379)
         ├── styxproxy-local-litellm-1  (LiteLLM proxy, port 4000, network_mode=host)
         └── ollama (MiniCPM5 1B, port 11434)
```

### 4b. Security Architecture
```
Authentication:
- Admin: email + bcrypt password + TOTP (rotates every 30s)
- TOTP recovery codes: 10 single-use, hashed at rest
- Session: JWT (15min access, 7d refresh), stored in httpOnly cookie
- Re-auth: required for sensitive actions (refunds, permission changes, maintenance toggle, admin creation)
- Recent-auth dep: require_recent_auth(min_age_seconds=300) on /api/v1/superadmin/* POST endpoints

Authorization:
- Roles: superadmin | admin | viewer (deny-by-default RBAC)
- Every router endpoint has explicit permission check via require_* dependencies
- Audit log: every write operation (who/what/when/IP/UA)

CSRF:
- Server Actions: built-in Next.js CSRF protection
- Standard form posts to /admin/*: double-submit cookie + Origin header check

Rate limits:
- /api/v1/admin/login: 5 req/min/IP + lockout after 5 failed
- /api/v1/charon/reply: 30 req/min/IP (chat) + 5 req/min unauthenticated burst
- /api/v1/platform/*: 60 req/min/IP

Secrets:
- Backend-only: DB password, Resend API key, JWT secret, TOTP encryption key
- Frontend-safe: Stripe pk_live (domain-scoped), OpenAI keys (BFF pattern)
- Env vars on VPS: starting point, rotate to Doppler/Vault in production

Headers:
- Content-Security-Policy: strict, no unsafe-inline except for Charon widget nonce
- X-Frame-Options: DENY
- Strict-Transport-Security: max-age=63072000; includeSubDomains
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin

Charon Security:
- Widget only on public pages (layout-level guard: !pathname.startsWith('/admin'))
- Output sanitization: strip phone numbers, IPs, emails from LLM responses before sending
- Input sanitization: strip HTML/scripts before LLM
- Citations always shown so user can verify
```

### 4c. Data Model
```sql
-- Existing tables (verified in DB Jul 22)
posts             -- blog posts (with featured flag pending)
categories        -- blog categories
post_categories   -- junction
charon_escalations-- escalation queue
system_settings   -- maintenance mode, feature flags
admin_audit_log   -- audit trail
feature_flags     -- per-feature toggles

-- Tables needed for P1-1, P1-2, P1-3, P1-4 (this sprint)
charon_knowledge_chunks  -- RAG: id, scenario_id, category, content, source_ref, status (draft|pending|approved|live|retired), version, created_by, approved_by, created_at, approved_at
charon_knowledge_versions -- audit trail of edits
charon_feedback           -- user thumbs up/down + review status
charon_sessions           -- chat session history (user_id, page, started_at, ended_at)
maintenance_schedules     -- scheduled windows: starts_at, ends_at, message, status (scheduled|active|completed|cancelled)
media_library             -- uploaded images: id, url, hash, alt_text, tags, uploaded_by
blog_review_state         -- per-post: status (draft|pending|approved|published|retracted), reviewer, review_notes
admin_sessions            -- device/IP tracking for session management
tickets                   -- persistent support tickets (from escalations)
admin_recovery_codes      -- TOTP backup codes, hashed
```

### 4d. Charon RAG Architecture
```
Scenario Files (MD in /scenarios/)
    ↓ [Parser — scenarios/parser.py]
JSON Chunks: { id, category, trigger_patterns, reply_templates, rules, source_ref }
    ↓ [Embedding: MiniCPM5 local or OpenAI text-embedding-3-small]
Vectors stored in: pgvector (production) or SQLite FTS5 (MVP)
    ↓ [Retrieval: similarity search on user query, top-k=3]
Top-k chunks → LLM context window (MiniCPM5 1B or MiniMax M2.5)
    ↓
Charon Response + citations (source_ref echoed to user)
    ↓
Feedback loop: thumbs up/down → admin review → new draft chunk → approval → live
```

### 4e. Observability Stack
```
Metrics:    /metrics endpoint (Prometheus format)
Logs:       structured JSON → Loki or CloudWatch (decided in P2-4)
Traces:     OpenTelemetry spans on /api/* endpoints (P2-4)
Errors:     Sentry (DSN in env)
Uptime:     UptimeRobot → status.styxproxy.com (external check every 60s)
Alerting:   Telegram bot @styxproxy_alerts → critical errors, escalation SLA breach, LiteLLM down > 5min, DB lag > 30s

Internal status panel (/admin/status):
- API uptime % (last 24h, 7d, 30d)
- Charon uptime % (LiteLLM + Ollama health)
- DB latency p50/p95/p99
- Redis ping
- Last backup time + age
- Active feature flags
```

---

## 5. TEST PLAN

| Layer | Tool | Frequency | Coverage Target | Status |
|---|---|---|---|---|
| Unit | pytest | Every PR | All backend models/schemas/services | ✅ 13 files exist |
| Integration | Postman/Newman | Every PR | All 40+ API endpoints | ❌ TODO |
| E2E | Playwright | Every PR | 7 critical user journeys | ❌ TODO |
| Contract | OpenAPI diff | Every PR | Frontend ↔ backend alignment | ❌ TODO |
| Load | k6 | Pre-release + weekly | p95 < 500ms public @ 100 VUs | ❌ TODO |
| Accessibility | axe-core (Playwright) | Every PR | WCAG 2.1 AA compliance | ❌ TODO |
| Security | TruffleHog + npm audit + pip-audit + schemathesis + OWASP ZAP | Every PR | 0 high/critical CVEs, 0 secrets, 0 schema crashes | ❌ TODO |
| Smoke | Health endpoint checks | Every deploy | /health, /api/v1/health, /api/v1/charon/health | 🟡 partial (chat/health is self-only) |
| Visual | Playwright screenshot diff | Every PR | Admin + blog pages unchanged | ❌ TODO |

---

## 6. ROLLOUT PLAN

### Sprint 1 (Jul 23–29): P0 Completion
- [ ] **P0-4** Build Superadmin frontend (audit-log, admins CRUD, customers, search, metrics, blog mgmt, charon mgmt)
- [ ] **P0-5** Bring LiteLLM back up + add watchdog cron + public health endpoint that includes LiteLLM status
- [ ] **P0-6** Blog SEO: og:image, Twitter card, masonry, Breadcrumb schema, remove DEMO_POSTS fallback, Lighthouse baseline

### Sprint 2 (Jul 30–Aug 5): P1 Foundation
- [ ] **P1-1** Scenarios → RAG parser, knowledge chunk DB table, admin knowledge tool
- [ ] **P1-2** Charon escalation queue + UI + ticket conversion
- [ ] **P1-3** Maintenance mode toggle + scheduling + animated page
- [ ] **P1-4** OpenAPI export + Zod generation + contract test in CI
- [ ] **P1-5** Zod mirror on frontend, file upload scan, CSRF on forms, rate-limit on auth

### Sprint 3 (Aug 6–12): Testing + Reliability
- [ ] **P1-6** Postman collection, Playwright E2E (7 journeys), k6 load tests, security scanning in CI
- [ ] **P2-2** Media library + alt-text enforcement
- [ ] **P2-4** Status panel + feature flags

### Phase 4: Hardening (Aug 13–26)
- [ ] **P2-1** RBAC deny-by-default audit, two-person approval for refunds, session management
- [ ] **P2-5** i18n strings extraction, axe-core a11y audit pass
- [ ] OWASP Top 10 scan + Strix penetration test

### Phase 5: Scale (Post-Launch)
- [ ] **P2-3** Public + admin search (Elasticsearch/Typesense later)
- [ ] **P2-6** Public blog masonry upgrade, featured posts, collections

### Release Checklist (Per Deploy)
```
Pre-deploy:
□ All tests green on main branch
□ Security scan: 0 high/critical CVEs, 0 secrets
□ Load test: p95 < 500ms public, p95 < 2000ms Charon
□ Manual smoke test: login, create post, maintenance toggle, Charon chat
□ Backup: pg_dump last 24h verified
□ Charon RAG: latest scenario chunks indexed
□ OpenAPI diff: no unapproved changes

Deploy:
□ git push → Vercel auto-deploy (frontend)
□ git push → Docker rebuild + restart (backend, zero-downtime)
□ Monitor: /api/v1/health (DB, Redis, LiteLLM, Ollama)

Post-deploy:
□ curl styxproxy.com → confirm 200
□ curl styxproxy.com/blog → confirm 200 (with og:image meta)
□ curl /api/v1/health → all services green
□ Check Sentry: 0 new errors
□ Notify: Telegram bot post to admin channel "Deploy complete ✅"
□ If maintenance was on for deploy: confirm auto-disabled per schedule
```

---

## 7. RISKS + MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **LiteLLM proxy down (currently true)** | High | Critical | systemd unit or `restart: always` in compose, watchdog cron pings every 60s, alert if down > 5min |
| Admin auth migration breaks existing login | Low | Critical | Single auth system in prod (no parallel), rollback script in `infra/` |
| Resend emails land in spam | Low | High | SPF/DKIM/DMARC configured (verified); Mailtrap pre-flight check |
| Charon MiniCPM5 OOM under load | Medium | High | LiteLLM keep-alive + restart script; MiniMax M2.5 fallback via env switch |
| RAG knowledge base goes stale | High | Medium | Admin review queue; feedback loop with admin approval gate |
| Blog CMS creates XSS via rich text | Medium | High | DOMPurify sanitization on all content; CSP headers; SanitizedHtml component ✅ |
| Database migrations break on rollback | Low | High | All migrations tested in staging; rollback tested before each |
| OpenAPI spec drifts from implementation | High | Medium | CI auto-generates types from spec; diff check gates merge |
| Maintenance mode blocks admin access | Medium | Critical | Explicit exclusion: `/admin/*` and `/api/v1/admin/*` and `/api/v1/superadmin/*` and `/api/v1/platform/*` always pass; order flow keeps working |
| Charon leaks PII in responses | Medium | Critical | Output filter strips phone numbers, IPs, emails; never send raw user input to LLM |
| Redis cache invalidation misses updates | Medium | Low | Invalidate on every write; TTL as backstop; cache hit rate metric |
| Frontend uses stale OpenAPI types | High | Medium | CI step: `npm run gen:api-types` runs on every PR; type errors fail build |
| ChatWidget renders on admin pages | Low | Critical | pathname.startsWith('/admin') guard ✅ + E2E test verifies |
| DEMO_POSTS fallback hides blog outage | Medium | High | Remove fallback; on error, render error state with retry |
| Lighthouse score regresses unnoticed | High | Medium | Lighthouse CI on every PR; fail if performance < 80 |

---

## 8. ADDITIONAL RECOMMENDATIONS (A–G)

### A. Security & Compliance

**Do now (this sprint):**
- Audit log viewer at `/admin/audit-log` ✅ (backend exists; UI stub)
- Session management: list active sessions, revoke individual sessions (`admin_sessions` table)
- IP allowlist: optional field in admin profile, checked on every request
- Two-person approval: for refunds > ₦10,000 — require second admin to confirm in UI
- Re-authentication gate on `/api/v1/superadmin/*` POST endpoints

**Later:**
- SOC 2 readiness checklist (if enterprise customers come)
- Data retention policy: customer data deleted after 2 years inactive
- PCI-DSS scope: card data never touches our servers (Flutterwave handles)

### B. Content & Media Tooling

**Now (with media library in Sprint 3):**
- `/admin/media` page: all uploaded images with tags, alt-text fields
- Alt-text required: if cover_image_url is set but alt_text empty → block publish
- Blog review workflow: draft → pending → approved → published (with reviewer + notes)
- Image dedup: SHA256 hash on upload → reject duplicates
- Image compression: WebP conversion at upload

**Later:**
- S3/Cloudflare R2 for image storage (currently URLs are external)
- CDN-served with signed URLs for private media

### C. Search Improvements

**Now:**
- Public: `/blog/search?q=keyword` — full-text search across title + excerpt + content (PostgreSQL `to_tsvector` for MVP)
- Admin: `/admin/search?q=anything` — searches customers, orders, posts, escalations in one query (backend ✅ exists)

**Later:**
- Elasticsearch or Typesense for full-text with fuzzy matching, facets, relevance tuning
- Saved search filters + email alerts
- CSV export from admin search results

### D. Observability & Reliability

**Now (Sprint 3):**
- Internal status page: `/admin/status` — API uptime %, Charon uptime, DB latency, Redis ping, last backup time
- Feature flags: `system_settings` + `feature_flags` table → UI at `/admin/features` to toggle per-feature
- Telegram alerts: critical errors → `@styxproxy_alerts` bot
- LiteLLM watchdog cron: ping every 60s, alert if down 5min

**Later:**
- Grafana dashboards for metrics
- Distributed tracing (OpenTelemetry)
- UptimeRobot for external uptime (status.styxproxy.com)

### G. Localization & Accessibility

**Foundation (this sprint):**
- All UI strings extracted to `/messages/en.json` (i18n-ready structure even if not loaded)
- `aria-label` on all icon-only buttons
- Keyboard navigation: Tab order logical, Escape closes modals, focus trap in modals
- Color contrast: WCAG AA (4.5:1 body, 3:1 large text) — already green in light/dark theme ✅

**Later:**
- i18n with `next-intl`: extract strings → translate → load by locale
- RTL support for Arabic/Urdu markets
- Screen reader audit with NVDA

---

## 9. RECOMMENDATIONS BEYOND SPEC

Things not in the original goals but worth doing, ordered by impact per cost.

### High-impact, low-cost (do in Sprint 1)
1. **Remove the `DEMO_POSTS` silent fallback in `blog/page.tsx`** — it's masking outages
2. **Add `og:image` + Twitter card** to blog post detail (5-min fix, big SEO win)
3. **Store a Lighthouse baseline** in `docs/lighthouse-baseline.json` so future regressions are detectable
4. **Add error tracking to LiteLLM failure path** — if Ollama returns 5xx, Charon should reply with a fallback message, not a 30s hang
5. **Email signature on all Resend templates** — Dannion's name + Telegram handle so customers always know who they're talking to
6. **Per-IP rate limit on admin login** — 5/min, lockout after 5 failures

### High-impact, medium-cost (Sprint 2)
7. **Charon voice/style guide as a system prompt** — currently MiniCPM5 drifts in tone; pin it
8. **One-shot handoff from order page to Charon with order context** — when customer is mid-checkout and types "help", Charon knows what they're looking at
9. **Admin dashboard "Quick Stats" card on landing** — current day's revenue, open escalations, posts pending review, at-a-glance
10. **Audit-log diff viewer** — diff two admins' actions over a date range (useful for incident review)
11. **Customer anonymous-feedback box on /thank-you page** — "How was your purchase?" → drives product improvements, doesn't pollute Charon RAG
12. **Postman auto-publish to internal site** — `internal.styxproxy.com/api` so non-engineers can poke endpoints
13. **Slack-style "what changed" deploy log** — `git log --oneline | head -10` posted to Telegram after every deploy

### Medium-impact, medium-cost (Sprint 3+)
14. **PgBouncer in front of PostgreSQL** — at 10k concurrent customers, connection pooling matters
15. **Cloudflare Turnstile on contact form + Charon entry** — invisible bot challenge, free
16. **JSON logging instead of plain text** — structured logs enable real search in Loki
17. **Postgres row-level security on `posts`** — only superadmin can see `draft`/`pending` rows; readers see only `published`
18. **Nginx-level rate limit as belt-and-suspenders** behind FastAPI limiter
19. **Cost dashboard in admin** — LiteLLM tokens used this month, Resend sends, Vercel bandwidth
20. **Health-check Telegram digest (daily)** — uptime summary, error count, slow endpoints

### Nice-to-have, future
21. **Voice reply from Charon** — TTS via Edge TTS en-GB-RyanNeural, send voice bubble on Telegram
22. **Admin mobile app** — React Native shell that calls existing `/api/v1/admin/*` endpoints; useful when Dannion is away from laptop
23. **Customer-facing admin lookup** — `/order/lookup?tx_ref=ABC123` → show order status without login
24. **Webhook signature audit** — replay attack test in CI (Resend, Flutterwave)
25. **Disaster recovery runbook** — printed PDF in 1Password, reviewed quarterly
26. **Customer NPS score** — quarterly email survey, track in `feedback_nps` table
27. **Public roadmap at /roadmap** — P1/P2/P3 cards, public vote (simple Upstash Redis-backed counter)

### Things to REMOVE (anti-recommendations)
- ❌ Don't add Stripe — Flutterwave covers NGN/USD, no need for a second processor
- ❌ Don't build a custom CMS — use the existing `/admin/blog` editor + media library
- ❌ Don't add "real-time" WebSocket chat — SSE for Charon streaming is enough; WS adds complexity without benefit
- ❌ Don't write your own analytics — Plausible or Umami is 10x better and cheaper

---

## 10. SUPERADMIN INVITE

```
Code:    nDIvMgm7Uqo-WjZ5gw
Email:   oyebiyiayomide30@gmail.com
Role:    superadmin
Expires: August 4, 2026 (14 days from generation)
Max Uses: 1
```

**To create your superadmin account:**
1. Go to `styxproxy.com/admin/setup`
2. Enter invite code: `gfDiCUN5LycJ1SPH` (expires August 4, 2026)
3. Set your email + password
4. Scan QR with your authenticator app (TOTP)
5. Save your backup codes somewhere safe

---

*Document maintained by: Sonny (Hermes Agent) | v1.2 audit pass Jul 22 2026*
*Next review: Aug 5 2026 (post-Sprint 1)*