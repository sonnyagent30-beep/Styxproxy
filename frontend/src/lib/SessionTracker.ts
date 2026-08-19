/**
 * SessionTracker — anonymous, session-level behavior tracking for Charon.
 *
 * All data stays in sessionStorage + memory. No PII, no cookies, no cross-session tracking.
 * Session IDs are random, non-sequential, and expire when the browser tab closes.
 *
 * Pages tracked: pricing, products, order flow, cart, blog.
 * NOT tracked: payment/checkout pages (customer is in a transaction — no outreach).
 */

import { DEMO_POSTS } from '@/data/blog-posts';

// ── Page taxonomy ──────────────────────────────────────────────────────────────

const PRICING_PAGES = ['/pricing', '/how-it-works', '/'];
const PRODUCT_PAGES = ['/products', '/residential', '/mobile', '/isp', '/datacenter'];
const BLOG_PAGES = ['/blog'];
const PAYMENT_PAGES = ['/order', '/thank-you', '/preview', '/receipt'];

// ── Theme keywords per page — used to give Charon page-level context ─────────

const PAGE_THEMES: Record<string, string[]> = {
  '/': ['landing page', 'proxy overview', 'hero section'],
  '/pricing': ['pricing', 'plan comparison', 'ISP', 'datacenter', 'residential'],
  '/products': ['product catalog', 'proxy types', 'ISP', 'datacenter', 'residential'],
  '/residential': ['residential proxies', 'home IPs', 'real ISPs', 'Nigeria'],
  '/datacenter': ['datacenter proxies', 'cloud servers', 'speed', 'scraping'],
  '/mobile': ['mobile proxies', '4G', 'social media', 'stealth'],
  '/isp': ['ISP proxies', 'static IPs', 'business', 'banking'],
  '/blog': ['blog', 'guides', 'tutorials', 'proxy education'],
  '/how-it-works': ['how it works', 'setup', 'configuration', 'SOCKS5'],
  '/order': ['order form', 'checkout', 'cart'],
};

// ── Blog posts index (built once, reused) ────────────────────────────────────

const BLOG_INDEX = DEMO_POSTS.map(p => ({
  slug: p.slug,
  title: p.title,
  excerpt: p.excerpt,
  tags: p.tags ?? [],
}));

// ── Tracker ───────────────────────────────────────────────────────────────────

export class SessionTracker {
  private sessionId: string;
  private pages: { url: string; visitedAt: number }[] = [];
  // Public properties accessed by TriggerEngine via bracket notation
  pricingVisits = 0;
  productVisits = 0;
  cartActive = false;
  scrollBottomFired = false;
  orderAndPricingVisited = false;
  blogVisits = 0;
  private firstVisitAt = 0;
  private lastActiveAt = 0;
  private firedTriggers = new Map<string, number>();
  private currentBlogSlug = '';
  private currentBlogTags: string[] = [];
  private currentBlogTitle = '';

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

    this.pages.push({ url, visitedAt: now });

    const path = url.split('?')[0].split('#')[0];

    if (PRICING_PAGES.includes(path)) {
      this.pricingVisits++;
    }

    if (PRODUCT_PAGES.includes(path)) {
      this.productVisits++;
    }

    if (BLOG_PAGES.some(b => path === b || path.startsWith(b + '/'))) {
      this.blogVisits++;
      // Try to detect current blog slug from URL
      const slug = this.extractBlogSlug(path);
      if (slug) {
        this.currentBlogSlug = slug;
        const post = BLOG_INDEX.find(p => p.slug === slug);
        if (post) {
          this.currentBlogTitle = post.title;
          this.currentBlogTags = post.tags;
        }
      }
    }

    if (path === '/order') {
      this.cartActive = true;
    }

    if (path === '/order' && this.pricingVisits > 0) {
      this.orderAndPricingVisited = true;
    }
    if (path === '/pricing' && this.cartActive) {
      this.orderAndPricingVisited = true;
    }
  }

  /** Derive blog slug from URL like /blog/web-scraping-nigeria-guide */
  private extractBlogSlug(path: string): string {
    const match = path.match(/^\/blog\/(.+?)(\/|$)/);
    return match ? match[1] : '';
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

  /** Mark that a trigger has fired. Prevents immediate re-fire. */
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
    const unique = new Set(this.pages.map((p) => p.url.split('?')[0].split('#')[0]));
    return unique.size;
  }

  /** Time in ms since the last page visit. */
  getTimeSinceLastPage(): number {
    if (this.pages.length === 0) return 0;
    return Date.now() - this.pages[this.pages.length - 1].visitedAt;
  }

  /** Seconds on current page (based on last visit timestamp). */
  getDwellTimeSeconds(url: string): number {
    const last = [...this.pages].reverse().find((p) => p.url.startsWith(url));
    if (!last) return 0;
    return Math.floor((Date.now() - last.visitedAt) / 1000);
  }

  isOnPaymentPage(): boolean {
    if (typeof window === 'undefined') return false;
    const path = window.location.pathname.split('?')[0].split('#')[0];
    return PAYMENT_PAGES.includes(path);
  }

  /** Returns theme keywords for the current page path. */
  getPageThemes(path: string): string[] {
    const clean = path.split('?')[0].split('#')[0];
    // Blog posts get dynamic tags from the post itself
    if (BLOG_PAGES.some(b => clean === b || clean.startsWith(b + '/'))) {
      if (this.currentBlogTags.length > 0) {
        return [...this.currentBlogTags.map(t => `blog:${t}`), 'blog'];
      }
      return ['blog', 'guides'];
    }
    return PAGE_THEMES[clean] ?? [];
  }

  /** Returns blog post data for the current blog slug (or empty if not on blog). */
  getCurrentBlogPost(): { slug: string; title: string; tags: string[] } | null {
    if (!this.currentBlogSlug) return null;
    return {
      slug: this.currentBlogSlug,
      title: this.currentBlogTitle,
      tags: this.currentBlogTags,
    };
  }

  /** Build the page_context object to send to Charon backend. */
  getPageContext(): Record<string, unknown> {
    if (typeof window === 'undefined') return {};
    const path = window.location.pathname;

    const ctx: Record<string, unknown> = {
      page_type: this.getPageType(path),
      path,
      themes: this.getPageThemes(path),
      session_pages: this.getPageCount(),
      session_duration_s: Math.floor(this.getActiveTimeMs() / 1000),
    };

    // Blog context
    const blog = this.getCurrentBlogPost();
    if (blog) {
      ctx.blog_post = blog;
    }

    // Cart context
    if (this.cartActive) {
      ctx.cart_active = true;
    }

    // Blog index — all posts so Charon can link to them
    ctx.blog_index = BLOG_INDEX;

    return ctx;
  }

  /** Derive a page_type string from a path. */
  private getPageType(path: string): string {
    const clean = path.split('?')[0].split('#')[0];
    if (PAYMENT_PAGES.includes(clean)) return 'payment';
    if (clean === '/pricing' || PRICING_PAGES.includes(clean)) return 'pricing';
    if (PRODUCT_PAGES.includes(clean)) return 'product';
    if (BLOG_PAGES.some(b => clean === b || clean.startsWith(b + '/'))) return 'blog_post';
    if (clean === '/order') return 'checkout';
    if (clean === '/how-it-works') return 'how_it_works';
    return 'general';
  }
}
