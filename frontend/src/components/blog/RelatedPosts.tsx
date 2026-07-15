import PostRow from './PostRow';
import type { BlogPost } from '@/types';

interface Props {
  posts: BlogPost[];
  excludeSlug?: string;
  excludeIds?: string[];
  title?: string;
  emptyMessage?: string;
}

export default function RelatedPosts({
  posts,
  excludeSlug,
  excludeIds = [],
  title = 'You might also like',
  emptyMessage,
}: Props) {
  const filtered = posts.filter(
    (p) => p.slug !== excludeSlug && !excludeIds.includes(p.id)
  );

  if (!filtered.length) {
    if (emptyMessage) {
      return (
        <div className="mt-16 pt-10 border-t border-[var(--border)]">
          <h3 className="text-lg font-bold text-[var(--foreground)] mb-4">{title}</h3>
          <p className="text-sm text-[var(--muted)]">{emptyMessage}</p>
        </div>
      );
    }
    return null;
  }

  return (
    <section className="mt-16 pt-10 border-t border-[var(--border)]">
      <div className="flex items-end justify-between mb-6">
        <h3 className="text-xl font-bold text-[var(--foreground)] tracking-[-0.02em]">
          {title}
        </h3>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
        {filtered.slice(0, 3).map((post) => (
          <PostRow key={post.id} post={post} variant="compact" />
        ))}
      </div>
    </section>
  );
}
