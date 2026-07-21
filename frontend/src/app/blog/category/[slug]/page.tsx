import { Metadata } from 'next';
import { api } from '@/lib/api';
import PostCard from '@/components/blog/PostCard';
import { DEMO_POSTS } from '@/data/blog-posts';

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

  // Fallback: filter demo posts by tag matching slug
  if (posts.length === 0) {
    const filtered = [...DEMO_POSTS].filter((p) =>
      p.tags?.some((t) => t.toLowerCase().replace(/\s+/g, '-') === slug)
    );
    if (filtered.length > 0) posts = filtered;
  }

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
      <header className="mb-10">
        <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider mb-2">
          Category
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-[-0.03em] leading-[1.05] mb-3">
          {name}
        </h1>
        <p className="text-base text-[var(--muted)]">
          {posts.length > 0 ? `${posts.length} post${posts.length !== 1 ? 's' : ''} in this category` : 'No posts yet'}
        </p>
      </header>

      {posts.length > 0 ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
          {hasMore && (
            <p className="text-center text-[var(--muted)] text-sm">
              More posts in this category coming soon.
            </p>
          )}
        </>
      ) : (
        <div className="text-center py-20 text-[var(--muted)]">
          <p className="text-lg mb-4">No posts in this category yet.</p>
          <a href="/blog" className="text-[var(--primary)] hover:underline">
            ← Back to all posts
          </a>
        </div>
      )}
    </main>
  );
}
