import { Metadata } from 'next';
import Link from 'next/link';
import { api } from '@/lib/api';
import BlogIndex from '@/components/blog/BlogIndex';
import BlogGraph from '@/components/blog/BlogGraph';
import BlogViews from '@/components/blog/BlogViews';
import type { BlogCategory, BlogPost } from '@/types';

export const metadata: Metadata = {
  title: 'Blog | Styxproxy',
  description: 'Notes on proxies, automation, anonymity, and building infrastructure that works.',
  openGraph: {
    title: 'Blog',
    description: 'Notes on proxies, automation, anonymity, and building infrastructure that works.',
    type: 'website',
    siteName: 'Styxproxy',
    url: 'https://styxproxy.com/blog',
    images: [{ url: '/og-image.png', width: 1200, height: 630, alt: 'Styxproxy Blog' }],
  },
  alternates: { canonical: 'https://styxproxy.com/blog' },
};

/**
 * Fetch every published post for the index.
 *
 * limit=50 is the backend's documented maximum (`blog.py`, `le=50`). This used
 * to request 100 for the tag row, which the API rejected with a 422 on every
 * load — the failure was swallowed and the page rendered an empty archive.
 * The backend is authoritative on its own cap; never ask for more than it
 * advertises.
 */
async function getPosts(): Promise<{ posts: BlogPost[]; hasNext: boolean }> {
  try {
    const result = await api.getBlogPosts(1, 50);
    if (result.data) {
      return { posts: result.data.posts, hasNext: result.data.pagination.has_next };
    }
    return { posts: [], hasNext: false };
  } catch (err) {
    console.error('getPosts error:', err);
    return { posts: [], hasNext: false };
  }
}

async function getCategories(): Promise<BlogCategory[]> {
  try {
    const result = await api.getBlogCategories();
    return result.data?.categories ?? [];
  } catch (err) {
    console.error('getCategories error:', err);
    return [];
  }
}

export const dynamic = 'force-dynamic';

export default async function BlogPage() {
  const [{ posts, hasNext }, categories] = await Promise.all([getPosts(), getCategories()]);

  return (
    <>
      {/* Hero Section */}
      <div className="relative overflow-hidden pt-12 pb-16 px-6">
        <div className="absolute inset-0 hero-bg-grid" aria-hidden="true" />
        <div className="absolute inset-0 hero-bg-rings" aria-hidden="true" />
        <div className="absolute inset-0 hero-bg-vignette" aria-hidden="true" />
        <div className="hero-orb hero-orb-1" aria-hidden="true" />
        <div className="hero-orb hero-orb-2" aria-hidden="true" />
        <div className="hero-orb hero-orb-3" aria-hidden="true" />

        <div className="relative text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-6 mx-auto">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
            <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">
              The Styxproxy Blog
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-6">
            Notes from the{' '}
            <br />
            <span className="text-[var(--primary-text)]">trenches.</span>
          </h1>
          <p className="text-lg max-w-xl mx-auto leading-relaxed text-[var(--muted)]">
            Guides on proxies, anonymity, automation, and the infrastructure that keeps the web
            working.
          </p>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="flex flex-col items-center gap-2 py-8">
        <span className="text-xs tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">
          Scroll
        </span>
        <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
      </div>

      <div className="max-w-6xl mx-auto px-6">
        <div className="section-divider-glow mb-12" />
      </div>

      {/* The list is SERVER-rendered and stays in the DOM; the graph hydrates
          on top of it as a presentation layer. See BlogViews. */}
      <BlogViews
        list={<BlogIndex posts={posts} categories={categories} />}
        graph={<BlogGraph posts={posts} categories={categories} />}
      />

      {hasNext && (
        <div className="max-w-6xl mx-auto px-6 pb-24 text-center">
          <Link
            href="/blog?page=2"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm font-medium text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
          >
            More posts
          </Link>
        </div>
      )}
    </>
  );
}
