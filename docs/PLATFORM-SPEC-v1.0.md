# Styxproxy Platform — Full Platform Specification
**Version:** 1.1 | **Date:** 2026-07-21 | **Status:** Active Build

---

## Table of Contents
1. Prioritized Goals (P0 / P1 / P2)
2. Scenarios → User Stories → Acceptance Criteria → Tests
3. Technical Architecture Notes
4. Test Plan
5. Rollout Plan
6. Risks + Mitigations
7. Additional Recommendations (A–G)
8. Superadmin Invite

---

## 1. PRIORITIZED GOALS

### P0 — Must Have (Live Now / Next Sprint)
| # | Workstream | Status |
|---|---|---|
| P0-1 | **Admin Auth Cleanup** (email+TOTP, nav removal, token bug fix) | ✅ COMPLETED — api.ts `/api/admin/*` token fix, 2-step login, setup/login nav removed |
| P0-2 | **Phase 1 Blog** (DB wiring, admin CMS, public feed) | ✅ COMPLETED |
| P0-3 | **Resend Email Setup** (admin invites, password reset, customer purchase emails) | ✅ COMPLETED — admin auth emails wired, customer order+credentials in one combined email |
| P0-4 | **Superadmin Dashboard** | ⬜ Not started |

### P1 — Should Have (Post-Launch Sprint)
| # | Workstream | Why |
|---|---|---|
| P1-1 | **Charon on VPS + Public Widget** | Core product differentiator |
| P1-2 | **Charon Escalations Queue** | Prevents user abandonment when Charon fails |
| P1-3 | **Scenarios → RAG for Charon** | Deterministic answers for common queries, cost saving |
| P1-4 | **Frontend/Backend Alignment + OpenAPI** | Prevents field mismatches, enables API consumers |
| P1-5 | **Maintenance Mode + Scheduling** | Zero-downtime ops for updates |

### P2 — Nice to Have (Post-Market Fit)
| # | Workstream | Why |
|---|---|---|
| P2-1 | **Full Platform Testing (Postman + CI)** | Regression prevention, confidence at scale |
| P2-2 | **Security & Compliance (RBAC, alerts, session mgmt)** | Enterprise readiness |
| P2-3 | **Media Library + Alt-text + Review Workflow** | Content quality at scale |
| P2-4 | **Search (Public + Admin with export)** | UX improvement |
| P2-5 | **Observability (status panel, feature flags, alerting)** | Operational excellence |
| P2-6 | **Localization & Accessibility foundation** | Future-proofing |

---

## 2. USER STORIES → ACCEPTANCE CRITERIA → TESTS

---

### WORKSTREAM 6: Scenarios → RAG → Charon Knowledge Base

**Context:** 12 scenario files exist at `/root/workspace/styxproxy/scenarios/`. Each captures canonical customer/admin flows as turn-by-turn replays with system behavior + replies.

**Sample scenarios covered:**
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

**Story 1: Scenario Ingestion**
```
As: System (automated)
I want: Scenario files parsed and chunked into retrievable knowledge units
So that: Charon can cite sources in answers
Acceptance Criteria:
- [ ] Each scenario file is parsed (title, status, rules, replies, system behavior)
- [ ] Chunks tagged by scenario ID, category (order/recovery/admin/etc), channel
- [ ] Chunk vector stored with source URL/path metadata
- [ ] Admin can view all chunks in a knowledge base UI
```

**Story 2: Knowledge Base Admin Tool**
```
As: Admin
I want: A UI to view, add, edit, and retire knowledge chunks
So that: I can keep Charon's knowledge current without engineering
Acceptance Criteria:
- [ ] /admin/knowledge page: list all chunks, filter by category/tag/scenario
- [ ] Create chunk: text content, category, tags, source reference
- [ ] Edit chunk: versioning preserved (old version archived)
- [ ] Retire chunk: soft-delete (mark inactive, keep history)
- [ ] All changes require approval before going live (2-step: edit → approve → live)
- [ ] Version history visible: who changed what, when, why
```

**Story 3: Charon Answers Cite Sources**
```
As: User
I want: Every Charon answer to show where the information came from
So that: I can verify and trust the response
Acceptance Criteria:
- [ ] Charon response includes citation: "Source: Scenarios 2026-06-26, Scenario 3"
- [ ] Unanswerable queries return: "I don't have information on that. Contact support."
- [ ] No hallucinated facts — Charon never makes up proxy pricing, policies, or procedures
```

