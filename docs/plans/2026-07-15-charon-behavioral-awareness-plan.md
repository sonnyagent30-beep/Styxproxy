# Charon Behavioral Awareness — Implementation Plan

> **For Hermes:** Use `subagent-driven-development` skill to implement this plan task-by-task.

**Goal:** Build Phase 1 of the Charon Behavioral Awareness system — SessionTracker, TriggerEngine, TriggerPresenter, backend tables, API endpoints, and learning cron.

**Architecture:** Frontend (Next.js) tracks anonymous session events and evaluates trigger conditions every 5s. Backend (FastAPI/Railway) stores trigger events and weights. A nightly cron job recalculates weights from aggregate engagement data.

**Tech Stack:** Next.js (frontend), FastAPI (backend), Postgres on Railway, Railway cron.

---

## BACKEND TASKS

### Task B1: Create trigger_events and trigger_weights tables

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/triggers.py`
- Modify: `backend/app/main.py` — import router

**Step 1: Write migration SQL**

Save to `backend/migrations/0003_trigger_tables.sql`:

```sql
CREATE TABLE IF NOT EXISTS trigger_events (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    trigger_id  TEXT NOT NULL,
    fired_at    TIMESTAMPTZ DEFAULT NOW(),
    outcome     TEXT NOT NULL CHECK (outcome IN ('opened_chat', 'dismissed', 'ignored', 'converted')),
    charon_msg  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trigger_events_trigger_id_fired
    ON trigger_events (trigger_id, fired_at);
CREATE INDEX IF NOT EXISTS idx_trigger_events_session_id
    ON trigger_events (session_id);

CREATE TABLE IF NOT EXISTS trigger_weights (
    trigger_id      TEXT PRIMARY KEY,
    weight          NUMERIC(5,3) NOT NULL DEFAULT 1.0,
    total_fires     BIGINT NOT NULL DEFAULT 0,
    total_opens     BIGINT NOT NULL DEFAULT 0,
    total_dismissed BIGINT NOT NULL DEFAULT 0,
    total_converted BIGINT NOT NULL DEFAULT 0,
    positive_rate   NUMERIC(5,4) NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed initial weights (all start at 1.0)
INSERT INTO trigger_weights (trigger_id, weight) VALUES
    ('repeat_pricing',   1.0),
    ('pricing_dwell',    1.0),
    ('product_browse',   1.0),
    ('cart_abandon',     1.0),
    ('order_confusion',  1.0),
    ('session_stuck',    1.0),
    ('scroll_bottom',    1.0),
    ('exit_intent',      1.0),
    ('geo_question',     1.0)
ON CONFLICT (trigger_id) DO NOTHING;
```

**Step 2: Create triggers model**

Create `backend/app/models/triggers.py`:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TriggerEventCreate(BaseModel):
    session_id: str
    trigger_id: str
    outcome: str  # opened_chat | dismissed | ignored | converted
    charon_msg: Optional[str] = None


class TriggerWeightResponse(BaseModel):
    weight: float
    total_fires: int


class TriggerWeightsResponse(BaseModel):
    weights: dict[str, TriggerWeightResponse]
```

**Step 3: Add to __init__.py**

Modify `backend/app/models/__init__.py` to export from `triggers`.

**Step 4: Run migration**

```bash
psql $DATABASE_URL -f backend/migrations/0003_trigger_tables.sql
```

**Verification:** `\dt` shows `trigger_events` and `trigger_weights`. `\d trigger_weights` shows all columns.

---

### Task B2: Create `/api/charon/trigger-event` POST endpoint

**Files:**
- Create: `backend/app/routers/charon_triggers.py`
- Modify: `backend/app/main.py` — add `app.include_router(charon_triggers.router)`

**Step 1: Write the router**

```python
# backend/app/routers/charon_triggers.py
from fastapi import APIRouter, HTTPException
from app.models.triggers import TriggerEventCreate
from app.database import get_db

router = APIRouter(prefix="/api/charon", tags=["charon"])


@router.post("/trigger-event")
async def record_trigger_event(event: TriggerEventCreate):
    """Record what happened after a trigger fired."""
    if event.outcome not in ("opened_chat", "dismissed", "ignored", "converted"):
        raise HTTPException(status_code=400, detail="Invalid outcome")

    db = get_db()
    try:
        # Insert event
        db.execute(
            """
            INSERT INTO trigger_events (session_id, trigger_id, outcome, charon_msg)
            VALUES (%s, %s, %s, %s)
            """,
            (event.session_id, event.trigger_id, event.outcome, event.charon_msg),
        )

        # Update aggregate counters in trigger_weights
        if event.outcome == "opened_chat":
            db.execute(
                "UPDATE trigger_weights SET total_opens = total_opens + 1, total_fires = total_fires + 1 WHERE trigger_id = %s",
                (event.trigger_id,)
            )
        elif event.outcome == "dismissed":
            db.execute(
                "UPDATE trigger_weights SET total_dismissed = total_dismissed + 1, total_fires = total_fires + 1 WHERE trigger_id = %s",
                (event.trigger_id,)
            )
        elif event.outcome == "converted":
            db.execute(
                "UPDATE trigger_weights SET total_converted = total_converted + 1, total_opens = total_opens + 1, total_fires = total_fires + 1 WHERE trigger_id = %s",
                (event.trigger_id,)
            )
        # ignored: only increment fires, no other counter
        elif event.outcome == "ignored":
            db.execute(
                "UPDATE trigger_weights SET total_fires = total_fires + 1 WHERE trigger_id = %s",
                (event.trigger_id,)
            )

        # Recalculate positive_rate
        db.execute(
            """
            UPDATE trigger_weights
            SET positive_rate = CASE
                WHEN total_fires > 0 THEN (total_opens + total_converted * 1.5)::numeric / total_fires
                ELSE 0
            END,
            updated_at = NOW()
            WHERE trigger_id = %s
            """,
            (event.trigger_id,)
        )

        db.commit()
        return {"ok": True}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
```

**Step 2: Register router in main.py**

Add to `app.include_router` imports and call in `main.py`.

**Step 3: Verify**

```bash
curl -X POST http://localhost:8000/api/charon/trigger-event \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test_sess","trigger_id":"repeat_pricing","outcome":"opened_chat"}'
# Expected: {"ok": true}
```

---

### Task B3: Create `/api/charon/weights` GET endpoint

**Files:**
- Modify: `backend/app/routers/charon_triggers.py`

**Step 1: Add GET endpoint to the router**

```python
from app.models.triggers import TriggerWeightsResponse, TriggerWeightResponse

@router.get("/weights", response_model=TriggerWeightsResponse)
async def get_trigger_weights():
    """Return current trigger weights for the frontend TriggerEngine."""
    db = get_db()
    try:
        rows = db.execute("SELECT trigger_id, weight, total_fires FROM trigger_weights").fetchall()
        weights = {
            row["trigger_id"]: TriggerWeightResponse(
                weight=float(row["weight"]),
                total_fires=int(row["total_fires"]),
            )
            for row in rows
        }
        return TriggerWeightsResponse(weights=weights)
    finally:
        db.close()
```

**Step 4: Verify**

```bash
curl http://localhost:8000/api/charon/weights
# Expected: {"weights": {"repeat_pricing": {"weight": 1.0, "total_fires": 0}, ...}}
```

---

### Task B4: Create weight recalculation cron job

**Files:**
- Create: `backend/scripts/update_trigger_weights.py`
- Create: `backend/scripts/requirements-cron.txt`

**Step 1: Write the cron script**

```python
# backend/scripts/update_trigger_weights.py
"""
Nightly job: recalculate trigger weights from the last 7 days of engagement data.
Formula:
  positive_rate = (opens + converted × 1.5) / total_engaged
  engagement_rate = total_engaged / total_fires
  signal = (positive_rate - 0.40) × engagement_boost
  new_weight = clamp(old_weight + 0.10 × signal, 0.2, 3.0)

  engagement_boost = min(engagement_rate, 1.0)  # cap at 1.0
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ["DATABASE_URL"]

BASELINE_RATE = 0.40
LEARNING_RATE = 0.10
MIN_WEIGHT = 0.2
MAX_WEIGHT = 3.0
MIN_FIRES_FOR_LEARNING = 20
MIN_DATA_POINTS = 10


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get all triggers
    cur.execute("SELECT trigger_id, weight FROM trigger_weights")
    triggers = {row["trigger_id"]: float(row["weight"]) for row in cur.fetchall()}

    for trigger_id in triggers:
        # Only recalculate if enough data
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE outcome IN ('opened_chat', 'converted')) AS engaged,
                COUNT(*) AS fires
            FROM trigger_events
            WHERE trigger_id = %s
              AND fired_at > NOW() - INTERVAL '7 days'
            """,
            (trigger_id,),
        )
        row = cur.fetchone()
        engaged = row["engaged"] or 0
        fires = row["fires"] or 0

        if fires < MIN_DATA_POINTS:
            continue  # not enough data to learn from

        positive_rate = engaged / fires if fires > 0 else 0
        engagement_rate = engaged / fires if fires > 0 else 0
        engagement_boost = min(engagement_rate, 1.0)
        signal = (positive_rate - BASELINE_RATE) * engagement_boost
        old_weight = triggers[trigger_id]
        new_weight = clamp(old_weight + LEARNING_RATE * signal, MIN_WEIGHT, MAX_WEIGHT)

        if fires >= MIN_FIRES_FOR_LEARNING:
            cur.execute(
                """
                UPDATE trigger_weights
                SET weight = %s,
                    positive_rate = %s,
                    total_fires = GREATEST(total_fires, %s),
                    updated_at = NOW()
                WHERE trigger_id = %s
                """,
                (round(new_weight, 3), round(positive_rate, 4), fires, trigger_id),
            )
            print(f"  {trigger_id}: fires={fires}, pos_rate={positive_rate:.3f}, "
                  f"old={old_weight:.3f} → new={new_weight:.3f}")

    conn.commit()
    cur.close()
    conn.close()
    print("Weight recalculation complete.")


if __name__ == "__main__":
    main()
```

**Step 2: Set up Railway cron**

In Railway dashboard → Styxproxy service → Cron Jobs:
- Name: `trigger-weight-update`
- Command: `python backend/scripts/update_trigger_weights.py`
- Schedule: `0 0 * * *` (daily at midnight UTC)
- Environment: attach `DATABASE_URL` variable

**Verification:** Run manually first:
```bash
DATABASE_URL="postgresql://..." python backend/scripts/update_trigger_weights.py
# Expected: prints weight changes
```

---

## FRONTEND TASKS

### Task F1: Create SessionTracker — anonymous behavior tracking

**Files:**
- Create: `frontend/src/lib/SessionTracker.ts`

**Step 1: Write SessionTracker**

```typescript
// frontend/src/lib/SessionTracker.ts
/**
 * Anonymous session behavior tracker.
 * All data stays in sessionStorage + memory. No PII. No cookies.
 */

export interface SessionState {
  pagesVisited: Set<string>;         // full paths e.g. '/pricing'
  pageDwellStart: Map<string, number>; // url → Date.now()
  totalActiveTime: number;           // seconds
  triggersFired: Set<string>;         // trigger IDs already fired this session
  lastTriggerFire: number;           // timestamp ms
  cartPresent: boolean;
  lastTriggerDismissed: Set<string>; // per-session per-trigger dismisses
  scrollBottomPages: Set<string>;    // which pages user scrolled to bottom
  visitedProductCount: number;       // /products sub-pages
}

const STORAGE_KEY = 'charon_session';
const VISITED_PRODUCT_PATHS = ['/products/isp', '/products/residential', '/products/mobile', '/products/datacenter'];

function newSession(): SessionState {
  return {
    pagesVisited: new Set(),
    pageDwellStart: new Map(),
    totalActiveTime: 0,
    triggersFired: new Set(),
    lastTriggerFire: 0,
    cartPresent: false,
    lastTriggerDismissed: new Set(),
    scrollBottomPages: new Set(),
    visitedProductCount: 0,
  };
}

export class SessionTracker {
  private state: SessionState;
  private active: boolean = false;
  private tabVisible: boolean = true;
  private lastTick: number = Date.now();
  private tickInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    // Restore from sessionStorage or create new
    const saved = sessionStorage.getItem(STORAGE_KEY);
    this.state = saved ? this.deserialize(saved) : newSession();
  }

  /** Call once when the app mounts */
  start(): void {
    if (this.active) return;
    this.active = true;
    this.lastTick = Date.now();
    this.trackPageChange();

    // Accumulate active time every second
    this.tickInterval = setInterval(() => {
      if (this.tabVisible) {
        this.state.totalActiveTime += (Date.now() - this.lastTick) / 1000;
        this.lastTick = Date.now();
      }
    }, 1000);

    // Track tab visibility
    const onVisibility = () => { this.tabVisible = document.visibilityState === 'visible'; };
    document.addEventListener('visibilitychange', onVisibility);

    // Persist every 5s
    setInterval(() => this.persist(), 5000);
  }

  /** Call when user navigates to a new page */
  onPageVisit(path: string): void {
    // Mark dwell end for previous page
    for (const [p, t] of this.state.pageDwellStart) {
      if (p !== path) {
        // dwell for previous page was at least 1 second
        this.state.pageDwellStart.delete(p);
      }
    }

    this.state.pagesVisited.add(path);
    this.state.pageDwellStart.set(path, Date.now());

    // Count product sub-page visits
    if (VISITED_PRODUCT_PATHS.includes(path)) {
      this.state.visitedProductCount += 1;
    }

    this.persist();
  }

  /** Call when user scrolls to bottom of a page */
  onScrollBottom(path: string): void {
    this.state.scrollBottomPages.add(path);
    this.persist();
  }

  /** Call when item is added to cart */
  onCartAdd(): void {
    this.state.cartPresent = true;
    this.persist();
  }

  /** Call when cart is cleared */
  onCartClear(): void {
    this.state.cartPresent = false;
    this.persist();
  }

  /** Mark a trigger as fired */
  markTriggerFired(triggerId: string): void {
    this.state.triggersFired.add(triggerId);
    this.state.lastTriggerFire = Date.now();
    this.persist();
  }

  /** Mark a trigger as dismissed for the session */
  dismissTrigger(triggerId: string): void {
    this.state.lastTriggerDismissed.add(triggerId);
    this.persist();
  }

  /** Check if a trigger can fire (not dismissed, not recently fired globally) */
  canFire(triggerId: string, cooldownMs: number = 60_000): boolean {
    if (this.state.lastTriggerDismissed.has(triggerId)) return false;
    if (this.state.triggersFired.has(triggerId)) return false;
    if (Date.now() - this.state.lastTriggerFire < cooldownMs) return false;
    return true;
  }

  /** Get current state snapshot for TriggerEngine */
  getState(): Readonly<SessionState> {
    return { ...this.state };
  }

  /** Time spent on current page */
  currentPageDwell(): number {
    const entries = Array.from(this.state.pageDwellStart.entries());
    if (entries.length === 0) return 0;
    const [_, start] = entries[entries.length - 1];
    return (Date.now() - start) / 1000;
  }

  private persist(): void {
    sessionStorage.setItem(STORAGE_KEY, this.serialize());
  }

  private serialize(): string {
    return JSON.stringify({
      pagesVisited: Array.from(this.state.pagesVisited),
      triggersFired: Array.from(this.state.triggersFired),
      lastTriggerFire: this.state.lastTriggerFire,
      cartPresent: this.state.cartPresent,
      scrollBottomPages: Array.from(this.state.scrollBottomPages),
      visitedProductCount: this.state.visitedProductCount,
      totalActiveTime: this.state.totalActiveTime,
    });
  }

  private deserialize(raw: string): SessionState {
    const s = JSON.parse(raw);
    return {
      pagesVisited: new Set(s.pagesVisited ?? []),
      pageDwellStart: new Map(),
      totalActiveTime: s.totalActiveTime ?? 0,
      triggersFired: new Set(s.triggersFired ?? []),
      lastTriggerFire: s.lastTriggerFire ?? 0,
      cartPresent: s.cartPresent ?? false,
      lastTriggerDismissed: new Set(),
      scrollBottomPages: new Set(s.scrollBottomPages ?? []),
      visitedProductCount: s.visitedProductCount ?? 0,
    };
  }

  private trackPageChange(): void {
    // Use Next.js router events
    if (typeof window === 'undefined') return;
    const { useRouter } = require('next/router');
    // This is a simplified version — the actual integration uses useEffect in ChatWidget
    // to listen to router events and call onPageVisit
  }
}
```

---

### Task F2: Create TriggerEngine — evaluates conditions and picks best trigger

**Files:**
- Create: `frontend/src/lib/TriggerEngine.ts`

**Step 1: Write TriggerEngine**

```typescript
// frontend/src/lib/TriggerEngine.ts
import { SessionTracker, SessionState } from './SessionTracker';

export interface Trigger {
  id: string;
  message: string;
  score: number; // weight × base_score
  weight: number;
  baseScore: number;
  cooldownMs: number;
  evaluate(state: SessionState, tracker: SessionTracker): boolean;
}

const ALL_TRIGGERS: Omit<Trigger, 'score' | 'weight' | 'evaluate'>[] = [
  {
    id: 'repeat_pricing',
    message: "Still comparing plans? I can help you pick the right one.",
    baseScore: 0.8,
    cooldownMs: 90_000,
  },
  {
    id: 'pricing_dwell',
    message: "Questions about our plans? I can clarify any doubt.",
    baseScore: 0.7,
    cooldownMs: 60_000,
  },
  {
    id: 'product_browse',
    message: "Looking for something specific? I know our proxy types well.",
    baseScore: 0.6,
    cooldownMs: 120_000,
  },
  {
    id: 'cart_abandon',
    message: "Your cart is still waiting. Need help completing checkout?",
    baseScore: 0.9,
    cooldownMs: 60_000,
  },
  {
    id: 'order_confusion',
    message: "Ready to order? I can walk you through it in 30 seconds.",
    baseScore: 0.85,
    cooldownMs: 120_000,
  },
  {
    id: 'session_stuck',
    message: "You've been browsing a while. Can I help you find something?",
    baseScore: 0.5,
    cooldownMs: 180_000,
  },
  {
    id: 'scroll_bottom',
    message: "Have questions about what you just read? I can answer them.",
    baseScore: 0.4,
    cooldownMs: 120_000,
  },
  {
    id: 'exit_intent',
    message: "Leaving? Before you go — what's stopping you from ordering?",
    baseScore: 0.75,
    cooldownMs: 120_000,
  },
  {
    id: 'geo_question',
    message: "Looking for a different country? I can check what's available.",
    baseScore: 0.6,
    cooldownMs: 90_000,
  },
];

function buildTrigger(t: Omit<Trigger, 'score' | 'weight' | 'evaluate'>): Trigger {
  return {
    ...t,
    weight: 1.0, // will be updated by fetchWeights
    score: t.baseScore,
    evaluate(state: SessionState, tracker: SessionTracker) {
      switch (t.id) {
        case 'repeat_pricing':
          return (state.pagesVisited.has('/pricing') &&
            Array.from(state.pagesVisited).filter(p => p === '/pricing').length >= 2);

        case 'pricing_dwell':
          return state.pagesVisited.has('/pricing') && tracker.currentPageDwell() > 25;

        case 'product_browse':
          return state.visitedProductCount >= 3;

        case 'cart_abandon':
          return state.cartPresent;

        case 'order_confusion':
          return state.pagesVisited.has('/order') && state.pagesVisited.has('/pricing');

        case 'session_stuck':
          return state.pagesVisited.size >= 5 &&
            state.totalActiveTime > 180 &&
            !state.triggersFired.has('session_stuck');

        case 'scroll_bottom': {
          const currentPath = typeof window !== 'undefined' ? window.location.pathname : '';
          return state.scrollBottomPages.has(currentPath);
        }

        case 'exit_intent':
          return false; // handled separately via mouseout event

        case 'geo_question':
          return false; // handled via chat context

        default:
          return false;
      }
    },
  } as Trigger;
}

const ALL_BUILT_TRIGGERS = ALL_TRIGGERS.map(buildTrigger);

export class TriggerEngine {
  private tracker: SessionTracker;
  private weights: Record<string, { weight: number; total_fires: number }> = {};
  private weightsCacheMs: number = 0;
  private readonly WEIGHTS_CACHE_TTL = 60_000; // 60s

  constructor(tracker: SessionTracker) {
    this.tracker = tracker;
  }

  /** Fetch latest weights from backend (cached) */
  async refreshWeights(): Promise<void> {
    if (Date.now() - this.weightsCacheMs < this.WEIGHTS_CACHE_TTL) return;
    try {
      const res = await fetch('/api/charon/weights');
      if (res.ok) {
        const data = await res.json();
        this.weights = data.weights ?? {};
        this.weightsCacheMs = Date.now();
        // Update trigger weights
        for (const t of ALL_BUILT_TRIGGERS) {
          const w = this.weights[t.id];
          if (w) {
            t.weight = w.weight;
            t.score = t.baseScore * t.weight;
          }
        }
      }
    } catch {
      // Silently fail — use cached/default weights
    }
  }

  /** Evaluate all triggers and return the best eligible one */
  evaluate(currentPath: string): Trigger | null {
    const state = this.tracker.getState();
    const candidates: Trigger[] = [];

    for (const t of ALL_BUILT_TRIGGERS) {
      if (!this.tracker.canFire(t.id, t.cooldownMs)) continue;
      if (!t.evaluate(state, this.tracker)) continue;
      candidates.push(t);
    }

    if (candidates.length === 0) return null;

    // Pick highest score
    candidates.sort((a, b) => b.score - a.score);
    return candidates[0];
  }

  /** Get the full trigger list (for reference/debugging) */
  getAllTriggers(): Trigger[] {
    return ALL_BUILT_TRIGGERS;
  }
}
```

---

### Task F3: Integrate SessionTracker + TriggerEngine into ChatWidget

**Files:**
- Modify: `frontend/src/components/ChatWidget.tsx`

**Step 1: Add imports and instantiate tracker + engine**

Add near the top of `ChatWidget`:
```typescript
import { SessionTracker } from '@/lib/SessionTracker';
import { TriggerEngine } from '@/lib/TriggerEngine';

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  // ... existing state ...

  // Singleton tracker — lives for the full session
  const trackerRef = useRef<SessionTracker | null>(null);
  const engineRef = useRef<TriggerEngine | null>(null);
  const [currentTrigger, setCurrentTrigger] = useState<{ id: string; message: string } | null>(null);
  const [showTriggerBubble, setShowTriggerBubble] = useState(false);
  const triggerIgnoreTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
```

**Step 2: Initialize tracker and engine on mount**

Add useEffect after existing effects:
```typescript
useEffect(() => {
  if (!trackerRef.current) {
    trackerRef.current = new SessionTracker();
    trackerRef.current.start();
    engineRef.current = new TriggerEngine(trackerRef.current);
  }
}, []);
```

**Step 3: Track page visits**

Add a router-change listener. In the main ChatWidget component, add a useEffect that listens to Next.js router:
```typescript
import { usePathname } from 'next/navigation';

export default function ChatWidget() {
  const pathname = usePathname();
  // ... after tracker init effect:
  useEffect(() => {
    trackerRef.current?.onPageVisit(pathname);
    // Reset trigger bubble on navigation
    setShowTriggerBubble(false);
    setCurrentTrigger(null);
  }, [pathname]);
```

**Step 4: Run TriggerEngine evaluation loop (every 5s)**

```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    if (!engineRef.current || !trackerRef.current) return;
    if (isOpen) return; // don't intrude while chat is open

    await engineRef.current.refreshWeights();
    const trigger = engineRef.current.evaluate(pathname);
    if (trigger) {
      setCurrentTrigger({ id: trigger.id, message: trigger.message });
      setShowTriggerBubble(true);
      trackerRef.current.markTriggerFired(trigger.id);

      // Auto-dismiss after 8s if ignored
      triggerIgnoreTimerRef.current = setTimeout(() => {
        setShowTriggerBubble(false);
        void reportOutcome(trigger.id, 'ignored');
      }, 8000);
    }
  }, 5000);

  return () => clearInterval(interval);
}, [isOpen, pathname]);
```

**Step 5: Add reportOutcome helper (fires to backend)**

```typescript
const reportOutcome = async (triggerId: string, outcome: string) => {
  const sessionId = sessionStorage.getItem('charon_session_id') ?? (() => {
    const id = 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem('charon_session_id', id);
    return id;
  })();
  try {
    await fetch('/api/charon/trigger-event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, trigger_id: triggerId, outcome }),
    });
  } catch {
    // silent — never block UX for analytics
  }
};
```

**Step 6: Add scroll-bottom tracking**

```typescript
useEffect(() => {
  const onScroll = () => {
    const scrolled = window.scrollY + window.innerHeight;
    const total = document.documentElement.scrollHeight;
    if (scrolled >= total - 100) {
      trackerRef.current?.onScrollBottom(pathname);
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  return () => window.removeEventListener('scroll', onScroll);
}, [pathname]);
```

**Step 7: Update reach-out bubble to show trigger message**

Modify the `{showReachOut && ...}` bubble to use `currentTrigger?.message`:

```typescript
{showReachOut && (
  <button
    onClick={() => {
      setShowReachOut(false);
      setIsOpen(true);
      if (currentTrigger) void reportOutcome(currentTrigger.id, 'opened_chat');
    }}
    className="fixed z-[9997] animate-reach-out"
    style={reachOutStyle}
  >
    <div className="relative flex items-center gap-2 pl-3 pr-4 py-2.5 ...">
      ...
      <div className="text-left">
        <p className="text-xs font-bold leading-tight">Charon here</p>
        <p className="text-[10px] text-[var(--muted)] leading-tight mt-0.5">
          {currentTrigger?.message ?? "Need help with your proxy? I'm online."}
        </p>
      </div>
      ...
    </div>
  </button>
)}
```

Also update the dismiss handler:
```typescript
onClick={e => {
  e.stopPropagation();
  setShowReachOut(false);
  if (currentTrigger) {
    trackerRef.current?.dismissTrigger(currentTrigger.id);
    void reportOutcome(currentTrigger.id, 'dismissed');
  }
  sessionStorage.setItem('charon_reachout_dismissed', '1');
}}
```

**Step 8: Add exit-intent detection (desktop)**

```typescript
useEffect(() => {
  if (typeof window === 'undefined') return;
  const onMouseOut = (e: MouseEvent) => {
    if (e.clientY <= 0 && !isOpen && engineRef.current && trackerRef.current) {
      const trigger = engineRef.current.evaluate(window.location.pathname);
      if (trigger?.id === 'exit_intent' && trackerRef.current.canFire('exit_intent')) {
        setCurrentTrigger({ id: trigger.id, message: trigger.message });
        setShowReachOut(true);
        trackerRef.current.markTriggerFired('exit_intent');
      }
    }
  };
  document.addEventListener('mouseout', onMouseOut);
  return () => document.removeEventListener('mouseout', onMouseOut);
}, [isOpen]);
```

**Step 9: Attach last trigger to chat messages**

In `sendMessage`, pass the current trigger ID:
```typescript
body: JSON.stringify({
  channel: 'web',
  conversation_id: undefined,
  user_message: trimmed,
  history,
  trigger_id: currentTrigger?.id, // attach context for Charon
}),
```

---

### Task F4: Wire up conversion webhook on order fulfillment

**Files:**
- Modify: `backend/app/routers/orders.py`

**Step 1: After order fulfillment, fire conversion event**

In the `fulfill_order` function (or wherever `status = 'fulfilled'` is set), add at the end:

```python
# Fire conversion event
try:
    session_id = order.get("session_id") or ""
    last_trigger = order.get("last_trigger_id") or ""
    if session_id and last_trigger:
        import httpx
        httpx.post(
            f"{os.environ.get('PUBLIC_URL', 'http://localhost:8000')}/api/charon/trigger-event",
            json={"session_id": session_id, "trigger_id": last_trigger, "outcome": "converted"},
            timeout=5,
        )
except Exception:
    pass  # never block fulfillment for analytics
```

Also update the orders table schema to include `session_id` and `last_trigger_id` columns (add via migration).

---

### Task F5: Add `/api/charon/weights` frontend route handler

**Files:**
- Create: `frontend/src/app/api/charon/weights/route.ts`

Since the frontend proxies to the backend Railway URL for this endpoint:
```typescript
// frontend/src/app/api/charon/weights/route.ts
import { NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://api.styxproxy.com';

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/charon/weights`, {
      next: { revalidate: 60 }, // cache 60s
    });
    if (!res.ok) return NextResponse.json({ weights: {} });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ weights: {} });
  }
}
```

Also create `frontend/src/app/api/charon/trigger-event/route.ts`:
```typescript
import { NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://api.styxproxy.com';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${API_BASE}/api/charon/trigger-event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ ok: false });
  }
}
```

---

## VERIFICATION CHECKLIST

After all tasks complete:

1. `curl http://localhost:8000/api/charon/weights` → returns weights object
2. `curl -X POST http://localhost:8000/api/charon/trigger-event -d '{"session_id":"t","trigger_id":"repeat_pricing","outcome":"opened_chat"}'` → `{"ok": true}`
3. Postgres: `SELECT * FROM trigger_events` → row inserted
4. Postgres: `SELECT * FROM trigger_weights` → all 9 triggers, weight = 1.0
5. Browser: visit `/pricing` twice → after 6s, reach-out bubble appears with "Still comparing plans?" message
6. Browser: dismiss bubble → dismissed for session, no re-fire
7. Browser: open chat from trigger → trigger marked as `opened_chat` in backend
8. `python backend/scripts/update_trigger_weights.py` → runs without error, prints weight changes

---

## FILES SUMMARY

| Action | File |
|---|---|
| Create | `backend/migrations/0003_trigger_tables.sql` |
| Create | `backend/app/models/triggers.py` |
| Modify | `backend/app/models/__init__.py` |
| Create | `backend/app/routers/charon_triggers.py` |
| Modify | `backend/app/main.py` |
| Create | `backend/scripts/update_trigger_weights.py` |
| Create | `frontend/src/lib/SessionTracker.ts` |
| Create | `frontend/src/lib/TriggerEngine.ts` |
| Modify | `frontend/src/components/ChatWidget.tsx` |
| Create | `frontend/src/app/api/charon/weights/route.ts` |
| Create | `frontend/src/app/api/charon/trigger-event/route.ts` |
| Modify | `backend/app/routers/orders.py` (conversion webhook) |
| Modify | `docs/superpowers/specs/2026-07-15-charon-behavioral-awareness.md` (committed already) |
