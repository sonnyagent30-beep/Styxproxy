'use client';

/**
 * BlogViews — the view switcher between the server-rendered list and the graph.
 *
 * Both views are passed in as already-rendered React trees:
 *   - `list` is server-rendered (real <a href> in the initial HTML)
 *   - `graph` is the client SVG layer
 *
 * The LIST IS THE DEFAULT and stays in the DOM. The graph is a presentation
 * layer shown on top of it, never a replacement:
 *   - Google crawls the served HTML, so the links must be there regardless of
 *     what a client-side toggle later decides to show.
 *   - With JS disabled this component never hydrates and the list stays visible.
 *   - `prefers-reduced-motion: reduce` forces the list: a force-directed-looking
 *     graph is close to unusable for motion-sensitive users and keyboard users
 *     navigating a 2D layout.
 *
 * Initial state is `list` and is resolved on mount, never during render — a
 * render-time read of localStorage/matchMedia would differ between the server
 * and the client and cause a hydration mismatch.
 */

import { useEffect, useState, type ReactNode } from 'react';

interface BlogViewsProps {
  list: ReactNode;
  graph: ReactNode;
}

type View = 'list' | 'graph';
const STORAGE_KEY = 'styxproxy_blog_view';

export default function BlogViews({ list, graph }: BlogViewsProps) {
  const [view, setView] = useState<View>('list');
  const [ready, setReady] = useState(false);

  // Resolve the preferred view AFTER mount. Reading localStorage or matchMedia
  // during render would produce different markup on server and client.
  useEffect(() => {
    let preferred: View = 'list';
    try {
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const isNarrow = window.matchMedia('(max-width: 640px)').matches;
      const saved = localStorage.getItem(STORAGE_KEY) as View | null;
      if (reduceMotion || isNarrow) {
        // Motion sensitivity and small screens always get the list.
        preferred = 'list';
      } else if (saved === 'graph' || saved === 'list') {
        preferred = saved;
      }
    } catch { /* keep the list */ }
    setView(preferred);
    setReady(true);
  }, []);

  const choose = (next: View) => {
    setView(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* non-fatal */ }
  };

  return (
    <>
      {/* Switcher — hidden until mounted so it cannot disagree with the SSR list */}
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-end gap-2 mb-2" style={{ visibility: ready ? 'visible' : 'hidden' }}>
        <span className="text-xs text-[var(--muted)] mr-1">View</span>
        <button
          type="button"
          onClick={() => choose('list')}
          aria-pressed={view === 'list'}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            view === 'list'
              ? 'bg-[var(--primary)] text-black font-bold'
              : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]'
          }`}
        >
          List
        </button>
        <button
          type="button"
          onClick={() => choose('graph')}
          aria-pressed={view === 'graph'}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            view === 'graph'
              ? 'bg-[var(--primary)] text-black font-bold'
              : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]'
          }`}
        >
          Network
        </button>
      </div>

      {/* The list is rendered by the SERVER and stays in the DOM even when the
          graph is shown — it is the crawlable layer and the no-JS fallback.
          Hiding it with CSS (not unmounting it) keeps the links present. */}
      <div hidden={ready && view === 'graph'}>{list}</div>
      {ready && view === 'graph' && graph}
    </>
  );
}
