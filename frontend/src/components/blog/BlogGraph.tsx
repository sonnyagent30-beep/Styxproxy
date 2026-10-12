'use client';

/**
 * BlogGraph — SVG node graph that hydrates OVER the server-rendered list.
 *
 * The list is the source of truth for the DOM: it is server-rendered with real
 * `<a href>` links, crawlable and usable with JS off. This component is a
 * PRESENTATION layer shown on top of it when JS is available. It is never a
 * replacement for the links.
 *
 * Accessibility contract:
 *   - Container is `role="group"`, NOT `role="img"`. `role="img"` makes an
 *     element a LEAF in the accessibility tree, which would hide every one of
 *     the node links inside it — the opposite of the intent.
 *   - Every node is a real `<a href>`, so it is focusable and activatable.
 *   - Edges are `aria-hidden` decoration.
 *   - The graph is only ever shown when motion is acceptable; otherwise the
 *     caller keeps the list.
 *
 * No canvas, no WebGL: SVG keeps the DOM inspectable and the links real.
 */

import { useMemo, useState } from 'react';
import type { BlogCategory, BlogPost } from '@/types';
import { buildGraph, GRAPH_WIDTH, GRAPH_HEIGHT } from '@/lib/blog-graph';
import { routeColorVars } from '@/lib/blog-routes';

interface BlogGraphProps {
  posts: BlogPost[];
  categories: BlogCategory[];
}

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

export default function BlogGraph({ posts, categories }: BlogGraphProps) {
  const graph = useMemo(() => buildGraph(posts, categories), [posts, categories]);
  const [activeRoute, setActiveRoute] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const dimmed = (routeSlug: string) => activeRoute !== null && activeRoute !== routeSlug;

  return (
    <div className="max-w-6xl mx-auto px-6 pb-24">
      {/* Route filter — real buttons, keyboard reachable */}
      <div className="flex flex-wrap items-center gap-2 mb-6" role="group" aria-label="Filter graph by route">
        <button
          type="button"
          onClick={() => setActiveRoute(null)}
          aria-pressed={activeRoute === null}
          className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors ${
            activeRoute === null
              ? 'bg-[var(--primary)] text-black font-bold'
              : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]'
          }`}
        >
          All routes
        </button>
        {graph.routes.map((r) => (
          <button
            key={r.slug}
            type="button"
            onClick={() => setActiveRoute(activeRoute === r.slug ? null : r.slug)}
            aria-pressed={activeRoute === r.slug}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors ${
              activeRoute === r.slug
                ? 'bg-[var(--primary)] text-black font-bold'
                : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]'
            }`}
          >
            {r.color && <span aria-hidden="true" className="route-marker w-2 h-2 rounded-full" style={routeColorVars(r.slug, r.color)} />}
            {r.name}
            <span className="opacity-60">{r.count}</span>
          </button>
        ))}
      </div>

      {/* role="group", not "img" — the node links must stay in the a11y tree */}
      <div
        role="group"
        aria-label={`Blog network: ${graph.nodes.length} posts across ${graph.routes.length} routes. Each post is a link.`}
        className="relative w-full overflow-x-auto"
      >
        <svg
          viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`}
          className="w-full h-auto min-w-[720px]"
          style={{ maxHeight: 640 }}
        >
          {/* Route cluster halos + labels */}
          {graph.routes.map((r) => (
            <g key={`route-${r.slug}`} opacity={dimmed(r.slug) ? 0.18 : 1} className="transition-opacity duration-300">
              <circle cx={r.x} cy={r.y} r={112} fill="var(--route-halo, rgba(10,210,90,0.04))" />
              <text
                x={r.x}
                y={r.y - 128}
                textAnchor="middle"
                className="fill-[var(--muted)]"
                style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase' }}
              >
                {r.name}
              </text>
            </g>
          ))}

          {/* Edges — decoration only */}
          <g aria-hidden="true">
            {graph.edges.map((e) => {
              const dim = dimmed(e.from.split(':')[0]);
              const hot = hovered === e.from || hovered === e.to;
              return (
                <line
                  key={`${e.from}->${e.to}`}
                  x1={e.x1}
                  y1={e.y1}
                  x2={e.x2}
                  y2={e.y2}
                  stroke="var(--primary)"
                  strokeWidth={hot ? 1.6 : 1}
                  opacity={dim ? 0.06 : hot ? 0.6 : 0.2}
                  className="transition-opacity duration-300"
                />
              );
            })}
          </g>

          {/* Nodes — every one a real link */}
          {graph.nodes.map((n) => {
            const r = 9;
            const shape = SHAPE_PATH[n.shape] ?? SHAPE_PATH.circle;
            const isDim = dimmed(n.routeSlug);
            const isHot = hovered === n.slug;
            return (
              <a
                key={n.slug}
                href={`/blog/${n.slug}`}
                onMouseEnter={() => setHovered(n.slug)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(n.slug)}
                onBlur={() => setHovered(null)}
                opacity={isDim ? 0.15 : 1}
                className="transition-opacity duration-300 outline-none"
              >
                <title>{`${n.title} — ${n.routeName}, ${n.readMinutes} min read`}</title>
                <path
                  d={shape(n.x, n.y, isHot ? r * 1.7 : r)}
                  fill={n.routeColor || 'var(--primary)'}
                  className="route-node transition-all duration-200"
                  style={routeColorVars(n.routeSlug, n.routeColor)}
                />
                {/* Generous invisible hit area so 9px nodes are clickable */}
                <circle cx={n.x} cy={n.y} r={16} fill="transparent" />
              </a>
            );
          })}
        </svg>
      </div>

      <p className="text-xs text-[var(--muted)] mt-4 text-center">
        {graph.nodes.length} posts · {graph.edges.length} tag connections · each node links to its post
      </p>
    </div>
  );
}
