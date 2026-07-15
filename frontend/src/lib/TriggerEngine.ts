/**
 * TriggerEngine — evaluates behavioral triggers and returns the best candidate.
 *
 * Loads weights from the backend (/api/charon/weights), caches them for 60s,
 * then evaluates all trigger conditions against the current SessionTracker state.
 * Returns the highest-scoring eligible trigger, or null if nothing qualifies.
 *
 * Outreach is NEVER shown on payment/checkout pages — the customer is in a
 * transaction and must not be interrupted until they initiate contact.
 */

import { SessionTracker } from './SessionTracker';

export interface Trigger {
  id: string;
  message: string;
  cooldownMs: number;
  score: number;   // base score × backend weight
  reason: string;  // human-readable reason (for debug/logging)
}

interface TriggerConfig {
  id: string;
  message: string;
  cooldownMs: number;
  baseScore: number;
  check(s: SessionTracker): boolean;
  reason(s: SessionTracker): string;
}

const ALL_TRIGGERS: TriggerConfig[] = [
  {
    id: 'repeat_pricing',
    message: "I've noticed you've been comparing plans — want help picking the right proxy for your use case?",
    cooldownMs: 5 * 60 * 1000, // 5 min
    baseScore: 1.0,
    check(s) { return s.getDwellTimeSeconds('/') >= 0 && s.getDwellTimeSeconds('/pricing') >= 0 && s['pricingVisits'] >= 2; },
    reason(s) { return `${s['pricingVisits']} pricing page visits`; },
  },
  {
    id: 'pricing_dwell',
    message: "Have questions about our plans? I'm online and ready to help.",
    cooldownMs: 3 * 60 * 1000,
    baseScore: 0.8,
    check(s) { return s.getDwellTimeSeconds('/pricing') > 25; },
    reason(s) { return `>${s.getDwellTimeSeconds('/pricing')}s on pricing page`; },
  },
  {
    id: 'product_browse',
    message: "Looking for something specific? I know our proxy types well — want a recommendation?",
    cooldownMs: 5 * 60 * 1000,
    baseScore: 0.9,
    check(s) { return s['productVisits'] >= 3; },
    reason(s) { return `${s['productVisits']} product page visits`; },
  },
  {
    id: 'cart_abandon',
    message: "Your cart is still waiting — need help completing your order?",
    cooldownMs: 10 * 60 * 1000,
    baseScore: 1.2,
    check(s) { return s['cartActive'] && s.getTimeSinceLastPage() > 30_000; },
    reason(s) { return `cart active, >${Math.round(s.getTimeSinceLastPage() / 1000)}s since last page`; },
  },
  {
    id: 'order_confusion',
    message: "Ready to order? I can walk you through it in 30 seconds — less time than reading another page.",
    cooldownMs: 10 * 60 * 1000,
    baseScore: 1.1,
    check(s) { return s['orderAndPricingVisited']; },
    reason(s) { return 'visited /order and /pricing in same session'; },
  },
  {
    id: 'session_stuck',
    message: "You've been browsing for a while — can I help you find what you're looking for?",
    cooldownMs: 15 * 60 * 1000,
    baseScore: 0.7,
    check(s) {
      return s.getPageCount() >= 5 && s.getActiveTimeMs() > 3 * 60 * 1000;
    },
    reason(s) { return `${s.getPageCount()} pages, ${Math.round(s.getActiveTimeMs() / 60000)}m active`; },
  },
  {
    id: 'scroll_bottom',
    message: "Have questions about what you just read? I can help clarify.",
    cooldownMs: 5 * 60 * 1000,
    baseScore: 0.6,
    check(s) { return s['scrollBottomFired']; },
    reason(s) { return 'scrolled to bottom of a page'; },
  },
  {
    id: 'geo_question',
    message: "Need a proxy from a specific country? I can show you what's available.",
    cooldownMs: 10 * 60 * 1000,
    baseScore: 0.5,
    check() { return false; }, // triggered by LLM chat context only
    reason() { return 'customer asked about a country'; },
  },
];

export class TriggerEngine {
  private tracker: SessionTracker;
  private weights: Map<string, number> = new Map();
  private lastRefresh = 0;
  private readonly CACHE_TTL_MS = 60_000;

  constructor(tracker: SessionTracker) {
    this.tracker = tracker;
    // Default weights — until backend delivers real ones
    for (const t of ALL_TRIGGERS) {
      this.weights.set(t.id, 1.0);
    }
  }

  /** Refresh weights from backend. Cached. */
  async refreshWeights(): Promise<void> {
    if (Date.now() - this.lastRefresh < this.CACHE_TTL_MS) return;
    try {
      const res = await fetch('/api/charon/weights');
      if (!res.ok) return;
      const data = await res.json();
      if (data.weights) {
        for (const [id, info] of Object.entries(data.weights as Record<string, { weight: number }>)) {
          this.weights.set(id, (info as { weight: number }).weight ?? 1.0);
        }
      }
      this.lastRefresh = Date.now();
    } catch {
      // silent — keep using cached/default weights
    }
  }

  /** Evaluate all triggers and return the best eligible one, or null. */
  evaluate(currentPath: string): Trigger | null {
    // NEVER outreach during payment/checkout
    if (this.tracker.isOnPaymentPage()) return null;

    const eligible: Trigger[] = [];

    for (const config of ALL_TRIGGERS) {
      const weight = this.weights.get(config.id) ?? 1.0;
      const score = config.baseScore * weight;

      if (score <= 0) continue; // suppressed by learning
      if (!config.check(this.tracker)) continue;
      if (!this.tracker.canFire(config.id, config.cooldownMs)) continue;

      eligible.push({
        id: config.id,
        message: config.message,
        cooldownMs: config.cooldownMs,
        score,
        reason: config.reason(this.tracker),
      });
    }

    if (eligible.length === 0) return null;

    // Return highest-scoring trigger
    eligible.sort((a, b) => b.score - a.score);
    return eligible[0];
  }
}
