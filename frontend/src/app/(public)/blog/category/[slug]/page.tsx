
/* eslint-disable @next/next/no-html-link-for-pages, @typescript-eslint/no-explicit-any */
import { Metadata } from 'next';
import Link from 'next/link';
import { api } from '@/lib/api';
import PostCard from '@/components/blog/PostCard';

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const name = slug.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  return {
    title: `${name} | Styxproxy Blog`,
    description: `Browse all posts in the ${name} category on the Styxproxy blog.`,
    alternates: { canonical: `https://styxproxy.com/blog/category/${slug}` },
    openGraph: {
      title: `${name} | Styxproxy Blog`,
      description: `Browse all posts in the ${name} category on the Styxproxy blog.`,
      type: 'website',
      siteName: 'Styxproxy',
    },
  };
}

export default async function CategoryPage({ params }: Props) {
  const { slug } = await params;
  const name = slug.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

  let posts: any[] = [];
  let hasMore = false;

  try {
    const result = await api.getBlogPosts(1, 9, undefined, slug);
    if (result.data) {
      posts = result.data.posts;
      hasMore = result.data.pagination.has_next;
    }
  } catch {
    posts = [];
  }

  // P0-6: no DEMO_POSTS fallback. If api returns no posts for this
  // category, we render the empty state rather than silently showing
  // fake content.

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
          <nav className="flex items-center justify-center gap-2 text-sm text-[var(--muted)] mb-6">
            <Link href="/blog" className="hover:text-[var(--primary)] transition-colors">
              Blog
            </Link>
            <span>/</span>
            <span className="text-[var(--foreground)]">{name}</span>
          </nav>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-4">
            {name}
          </h1>
          <p className="text-lg text-[var(--muted)]">
            {posts.length > 0 ? `${posts.length} post${posts.length !== 1 ? 's' : ''} in this category` : 'No posts yet'}
          </p>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="flex flex-col items-center gap-2 py-8">
        <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
        <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
      </div>

      {/* Posts Grid — 1-col mobile / 2-col desktop */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        <div className="section-divider-glow mb-12" />
        {posts.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
              {posts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
            {hasMore && (
              <p className="text-center text-[var(--muted)] text-sm mt-12">
                More posts in this category coming soon.
              </p>
            )}
          </>
        ) : (
          <div className="text-center py-20 text-[var(--muted)]">
            <p className="text-lg mb-4">No posts in this category yet.</p>
            <Link href="/blog" className="text-[var(--primary)] hover:underline">
              ← Back to all posts
            </Link>
          </div>
        )}
      </section>
    </>
  );
}
