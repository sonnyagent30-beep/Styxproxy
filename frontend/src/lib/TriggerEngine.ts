/**
 * TriggerEngine — evaluates behavioral triggers and returns the best candidate.
 *
 * Loads weights from the backend (/api/charon/weights), caches them for 60s,
 * then evaluates all trigger conditions against the current SessionTracker state.
 * Returns the highest-scoring eligible trigger, or null if nothing qualifies.
 *
 * Outreach is NEVER shown on payment/checkout pages — the customer is in a
 * transaction and must not be interrupted until they initiate contact.
 *
 * Page-aware timing:
 * - Landing page: short threshold (15s) — catch interest fast
 * - Pricing page: medium threshold (25s) — they need time to compare
 * - Product pages: medium (20s) — browsing mode
 * - Blog pages: long threshold (45s) — reading mode, don't interrupt
 * - General pages: 30s default
 *
 * Blog-aware: triggers fire differently when user is reading a blog post,
 * surfacing blog-specific outreach + suggesting related posts.
 */

import { SessionTracker } from './SessionTracker';

export interface Trigger {
  id: string;
  message: string;
  cooldownMs: number;
  score: number;
  reason: string;
  /** Override auto-dismiss timeout (ms). Defaults to 8000. */
  dismissAfterMs?: number;
  /** Override initial delay before showing bubble (ms). Defaults to 0. */
  delayMs?: number;
}

interface TriggerConfig {
  id: string;
  message: string;
  cooldownMs: number;
  baseScore: number;
  dismissAfterMs: number;
  /** Default 0ms (show immediately). */
  delayMs?: number;
  check(s: SessionTracker): boolean;
  reason(s: SessionTracker): string;
  /** Override message when user is on a blog post. */
  blogMessage?: (s: SessionTracker) => string;
}

// ── Dwell thresholds per page type (seconds) ────────────────────────────────────

const DWELL = {
  landing: 15,
  pricing: 25,
  product: 20,
  blog: 45,
  how_it_works: 30,
  checkout: 30,
  general: 20,
} as const;

function getDwellForPage(pageType: string): number {
  return DWELL[pageType as keyof typeof DWELL] ?? DWELL.general;
}

// ── All trigger configs ────────────────────────────────────────────────────────

