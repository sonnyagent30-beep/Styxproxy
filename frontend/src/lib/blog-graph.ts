/**
 * Blog graph geometry — pure, deterministic, server-computed.
 *
 * WHY DETERMINISTIC: the graph is rendered inside a client component, so any
 * randomness or physics simulation would produce different coordinates on the
 * server and on the client and trigger a React hydration mismatch. Every
 * position here is a pure function of the post list, so both renders agree.
 *
 * Layout: five route clusters on a pentagon, posts arranged on a small circle
 * inside their cluster. Route order comes from the API, so the geometry follows
 * the taxonomy rather than a hardcoded list.
 *
 * Edges are SHARED TAGS, not routes. Route decides position; tags decide
 * relatedness — conflating the two produces five disconnected islands. A
 * minimum of 2 shared tags plus a per-node cap keeps this a readable network
 * instead of a hairball once the corpus grows past ~40 posts.
 */

import type { BlogCategory, BlogPost } from '@/types';

/** Route shapes — a second differentiator so the graph survives colour-blindness. */
export const ROUTE_SHAPE: Record<string, 'circle' | 'square' | 'diamond' | 'triangle' | 'hexagon'> = {
  guides: 'circle',
  comparisons: 'diamond',
  'proxy-types': 'square',
  'best-practices': 'triangle',
  nigeria: 'hexagon',
};

export const GRAPH_WIDTH = 1000;
export const GRAPH_HEIGHT = 700;
const CLUSTER_RADIUS = 235;
const NODE_RADIUS = 9;
const MIN_SHARED_TAGS = 2;
const MAX_EDGES_PER_NODE = 3;

export interface GraphNode {
  slug: string;
  title: string;
  routeSlug: string;
  routeName: string;
  routeColor?: string;
  shape: 'circle' | 'square' | 'diamond' | 'triangle' | 'hexagon';
  x: number;
  y: number;
  readMinutes: number;
  date: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  sharedTags: string[];
}

export interface GraphRoute {
  slug: string;
  name: string;
  color?: string;
  shape: 'circle' | 'square' | 'diamond' | 'triangle' | 'hexagon';
  x: number;
  y: number;
  count: number;
}

export interface BlogGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  routes: GraphRoute[];
}

function readMinutes(content?: string): number {
  if (!content) return 1;
  return Math.max(1, Math.round(content.trim().split(/\s+/).length / 200));
}

