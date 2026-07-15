import { Metadata } from 'next';
import { DEMO_POSTS } from '@/data/blog-posts';
import PostRow from '@/components/blog/PostRow';
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
  
  // Sort by date - newest first
  const sortedPosts = [...allPosts].sort(
    (a, b) => new Date(b.published_at || b.created_at).getTime() -
              new Date(a.published_at || a.created_at).getTime()
  );

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-4xl sm:text-5xl font-bold text-[#f5f5f5] mb-3 tracking-tight" style={{ letterSpacing: '-0.03em' }}>
          Blog
        </h1>
        <p className="text-base text-[var(--muted)] max-w-2xl">
          Insights, tutorials, and guides on proxies, automation, and staying anonymous online. Built for developers and businesses in Africa.
        </p>
      </div>

      {/* Tag filter bar - horizontal scrollable */}
      <div className="mb-12">
        <TagFilter tags={tags} />
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

      {/* Empty state */}
      {allPosts.length === 0 && (
        <div className="text-center py-16">
          <p className="text-[var(--muted)]">No blog posts yet. Check back soon!</p>
        </div>
      )}
    </main>
  );
}
