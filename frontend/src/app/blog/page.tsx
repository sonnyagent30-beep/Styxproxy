import { Metadata } from 'next';
import { DEMO_POSTS } from '@/data/blog-posts';
import BlogCard from '@/components/blog/BlogCard';
import TagFilter from '@/components/blog/TagFilter';
import type { BlogPost } from '@/types';

export const metadata: Metadata = {
  title: 'Blog | Styxproxy',
  description: 'Latest news, tutorials, and insights about proxies, automation, and staying anonymous online.',
  openGraph: {
    title: 'Blog | Styxproxy',
    description: 'Latest news, tutorials, and insights about proxies, automation, and staying anonymous online.',
    type: 'website',
    siteName: 'Styxproxy',
  },
};

function getAllTags(posts: BlogPost[]): string[] {
  const tagSet = new Set<string>();
  posts.forEach(p => p.tags?.forEach(t => tagSet.add(t)));
  return Array.from(tagSet).sort();
}

export default function BlogPage() {
  const allPosts = DEMO_POSTS;
  const tags = getAllTags(allPosts);
  const [featured, ...rest] = allPosts;

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[var(--foreground)] mb-2">Blog</h1>
        <p className="text-[var(--muted)]">
          Latest news, tutorials, and insights about proxies, automation, and staying anonymous online.
        </p>
      </div>

      {/* Tag filter bar */}
      <div className="mb-8">
        <TagFilter tags={tags} />
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