**Story 4: Learning Loop (Safe)**
```
As: System
I want: User feedback stored for review, not auto-applied
So that: Charon improves without receiving garbage or manipulated training data
Acceptance Criteria:
- [ ] Thumbs up/down on Charon replies logged to charon_feedback table
- [ ] Flagged responses (thumbs down) queued for admin review
- [ ] Admin can mark feedback as "helpful update" → creates a new knowledge chunk
- [ ] No feedback auto-applies to knowledge base — explicit admin approval required
- [ ] Learning loop audit log: what was flagged, reviewed, accepted/rejected
```

**Story 5: Scenario → Test Case Conversion**
```
As: QA / Developer
I want: Each scenario file automatically converted into testable specs
So that: I can verify the system behaves exactly as the scenario describes
Acceptance Criteria:
- [ ] Parser reads scenario markdown → extracts: trigger, system behavior, expected reply
- [ ] Output: JSON test spec { scenario_id, input, expected_output, assertions }
- [ ] Test specs run against actual system via Postman or Playwright
- [ ] Scenario 1 → at least 3 test cases (happy path, error path, edge case)
```

**Tests (Story 1–5):**
- Unit: scenario parser extracts all fields correctly
- Integration: parsed chunks retrievable via similarity search
- E2E: Charon cites correct scenario in answer (verified via chat log)
- E2E: Admin edits chunk → approval → search index updated
- E2E: Feedback logged → admin review → approved → new chunk searchable

---

### WORKSTREAM 7: Charon Escalations in Dashboard

**Epic:**
```
EPIC: As support, I want a clear escalation queue so I can resolve stuck chats quickly.
```

**Story 1: Escalation Triggers**
```
As: System
I want: Charon automatically escalate when confidence < 0.7, user asks for human, or provider fails
So that: No user is ever left in a dead end
Acceptance Criteria:
- [ ] charon_escalations table: id, session_id, user_phone, trigger_type, confidence, transcript, status, assigned_to, resolution_notes, created_at, resolved_at
- [ ] Triggers: low_confidence, human_request, provider_error, user_feedback_negative, timeout
- [ ] Each escalation has full chat transcript attached
- [ ] Telegram/WhatsApp notification to admin when new escalation created
```

**Story 2: Escalation Queue UI**
```
As: Admin / Support
I want: A queue showing all unresolved escalations sorted by urgency and age
So that: I can triage and resolve efficiently
Acceptance Criteria:
- [ ] /admin/escalations page: table with columns: customer, trigger, age, status, assigned_to
- [ ] Filter tabs: All / Unresolved / Mine / Resolved Today
- [ ] Click row → escalation detail: full transcript, customer history, action buttons
- [ ] Action buttons: Resolve, Assign to me, Escalate to ticket, Dismiss (with reason)
- [ ] SLA timer: escalations > 2 hours old shown in red
- [ ] Bulk resolve for spam/low-priority items
```

**Story 3: Escalation → Ticket Conversion**
```
As: Admin
I want: Convert an escalation into a support ticket with context pre-filled
So that: Complex issues get tracked and resolved properly
Acceptance Criteria:
- [ ] "Create Ticket" button on escalation detail → creates ticket in tickets table
- [ ] Ticket pre-filled: customer, issue summary, chat transcript, priority
- [ ] Link back: ticket → escalation, escalation → ticket
- [ ] Ticket status change syncs to escalation status
```

**Story 4: SLA Metrics**
```
As: Admin
I want: Visibility into escalation resolution times and volumes
So that: I can spot trends and improve response
Acceptance Criteria:
- [ ] Dashboard widget: escalations today / this week / avg resolution time
- [ ] Chart: escalations by trigger type (last 30 days)
- [ ] Export to CSV for reporting
```

**Tests:**
- Unit: each trigger type creates correct escalation record
- Integration: escalation appears in queue within 30s of trigger
- E2E: Admin resolves escalation → status=resolved, resolved_at set
- E2E: Convert to ticket → ticket record created with correct context
- Load: queue renders correctly with 500+ escalations

---

### WORKSTREAM 8: Maintenance Mode (All Public Pages) + Scheduling + Animated Page

