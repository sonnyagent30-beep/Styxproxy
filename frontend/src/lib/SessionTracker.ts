/**
 * SessionTracker — anonymous, session-level behavior tracking for Charon.
 *
 * All data stays in sessionStorage + memory. No PII, no cookies, no cross-session tracking.
 * Session IDs are random, non-sequential, and expire when the browser tab closes.
 *
 * Pages tracked: pricing, products, order flow, cart.
 * NOT tracked: payment/checkout pages (customer is in a transaction — no outreach).
 */

const PRICING_PAGES = ['/pricing', '/how-it-works', '/'];
const PAYMENT_PAGES = ['/order', '/thank-you', '/preview', '/receipt'];
const PRODUCT_PAGES = ['/products', '/residential', '/mobile', '/isp', '/datacenter'];

export class SessionTracker {
  private sessionId: string;
  private pages: { url: string; visitedAt: number }[] = [];
  private pricingVisits = 0;
  private productVisits = 0;
  private cartActive = false;
  private firstVisitAt = 0;
  private lastActiveAt = 0;
  private scrollBottomFired = false;
  private orderAndPricingVisited = false; // visited /order AND /pricing in same session
  private firedTriggers = new Map<string, number>(); // trigger_id → last fired timestamp

  constructor() {
    this.sessionId = this.getOrCreateSessionId();
    this.firstVisitAt = Date.now();
    this.lastActiveAt = Date.now();
  }

  private getOrCreateSessionId(): string {
    const key = 'charon_session_id';
    let id = sessionStorage.getItem(key);
    if (!id) {
      id = 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      sessionStorage.setItem(key, id);
    }
    return id;
  }

  getSessionId(): string {
    return this.sessionId;
  }

  /** Record a page visit. Call on every navigation. */
  onPageVisit(url: string): void {
    const now = Date.now();
    this.lastActiveAt = now;

    // Always track pages for session_stuck
    this.pages.push({ url, visitedAt: now });

    const path = url.split('?')[0].split('#')[0];

    if (PRICING_PAGES.includes(path)) {
      this.pricingVisits++;
    }

    if (PRODUCT_PAGES.includes(path)) {
      this.productVisits++;
    }

    if (path === '/order') {
      this.cartActive = true;
    }

    // Detect order+pricing in same session
    if (path === '/order' && this.pricingVisits > 0) {
      this.orderAndPricingVisited = true;
    }
    if (path === '/pricing' && this.cartActive) {
      this.orderAndPricingVisited = true;
    }
  }

  /** Record cart add. */
  onCartAdd(): void {
    this.cartActive = true;
    this.lastActiveAt = Date.now();
  }

  /** Record cart clear/remove. */
  onCartClear(): void {
    this.cartActive = false;
  }

  /** Record scroll to bottom of a page. Fires once per page visit. */
  onScrollBottom(url: string): void {
    if (!this.scrollBottomFired) {
      this.scrollBottomFired = true;
      this.lastActiveAt = Date.now();
    }
  }

  resetScrollBottom(): void {
    this.scrollBottomFired = false;
  }

  /** Mark that a trigger has fired. Prevents immediate re-fire on same trigger. */
  markTriggerFired(triggerId: string): void {
    this.firedTriggers.set(triggerId, Date.now());
  }

  /** Check if a trigger can fire (cooldown elapsed). */
  canFire(triggerId: string, cooldownMs: number): boolean {
    const lastFired = this.firedTriggers.get(triggerId);
    if (lastFired === undefined) return true;
    return Date.now() - lastFired > cooldownMs;
  }

  /** Dismiss a trigger — marks it as fired so it won't re-fire until cooldown. */
  dismissTrigger(triggerId: string): void {
    this.firedTriggers.set(triggerId, Date.now());
  }

  /** Total active time in ms since first visit. */
  getActiveTimeMs(): number {
    return this.lastActiveAt - this.firstVisitAt;
  }

  /** Number of unique pages visited this session. */
  getPageCount(): number {
    const unique = new Set(this.pages.map((p: { url: string }) => p.url.split('?')[0].split('#')[0]));
    return unique.size;
  }

  /** Time in ms since the last page visit. */
  getTimeSinceLastPage(): number {
    if (this.pages.length === 0) return 0;
    return Date.now() - this.pages[this.pages.length - 1].visitedAt;
  }

  /** Seconds on current page (based on last visit timestamp). */
  getDwellTimeSeconds(url: string): number {
    const last = [...this.pages].reverse().find((p: { url: string }) => p.url.startsWith(url));
    if (!last) return 0;
    return Math.floor((Date.now() - last.visitedAt) / 1000);
  }

  isOnPaymentPage(): boolean {
    if (typeof window === 'undefined') return false;
    const path = window.location.pathname.split('?')[0].split('#')[0];
    return PAYMENT_PAGES.includes(path);
  }
}
