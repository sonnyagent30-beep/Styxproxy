import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { DEMO_POSTS } from '@/data/blog-posts';
import BlogCard from '@/components/blog/BlogCard';
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

  const [featured, ...rest] = filtered;

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-2">
        <div className="flex items-center gap-2 text-sm text-[var(--muted)] mb-1">
          <a href="/blog" className="hover:text-[var(--accent)] transition-colors">Blog</a>
          <span>/</span>
          <span className="text-[var(--foreground)]">#{decoded}</span>
        </div>
        <h1 className="text-3xl font-bold text-[var(--foreground)]">
          <span className="text-[var(--accent)]">#</span>{decoded}
        </h1>
        <p className="text-[var(--muted)] mt-1">
          {filtered.length} {filtered.length === 1 ? 'post' : 'posts'}
        </p>
      </div>

      {/* Tag filter bar */}
      <div className="mb-8">
        <TagFilter tags={tags} activeTag={decoded} />
      </div>

      {/* Featured post */}
      <div className="mb-10">
        <BlogCard post={featured} featured />
      </div>

      {/* Post list */}
      <div className="space-y-1">
        {rest.map((post) => (
          <BlogCard key={post.id} post={post} />
        ))}
      </div>
    </main>
  );
}