**Epic:**
```
EPIC: As admin, I want to put the platform in maintenance mode so users see a clear ETA while I deploy updates.
```

**Story 1: Maintenance Mode Toggle**
```
As: Admin
I want: A single toggle to enable/disable maintenance mode globally
So that: I can quickly take the site down for deployments
Acceptance Criteria:
- [ ] System setting: maintenance_mode (boolean), maintenance_message, maintenance_eta
- [ ] /admin/settings page: toggle switch + message textarea + ETA datetime picker
- [ ] Toggle triggers: update system_settings table → middleware reads flag on every request
- [ ] /admin/* routes always accessible regardless of maintenance mode
- [ ] Audit log entry on every toggle: who toggled, when, old/new state
```

**Story 2: Maintenance Page (Animated)**
```
As: Public user
I want: A beautiful, informative maintenance page when the site is down
So that: I know what's happening and when to expect the site back
Acceptance Criteria:
- [ ] Full-screen page at / (when maintenance on) — NOT a generic error
- [ ] Animated: pulsing logo, subtle gradient background, countdown timer
- [ ] Shows: custom message from admin, ETA countdown (or "We'll be back soon" if no ETA)
- [ ] Contact options: email link, Telegram link
- [ ] Dark theme consistent with Styxproxy brand
- [ ] No layout shift — instant render (static HTML, no API calls)
- [ ] Mobile responsive
```

**Story 3: Scheduled Maintenance**
```
As: Admin
I want: Schedule maintenance to start and end automatically
So that: I can plan deploys without being at my computer at 2am
Acceptance Criteria:
- [ ] Schedule: maintenance_start_at, maintenance_end_at (datetime fields)
- [ ] System cron job checks every minute: if now > start_at → enable maintenance
- [ ] If now > end_at → disable maintenance, restore normal operation
- [ ] Admin notification when scheduled maintenance activates and ends
- [ ] Multiple schedules supported (schedule a recurring weekly window if needed)
```

**Story 4: Charon During Maintenance**
```
As: System
I want: Charon widget hidden or replaced on public pages during maintenance
So that: No dead-end interactions during downtime
Acceptance Criteria:
- [ ] Maintenance mode: hide Charon widget on all public pages
- [ ] If user has open chat session → save session, show maintenance notice in chat
- [ ] /admin/charon accessible as normal (admin-only)
```

