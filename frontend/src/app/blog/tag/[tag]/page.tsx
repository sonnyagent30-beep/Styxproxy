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
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-[var(--muted)] mb-6">
        <Link href="/blog" className="hover:text-[var(--primary)] transition-colors">
          Blog
        </Link>
        <span>/</span>
        <span className="text-white">#{decoded}</span>
      </nav>

      {/* Header */}
      <header className="mb-10">
        <h1
          className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-[-0.03em] leading-[1.05] mb-2"
          style={{ textWrap: 'balance' }}
        >
          <span className="text-[var(--primary)]">#</span>
          <span className="text-white">{decoded}</span>
        </h1>
        <p className="text-base text-[var(--muted)]">
          {posts.length} {posts.length === 1 ? 'post' : 'posts'}
        </p>
      </header>

      {/* Posts Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>

      {/* Related tags — cross-link to other tags */}
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
                className="px-3 py-1.5 rounded-full text-xs font-medium bg-[var(--surface)] border border-[var(--border)] text-[var(--muted)] hover:text-white hover:border-[var(--primary)]/60 transition-colors"
              >
                #{t}
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
