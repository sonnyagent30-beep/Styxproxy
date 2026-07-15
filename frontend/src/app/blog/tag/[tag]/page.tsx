import { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { DEMO_POSTS } from '@/data/blog-posts';
import PostRow from '@/components/blog/PostRow';
import TagFilter from '@/components/blog/TagFilter';
import type { BlogPost } from '@/types';

interface Props {
  params: Promise<{ tag: string }>;
}

export async function generateStaticParams() {
  const tagSet = new Set<string>();
  DEMO_POSTS.forEach(p => p.tags?.forEach(t => tagSet.add(t)));
  return Array.from(tagSet).map((tag) => ({ tag: encodeURIComponent(tag) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { tag } = await params;
  const decoded = decodeURIComponent(tag);
  return {
    title: `#${decoded} | Styxproxy Blog`,
    description: `Browse all Styxproxy blog posts tagged with #${decoded}.`,
    openGraph: {
      title: `#${decoded} | Styxproxy Blog`,
      description: `Browse all Styxproxy blog posts tagged with #${decoded}.`,
      type: 'website',
      siteName: 'Styxproxy',
    },
  };
}

function getAllTags(posts: BlogPost[]): string[] {
  const tagSet = new Set<string>();
  posts.forEach(p => p.tags?.forEach(t => tagSet.add(t)));
  return Array.from(tagSet).sort();
}

export default async function TagPage({ params }: Props) {
  const { tag } = await params;
  const decoded = decodeURIComponent(tag);

  const allPosts = DEMO_POSTS;
  const filtered = allPosts.filter(p => p.tags?.includes(decoded));
  const tags = getAllTags(allPosts);

  if (!filtered.length) notFound();

  // Sort by date - newest first
  const sortedPosts = [...filtered].sort(
    (a, b) => new Date(b.published_at || b.created_at).getTime() -
              new Date(a.published_at || a.created_at).getTime()
  );

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
      {/* Header with back link */}
      <div className="mb-10">
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-sm text-[var(--muted)] hover:text-[var(--primary)] transition-colors mb-6"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Blog
        </Link>
        
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1 className="text-3xl sm:text-4xl font-bold text-[var(--primary)]" style={{ letterSpacing: '-0.03em' }}>
            #{decoded}
          </h1>
          <span className="text-[var(--muted)] text-sm">
            {filtered.length} {filtered.length === 1 ? 'post' : 'posts'}
          </span>
        </div>
      </div>

      {/* Tag filter bar */}
      <div className="mb-12">
        <TagFilter tags={tags} activeTag={decoded} />
      </div>

      {/* Featured post - full-width editorial row */}
      {sortedPosts.length > 0 && (
        <div className="mb-16">
          <PostRow post={sortedPosts[0]} featured imagePosition="left" />
        </div>
      )}

      {/* Post list - alternate image position for visual rhythm */}
      {sortedPosts.slice(1).map((post, index) => (
        <PostRow 
          key={post.id} 
          post={post} 
          imagePosition={index % 2 === 0 ? 'right' : 'left'} 
        />
      ))}
    </main>
  );
}