const ALL_TRIGGERS: TriggerConfig[] = [
  {
    id: 'repeat_pricing',
    message: "I've noticed you've been comparing plans — want help picking the right proxy for your use case?",
    blogMessage: (s) =>
      `You've been exploring our pricing alongside "${s.getCurrentBlogPost()?.title ?? 'that guide'}" — want help finding the plan that fits your goal?`,
    cooldownMs: 5 * 60 * 1000,
    baseScore: 1.0,
    dismissAfterMs: 10_000,
    check(s) {
      return s.getDwellTimeSeconds('/pricing') >= 0 && s['pricingVisits'] >= 2;
    },
    reason(s) { return `${s['pricingVisits']} pricing page visits`; },
  },
  {
    id: 'pricing_dwell',
    message: "Have questions about our plans? I'm online and ready to help.",
    cooldownMs: 3 * 60 * 1000,
    baseScore: 0.8,
    dismissAfterMs: 8_000,
    check(s) {
      const dwell = s.getDwellTimeSeconds('/pricing');
      return dwell > getDwellForPage('pricing');
    },
    reason(s) { return `>${s.getDwellTimeSeconds('/pricing')}s on pricing page`; },
  },
  {
    id: 'product_browse',
    message: "Looking for something specific? I know our proxy types well — want a recommendation?",
    blogMessage: (s) => {
      const blog = s.getCurrentBlogPost();
      if (blog) {
        const tag = blog.tags[0] ?? 'proxy';
        return `Our guide covers ${tag} in depth — want a recommendation for your use case?`;
      }
      return "Looking for something specific? I know our proxy types well — want a recommendation?";
    },
    cooldownMs: 5 * 60 * 1000,
    baseScore: 0.9,
    dismissAfterMs: 8_000,
    check(s) { return s['productVisits'] >= 3; },
    reason(s) { return `${s['productVisits']} product page visits`; },
  },
  {
    id: 'cart_abandon',
    message: "Your cart is still waiting — need help completing your order?",
    cooldownMs: 10 * 60 * 1000,
    baseScore: 1.2,
    dismissAfterMs: 12_000,
    check(s) { return s['cartActive'] && s.getTimeSinceLastPage() > 30_000; },
    reason(s) { return `cart active, >${Math.round(s.getTimeSinceLastPage() / 1000)}s since last page`; },
  },
  {
    id: 'order_confusion',
    message: "Ready to order? I can walk you through it in 30 seconds — less time than reading another page.",
    cooldownMs: 10 * 60 * 1000,
    baseScore: 1.1,
    dismissAfterMs: 10_000,
    check(s) { return s['orderAndPricingVisited']; },
    reason(s) { return 'visited /order and /pricing in same session'; },
  },
  {
    id: 'session_stuck',
    message: "You've been browsing for a while — can I help you find what you're looking for?",
    cooldownMs: 15 * 60 * 1000,
    baseScore: 0.7,
    dismissAfterMs: 8_000,
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
    dismissAfterMs: 6_000,
    check(s) { return s['scrollBottomFired']; },
    reason(s) { return 'scrolled to bottom of a page'; },
  },
  {
    id: 'geo_question',
    message: "Need a proxy from a specific country? I can show you what's available.",
    cooldownMs: 10 * 60 * 1000,
    baseScore: 0.5,
    dismissAfterMs: 8_000,
    check() { return false; }, // triggered by LLM chat context only
    reason() { return 'customer asked about a country'; },
  },
  // ── Blog-aware triggers ────────────────────────────────────────────────
  {
    id: 'blog_deep_read',
    message: "Good read? I can answer questions about anything in that article — or suggest the next one.",
    cooldownMs: 8 * 60 * 1000,
    baseScore: 0.85,
    dismissAfterMs: 10_000,
    delayMs: 3_000, // wait 3s after page load before showing
    check(s) {
      const blog = s.getCurrentBlogPost();
      if (!blog) return false;
      // Fire after 45s on any blog post (reading time)
      return s.getDwellTimeSeconds(`/blog/${blog.slug}`) > getDwellForPage('blog');
    },
    reason(s) {
      const blog = s.getCurrentBlogPost();
      return `read "${blog?.title ?? 'blog post'}" for >${getDwellForPage('blog')}s`;
    },
  },
  {
    id: 'blog_related_offer',
    message: "We have a full guide series on this topic — want me to point you to the most relevant one?",
    cooldownMs: 15 * 60 * 1000,
    baseScore: 0.7,
    dismissAfterMs: 10_000,
    delayMs: 5_000,
    check(s) {
      const blog = s.getCurrentBlogPost();
      if (!blog) return false;
      // Fire if they visited 2+ blog posts
      return s['blogVisits'] >= 2;
    },
    reason(s) {
      const blog = s.getCurrentBlogPost();
      return `read "${blog?.title ?? 'blog'}" and visited ${s['blogVisits']} blog posts`;
    },
  },
];

export class TriggerEngine {
  private tracker: SessionTracker;
  private weights: Map<string, number> = new Map();
  private lastRefresh = 0;
  private readonly CACHE_TTL_MS = 60_000;

  constructor(tracker: SessionTracker) {
    this.tracker = tracker;
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
    if (this.tracker.isOnPaymentPage()) return null;

    const eligible: Trigger[] = [];

    for (const config of ALL_TRIGGERS) {
      const weight = this.weights.get(config.id) ?? 1.0;
      const score = config.baseScore * weight;

      if (score <= 0) continue;
      if (!config.check(this.tracker)) continue;
      if (!this.tracker.canFire(config.id, config.cooldownMs)) continue;

      // Pick message: use blog variant if on a blog page and config has one
      const isOnBlog = currentPath.startsWith('/blog');
      const message =
        isOnBlog && config.blogMessage
          ? config.blogMessage(this.tracker)
          : config.message;

      eligible.push({
        id: config.id,
        message,
        cooldownMs: config.cooldownMs,
        score,
        reason: config.reason(this.tracker),
        dismissAfterMs: config.dismissAfterMs,
        delayMs: config.delayMs,
      });
    }

    if (eligible.length === 0) return null;

    eligible.sort((a, b) => b.score - a.score);
    return eligible[0];
  }
}
