/**
 * BlogIndex — the server-rendered blog archive.
 *
 * This is deliberately a SERVER component with no client JS. The blog is both
 * our SEO surface and a corpus Charon indexes, so the post list must exist as
 * real `<ul><li><a href>` markup in the initial HTML:
 *
 *   - Google crawls links, not React state. The previous index built its list
 *     in a client component from `useState`, so the posts were absent from the
 *     served HTML and the page indexed as empty.
 *   - With JS disabled or still loading, the reader still gets a full archive.
 *   - The graph (when it ships) becomes a presentation layer hydrating OVER
 *     this markup — it must never replace the links.
 *
 * Route grouping uses the live categories from /api/blog/categories. Route
 * colours come from the API (`color`), not from a hardcoded map: the backend is
 * the source of truth, so recolouring a route in the dashboard recolours the
 * index without a deploy.
 */

import Link from 'next/link';
import type { BlogCategory, BlogPost } from '@/types';

interface BlogIndexProps {
  posts: BlogPost[];
  categories: BlogCategory[];
}

function formatDate(value?: string): string {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' });
}

/** Reading time from the post body. ~200 wpm, floored at 1. */
function readMinutes(content?: string): number {
  if (!content) return 1;
  const words = content.trim().split(/\s+/).length;
  return Math.max(1, Math.round(words / 200));
}

export default function BlogIndex({ posts, categories }: BlogIndexProps) {
  // Group posts under their first category. A post with no category still gets
  // rendered under "Latest" rather than being dropped — an unrouted post must
  // never become an invisible one.
  const byRoute = new Map<string, BlogPost[]>();
  const unrouted: BlogPost[] = [];

  for (const post of posts) {
    const cat = post.categories?.[0];
    if (!cat) {
      unrouted.push(post);
      continue;
    }
    const list = byRoute.get(cat.slug) ?? [];
    list.push(post);
    byRoute.set(cat.slug, list);
  }

  // Keep the API's ordering of routes; only render routes that have posts.
  const routes = categories
    .map((c) => ({ category: c, posts: byRoute.get(c.slug) ?? [] }))
    .filter((r) => r.posts.length > 0);

  return (
    <div className="max-w-6xl mx-auto px-6 pb-24">
      {/* Route navigation — real links, crawlable, works without JS */}
      {categories.length > 0 && (
        <nav aria-label="Blog categories" className="mb-12">
          <ul className="flex flex-wrap items-center gap-2">
            <li>
              <span
                aria-current="page"
                className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-bold bg-[var(--primary)] text-black"
              >
                All posts
              </span>
            </li>
            {categories.map((cat) => (
              <li key={cat.slug}>
                <Link
                  href={`/blog/category/${cat.slug}`}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
                >
                  {cat.color && (
                    <span
                      aria-hidden="true"
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: cat.color }}
                    />
                  )}
                  {cat.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}

      {posts.length === 0 && (
        <p className="text-center py-20 text-[var(--muted)]">
          No posts published yet. Check back soon.
        </p>
      )}

      {routes.map(({ category, posts: routePosts }) => (
        <section key={category.slug} className="mb-16" aria-labelledby={`route-${category.slug}`}>
          <div className="flex items-baseline justify-between gap-4 mb-6">
            <h2
              id={`route-${category.slug}`}
              className="text-2xl sm:text-3xl font-black tracking-tight flex items-center gap-3"
            >
              {category.color && (
                <span
                  aria-hidden="true"
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: category.color }}
                />
              )}
              {category.name}
            </h2>
            <Link
              href={`/blog/category/${category.slug}`}
              className="text-xs font-medium text-[var(--primary-text)] hover:underline shrink-0"
            >
              View all →
            </Link>
          </div>

          {category.description && (
            <p className="text-sm text-[var(--muted)] mb-6 max-w-2xl">{category.description}</p>
          )}

          <ul className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {routePosts.map((post) => (
              <li key={post.id}>
                <article className="py-5 group">
                  <Link href={`/blog/${post.slug}`} className="block">
                    <h3 className="text-lg font-semibold text-[var(--foreground)] group-hover:text-[var(--primary-text)] transition-colors mb-1.5">
                      {post.title}
                    </h3>
                    {post.excerpt && (
                      <p className="text-sm text-[var(--muted)] leading-relaxed line-clamp-2 mb-2">
                        {post.excerpt}
                      </p>
                    )}
                    <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
                      <time dateTime={post.published_at || post.created_at}>
                        {formatDate(post.published_at || post.created_at)}
                      </time>
                      <span aria-hidden="true">·</span>
                      <span>{readMinutes(post.content)} min read</span>
                    </div>
                  </Link>
                </article>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {/* Unrouted posts must still be reachable — see note above. */}
      {unrouted.length > 0 && (
        <section className="mb-16" aria-labelledby="route-latest">
          <h2 id="route-latest" className="text-2xl sm:text-3xl font-black tracking-tight mb-6">
            Latest
          </h2>
          <ul className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {unrouted.map((post) => (
              <li key={post.id}>
                <article className="py-5 group">
                  <Link href={`/blog/${post.slug}`} className="block">
                    <h3 className="text-lg font-semibold text-[var(--foreground)] group-hover:text-[var(--primary-text)] transition-colors mb-1.5">
                      {post.title}
                    </h3>
                    {post.excerpt && (
                      <p className="text-sm text-[var(--muted)] leading-relaxed line-clamp-2 mb-2">
                        {post.excerpt}
                      </p>
                    )}
                    <time
                      dateTime={post.published_at || post.created_at}
                      className="text-xs text-[var(--muted)]"
                    >
                      {formatDate(post.published_at || post.created_at)}
                    </time>
                  </Link>
                </article>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
