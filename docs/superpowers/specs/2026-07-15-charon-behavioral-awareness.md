# Charon Behavioral Awareness System — Design Spec
**Date:** 2026-07-15
**Status:** Approved
**Goal:** Charon watches anonymous session behavior, reaches out at high-intent moments, and continuously learns from engagement to improve conversion.

---

## 1. Goal

Charon (the support chatbot) becomes a **proactive sales agent** — aware of what users are doing on the site, reaching out at moments of hesitation or high intent, and continuously improving its timing and messaging based on real engagement data. The north-star metric: **trigger → conversation → purchase**.

---

## 2. Design Principles

- **Anonymous only** — no PII, no IP linking, no cookies beyond session. Session IDs are random tokens with no tie to identity.
- **Learn / Unlearn / Relearn** — weights can go up AND down. Dismissals suppress triggers. Opens and conversions boost them. The system adapts to real behavior, not assumptions.
- **Non-intrusive** — same UX rules as before: one bubble at a time, clear dismiss, respects cooldown, never fires twice in the same session for the same trigger.
- **Aggregate learning** — all users' sessions feed one shared model. Everyone benefits from every session.

---

## 3. Behavioral Triggers

All triggers are anonymous session events. Conditions are evaluated every **5 seconds** while the tab is open.

| Trigger ID | Detects when... | Base Message |
|---|---|---|
| `repeat_pricing` | `/pricing` visited 2+ times | "Still comparing plans? I can help you pick the right one." |
| `pricing_dwell` | On `/pricing` > 25s without clicking any plan | "Questions about our plans? I can clarify any doubt." |
| `product_browse` | 3+ product sub-pages visited without ordering | "Looking for something specific? I know our proxy types well." |
| `cart_abandon` | Item in cart; user navigated away from `/order` | "Your cart is still waiting. Need help completing checkout?" |
| `order_confusion` | Both `/order` and `/pricing` visited without completing | "Ready to order? I can walk you through it in 30 seconds." |
| `session_stuck` | 5+ pages, > 3 min active, no chat opened | "You've been browsing a while. Can I help you find something?" |
| `scroll_bottom` | User scrolled to bottom of any main content page | "Have questions about what you just read? I can answer them." |
| `exit_intent` | User moves cursor toward browser bar (desktop only) | "Leaving? Before you go — what's stopping you from ordering?" |
| `geo_question` | User visits country not on their plan | "Looking for a different country? I can check what's available." |

---

## 4. Trigger Lifecycle & Outcomes

### States
```
trigger_fired
    │
    ├── user_opened_chat       → positive
    ├── user_dismissed         → negative  
    ├── user_ignored (5s)     → neutral
    └── user_replied + bought  → very_positive
```

### Cooldown rules
- Same trigger: **minimum 60 seconds** between fires
- Same trigger in same session: **once only** (already enforced)
- Global suppression: if any trigger fired in last 45s, block new fires

### Conversion tracking
- If user opens chat from a trigger, a `trigger_id` is attached to the chat message context
- If that session results in a purchase (`order.status = fulfilled` via webhook), that trigger gets a `converted` signal

---

## 5. Learning System

### Weight formula

```
positive_rate = (opens + converted × 1.5) / total_engaged
engagement_rate = total_engaged / total_fires
signal = (positive_rate - BASELINE_RATE) × engagement_boost

new_weight = clamp(old_weight + LEARNING_RATE × signal, 0.2, 3.0)

BASELINE_RATE = 0.40        // expected open rate
LEARNING_RATE = 0.10        // slow, stable learning
MIN_WEIGHT = 0.2            // suppress annoying triggers
MAX_WEIGHT = 3.0            // boost highly effective triggers
```

### Weight initialization
All triggers start at `weight = 1.0` so they all fire by default. After 50 aggregate fires, learning takes over.

### Weight recalculation
Runs **every 24 hours** as a Railway cron job:
1. Read all `trigger_events` from last 7 days
2. Compute `positive_rate` and `engagement_rate` per trigger
3. Apply formula to get new weight
4. Write to `trigger_weights` table

### Learning rate strategy
- `LEARNING_RATE = 0.10` — changes are gradual, won't oscillate from a single bad batch
- Only recalculate triggers with ≥ 20 fires (enough data)
- Triggers with < 10 fires in 7 days: weight stays unchanged (insufficient data)

---

## 6. Data Model

