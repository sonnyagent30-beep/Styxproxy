import { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { api } from '@/lib/api';
import PostCard from '@/components/blog/PostCard';

interface Props {
  params: Promise<{ tag: string }>;
  searchParams: Promise<{ tag?: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { tag } = await params;
  const decoded = decodeURIComponent(tag);
  return {
    title: `#${decoded} | Styxproxy Blog`,
    description: `Styxproxy blog posts tagged with #${decoded}.`,
    openGraph: {
      title: `#${decoded} | Styxproxy Blog`,
      description: `Styxproxy blog posts tagged with #${decoded}.`,
      type: 'website',
      siteName: 'Styxproxy',
    },
  };
}

export default async function TagPage({ params }: Props) {
  const { tag } = await params;
  const decoded = decodeURIComponent(tag);

  // Fetch posts with tag filter
  const result = await api.getBlogPosts(1, 50, decoded);
  const posts = (result.data?.posts || [])
    .sort(
      (a, b) =>
        new Date(b.published_at || b.created_at).getTime() -
        new Date(a.published_at || a.created_at).getTime()
    );

  if (!posts.length) notFound();

  // Get related tags from filtered posts
  const relatedTags = Array.from(
    new Set(
      posts.flatMap((p) => p.tags || []).filter((t) => t !== decoded)
    )
  ).slice(0, 8);

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
            <span className="text-[var(--foreground)]">#{decoded}</span>
          </nav>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-4">
            <span className="text-[var(--primary)]">#</span>{decoded}
          </h1>
          <p className="text-lg text-[var(--muted)]">
            {posts.length} {posts.length === 1 ? 'post' : 'posts'}
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>

        {/* Related tags */}
        {relatedTags.length > 0 && (
          <section className="mt-16 pt-10 border-t border-[var(--border)]">
            <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider mb-4">
              Related topics
            </p>
            <div className="flex flex-wrap gap-2">
              {relatedTags.map((t) => (
                <Link
                  key={t}
                  href={`/blog/tag/${encodeURIComponent(t)}`}
                  className="px-3.5 py-1.5 rounded-full text-xs font-medium bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
                >
                  #{t}
                </Link>
              ))}
            </div>
          </section>
        )}
      </section>
    </>
  );
}
