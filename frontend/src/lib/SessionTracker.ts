/**
 * SessionTracker — anonymous, session-level behavior tracking for Charon.
 *
 * All data stays in sessionStorage + memory. No PII, no cookies, no cross-session tracking.
 * Session IDs are random 24-char tokens with zero tie to identity.
 *
 * Tracked:
 *  - pages visited (Set of full paths)
 *  - dwell time per page (accumulated active seconds)
 *  - total active time (seconds, excluding tab-hidden time)
 *  - triggers fired (per-session deduplication)
 *  - cart state (item added/cleared)
 *  - scroll depth (which pages reached bottom)
 *  - product sub-page visits (count)
 */

export interface SessionState {
  pagesVisited: string[];
  pageDwellStart: [string, number][]; // url, timestamp
  totalActiveTime: number; // seconds
  triggersFired: string[];
  lastTriggerFire: number; // ms timestamp
  cartPresent: boolean;
  dismissedTriggers: string[]; // per-session dismissals
  scrollBottomPages: string[];
  visitedProductCount: number;
  productPaths: string[];
}

const STORAGE_KEY = 'charon_session';
const VISITED_PRODUCT_PATHS = [
  '/products/isp',
  '/products/residential',
  '/products/mobile',
  '/products/datacenter',
];

function newState(): SessionState {
  return {
    pagesVisited: [],
    pageDwellStart: [],
    totalActiveTime: 0,
    triggersFired: [],
    lastTriggerFire: 0,
    cartPresent: false,
    dismissedTriggers: [],
    scrollBottomPages: [],
    visitedProductCount: 0,
    productPaths: [],
  };
}

export class SessionTracker {
  private state: SessionState;
  private active = false;
  private tabVisible = true;
  private lastTick = Date.now();
  private tickInterval: ReturnType<typeof setInterval> | null = null;
  private persistInterval: ReturnType<typeof setInterval> | null = null;
  private onDwellChange?: (path: string, dwellSeconds: number) => void;

  constructor() {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    this.state = saved ? this.deserialize(saved) : newState();
  }

  /** Start tracking. Call once when the app mounts. */
  start(): void {
    if (this.active) return;
    this.active = true;
    this.lastTick = Date.now();

    // Accumulate active time every second (only when tab is visible)
    this.tickInterval = setInterval(() => {
      if (this.tabVisible) {
        this.state.totalActiveTime += (Date.now() - this.lastTick) / 1000;
        this.lastTick = Date.now();
        this.persist();
      }
    }, 1000);

    // Tab visibility tracking
    const onVisibility = () => {
      this.tabVisible = document.visibilityState === 'visible';
      if (this.tabVisible) this.lastTick = Date.now();
    };
    document.addEventListener('visibilitychange', onVisibility);

    // Persist every 5s
    this.persistInterval = setInterval(() => this.persist(), 5000);

    // Track initial page
    this.onPageVisit(window.location.pathname);
  }

  /** Stop tracking. Call when component unmounts (if needed). */
  stop(): void {
    if (this.tickInterval) clearInterval(this.tickInterval);
    if (this.persistInterval) clearInterval(this.persistInterval);
    this.active = false;
  }

  /** Register a callback for when dwell time on a page changes significantly. */
  onDwellUpdate(fn: (path: string, dwellSeconds: number) => void): void {
    this.onDwellChange = fn;
  }

  /** Call when user navigates to a new page. */
  onPageVisit(path: string): void {
    // End dwell tracking for previous page
    if (this.state.pageDwellStart.length > 0) {
      const [prevPath, startTime] = this.state.pageDwellStart[this.state.pageDwellStart.length - 1];
      if (prevPath !== path) {
        const dwell = (Date.now() - startTime) / 1000;
        if (this.onDwellChange && dwell > 2) {
          this.onDwellChange(prevPath, dwell);
        }
      }
    }

    // Don't double-count the same path if visited multiple times
    // (we want repeat visits to show as separate)
    this.state.pagesVisited.push(path);
    this.state.pageDwellStart.push([path, Date.now()]);

    // Count product sub-page visits
    if (VISITED_PRODUCT_PATHS.includes(path)) {
      this.state.visitedProductCount += 1;
      if (!this.state.productPaths.includes(path)) {
        this.state.productPaths.push(path);
      }
    }

    this.persist();
  }

