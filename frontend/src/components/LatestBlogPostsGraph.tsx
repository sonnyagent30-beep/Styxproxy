'use client';

/**
 * LatestBlogPostsGraph — homepage blog teaser with server-rendered list + SVG overlay.
 *
 * ARCHITECTURE (per spec + ssr-progressive-enhancement reference):
 *   - Server renders a real `<ul><li><a href="/blog/{slug}">` list of the latest 6 posts.
 *     This is the crawlable layer — Google indexes these links, not React state.
 *   - On desktop (≥640px) with no prefers-reduced-motion, a 3x2 SVG node grid hydrates
 *     over the list as a presentation layer. The list stays in the DOM (hidden with CSS).
 *   - On mobile (<640px) or with prefers-reduced-motion, the static list is shown.
 *   - View switching is resolved in useEffect, never during render (hydration-safe).
 *
 * ACCESSIBILITY:
 *   - role="group" on the container (NOT role="img" — that would hide all child links).
 *   - Every node is a real `<a href>`, focusable and activatable.
 *   - aria-hidden="true" on decorative SVG shapes.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { BlogCategory, BlogPost } from '@/types';
import { ROUTE_SHAPE } from '@/lib/blog-graph';
import { routeColorVars } from '@/lib/blog-routes';
import { api } from '@/lib/api';

interface Props {
  initialPosts?: BlogPost[];
  categories?: BlogCategory[];
}

/** Deterministic shape paths — pure functions, no randomness. */
const SHAPE_PATH: Record<string, (x: number, y: number, r: number) => string> = {
  circle: (x, y, r) => `M ${x - r} ${y} a ${r} ${r} 0 1 0 ${r * 2} 0 a ${r} ${r} 0 1 0 ${-r * 2} 0`,
  square: (x, y, r) => `M ${x - r} ${y - r} h ${r * 2} v ${r * 2} h ${-r * 2} Z`,
  diamond: (x, y, r) => `M ${x} ${y - r * 1.2} L ${x + r * 1.2} ${y} L ${x} ${y + r * 1.2} L ${x - r * 1.2} ${y} Z`,
  triangle: (x, y, r) =>
    `M ${x} ${y - r * 1.25} L ${x + r * 1.15} ${y + r * 0.85} L ${x - r * 1.15} ${y + r * 0.85} Z`,
  hexagon: (x, y, r) => {
    const pts = Array.from({ length: 6 }, (_, i) => {
      const a = (i / 6) * Math.PI * 2 - Math.PI / 2;
      return `${x + Math.cos(a) * r},${y + Math.sin(a) * r}`;
    });
    return `M ${pts.join(' L ')} Z`;
  },
};

export default function LatestBlogPostsGraph({ initialPosts = [], categories = [] }: Props) {
  const [posts, setPosts] = useState<BlogPost[]>(initialPosts);
  const [loading, setLoading] = useState(!initialPosts.length);
  const [showGraph, setShowGraph] = useState(false);

  // Client-side fetch only when server didn't provide posts
  useEffect(() => {
    if (initialPosts.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const result = await api.getBlogPosts(1, 6);
        if (!cancelled && result.data?.posts) {
          setPosts(result.data.posts);
        }
      } catch {
        // render nothing on error
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [initialPosts]);

  // Resolve view AFTER mount — never during render
  useEffect(() => {
    try {
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const isNarrow = window.matchMedia('(max-width: 640px)').matches;
      setShowGraph(!reduceMotion && !isNarrow);
    } catch {
      setShowGraph(false);
    }
  }, []);

  if (loading) {
    return (
      <section className="py-16 sm:py-24 lg:py-32 px-6 bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="rounded-2xl bg-[var(--card)] border border-[var(--border)] overflow-hidden animate-pulse">
                <div className="aspect-[16/9] bg-[var(--surface)]" />
                <div className="p-5 space-y-3">
                  <div className="h-3 w-16 bg-[var(--surface)] rounded" />
                  <div className="h-4 w-full bg-[var(--surface)] rounded" />
                  <div className="h-4 w-2/3 bg-[var(--surface)] rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (!posts || posts.length === 0) return null;

  return (
    <section className="py-16 sm:py-24 lg:py-32 px-6 bg-[var(--surface)]">
      <div className="max-w-6xl mx-auto">
        <div className="mb-12">
          <p className="text-base font-medium tracking-[0.3em] uppercase text-[var(--primary-text)] mb-3">
            Latest from the blog
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
            Notes from the<br />
            <span className="text-[var(--muted)]">trenches.</span>
          </h2>
        </div>

        {/* Server-rendered list — crawlable, stays in DOM even when graph is shown */}
        <div hidden={showGraph}>
          <ul className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {posts.slice(0, 6).map((post) => (
              <li key={post.id}>
                <Link
                  href={`/blog/${post.slug}`}
                  className="py-3 block group"
                >
                  <h3 className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--primary-text)] transition-colors line-clamp-1">
                    {post.title}
                  </h3>
                  {post.excerpt && (
                    <p className="text-xs text-[var(--muted)] line-clamp-1 mt-0.5">
                      {post.excerpt}
                    </p>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Graph overlay — 3x2 grid of nodes, desktop only */}
        {showGraph && (
          <div
            role="group"
            aria-label={`Latest ${Math.min(posts.length, 6)} blog posts. Each node links to its post.`}
            className="grid grid-cols-3 gap-4"
          >
            {posts.slice(0, 6).map((post) => {
              const cat = post.categories?.[0];
              const shape = ROUTE_SHAPE[cat?.slug ?? ''] ?? 'circle';
              const slug = cat?.slug ?? '';
              const color = cat?.color;
              return (
                <Link
                  key={post.slug}
                  href={`/blog/${post.slug}`}
                  className="flex flex-col items-center gap-2 p-4 rounded-xl hover:bg-[var(--card)] transition-colors"
                >
                  <svg viewBox="0 0 24 24" className="route-dot w-8 h-8" aria-hidden="true">
                    <path
                      d={SHAPE_PATH[shape](12, 12, 9)}
                      className="route-node"
                      style={routeColorVars(slug, color)}
                    />
                  </svg>
                  <span className="text-[var(--muted)] text-[11px] text-center leading-tight line-clamp-2 w-full">
                    {post.title}
                  </span>
                </Link>
              );
            })}
          </div>
        )}

        <div className="mt-10 text-center">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm font-bold text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
          >
            View all blog posts
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 256 256"><path d="M221.66,133.66l-72,72a8,8,0,0,1-11.32-11.32L196.69,136H40a8,8,0,0,1,0-16H196.69L138.34,61.66a8,8,0,0,1,11.32-11.32l72,72A8,8,0,0,1,221.66,133.66Z" /></svg>
          </Link>
        </div>
      </div>
    </section>
  );
}