function formatDate(value?: string): string {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function buildGraph(posts: BlogPost[], categories: BlogCategory[]): BlogGraphData {
  const cx = GRAPH_WIDTH / 2;
  const cy = GRAPH_HEIGHT / 2;

  // Group posts by their first category. Unrouted posts get their own bucket so
  // they stay visible rather than silently vanishing from the graph.
  const buckets = new Map<string, BlogPost[]>();
  const unrouted: BlogPost[] = [];
  for (const p of posts) {
    const cat = p.categories?.[0];
    if (!cat) {
      unrouted.push(p);
      continue;
    }
    const list = buckets.get(cat.slug) ?? [];
    list.push(p);
    buckets.set(cat.slug, list);
  }

  const activeRoutes = categories.filter((c) => (buckets.get(c.slug) ?? []).length > 0);
  // Only render clusters that hold posts; the pentagon re-spaces around them so
  // an empty route does not leave a hole in the layout.
  const routeCount = Math.max(1, activeRoutes.length);

  const routes: GraphRoute[] = [];
  const nodes: GraphNode[] = [];

  activeRoutes.forEach((cat, i) => {
    // Start at -90deg so the first cluster sits at the top, and wrap clockwise.
    const angle = (i / routeCount) * Math.PI * 2 - Math.PI / 2;
    const rx = cx + Math.cos(angle) * CLUSTER_RADIUS;
    const ry = cy + Math.sin(angle) * CLUSTER_RADIUS;
    const shape = ROUTE_SHAPE[cat.slug] ?? 'circle';

    routes.push({
      slug: cat.slug,
      name: cat.name,
      color: cat.color,
      shape,
      x: rx,
      y: ry,
      count: (buckets.get(cat.slug) ?? []).length,
    });

    const routePosts = buckets.get(cat.slug) ?? [];
    // Spread nodes on a ring sized to the cluster so 3 and 8 posts both look
    // intentional instead of a fixed radius that crowds or scatters.
    const innerRadius = Math.min(78, 34 + routePosts.length * 6);

    routePosts.forEach((post, j) => {
      const a = (j / Math.max(1, routePosts.length)) * Math.PI * 2 - Math.PI / 2;
      nodes.push({
        slug: post.slug,
        title: post.title,
        routeSlug: cat.slug,
        routeName: cat.name,
        routeColor: cat.color,
        shape,
        x: Math.round((rx + Math.cos(a) * innerRadius) * 100) / 100,
        y: Math.round((ry + Math.sin(a) * innerRadius) * 100) / 100,
        readMinutes: readMinutes(post.content),
        date: formatDate(post.published_at || post.created_at),
      });
    });
  });

  // Unrouted posts: a centre cluster, clearly separate from the routes.
  if (unrouted.length > 0) {
    routes.push({ slug: '_latest', name: 'Latest', shape: 'circle', x: cx, y: cy, count: unrouted.length });
    unrouted.forEach((post, j) => {
      const a = (j / Math.max(1, unrouted.length)) * Math.PI * 2 - Math.PI / 2;
      const r = Math.min(70, 30 + unrouted.length * 6);
      nodes.push({
        slug: post.slug,
        title: post.title,
        routeSlug: '_latest',
        routeName: 'Latest',
        shape: 'circle',
        x: Math.round((cx + Math.cos(a) * r) * 100) / 100,
        y: Math.round((cy + Math.sin(a) * r) * 100) / 100,
        readMinutes: readMinutes(post.content),
        date: formatDate(post.published_at || post.created_at),
      });
    });
  }

  // ── Edges: shared tags ────────────────────────────────────────────────
  const byslug = new Map(posts.map((p) => [p.slug, p]));
  const candidates: { from: string; to: string; shared: string[] }[] = [];

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = byslug.get(nodes[i].slug);
      const b = byslug.get(nodes[j].slug);
      if (!a || !b) continue;
      const tagsA = new Set((a.tags ?? []).map((t) => t.toLowerCase()));
      const shared = (b.tags ?? []).map((t) => t.toLowerCase()).filter((t) => tagsA.has(t));
      // 2+ shared tags is the density guard: single-tag pairs turn this into a
      // hairball the moment the corpus grows.
      if (shared.length >= MIN_SHARED_TAGS) {
        candidates.push({ from: nodes[i].slug, to: nodes[j].slug, shared });
      }
    }
  }

  // Cap edges per node, strongest (most shared tags) first, so no node becomes
  // a hub with 30 lines through it.
  candidates.sort((x, y) => y.shared.length - x.shared.length);
  const degree = new Map<string, number>();
  const kept: typeof candidates = [];
  for (const c of candidates) {
    const d1 = degree.get(c.from) ?? 0;
    const d2 = degree.get(c.to) ?? 0;
    if (d1 >= MAX_EDGES_PER_NODE || d2 >= MAX_EDGES_PER_NODE) continue;
    degree.set(c.from, d1 + 1);
    degree.set(c.to, d2 + 1);
    kept.push(c);
  }

  const pos = new Map(nodes.map((n) => [n.slug, n]));
  const edges: GraphEdge[] = kept.map((c) => ({
    from: c.from,
    to: c.to,
    x1: pos.get(c.from)!.x,
    y1: pos.get(c.from)!.y,
    x2: pos.get(c.to)!.x,
    y2: pos.get(c.to)!.y,
    sharedTags: c.shared,
  }));

  return { nodes, edges, routes };
}
