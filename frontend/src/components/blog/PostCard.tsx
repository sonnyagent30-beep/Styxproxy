'use client';

import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';

interface PostCardProps {
  post: BlogPost;
}

/**
 * Instagram-style post card.
 * - Square cover image (1:1 on mobile, 4:5 on larger screens)
 * - Author header (avatar + username + follow date)
 * - Action row (like / comment / share icons — visual only, count from post)
 * - Caption area: title + excerpt + tags
 * - Engagement meta (view count, read time)
 *
 * Hovering reveals a soft overlay (like Instagram's "double-tap to like" hint).
 * Cards are full-width on mobile, 2-up on tablet, 2-up on desktop (NOT 3-up —
 * Instagram-style feed feels right at 1-2 columns, never 3).
 */
export default function PostCard({ post }: PostCardProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const estimateReadTime = (content: string): number => {
    const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
    return Math.max(1, Math.ceil(words / 200));
  };

  const readTime = estimateReadTime(post.content || post.excerpt || '');
  const initial = (post.author?.charAt(0) || 'S').toUpperCase();

  return (
    <article
      className="group bg-[var(--surface)] border border-[var(--border)] rounded-2xl overflow-hidden hover:border-[var(--primary)]/50 transition-all duration-300"
      data-testid="post-card"
    >
      {/* Author header */}
      <header className="flex items-center justify-between px-4 py-3">
        <Link
          href={`/blog/author/${encodeURIComponent(post.author)}`}
          className="flex items-center gap-3 min-w-0"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] flex items-center justify-center text-black text-sm font-bold flex-shrink-0 ring-2 ring-[var(--primary)]/20">
            {initial}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[var(--foreground)] truncate">
              {post.author}
            </p>
            <p className="text-xs text-[var(--muted)]">
              {formatDate(post.published_at || post.created_at)} · {readTime} min read
            </p>
          </div>
        </Link>
        <span className="text-xs text-[var(--muted)] uppercase tracking-wider font-medium">
          {post.featured ? 'Featured' : 'Post'}
        </span>
      </header>

      {/* Cover image — Instagram uses 1:1 here, we use 4:5 for editorial feel */}
      {post.cover_image_url ? (
        <Link
          href={`/blog/${post.slug}`}
          className="block relative aspect-[4/5] sm:aspect-[4/5] overflow-hidden bg-[var(--card)]"
          aria-label={post.title}
        >
          <Image
            src={post.cover_image_url}
            alt={post.title}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 600px"
            className="object-cover group-hover:scale-[1.02] transition-transform duration-700"
          />
          {/* Soft gradient at bottom for caption overlay on hover */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        </Link>
      ) : (
        <Link
          href={`/blog/${post.slug}`}
          className="block aspect-[4/5] bg-gradient-to-br from-[var(--card)] to-[var(--surface)]"
        />
      )}

      {/* Action row — Instagram-style icons (visual; actions wired to engagement) */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border)]">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
            </svg>
            <span className="text-xs font-medium tabular-nums">{post.view_count ?? 0}</span>
          </span>
          <span className="flex items-center gap-1.5 text-[var(--muted)]">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 0 1-.923 1.785A5.969 5.969 0 0 0 6 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337Z" />
            </svg>
          </span>
          <span className="flex items-center gap-1.5 text-[var(--muted)]">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
            </svg>
          </span>
        </div>
        <span className="text-xs text-[var(--muted)]">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z" />
          </svg>
        </span>
      </div>

      {/* Caption — title + excerpt + tags */}
      <Link href={`/blog/${post.slug}`} className="block px-4 pb-4">
        <h2 className="text-base sm:text-lg font-bold text-[var(--foreground)] tracking-[-0.01em] leading-snug mb-2 line-clamp-2 group-hover:text-[var(--primary)] transition-colors">
          {post.title}
        </h2>
        <p className="text-sm text-[var(--muted)] leading-relaxed mb-3 line-clamp-3">
          {post.excerpt}
        </p>
        {post.tags && post.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {post.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="text-xs font-medium text-[var(--primary)]/80"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </Link>
    </article>
  );
}