### `trigger_events` table (Postgres)
```sql
CREATE TABLE trigger_events (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,          -- random anonymous token
    trigger_id  TEXT NOT NULL,
    fired_at    TIMESTAMPTZ DEFAULT NOW(),
    outcome     TEXT NOT NULL,          -- opened_chat | dismissed | ignored | converted
    charon_msg  TEXT,                   -- actual message shown (for A/B later)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON trigger_events (trigger_id, fired_at);
CREATE INDEX ON trigger_events (session_id);
```

### `trigger_weights` table (Postgres)
```sql
CREATE TABLE trigger_weights (
    trigger_id      TEXT PRIMARY KEY,
    weight          NUMERIC(5,3) NOT NULL DEFAULT 1.0,
    total_fires     BIGINT NOT NULL DEFAULT 0,
    total_opens     BIGINT NOT NULL DEFAULT 0,
    total_dismissed BIGINT NOT NULL DEFAULT 0,
    total_converted BIGINT NOT NULL DEFAULT 0,
    positive_rate   NUMERIC(5,4) NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 7. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/charon/trigger-event` | Frontend reports outcome when trigger fires |
| `GET` | `/api/charon/weights` | Frontend fetches current trigger weights |

### `POST /api/charon/trigger-event`
```json
// Request
{ "session_id": "sess_abc123", "trigger_id": "repeat_pricing", "outcome": "opened_chat" }

// Response
{ "ok": true }
```

### `GET /api/charon/weights`
```json
// Response
{
  "weights": {
    "repeat_pricing": { "weight": 1.35, "total_fires": 847 },
    "cart_abandon":   { "weight": 1.82, "total_fires": 234 },
    ...
  }
}
```

---

## 8. Frontend Architecture

```
ChatWidget
  ├── SessionTracker            ← in-memory Map + sessionStorage
  │     └── Tracks: page visits, dwell time, scroll, cart, trigger fires
  │
  ├── TriggerEngine             ← polls every 5s while tab active
  │     └── Fetches weights from /api/charon/weights (cached 60s)
  │     └── Evaluates all trigger conditions
  │     └── Picks highest-scoring eligible trigger
  │
  ├── TriggerPresenter          ← shows bubble or FAB badge
  │     └── Uses existing reach-out bubble from v1
  │     └── On open: POST outcome=opened_chat
  │     └── On dismiss: POST outcome=dismissed, hide for session
  │     └── On timeout (8s): POST outcome=ignored
  │
  └── CharonChat               ← existing chat (unchanged)
```

### Session state tracked (sessionStorage + memory)
- `pagesVisited: Set<string>` — page URLs
- `pageDwellStart: Map<url, timestamp>` — when user entered each page
- `totalActiveTime: number` — accumulated seconds
- `triggersFired: Set<trigger_id>` — already fired this session
- `lastTriggerFire: timestamp` — cooldown enforcement
- `cartPresent: boolean` — if cart has items

---

## 9. Conversion Webhook

When an order completes (`status = fulfilled`), the backend fires:
```
POST /api/charon/trigger-event
{ "session_id": "[from order metadata]", "trigger_id": "[last_trigger]", "outcome": "converted" }
```

The `session_id` is attached to the order at checkout time (stored in the `orders` table). After fulfillment, the last active trigger is looked up and recorded as `converted`.

---

## 10. Rollout Phases

**Phase 1 — Core loop (this build)**
- SessionTracker + TriggerEngine + TriggerPresenter in ChatWidget
- All 9 triggers wired with initial messages
- Backend tables + API endpoints
- Learning cron job (daily)
- No learning in Phase 1 — weights start at 1.0

**Phase 2 — Learning (after 7 days of data)**
- Weight recalculation cron activated
- Weights start adjusting based on real engagement

**Phase 3 — Message optimization (after 30 days)**
- Track which message variant (A/B) led to opens
- Store `charon_msg` in `trigger_events`
- Add simple message rotation based on best performer

---

## 11. Privacy & Ethics

- Session IDs are random 24-char tokens, **never tied to user identity**
- No IP addresses, emails, or device fingerprints stored
- No cross-session tracking — a new visit = a new session
- All data stays in Railway Postgres (owned by Styxproxy)
- GDPR note: session behavior data is not PII; no cookie consent needed for functional session tracking
- User can always dismiss Charon; dismissed = suppressed for that session

---

## 12. Open Questions

- [x] Aggregate vs per-session learning → **Aggregate** (all users feed one model)
- [x] Rule-based vs learning → **Rule-based + learning**
- [x] Analytics backend → **Own Railway Postgres**
- [x] Learn / unlearn / relearn → **Weights go up AND down based on engagement**
- [ ] Message A/B testing → **Deferred to Phase 3**
- [ ] Exit-intent detection → **Desktop only, cursor toward top of screen**
