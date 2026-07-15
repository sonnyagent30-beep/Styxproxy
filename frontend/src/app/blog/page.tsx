import { Metadata } from 'next';
import {
  DEMO_POSTS,
  getAllTags,
  getPostsByAuthor,
} from '@/data/blog-posts';
import PostRow from '@/components/blog/PostRow';
import TagFilter from '@/components/blog/TagFilter';

export const metadata: Metadata = {
  title: 'Blog | Styxproxy',
  description: 'Notes on proxies, automation, anonymity, and building infrastructure that works.',
  openGraph: {
    title: 'Blog | Styxproxy',
    description: 'Notes on proxies, automation, anonymity, and building infrastructure that works.',
    type: 'website',
    siteName: 'Styxproxy',
  },
};

export default function BlogPage() {
  const allPosts = [...DEMO_POSTS].sort(
    (a, b) =>
      new Date(b.published_at || b.created_at).getTime() -
      new Date(a.published_at || a.created_at).getTime()
  );
  const tags = getAllTags();
  const [hero, ...rest] = allPosts;
  const author = 'Oyebiyi Ayomide';
  const authorPosts = getPostsByAuthor(author, hero?.slug);

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
      {/* Header */}
      <header className="mb-10">
        <h1
          className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-[-0.03em] leading-[1.05] mb-3"
          style={{ textWrap: 'balance' }}
        >
          Blog
        </h1>
        <p className="text-base sm:text-lg text-[var(--muted)] max-w-2xl leading-relaxed">
          Notes on proxies, anonymity, and the infrastructure that keeps the web working.
        </p>
      </header>

      {/* Search + tag filter */}
      <div className="mb-10">
        <TagFilter tags={tags} />
      </div>

      {/* Hero post — latest */}
      <div className="mb-12">
        <PostRow post={hero} variant="hero" />
      </div>

      {/* Latest posts — masonry with varied variants */}
      <section className="mb-12">
        <h2 className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider mb-4">
          Latest posts
        </h2>
        <div>
          {rest.map((post, idx) => (
            <PostRow
              key={post.id}
              post={post}
              variant={idx === 0 ? 'feature' : 'standard'}
              imagePosition={idx % 2 === 0 ? 'left' : 'right'}
            />
          ))}
          <div className="border-t border-[var(--border)]" />
        </div>
      </section>

      {/* More from author */}
      {authorPosts.length > 0 && (
        <section className="mt-16 pt-10 border-t border-[var(--border)]">
          <div className="flex items-end justify-between mb-6">
            <div>
              <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider mb-2">
                More from {author}
              </p>
              <h3 className="text-xl font-bold text-[var(--foreground)] tracking-[-0.02em]">
                Recent from the author
              </h3>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
            {authorPosts.slice(0, 4).map((post) => (
              <PostRow key={post.id} post={post} variant="compact" />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
