import { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import {
  DEMO_POSTS,
  getAllTags,
  getPostsByTag,
} from '@/data/blog-posts';
import PostRow from '@/components/blog/PostRow';
import TagFilter from '@/components/blog/TagFilter';
import type { BlogPost } from '@/types';

interface Props {
  params: Promise<{ tag: string }>;
}

export async function generateStaticParams() {
  return getAllTags().map((tag) => ({ tag: encodeURIComponent(tag) }));
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

  const allPosts = [...DEMO_POSTS].sort(
    (a, b) =>
      new Date(b.published_at || b.created_at).getTime() -
      new Date(a.published_at || a.created_at).getTime()
  );
  const filtered = getPostsByTag(decoded).sort(
    (a, b) =>
      new Date(b.published_at || b.created_at).getTime() -
      new Date(a.published_at || a.created_at).getTime()
  );
  const allTags = getAllTags();
  // Related tags = tags that co-occur with current tag, sorted by frequency
  const relatedTags = Array.from(
    new Set(
      filtered.flatMap((p) => p.tags || []).filter((t) => t !== decoded)
    )
  ).slice(0, 8);

  if (!filtered.length) notFound();

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
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
          {filtered.length} {filtered.length === 1 ? 'post' : 'posts'}
        </p>
      </header>

      {/* Search + tag filter */}
      <div className="mb-8">
        <TagFilter tags={allTags} activeTag={decoded} />
      </div>

      {/* Posts — alternating */}
      <div>
        {filtered.map((post, idx) => (
          <PostRow
            key={post.id}
            post={post}
            variant={idx === 0 ? 'feature' : 'standard'}
            imagePosition={idx % 2 === 0 ? 'left' : 'right'}
          />
        ))}
        <div className="border-t border-[var(--border)]" />
      </div>

      {/* Related tags — cross-link to other tags */}
      {relatedTags.length > 0 && (
        <section className="mt-16 pt-10 border-t border-[var(--border)]">
          <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider mb-4">
            Related topics
          </p>
          <div className="flex flex-wrap gap-2">
            {relatedTags.map((tag) => (
              <Link
                key={tag}
                href={`/blog/tag/${encodeURIComponent(tag)}`}
                className="px-3 py-1.5 rounded-full text-xs font-medium bg-[var(--surface)] border border-[var(--border)] text-[var(--muted)] hover:text-white hover:border-[var(--primary)]/60 transition-colors"
              >
                #{tag}
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
