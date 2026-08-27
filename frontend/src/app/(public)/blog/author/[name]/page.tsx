import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { api } from '@/lib/api';
import PostCard from '@/components/blog/PostCard';

interface Props {
  params: Promise<{ name: string }>;
}

const POST_AUTHOR = 'Styxproxy Team';

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { name } = await params;
  const decoded = decodeURIComponent(name);
  return {
    title: `${decoded} | Styxproxy Blog`,
    description: `Posts by ${decoded} on the Styxproxy blog.`,
    openGraph: {
      title: `${decoded} | Styxproxy Blog`,
      description: `Posts by ${decoded} on the Styxproxy blog.`,
      type: 'profile',
      siteName: 'Styxproxy',
    },
  };
}

export default async function AuthorPage({ params }: Props) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);

  // Fetch posts - filter by author on client side since API doesn't have author filter
  const result = await api.getBlogPosts(1, 50);
  const allPosts = result.data?.posts || [];
  
  // Filter by author
  const posts = allPosts
    .filter((post) => post.author === decoded)
    .sort(
      (a, b) =>
        new Date(b.published_at || b.created_at).getTime() -
        new Date(a.published_at || a.created_at).getTime()
    );

  if (!posts.length) notFound();

  // Get top tags from author's posts
  const tagCounts: Record<string, number> = {};
  posts.forEach((p) => (p.tags || []).forEach((t) => (tagCounts[t] = (tagCounts[t] || 0) + 1)));
  const topTags = Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([t]) => t);

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
          <div className="w-20 h-20 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-black text-2xl mx-auto mb-6">
            S
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-4 text-[var(--foreground)]">
            Styxproxy Team
          </h1>
          <p className="text-lg text-[var(--muted)]">
            {posts.length} {posts.length === 1 ? 'post' : 'posts'}
          </p>
          {topTags.length > 0 && (
            <div className="flex flex-wrap justify-center gap-2 mt-6">
              {topTags.map((tag) => (
                <a
                  key={tag}
                  href={`/blog/tag/${encodeURIComponent(tag)}`}
                  className="px-3.5 py-1.5 rounded-full text-xs font-medium bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
                >
                  #{tag}
                </a>
              ))}
            </div>
          )}
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
      </section>
    </>
  );
}
