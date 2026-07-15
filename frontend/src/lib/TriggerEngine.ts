/**
 * TriggerEngine — evaluates behavioral triggers and returns the best candidate.
 *
 * Loads weights from the backend (/api/charon/weights), caches them for 60s,
 * then evaluates all trigger conditions against the session state.
 * Returns the highest-scoring eligible trigger, or null.
 */

import { SessionTracker } from './SessionTracker';

export interface Trigger {
  id: string;
  message: string;
  baseScore: number;  // unweighted score
  weight: number;     // from backend
  score: number;      // baseScore × weight
  cooldownMs: number;
}

export interface TriggerCandidate {
  trigger: Trigger;
  eligible: boolean;
  reason: string;
}

const ALL_TRIGGERS: Omit<Trigger, 'weight' | 'score'>[] = [
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

function evaluateCondition(
  triggerId: string,
  state: ReturnType<SessionTracker['getState']>,
  currentPath: string,
  currentPageDwell: number,
): boolean {
  switch (triggerId) {
    case 'repeat_pricing':
      return state.pagesVisited.filter(p => p === '/pricing').length >= 2;

    case 'pricing_dwell':
      return currentPath === '/pricing' && currentPageDwell > 25;

    case 'product_browse':
      return state.visitedProductCount >= 3;

    case 'cart_abandon':
      return state.cartPresent;

    case 'order_confusion':
      return (
        state.pagesVisited.includes('/order') &&
        state.pagesVisited.includes('/pricing')
      );

    case 'session_stuck':
      return (
        state.pagesVisited.length >= 5 &&
        state.totalActiveTime > 180
      );

    case 'scroll_bottom':
      return state.scrollBottomPages.includes(currentPath);

    case 'exit_intent':
      // Exit intent is handled via a separate mouseout listener
      // Here we just return false — it won't be picked by the engine
      return false;

    case 'geo_question':
      // Geo question is triggered by chat context, not by page behavior
      return false;

    default:
      return false;
  }
}

export class TriggerEngine {
  private tracker: SessionTracker;
  private weights: Record<string, { weight: number; total_fires: number }> = {};
  private weightsCacheMs = 0;
  private readonly WEIGHTS_CACHE_TTL = 60_000; // 60 seconds

  constructor(tracker: SessionTracker) {
    this.tracker = tracker;
  }

  /** Fetch latest weights from backend. Cached. Silently fails on error. */
  async refreshWeights(): Promise<void> {
    if (Date.now() - this.weightsCacheMs < this.WEIGHTS_CACHE_TTL) return;
    try {
      const res = await fetch('/api/charon/weights');
      if (!res.ok) return;
      const data = await res.json();
      this.weights = data.weights ?? {};
      this.weightsCacheMs = Date.now();
    } catch {
      // Network error — use cached/default weights
    }
  }

  /**
   * Evaluate all triggers and return the highest-scoring eligible one.
   * Returns null if no trigger qualifies.
   */
  evaluate(currentPath: string): Trigger | null {
    const state = this.tracker.getState();
    const currentDwell = this.tracker.currentPageDwell();

    const candidates: Trigger[] = [];

    for (const t of ALL_TRIGGERS) {
      const weight = this.weights[t.id]?.weight ?? 1.0;
      const score = t.baseScore * weight;

      const eligible = evaluateCondition(t.id, state, currentPath, currentDwell);
      if (!eligible) continue;

      if (!this.tracker.canFire(t.id, t.cooldownMs)) continue;

      candidates.push({ ...t, weight, score });
    }

    if (candidates.length === 0) return null;

    // Pick the highest score
    candidates.sort((a, b) => b.score - a.score);
    return candidates[0];
  }

  /**
   * Evaluate all triggers and return debug info for each.
   * Useful for building the dashboard or debugging.
   */
  evaluateAll(currentPath: string): TriggerCandidate[] {
    const state = this.tracker.getState();
    const currentDwell = this.tracker.currentPageDwell();

    return ALL_TRIGGERS.map(t => {
      const weight = this.weights[t.id]?.weight ?? 1.0;
      const score = t.baseScore * weight;
      const eligible = evaluateCondition(t.id, state, currentPath, currentDwell);
      const canFire = this.tracker.canFire(t.id, t.cooldownMs);

      let reason = '';
      if (!eligible) {
        reason = `condition not met (score=${score.toFixed(2)}, weight=${weight})`;
      } else if (!canFire) {
        reason = `blocked by cooldown or dismissal`;
      }

      return {
        trigger: { ...t, weight, score },
        eligible: eligible && canFire,
        reason,
      };
    });
  }

  /** Get all trigger definitions (for reference). */
  getAllTriggers(): Omit<Trigger, 'weight' | 'score'>[] {
    return ALL_TRIGGERS;
  }

  /** Force clear the weights cache. */
  clearCache(): void {
    this.weightsCacheMs = 0;
    this.weights = {};
  }
}
