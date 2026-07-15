import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { DEMO_POSTS, getPostsByAuthor } from '@/data/blog-posts';
import PostRow from '@/components/blog/PostRow';

interface Props {
  params: Promise<{ name: string }>;
}

export async function generateStaticParams() {
  const authors = Array.from(new Set(DEMO_POSTS.map((p) => p.author)));
  return authors.map((name) => ({ name: encodeURIComponent(name) }));
}

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

  const posts = [...getPostsByAuthor(decoded)].sort(
    (a, b) =>
      new Date(b.published_at || b.created_at).getTime() -
      new Date(a.published_at || a.created_at).getTime()
  );

  if (!posts.length) notFound();

  const tagCounts: Record<string, number> = {};
  posts.forEach((p) => (p.tags || []).forEach((t) => (tagCounts[t] = (tagCounts[t] || 0) + 1)));
  const topTags = Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([t]) => t);

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
      {/* Header card */}
      <header className="mb-12 pb-10 border-b border-[var(--border)]">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold text-2xl sm:text-3xl flex-shrink-0">
            {decoded.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <h1
              className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-[-0.03em] leading-[1.05] mb-2"
              style={{ textWrap: 'balance' }}
            >
              {decoded}
            </h1>
            <p className="text-base text-[var(--muted)] mb-4">
              {posts.length} {posts.length === 1 ? 'post' : 'posts'}
            </p>
            {topTags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {topTags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 rounded-full text-xs font-medium bg-[var(--surface)] border border-[var(--border)] text-[var(--muted)]"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Posts */}
      <div>
        {posts.map((post, idx) => (
          <PostRow
            key={post.id}
            post={post}
            variant={idx === 0 ? 'feature' : 'standard'}
            imagePosition={idx % 2 === 0 ? 'left' : 'right'}
          />
        ))}
        <div className="border-t border-[var(--border)]" />
      </div>
    </main>
  );
}