  /** Call when user scrolls to the bottom of the current page. */
  onScrollBottom(path: string): void {
    if (!this.state.scrollBottomPages.includes(path)) {
      this.state.scrollBottomPages.push(path);
      this.persist();
    }
  }

  /** Call when user adds an item to cart. */
  onCartAdd(): void {
    this.state.cartPresent = true;
    this.persist();
  }

  /** Call when user removes item from cart or clears cart. */
  onCartClear(): void {
    this.state.cartPresent = false;
    this.persist();
  }

  /** Mark a trigger as fired (won't fire again this session). */
  markTriggerFired(triggerId: string): void {
    if (!this.state.triggersFired.includes(triggerId)) {
      this.state.triggersFired.push(triggerId);
    }
    this.state.lastTriggerFire = Date.now();
    this.persist();
  }

  /** Mark a trigger as dismissed by the user (suppressed for session). */
  dismissTrigger(triggerId: string): void {
    if (!this.state.dismissedTriggers.includes(triggerId)) {
      this.state.dismissedTriggers.push(triggerId);
    }
    // Also mark as fired so it doesn't re-trigger
    if (!this.state.triggersFired.includes(triggerId)) {
      this.state.triggersFired.push(triggerId);
    }
    this.persist();
  }

  /**
   * Check if a trigger can fire.
   * @param triggerId - the trigger ID
   * @param cooldownMs - minimum ms between fires of ANY trigger (global cooldown)
   */
  canFire(triggerId: string, cooldownMs = 60_000): boolean {
    // Already dismissed this session
    if (this.state.dismissedTriggers.includes(triggerId)) return false;
    // Already fired this session
    if (this.state.triggersFired.includes(triggerId)) return false;
    // Global cooldown window
    if (Date.now() - this.state.lastTriggerFire < cooldownMs) return false;
    return true;
  }

  /** Get current dwell time on the current page. */
  currentPageDwell(): number {
    if (this.state.pageDwellStart.length === 0) return 0;
    const [, startTime] = this.state.pageDwellStart[this.state.pageDwellStart.length - 1];
    return (Date.now() - startTime) / 1000;
  }

  /** Get total active time spent on site this session (seconds). */
  totalActiveTime(): number {
    return this.state.totalActiveTime;
  }

  /** Get a read-only snapshot of the current state. */
  getState(): Readonly<SessionState> {
    return { ...this.state };
  }

  /** Check if cart has items. */
  hasCart(): boolean {
    return this.state.cartPresent;
  }

  /** Get how many pages visited. */
  pageCount(): number {
    return this.state.pagesVisited.length;
  }

  /** Check if user visited a specific path (true even on revisit). */
  visitedPath(path: string): number {
    return this.state.pagesVisited.filter(p => p === path).length;
  }

  /** Check if user visited multiple specific paths. */
  visitedPaths(paths: string[]): boolean {
    return paths.every(p => this.state.pagesVisited.includes(p));
  }

  private persist(): void {
    try {
      sessionStorage.setItem(STORAGE_KEY, this.serialize());
    } catch {
      // sessionStorage full — ignore
    }
  }

  private serialize(): string {
    return JSON.stringify(this.state);
  }

  private deserialize(raw: string): SessionState {
    const s = JSON.parse(raw);
    return {
      pagesVisited: Array.isArray(s.pagesVisited) ? s.pagesVisited : [],
      pageDwellStart: Array.isArray(s.pageDwellStart) ? s.pageDwellStart : [],
      totalActiveTime: typeof s.totalActiveTime === 'number' ? s.totalActiveTime : 0,
      triggersFired: Array.isArray(s.triggersFired) ? s.triggersFired : [],
      lastTriggerFire: typeof s.lastTriggerFire === 'number' ? s.lastTriggerFire : 0,
      cartPresent: Boolean(s.cartPresent),
      dismissedTriggers: Array.isArray(s.dismissedTriggers) ? s.dismissedTriggers : [],
      scrollBottomPages: Array.isArray(s.scrollBottomPages) ? s.scrollBottomPages : [],
      visitedProductCount: typeof s.visitedProductCount === 'number' ? s.visitedProductCount : 0,
      productPaths: Array.isArray(s.productPaths) ? s.productPaths : [],
    };
  }
}