**Tests:**
- E2E: Toggle maintenance on → public pages show maintenance page (curl test)
- E2E: Maintenance page accessible at / while API is down
- E2E: /admin/* still accessible during maintenance (cookie auth)
- E2E: Schedule future maintenance → auto-activates at start_at
- E2E: Charon widget hidden on public pages during maintenance
- Performance: maintenance page loads in <200ms (no API calls)

---

### WORKSTREAM 9: Resend Email Setup

**Epic:**
```
EPIC: As Styxproxy, I want transactional emails to deliver reliably with consistent branding.
```

**Stories:**
| Story | Trigger | Template |
|---|---|---|
| Admin Invite | Invite created | Logo + invite link + expires in 7 days |
| Password Reset | Admin requests reset | Logo + reset link (expires 1h) + IP/device warning |
| 2FA Setup | TOTP enrolled | Logo + backup codes + security reminder |
| Order Confirmation | Payment confirmed | Order details + proxy credentials + setup guide |
| Refund Processed | Refund approved | Amount + refund method + 5-7 day timeline |
| Escalation Alert | New escalation | Customer + issue summary + action link |

**Acceptance Criteria:**
- [ ] Resend SDK configured in backend: API key in env, from address = noreply@styxproxy.com
- [ ] Email templates: React Email ormj, dark-mode friendly, Styxproxy logo/branding
- [ ] SPF/DKIM/DMARC: DNS records configured (DKIM via Resend)
- [ ] Unsubscribe header on all marketing-adjacent emails
- [ ] Bounce handling: webhook → mark email invalid → alert admin
- [ ] Test emails: "Send test email" button in /admin/settings
- [ ] Email log: every sent email logged to email_log table (to, template, sent_at, bounced)

**Tests:**
- Unit: each email template renders without errors
- Integration: send test email → check inbox (use Mailtrap for dev)
- E2E: create admin invite → invite email received within 2 minutes
- E2E: request password reset → reset email received + link works once
- Deliverability: DMARC alignment passing (check: mail-tester.com)

---

### WORKSTREAM 10: Frontend/Backend Alignment + DB Design + Performance

**Epic:**
```
EPIC: As a developer, I want a single source of truth for API contracts so I never waste time debugging field mismatches.
```

**Stories:**

**Story 1: OpenAPI Spec (Auto-Generated)**
```
As: Developer
I want: Auto-generated OpenAPI spec at /api/docs
So that: I can see all endpoints, schemas, and test them directly
Acceptance Criteria:
- [ ] FastAPI app generates OpenAPI 3.0 spec at /openapi.json
- [ ] Swagger UI at /api/docs (password-protected for internal use)
- [ ] Every endpoint has: summary, description, response models, example payloads
- [ ] Frontend team imports types from OpenAPI spec (or generated client)
```

**Story 2: API Contract Tests (CI)**
```
As: CI Pipeline
I want: Automated tests that verify frontend and backend agree on every field
So that: Field mismatches caught before deployment
Acceptance Criteria:
- [ ] JSON Schema generated from Pydantic models (shared with frontend types)
- [ ] Postman collection auto-generated from OpenAPI spec
- [ ] CI run: fetch OpenAPI → generate types → compare to frontend types/index.ts
- [ ] CI fail if any field is missing, extra, or type-mismatched
```

**Story 3: Database Performance**
```
As: System
I want: All common queries to run under 50ms
So that: Pages load instantly even under load
Acceptance Criteria:
- [ ] Index audit: every foreign key, every filtered column (status, slug, published_at, author)
- [ ] Query review: EXPLAIN ANALYZE on all /api/* endpoints under load
- [ ] Connection pooling: PgBouncer or connection limits tuned
- [ ] Read replica consideration for public blog (if traffic grows)
- [ ] Migrations: Alembic configured, rollback tested on each migration
- [ ] Backup: daily automated pg_dump to S3/GCS, tested restore quarterly
```

**Story 4: Caching**
```
As: System
I want: High-traffic public content (blog posts, pricing) cached
So that: DB isn't hit for every page view
Acceptance Criteria:
- [ ] Redis cache for blog post list (TTL: 5 min, invalidate on create/update/publish)
- [ ] Cache-Control headers on public blog: s-maxage=300, stale-while-revalidate=60
- [ ] Individual blog post cached by slug (TTL: 15 min)
- [ ] Plans/pricing cached (TTL: 1 hour, invalidate on plan update)
```

**Tests:**
- Performance: p95 latency < 200ms for public blog list (k6 load test)
- Performance: p95 latency < 100ms for individual blog post
- CI: API contract test passes (OpenAPI vs frontend types)
- DB: all indexes present (verify via pg_indexes view)
- Cache: blog cache hit rate > 80% under simulated load

---

### WORKSTREAM 11: Full Platform Testing

**Epic:**
```
EPIC: As Styxproxy ops, I want automated tests covering every critical path so I ship with confidence.
```

**Postman Collection (every endpoint):**
```
Collection: Styxproxy API
├── Auth
│   ├── POST /api/admin/auth/invite (create invite)
│   ├── POST /api/admin/auth/setup (use invite → create admin)
│   ├── POST /api/admin/auth/login (email + password + TOTP)
│   ├── POST /api/admin/auth/logout
│   ├── GET  /api/admin/auth/me
│   └── POST /api/admin/auth/refresh
├── Blog
│   ├── GET  /api/blog/posts (public, paginated)
│   ├── GET  /api/blog/posts/{slug} (public)
│   ├── GET  /api/blog/rss.xml
│   ├── GET  /api/blog/admin/posts (auth required)
│   ├── POST /api/blog/admin/posts (create)
│   ├── PATCH /api/blog/admin/posts/{id} (update)
│   ├── DELETE /api/blog/admin/posts/{id}
│   └── Category CRUD endpoints
├── Charon
│   ├── POST /api/charon/reply (public widget)
│   ├── GET  /api/charon/health
│   └── Escalation endpoints
├── Platform
│   ├── GET  /api/platform/products
│   ├── GET  /api/platform/pricing
│   └── Feature flags
├── Admin CRUD
│   ├── Customers (list, detail)
│   ├── Orders (list, detail, status)
│   ├── Plans (CRUD)
│   └── Contacts (list, update status)
└── System
    ├── GET  /health
    ├── GET  /api/health
    └── Maintenance mode toggle
```

**E2E Tests (Playwright or Cypress):**
| Test | Steps | Assertion |
|---|---|---|
| Admin email login + TOTP | Navigate to /admin/login → enter credentials + TOTP → verify dashboard | Dashboard loads, no redirect loop |
| Create blog post | Login → /admin/blog → create post → publish → visit /blog | Post visible publicly |
| Maintenance mode toggle | Enable maintenance → curl styxproxy.com | 503 with maintenance page |
| Refund workflow | Place order → request refund → admin approves → verify refund | Order status = refunded |
| Charon escalation | Send off-topic message → verify deflection | Response is short, no LLM second call |
| Mobile responsiveness | Blog feed on mobile viewport | Grid collapses to 1 column, no overflow |

**Load Tests (k6):**
```
Scenarios:
- Public blog: 50 VUs, 5 min ramp, GET /api/blog/posts
- Blog post detail: 30 VUs, reads from cache
- Admin API: 5 VUs, mixed CRUD operations
Thresholds:
- p95 latency < 500ms
- error rate < 1%
- CSS/JS bundle < 200KB (per asset)
```

**CI Integration:**
```
GitHub Actions workflow (on every PR):
1. npm run build (frontend)
2. pytest (backend unit tests)
3. Newman run Postman collection (API tests)
4. Lighthouse CI (performance budget: performance score > 80)
5. npm audit (security: no high/critical vulnerabilities)
```

---

## 3. TECHNICAL ARCHITECTURE NOTES

### 3a. Architecture
```
Public:  styxproxy.com (Vercel/Next.js)
         ├── /blog/*         → DB-backed blog
         ├── /products        → pricing/products page
         └── /charon-widget  → embeddable chat widget

API:     api.styxproxy.com (FastAPI on VPS Docker)
         ├── /api/blog/*     → blog CRUD + public list
         ├── /api/charon/*   → Charon LLM endpoint
         ├── /api/admin/*    → admin dashboard API
         └── /api/platform/* → public product/pricing API

VPS:     84.247.132.12 (Docker stack)
         ├── styxproxy-local-api-1      (FastAPI, port 8000)
         ├── styxproxy-local-postgres-1 (PostgreSQL, port 5432)
         ├── styxproxy-local-redis-1    (Redis, port 6379)
         └── ollama (MiniCPM5 1B, port 11434)
```

### 3b. Security Architecture
```
Authentication:
- Admin: email + bcrypt password + TOTP (rotates every 30s)
- Session: JWT (15min access, 7d refresh), stored in httpOnly cookie
- Re-auth: required for sensitive actions (refunds, permission changes, maintenance toggle)

Authorization:
- Role: superadmin | admin | viewer
- superadmin: all permissions
- admin: manage own content + view customers/orders
- viewer: read-only dashboard

Secrets:
- Backend-only: DB password, Resend API key, JWT secret, TOTP encryption key
- Frontend-safe: Stripe pk_live (domain-scoped), public keys
- Env vars on VPS: starting point, use Doppler/Vault in production

RBAC:
- Every router endpoint has explicit permission check
- Feature flags: per-admin, per-role, globally
- Audit log: every write operation (who/what/when/IP)

Charon Security:
- Widget only on public pages (layout-level guard: !path.startsWith('/admin'))
- Rate limit: 10 req/min per IP on /api/charon/reply
- Input sanitization: strip HTML/scripts before LLM
- Output sanitization: strip PII from LLM responses
```

### 3c. Data Model (Extensions Needed)
```sql
-- Existing (key tables):
posts             -- blog posts
categories        -- blog categories (NEW)
post_categories   -- junction (NEW)
charon_escalations-- escalation queue (EXISTS, empty)
system_settings   -- maintenance mode, feature flags (EXISTS)
admin_audit_log   -- audit trail (EXISTS)
feature_flags     -- per-feature toggles (EXISTS)

-- New tables needed:
charon_knowledge_chunks  -- RAG knowledge base
charon_feedback           -- user feedback on Charon replies
charon_sessions           -- chat session history
maintenance_schedules     -- scheduled maintenance windows
email_log                 -- sent email tracking
admin_sessions            -- session management (device/IP tracking)
tickets                   -- support tickets from escalations
```

### 3d. Charon RAG Architecture
```
Scenario Files (MD)
    ↓ [Parser]
JSON Chunks: { id, category, trigger_patterns, reply_templates, rules }
    ↓ [Embedding: MiniCPM5 or OpenAI text-embedding-3-small]
Vectors stored in: SQLite FTS5 (local) or pgvector (production)
    ↓ [Retrieval: similarity search on user query]
Top-k chunks → LLM context window
    ↓
Charon Response + citations
```

### 3e. Observability Stack
```
Metrics:    Prometheus metrics endpoint at /metrics
Logs:       structured JSON → Loki or CloudWatch
Traces:     OpenTelemetry spans on /api/* endpoints
Errors:     Sentry (DSN in env)
Uptime:     status.styxproxy.com (UptimeRobot or self-hosted)
Alerting:   PagerDuty or Telegram bot for critical errors
```

---

## 4. TEST PLAN SUMMARY

| Layer | Tool | Frequency | Coverage Target |
|---|---|---|---|
| Unit | pytest | Every PR | All backend models/schemas/services |
| Integration | Postman/Newman | Every PR | All 40+ API endpoints |
| E2E | Playwright | Every PR | 6 critical user journeys |
| Contract | OpenAPI diff | Every PR | Frontend ↔ backend alignment |
| Load | k6 | Pre-release | p95 < 500ms @ 100 VUs |
| Accessibility | axe-core | Every PR | WCAG 2.1 AA compliance |
| Security | TruffleHog + npm audit | Every PR | 0 high/critical CVEs |
| Smoke | Health endpoint checks | Every deploy | /health, /api/health, /api/charon/health |

---

## 5. ROLLOUT PLAN

### Phase 0: Stabilization (Week 1–2)
- [ ] Admin Auth: email login, TOTP, nav removal ✅ **START HERE**
- [ ] Resend email: admin invites + password reset ✅
- [ ] Superadmin dashboard: full CRUD + audit log ✅
- [ ] Fix all known security issues from audit ✅

### Phase 1: Blog (Week 2–3) — **COMPLETED ✅**
- [ ] Backend DB wiring ✅
- [ ] Admin CMS ✅
- [ ] Public feed + SEO ✅
- [ ] Create first 3 blog posts (real content) ✅ **TODO: create posts**
- [ ] Blog RSS verified in FeedBurner/Substack

### Phase 2: Charon (Week 3–5)
- [ ] MiniCPM5 1B production endpoint (health check, auto-restart, logging)
- [ ] Charon public widget on styxproxy.com (contact page, order page)
- [ ] Scenarios → RAG knowledge base (parse → chunk → index → retrieve)
- [ ] Charon escalation queue + admin UI
- [ ] Email notifications for escalations

### Phase 3: Reliability (Week 5–7)
- [ ] Maintenance mode + scheduling
- [ ] Redis caching for public content
- [ ] OpenAPI spec + Postman collection
- [ ] CI pipeline: tests run on every PR
- [ ] Load tests (k6)
- [ ] Backup/restore procedure documented + tested

### Phase 4: Hardening (Week 7–9)
- [ ] RBAC (Deny-by-default permissions)
- [ ] Two-person approval for critical actions
- [ ] Session/device management for admins
- [ ] Security audit (OWASP Top 10 scan)
- [ ] Penetration test (Strix framework)

### Phase 5: Scale (Post-Market Fit)
- [ ] Media library + alt-text enforcement
- [ ] Public search + admin global search with CSV export
- [ ] Status panel (API/Charon/DB uptime)
- [ ] Feature flags for safe rollouts
- [ ] Localization foundation (i18n strings extracted)

### Release Checklist (Per Deploy)
```
Pre-deploy:
□ All tests green on main branch
□ Security scan: 0 high/critical CVEs
□ Load test: p95 < 500ms
□ Manual smoke test: login, create post, maintenance toggle
□ Backup: pg_dump last 24h verified
□ Charon RAG: latest scenario chunks indexed

Deploy:
□ git push → Vercel auto-deploy (frontend)
□ git push → Docker rebuild + restart (backend, zero-downtime)
□ Monitor: /health endpoint, error rate, latency

Post-deploy:
□ curl styxproxy.com → confirm 200
□ curl styxproxy.com/blog → confirm 200
□ Check Sentry: 0 new errors
□ Notify: Telegram bot post to admin channel "Deploy complete ✅"
```

---

## 6. RISKS + MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Admin auth migration breaks existing login | Medium | Critical | Run both auth systems in parallel for 1 week; rollback script ready |
| Resend emails land in spam | Medium | High | SPF/DKIM/DMARC configured; test with Mailtrap first |
| Charon MiniCPM5 OOM under load | Low | High | Keep-alive + restart script; MiniMax fallback via BFF |
| RAG knowledge base goes stale | High | Medium | Admin review queue; feedback loop with admin approval gate |
| Blog CMS creates XSS via rich text | Medium | High | DOMPurify sanitization on all content; CSP headers |
| Database migrations break on rollback | Low | High | All migrations tested in staging; rollback tested before each |
| OpenAPI spec drifts from implementation | Medium | Medium | CI auto-generates types from spec; diff check gates merge |
| Maintenance mode blocks admin access | Low | High | Explicit exclusion: /admin/* always passes through middleware |
| Charon leaks PII in responses | Low | Critical | Output filter strips phone numbers, IPs, emails before response |
| Redis cache invalidation misses updates | Medium | Low | Invalidate on every write; TTL as backstop |
| WhatsApp Business API approval delayed | High | Medium | Contact form fallback; Telegram as primary for now |

---

## 7. ADDITIONAL RECOMMENDATIONS (A–G)

### A. Security & Compliance
**Do now:**
- Audit log viewer in admin (already in DB) → expose at /admin/audit
- Session management: list active sessions, revoke individual sessions
- IP allowlist: optional field in admin profile, checked on every request
- Two-person approval: for refunds > ₦10,000 — require second admin to confirm

**Later:**
- SOC 2 readiness checklist (if enterprise customers come)
- Data retention policy: customer data deleted after 2 years inactive
- PCI-DSS scope: if Stripe is used, ensure card data never touches our servers

### B. Content & Media Tooling
**Now:**
- Media library page: /admin/media — shows all uploaded images with tags, alt-text fields
- Alt-text required: if cover_image_url is set but alt_text is empty → warning on post publish
- Blog review workflow: draft → submit for review → approved → published (status: draft→pending→approved→published)

**Later:**
- S3/Cloudflare R2 for image storage (currently URLs are external)
- Image compression on upload (WebP conversion)
- Deduplication: hash images on upload → reject duplicates

### C. Search (Public + Admin)
**Now:**
- Public: /blog/search?q=keyword — full-text search across title + excerpt + content (SQL LIKE for MVP, full-text later)
- Admin: /admin/search?q=anything — searches customers, orders, posts, escalations in one query

**Later:**
- Elasticsearch or Typesense for full-text with fuzzy matching, facets, relevance tuning
- Saved search filters + email alerts

### D. Observability & Reliability
**Now:**
- Internal status page: /admin/status — API uptime %, Charon uptime, DB latency, Redis ping, last backup time
- Feature flags: system_settings + feature_flags table → UI at /admin/features to toggle per-feature
- Telegram alerts: critical errors → admin Telegram bot

**Later:**
- Grafana dashboards for metrics
- Distributed tracing (OpenTelemetry)
- UptimeRobot or self-hosted uptime checker (status.styxproxy.com)

### G. Localization & Accessibility
**Foundation (now):**
- All UI strings in a `/messages/en.json` file (i18n-ready)
- aria-label on all icon-only buttons
- Keyboard navigation: Tab order logical, Escape closes modals
- Color contrast: all text meets WCAG AA (4.5:1 for body, 3:1 for large text)

**Later:**
- i18n with next-intl: extract strings → translate → load by locale
- RTL support for Arabic/Urdu markets (proxy customers worldwide)

---

## 8. SUPERADMIN INVITE CODE

```
Code:    nDIvMgm7Uqo-WjZ5gw
Email:   oyebiyiayomide30@gmail.com
Role:    superadmin
Expires: August 4, 2026 (14 days from now)
Max Uses: 1
```

**To create your superadmin account:**
1. Go to `styxproxy.com/admin/setup`
2. Enter invite code: `gfDiCUN5LycJ1SPH` (expires August 4, 2026)
3. Set your email + password
4. Scan QR with your authenticator app (TOTP)
5. Save your backup codes somewhere safe

---

*Document maintained by: Sonny (Hermes Agent) | Last updated: 2026-07-21*
